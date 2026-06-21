/*
  Faun CoreAudio (AudioQueue) backend — macOS

  上游 faun(codeberg.org/wickedsmoke/faun v0.2.3)只內建 Android(AAudio)、
  Linux(PulseAudio)、Windows(WASAPI)三個音訊後端,沒有 macOS。本檔為 Ultima IV
  繁中版補上 macOS 音訊輸出。

  設計(callback 拉取式,robust):
    - AudioQueue 的 callback(ca_callback)是唯一的「消費者」:每次播完一塊,就從內部
      PCM ring buffer 拉資料填滿、立即 re-enqueue。佇列因此「永不枯竭」→ 不會 underrun
      停掉、不會卡死。ring 沒料時補靜音(短暫無聲)而非停止。
    - faun 的 mixer 執行緒呼叫 sysaudio_write(),只把混音 PCM 推進 ring(非阻塞,滿了丟最舊)
      → 永不阻塞 → 不會回堵 faun 指令佇列 → 遊戲端不卡死。
    這取代了原本的「push + 空閒 buffer 號誌阻塞」模型:該模型在新版 macOS 會因 3 塊小 buffer
    一旦被生產端的瞬間延遲(場景切換等)掏空,硬體即停止回呼且不再恢復 → 表現為「開頭播一下
    就全靜音」或(無逾時保護時)整機卡死。callback 自我延續的拉取式可徹底避免。

  faun 系統 voice 固定 FAUN_F32 / 立體聲 / 44100;此檔由 faun.c 在 defined(__APPLE__) 時
  #include 進來,FaunVoice / FAUN_* / faun_channelCount 等型別在此可見。
*/

#include <AudioToolbox/AudioToolbox.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>

#define CA_NUM_BUFFERS  4       // callback 自我延續,4 塊已足夠平順

typedef struct {
    AudioQueueRef        queue;
    AudioQueueBufferRef  bufPool[CA_NUM_BUFFERS];
    UInt32               bufBytes;       // 每塊大小
    unsigned char*       ring;           // 內部 PCM ring(bytes)
    size_t               ringCap;        // ring 容量(bytes)
    size_t               rHead;          // 消費(callback)讀位置
    size_t               rTail;          // 生產(write)寫位置
    size_t               rUsed;          // 目前累積位元組
    pthread_mutex_t      lock;
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
    pthread_mutex_unlock(&s->lock);
    if (take < n)
        memset(dst + take, 0, n - take);    // 補靜音
}

// 把 n bytes 推進 ring;空間不足就丟最舊(advance head),確保 write 永不阻塞。
static void ring_push(CoreAudioSession* s, const unsigned char* src, size_t n)
{
    size_t freeSpace, first;
    pthread_mutex_lock(&s->lock);
    if (n > s->ringCap) { src += n - s->ringCap; n = s->ringCap; }
    freeSpace = s->ringCap - s->rUsed;
    if (n > freeSpace) {                     // 丟最舊以騰出空間
        size_t drop = n - freeSpace;
        s->rHead = (s->rHead + drop) % s->ringCap;
        s->rUsed -= drop;
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

    // 內部 ring:給足緩衝吸收生產端抖動(約 16 塊 ≈ 0.3s)。
    s->ringCap = (size_t) s->bufBytes * 16;
    s->ring = (unsigned char*) malloc(s->ringCap);
    if (! s->ring)
        return "CoreAudio ring alloc failed";
    s->rHead = s->rTail = s->rUsed = 0;
    pthread_mutex_init(&s->lock, NULL);

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
    if (s && s->queue) {
        AudioQueueStop(s->queue, true);
        AudioQueueDispose(s->queue, true);
        s->queue = NULL;
        if (s->ring) { free(s->ring); s->ring = NULL; }
        pthread_mutex_destroy(&s->lock);
        voice->backend = NULL;
    }
}

// 非阻塞:把混音 PCM 推進 ring。faun mixer 執行緒永不在此卡住。
static const char* sysaudio_write(FaunVoice* voice, const void* data,
                                  uint32_t len)
{
    CoreAudioSession* s = CAS;
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
