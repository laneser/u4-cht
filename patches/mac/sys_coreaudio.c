/*
  Faun CoreAudio (AudioQueue) backend — macOS

  上游 faun(codeberg.org/wickedsmoke/faun v0.2.3)只內建 Android(AAudio)、
  Linux(PulseAudio)、Windows(WASAPI)三個音訊後端,沒有 macOS。本檔為 Ultima IV
  繁中版補上 macOS 音訊輸出。

  設計(callback 拉取式 + 準時生產端 + back-pressure,robust):
    - AudioQueue 的 callback(ca_callback)是唯一的「消費者」:每次播完一塊,就從內部
      PCM ring buffer 拉資料填滿、立即 re-enqueue。佇列因此「永不枯竭」→ 不會 underrun
      停掉、不會卡死。ring 沒料時補靜音(短暫無聲)而非停止。
    - faun 的 mixer 執行緒呼叫 sysaudio_write() 把混音 PCM 推進 ring;ring 達目標水位
      (CA_HIGH_BUFFERS)即短暫阻塞生產端(cond_timedwait,callback 拉完料後 signal),
      把緩衝穩定停在 ~125ms,既不被抽乾(underrun)也不滿出(drop 最舊)。
    這取代了原本的「push + 空閒 buffer 號誌阻塞」模型:該模型在新版 macOS 會因 3 塊小 buffer
    一旦被生產端的瞬間延遲(場景切換等)掏空,硬體即停止回呼且不再恢復 → 表現為「開頭播一下
    就全靜音」或(無逾時保護時)整機卡死。callback 自我延續的拉取式可徹底避免。

  macOS「微頓」根因(實測 drops=0 / underruns=43 確認):
    生產端從未領先(drops=0)→ ring 永遠填不滿 → 一抖動就掏空(underruns)。原因是 faun mixer
    每輪固定產 44100/updateHz=918 frames(20.8ms),靠 dispatch_walltime 的 ~18ms 等待醒來,
    但 macOS 的 timer coalescing(尤以筆電省電時)會把該等待拖晚,使每輪產出 ≤ 實時、毫無餘裕。
    對應修法(Windows 是 timeBeginPeriod(1) 把計時器拉到 1ms;macOS 無此開關):
      (1) sysaudio_write 首次呼叫時把「mixer 執行緒」設為 QOS_CLASS_USER_INTERACTIVE,
          降低 coalescing、優先排程 → 準時醒 → 每輪的 +2.8ms 餘裕得以累積成緩衝。
      (2) back-pressure 把緩衝封頂在 CA_HIGH_BUFFERS,避免領先後又丟最舊。
    caDrops / caUnderruns 計數器保留,退出時印到 stderr 供驗證(理想:兩者皆 0)。

  faun 系統 voice 固定 FAUN_F32 / 立體聲 / 44100;此檔由 faun.c 在 defined(__APPLE__) 時
  #include 進來,FaunVoice / FAUN_* / faun_channelCount 等型別在此可見。
*/

#include <AudioToolbox/AudioToolbox.h>
#include <pthread.h>
#include <pthread/qos.h>
#include <errno.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CA_NUM_BUFFERS    4     // AudioQueue 在途輸出塊數(callback 自我延續,4 足夠)
#define CA_RING_BUFFERS   32    // ring 容量上限塊數(≈0.66s 天花板)
#define CA_HIGH_BUFFERS   6     // back-pressure 目標水位(≈125ms cushion):生產端到此就阻塞
#define CA_PUSH_TIMEOUT_MS 50   // 生產端阻塞上限:輸出疑似暫停/停滯時不卡死 mixer

// 診斷計數器:drops=ring 滿丟最舊;underruns=ring 空補靜音。退出時印出(理想皆 0)。
static unsigned long caDrops     = 0;
static unsigned long caUnderruns = 0;

typedef struct {
    AudioQueueRef        queue;
    AudioQueueBufferRef  bufPool[CA_NUM_BUFFERS];
    UInt32               bufBytes;       // 每塊大小
    unsigned char*       ring;           // 內部 PCM ring(bytes)
    size_t               ringCap;        // ring 容量(bytes)
    size_t               highWater;      // back-pressure 水位(bytes)
    size_t               rHead;          // 消費(callback)讀位置
    size_t               rTail;          // 生產(write)寫位置
    size_t               rUsed;          // 目前累積位元組
    pthread_mutex_t      lock;
    pthread_cond_t       spaceCond;      // callback 拉完料 → signal 喚醒被 back-pressure 擋住的生產端
}
CoreAudioSession;

static CoreAudioSession caSession;

// 從 ring 拉 n bytes 到 dst;不足部分補靜音(underrun → 無聲而非停機)。
static void ring_pull(CoreAudioSession* s, unsigned char* dst, size_t n)
{
    size_t take, first;
    pthread_mutex_lock(&s->lock);
    take = (s->rUsed < n) ? s->rUsed : n;
    first = s->ringCap - s->rHead;
    if (first > take) first = take;
    memcpy(dst, s->ring + s->rHead, first);
    if (take > first)
        memcpy(dst + first, s->ring, take - first);
    s->rHead = (s->rHead + take) % s->ringCap;
    s->rUsed -= take;
    pthread_cond_signal(&s->spaceCond);     // 騰出空間 → 喚醒被 back-pressure 擋住的生產端
    pthread_mutex_unlock(&s->lock);
    if (take < n) {
        memset(dst + take, 0, n - take);    // 補靜音
        caUnderruns++;                      // 記一次掏空
    }
}

// 把 n bytes 推進 ring。back-pressure:超過 highWater 就阻塞生產端(由 callback signal 喚醒),
// 把 mixer 壓回實時消費速率、緩衝穩定在 ~highWater。阻塞有逾時上限,輸出停滯時不卡死。
static void ring_push(CoreAudioSession* s, const unsigned char* src, size_t n)
{
    size_t freeSpace, first;
    pthread_mutex_lock(&s->lock);
    if (n > s->ringCap) { src += n - s->ringCap; n = s->ringCap; }

    // back-pressure:緩衝已達目標水位 → 等 callback 拉走資料再寫,避免領先後又丟最舊。
    while (s->rUsed + n > s->highWater) {
        struct timespec dl;
        clock_gettime(CLOCK_REALTIME, &dl);
        dl.tv_nsec += (long) CA_PUSH_TIMEOUT_MS * 1000000L;
        if (dl.tv_nsec >= 1000000000L) { dl.tv_nsec -= 1000000000L; dl.tv_sec++; }
        if (pthread_cond_timedwait(&s->spaceCond, &s->lock, &dl) == ETIMEDOUT)
            break;                           // 輸出疑似暫停/停滯,別卡住 mixer
    }

    freeSpace = s->ringCap - s->rUsed;
    if (n > freeSpace) {                     // 仍滿(逾時退出)→ 丟最舊保底,永不卡死
        size_t drop = n - freeSpace;
        s->rHead = (s->rHead + drop) % s->ringCap;
        s->rUsed -= drop;
        caDrops++;                           // 記一次丟最舊
    }
    first = s->ringCap - s->rTail;
    if (first > n) first = n;
    memcpy(s->ring + s->rTail, src, first);
    if (n > first)
        memcpy(s->ring, src + first, n - first);
    s->rTail = (s->rTail + n) % s->ringCap;
    s->rUsed += n;
    pthread_mutex_unlock(&s->lock);
}

// AudioQueue 播完一塊 → 從 ring 拉資料填滿並「立即 re-enqueue」,佇列永不枯竭。
static void ca_callback(void* userData, AudioQueueRef aq, AudioQueueBufferRef buf)
{
    CoreAudioSession* s = (CoreAudioSession*) userData;
    ring_pull(s, (unsigned char*) buf->mAudioData, s->bufBytes);
    buf->mAudioDataByteSize = s->bufBytes;
    AudioQueueEnqueueBuffer(aq, buf, 0, NULL);
}

static void sysaudio_close(void)
{
    // CoreAudio 無全域 context,no-op。
}

static const char* sysaudio_open(const char* appName)
{
    (void) appName;
    return NULL;
}

static const char* sysaudio_allocVoice(FaunVoice* voice, int updateHz,
                                       const char* appName)
{
    CoreAudioSession* s = &caSession;
    OSStatus err;
    int chan, bytesPerSample, i;
    AudioStreamBasicDescription fmt;

    (void) updateHz;
    (void) appName;
    memset(s, 0, sizeof(*s));

    chan = faun_channelCount(voice->mix.chanLayout);

    memset(&fmt, 0, sizeof(fmt));
    fmt.mSampleRate       = voice->mix.rate;
    fmt.mFormatID         = kAudioFormatLinearPCM;
    fmt.mChannelsPerFrame = chan;
    fmt.mFramesPerPacket  = 1;

    switch (voice->mix.format) {
        case FAUN_U8:
            fmt.mFormatFlags = kAudioFormatFlagIsPacked;
            fmt.mBitsPerChannel = 8;  bytesPerSample = 1; break;
        case FAUN_S16:
            fmt.mFormatFlags = kAudioFormatFlagIsSignedInteger |
                               kAudioFormatFlagIsPacked;
            fmt.mBitsPerChannel = 16; bytesPerSample = 2; break;
        case FAUN_S24:
            fmt.mFormatFlags = kAudioFormatFlagIsSignedInteger |
                               kAudioFormatFlagIsPacked;
            fmt.mBitsPerChannel = 24; bytesPerSample = 3; break;
        case FAUN_F32:
        default:
            fmt.mFormatFlags = kAudioFormatFlagIsFloat |
                               kAudioFormatFlagIsPacked;
            fmt.mBitsPerChannel = 32; bytesPerSample = 4; break;
    }
    fmt.mBytesPerFrame  = chan * bytesPerSample;
    fmt.mBytesPerPacket = fmt.mBytesPerFrame;

    err = AudioQueueNewOutput(&fmt, ca_callback, s, NULL, NULL, 0, &s->queue);
    if (err)
        return "AudioQueueNewOutput failed";

    s->bufBytes = voice->mix.avail * fmt.mBytesPerFrame;
    if (s->bufBytes < 4096)
        s->bufBytes = 4096;

    // 內部 ring:容量為上限(CA_RING_BUFFERS),back-pressure 目標水位 highWater
    // (CA_HIGH_BUFFERS)才是穩態緩衝量;water 必須 < 容量,讓逾時保底的丟最舊有餘地。
    s->ringCap   = (size_t) s->bufBytes * CA_RING_BUFFERS;
    s->highWater = (size_t) s->bufBytes * CA_HIGH_BUFFERS;
    s->ring = (unsigned char*) malloc(s->ringCap);
    if (! s->ring)
        return "CoreAudio ring alloc failed";
    s->rHead = s->rTail = s->rUsed = 0;
    pthread_mutex_init(&s->lock, NULL);
    pthread_cond_init(&s->spaceCond, NULL);

    // 預充靜音並 enqueue 全部 buffer,再啟動。之後由 ca_callback 自我延續。
    for (i = 0; i < CA_NUM_BUFFERS; ++i) {
        err = AudioQueueAllocateBuffer(s->queue, s->bufBytes, &s->bufPool[i]);
        if (err)
            return "AudioQueueAllocateBuffer failed";
        memset(s->bufPool[i]->mAudioData, 0, s->bufBytes);
        s->bufPool[i]->mAudioDataByteSize = s->bufBytes;
        AudioQueueEnqueueBuffer(s->queue, s->bufPool[i], 0, NULL);
    }
    AudioQueueSetParameter(s->queue, kAudioQueueParam_Volume, 1.0f);
    AudioQueueStart(s->queue, NULL);

    voice->backend = s;
    return NULL;
}

#define CAS  ((CoreAudioSession*) voice->backend)

static void sysaudio_freeVoice(FaunVoice* voice)
{
    CoreAudioSession* s = CAS;
    // 診斷計數器:預設靜音,U4CHT_AUDIO_DEBUG=1 才印(理想 drops=0 且 underruns=0)。
    if (getenv("U4CHT_AUDIO_DEBUG"))
        fprintf(stderr, "[CoreAudio] drops=%lu underruns=%lu (理想皆 0)\n",
                caDrops, caUnderruns);
    if (s && s->queue) {
        // 喚醒可能卡在 back-pressure 的生產端,避免它空等到逾時。
        pthread_mutex_lock(&s->lock);
        pthread_cond_broadcast(&s->spaceCond);
        pthread_mutex_unlock(&s->lock);
        AudioQueueStop(s->queue, true);
        AudioQueueDispose(s->queue, true);
        s->queue = NULL;
        if (s->ring) { free(s->ring); s->ring = NULL; }
        pthread_cond_destroy(&s->spaceCond);
        pthread_mutex_destroy(&s->lock);
        voice->backend = NULL;
    }
}

// 把混音 PCM 推進 ring(達水位時短暫阻塞,見 ring_push)。首次呼叫順便把「呼叫此函式的
// mixer 執行緒」設為高 QoS,降低 macOS timer coalescing 造成的晚醒 → 生產端準時、緩衝填得起來。
static const char* sysaudio_write(FaunVoice* voice, const void* data,
                                  uint32_t len)
{
    CoreAudioSession* s = CAS;
    static int qosSet = 0;
    if (! qosSet) {
        // 對照實驗開關:U4CHT_NO_QOS=1 時跳過 QoS,用來驗證「晚醒」是否為病因。
        if (! getenv("U4CHT_NO_QOS"))
            pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
        qosSet = 1;
    }
    ring_push(s, (const unsigned char*) data, len);
    return NULL;
}

static int sysaudio_startVoice(FaunVoice* voice)
{
    CoreAudioSession* s = CAS;
    AudioQueueStart(s->queue, NULL);
    return 1;
}

static int sysaudio_stopVoice(FaunVoice* voice)
{
    CoreAudioSession* s = CAS;
    AudioQueuePause(s->queue);
    return 1;
}
