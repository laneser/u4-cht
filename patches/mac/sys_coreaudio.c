/*
  Faun CoreAudio (AudioQueue) backend — macOS

  上游 faun 只內建 Android/Linux/Windows 音訊後端,沒有 macOS。本檔為 Ultima IV
  繁中版補上 macOS 音訊輸出。

  設計(callback 拉取式 + 有界背壓,robust 且平順):
    - AudioQueue 的 callback(ca_callback)是唯一消費者:播完一塊即從內部 PCM ring 拉
      資料填滿、立即 re-enqueue → 佇列永不枯竭(不會 underrun 停掉、不會卡死)。
    - faun mixer 執行緒呼叫 sysaudio_write() 把混音 PCM 推進 ring。為避免 mixer 與硬體
      時脈漂移(實測 faun 軟體計時器比硬體略慢 → ring 耗盡 → 斷斷續續),這裡做兩件事:
        (a) allocVoice 把 voice->updateHz 調高,讓 mixer 有能力「快過實時」地生產;
        (b) sysaudio_write 加「有界背壓」:ring 超過 highWater 就(限時)等 callback 取走
            → 把 mixer 節流到硬體消費速率。兩者合起來:ring 穩定維持在 highWater 附近的
            健康水位(足夠緩衝吸收抖動)→ 不再 underrun。背壓有逾時上限,佇列又永不死,
            故不會卡死。

  faun 系統 voice 固定 FAUN_F32 / 立體聲 / 44100;此檔由 faun.c 在 __APPLE__ 時 #include。
*/

#include <AudioToolbox/AudioToolbox.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>

#define CA_NUM_BUFFERS  4

typedef struct {
    AudioQueueRef        queue;
    AudioQueueBufferRef  bufPool[CA_NUM_BUFFERS];
    UInt32               bufBytes;
    unsigned char*       ring;
    size_t               ringCap;
    size_t               rHead;
    size_t               rTail;
    size_t               rUsed;
    size_t               cushion;        // pre-roll 門檻
    size_t               highWater;      // 背壓門檻
    int                  primed;
    pthread_mutex_t      lock;
    pthread_cond_t       drained;        // callback 取走後通知 writer
}
CoreAudioSession;

static CoreAudioSession caSession;

// 以下 *_locked 假設已持有 s->lock。
static void ring_pull_locked(CoreAudioSession* s, unsigned char* dst, size_t n)
{
    size_t take = (s->rUsed < n) ? s->rUsed : n;
    size_t first = s->ringCap - s->rHead;
    if (first > take) first = take;
    memcpy(dst, s->ring + s->rHead, first);
    if (take > first)
        memcpy(dst + first, s->ring, take - first);
    s->rHead = (s->rHead + take) % s->ringCap;
    s->rUsed -= take;
    if (take < n) memset(dst + take, 0, n - take);      // underrun → 補靜音
}

static void ring_push_locked(CoreAudioSession* s, const unsigned char* src, size_t n)
{
    size_t freeSpace, first;
    if (n > s->ringCap) { src += n - s->ringCap; n = s->ringCap; }
    freeSpace = s->ringCap - s->rUsed;
    if (n > freeSpace) {
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
}

static void ca_callback(void* userData, AudioQueueRef aq, AudioQueueBufferRef buf)
{
    CoreAudioSession* s = (CoreAudioSession*) userData;

    pthread_mutex_lock(&s->lock);
    if (! s->primed && s->rUsed >= s->cushion)
        s->primed = 1;
    if (s->primed)
        ring_pull_locked(s, (unsigned char*) buf->mAudioData, s->bufBytes);
    else
        memset(buf->mAudioData, 0, s->bufBytes);    // 預充期:靜音
    pthread_cond_signal(&s->drained);               // 通知 writer:已騰出空間
    pthread_mutex_unlock(&s->lock);

    buf->mAudioDataByteSize = s->bufBytes;
    AudioQueueEnqueueBuffer(aq, buf, 0, NULL);
}

static void sysaudio_close(void) {}

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

    // mixer 生產能力:把 updateHz 調高 → mixer 計時器更短 → 能快過實時生產,讓背壓得以
    // 把 ring 維持在健康水位(fades 為 per-frame,不受 updateHz 影響,安全)。
    voice->updateHz = 96;

    s->bufBytes = voice->mix.avail * fmt.mBytesPerFrame;
    if (s->bufBytes < 4096)
        s->bufBytes = 4096;

    s->ringCap   = (size_t) s->bufBytes * 16;
    s->cushion   = (size_t) s->bufBytes * 6;    // pre-roll ≈125ms
    s->highWater = (size_t) s->bufBytes * 8;    // 背壓水位 ≈166ms
    s->ring = (unsigned char*) malloc(s->ringCap);
    if (! s->ring)
        return "CoreAudio ring alloc failed";
    s->rHead = s->rTail = s->rUsed = 0;
    s->primed = 0;
    pthread_mutex_init(&s->lock, NULL);
    pthread_cond_init(&s->drained, NULL);

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
        pthread_cond_destroy(&s->drained);
        pthread_mutex_destroy(&s->lock);
        voice->backend = NULL;
    }
}

// 有界背壓:ring 滿到 highWater 就等 callback 取走(限時 50ms),把 mixer 節流到硬體速率。
static const char* sysaudio_write(FaunVoice* voice, const void* data, uint32_t len)
{
    CoreAudioSession* s = CAS;
    pthread_mutex_lock(&s->lock);
    while (s->rUsed > s->highWater) {
        struct timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        ts.tv_nsec += 50 * 1000000L;
        if (ts.tv_nsec >= 1000000000L) { ts.tv_sec++; ts.tv_nsec -= 1000000000L; }
        if (pthread_cond_timedwait(&s->drained, &s->lock, &ts) == ETIMEDOUT)
            break;      // 佇列疑似停滯 → 不無限等
    }
    ring_push_locked(s, (const unsigned char*) data, len);
    pthread_mutex_unlock(&s->lock);
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
