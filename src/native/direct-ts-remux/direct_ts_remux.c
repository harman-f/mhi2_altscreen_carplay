#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdint.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/dict.h>
#include <libavutil/error.h>
#include <libavutil/mem.h>
#include <libavutil/time.h>

#define TS_SIZE 188
#define MOST_BLOCK_PACKETS 64
#define MOST_BLOCK_BYTES (MOST_BLOCK_PACKETS * TS_SIZE)
#define REMUX_STATUS_PATH "/tmp/mibr-direct-remux.status"
#define PACE_QUEUE_CAP 10
#define M1AU_HEADER_BYTES 56
#define M1AU_MAX_PAYLOAD (3u * 1024u * 1024u)

typedef struct {
    int fd;
    int device_mode;
    uint8_t pending[MOST_BLOCK_BYTES];
    int pending_len;
    uint64_t packets;
    uint64_t blocks;
    uint64_t pad_packets;
    uint64_t input_h264_bytes;
    uint64_t write_attempts;
    uint64_t write_eagain;
    uint64_t write_timeouts;
    uint64_t write_errors;
    uint64_t short_writes;
    uint64_t over20ms_blocks;
    int64_t last_write_us;
    int64_t last_write_call_us;
    int64_t last_block_wait_us;
    int64_t max_block_wait_us;
    int64_t rate_prev_us;
    uint64_t rate_prev_input_bytes;
    uint64_t rate_prev_most_bytes;
    uint64_t input_bps;
    uint64_t most_bps;

    int pace_enabled;
    int pace_fps;
    int pace_buffer_target;
    int pace_queue_depth;
    int pace_queue_max;
    uint64_t pace_underflows;
    uint64_t pace_late_frames;
    uint64_t pace_backpressure_waits;
    int64_t last_input_interval_us;
    int64_t min_input_interval_us;
    int64_t max_input_interval_us;
    int64_t last_emit_interval_us;
    int64_t max_emit_jitter_us;
    int64_t last_emit_us;

    int input_framed;
    uint64_t m1au_records;
    uint64_t m1au_stream;
    uint64_t m1au_codec;
    uint64_t m1au_consumer;
    uint64_t m1au_sequence;
    uint32_t m1au_flags;
    uint32_t m1au_ts_word1_le;
    uint32_t m1au_ts_word2_le;
    int64_t m1au_ts_word1_delta;
    int64_t m1au_ts_word2_delta;
    uint8_t m1au_ts_raw[8];
    uint64_t m1au_sequence_gaps;
} OutCtx;

typedef struct {
    int fd;
    int64_t *deadline;
    size_t payload_remaining;
    pthread_mutex_t lock;
    uint64_t records;
    uint64_t stream,codec,consumer,sequence;
    uint64_t previous_sequence;
    uint64_t sequence_gaps;
    uint32_t flags;
    uint8_t ts_raw[8];
    uint32_t ts_word1_le,ts_word2_le;
    uint32_t prev_ts_word1_le,prev_ts_word2_le;
    int have_prev_ts;
    int64_t ts_word1_delta,ts_word2_delta;
} FramedInput;

typedef struct {
    AVPacket pkt;
    int64_t arrival_us;
} PacePacket;

typedef struct {
    pthread_mutex_t lock;
    pthread_cond_t cv;
    AVFormatContext *ic;
    int video;
    PacePacket q[PACE_QUEUE_CAP];
    int head;
    int count;
    int max_depth;
    int stop;
    int done;
    int reader_rc;
    uint64_t input_bytes;
    uint64_t backpressure_waits;
    int max_seen_depth;
    int64_t last_arrival_us;
    int64_t last_interval_us;
    int64_t min_interval_us;
    int64_t max_interval_us;
} PaceQueue;

static uint64_t g_status_seq;
static int64_t g_last_status_us;
static int g_status_error_logged;
static FramedInput *g_framed_status;
static int interrupt_cb(void *opaque);

static int env_int(const char *name,int defval) {
    const char *v=getenv(name);
    char *end=NULL;
    long n;
    if(!v||!*v) return defval;
    n=strtol(v,&end,10);
    if(end==v||*end!='\0') return defval;
    return (int)n;
}

static int64_t abs_i64(int64_t v) {
    return v<0?-v:v;
}

static uint16_t m1au_get_be16(const uint8_t *p) {
    return (uint16_t)(((uint16_t)p[0]<<8)|p[1]);
}

static uint32_t m1au_get_be32(const uint8_t *p) {
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
}

static uint64_t m1au_get_be64(const uint8_t *p) {
    uint64_t v=0;
    unsigned i;
    for(i=0;i<8u;++i)v=(v<<8)|p[i];
    return v;
}

static uint32_t m1au_get_le32(const uint8_t *p) {
    return ((uint32_t)p[0])|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}

static void framed_snapshot(OutCtx *o) {
    FramedInput *f=g_framed_status;
    if(!o||!f)return;
    pthread_mutex_lock(&f->lock);
    o->m1au_records=f->records;
    o->m1au_stream=f->stream;
    o->m1au_codec=f->codec;
    o->m1au_consumer=f->consumer;
    o->m1au_sequence=f->sequence;
    o->m1au_flags=f->flags;
    o->m1au_ts_word1_le=f->ts_word1_le;
    o->m1au_ts_word2_le=f->ts_word2_le;
    o->m1au_ts_word1_delta=f->ts_word1_delta;
    o->m1au_ts_word2_delta=f->ts_word2_delta;
    memcpy(o->m1au_ts_raw,f->ts_raw,8u);
    o->m1au_sequence_gaps=f->sequence_gaps;
    pthread_mutex_unlock(&f->lock);
}

static void pace_queue_snapshot_locked(PaceQueue *q,OutCtx *o) {
    if(!q||!o) return;
    o->input_h264_bytes=q->input_bytes;
    o->pace_queue_depth=q->count;
    o->pace_queue_max=q->max_seen_depth;
    o->pace_backpressure_waits=q->backpressure_waits;
    o->last_input_interval_us=q->last_interval_us;
    o->min_input_interval_us=q->min_interval_us;
    o->max_input_interval_us=q->max_interval_us;
}

static void pace_queue_init(PaceQueue *q,AVFormatContext *ic,int video,int max_depth) {
    int i;
    memset(q,0,sizeof(*q));
    pthread_mutex_init(&q->lock,NULL);
    pthread_cond_init(&q->cv,NULL);
    q->ic=ic;
    q->video=video;
    q->max_depth=max_depth;
    q->reader_rc=AVERROR_EOF;
    for(i=0;i<PACE_QUEUE_CAP;i++) memset(&q->q[i].pkt,0,sizeof(q->q[i].pkt));
}

static void pace_queue_stop(PaceQueue *q) {
    pthread_mutex_lock(&q->lock);
    q->stop=1;
    pthread_cond_broadcast(&q->cv);
    pthread_mutex_unlock(&q->lock);
}

static void pace_queue_destroy(PaceQueue *q) {
    int i;
    pthread_mutex_lock(&q->lock);
    for(i=0;i<q->count;i++) {
        int idx=(q->head+i)%PACE_QUEUE_CAP;
        av_packet_unref(&q->q[idx].pkt);
    }
    q->count=0;
    pthread_mutex_unlock(&q->lock);
    pthread_cond_destroy(&q->cv);
    pthread_mutex_destroy(&q->lock);
}

static void *pace_reader_main(void *opaque) {
    PaceQueue *q=(PaceQueue *)opaque;
    int rc=0;

    for(;;) {
        AVPacket pkt;
        int64_t now;
        memset(&pkt,0,sizeof(pkt));
        rc=av_read_frame(q->ic,&pkt);
        if(rc<0) break;
        if(pkt.stream_index!=q->video) {
            av_packet_unref(&pkt);
            continue;
        }

        now=av_gettime_relative();
        pthread_mutex_lock(&q->lock);
        if(q->last_arrival_us>0) {
            int64_t dt=now-q->last_arrival_us;
            q->last_interval_us=dt;
            if(q->min_interval_us==0||dt<q->min_interval_us)q->min_interval_us=dt;
            if(dt>q->max_interval_us)q->max_interval_us=dt;
        }
        q->last_arrival_us=now;
        q->input_bytes+=(uint64_t)(pkt.size>0?pkt.size:0);

        while(!q->stop && q->count>=q->max_depth) {
            ++q->backpressure_waits;
            pthread_cond_wait(&q->cv,&q->lock);
        }
        if(q->stop) {
            pthread_mutex_unlock(&q->lock);
            av_packet_unref(&pkt);
            rc=AVERROR_EXIT;
            break;
        }

        {
            int idx=(q->head+q->count)%PACE_QUEUE_CAP;
            av_packet_move_ref(&q->q[idx].pkt,&pkt);
            q->q[idx].arrival_us=now;
            ++q->count;
            if(q->count>q->max_seen_depth)q->max_seen_depth=q->count;
        }
        pthread_cond_broadcast(&q->cv);
        pthread_mutex_unlock(&q->lock);
    }

    pthread_mutex_lock(&q->lock);
    q->reader_rc=rc;
    q->done=1;
    pthread_cond_broadcast(&q->cv);
    pthread_mutex_unlock(&q->lock);
    return NULL;
}

static int pace_pop(PaceQueue *q,AVPacket *pkt,int64_t *arrival_us,int *waited,OutCtx *o) {
    int rc=0;
    *waited=0;
    memset(pkt,0,sizeof(*pkt));

    pthread_mutex_lock(&q->lock);
    while(q->count==0&&!q->done&&!q->stop) {
        *waited=1;
        pthread_cond_wait(&q->cv,&q->lock);
    }
    if(q->count==0) {
        rc=q->reader_rc;
        pace_queue_snapshot_locked(q,o);
        pthread_mutex_unlock(&q->lock);
        return rc<0?rc:AVERROR_EOF;
    }

    av_packet_move_ref(pkt,&q->q[q->head].pkt);
    *arrival_us=q->q[q->head].arrival_us;
    q->head=(q->head+1)%PACE_QUEUE_CAP;
    --q->count;
    pace_queue_snapshot_locked(q,o);
    pthread_cond_broadcast(&q->cv);
    pthread_mutex_unlock(&q->lock);
    return 0;
}

static void pace_sleep_until(int64_t due_us) {
    for(;;) {
        int64_t now=av_gettime_relative();
        int64_t left=due_us-now;
        if(left<=0) return;
        if(left>200000LL) left=200000LL;
        usleep((unsigned int)left);
    }
}

static void publish_remux_status(OutCtx *o, int64_t frame_no,
                                 int64_t start_us, int64_t last_input_us,
                                 const char *state, int rc, int force) {
    char buf[2800], tmp[96];
    int fd, n;
    int64_t now=av_gettime_relative();
    if(!force && g_last_status_us>0 && now-g_last_status_us<1000000LL) return;
    g_last_status_us=now;
    if(o && o->input_framed) framed_snapshot(o);
    if(o) {
        uint64_t most_bytes_now=o->blocks*(uint64_t)MOST_BLOCK_BYTES;
        if(o->rate_prev_us>0 && now>o->rate_prev_us) {
            uint64_t dus=(uint64_t)(now-o->rate_prev_us);
            o->input_bps=((o->input_h264_bytes-o->rate_prev_input_bytes)*8000000ULL)/dus;
            o->most_bps=((most_bytes_now-o->rate_prev_most_bytes)*8000000ULL)/dus;
        }
        o->rate_prev_us=now;
        o->rate_prev_input_bytes=o->input_h264_bytes;
        o->rate_prev_most_bytes=most_bytes_now;
    }
    ++g_status_seq;
    n=snprintf(buf,sizeof(buf),
        "state=%s\n"
        "pid=%d\n"
        "seq=%llu\n"
        "frames=%lld\n"
        "ts_packets_out=%llu\n"
        "most_blocks=%llu\n"
        "most_bytes=%llu\n"
        "input_h264_bytes=%llu\n"
        "input_bps=%llu\n"
        "most_bps=%llu\n"
        "write_attempts=%llu\n"
        "write_eagain=%llu\n"
        "write_timeouts=%llu\n"
        "write_errors=%llu\n"
        "short_writes=%llu\n"
        "over20ms_blocks=%llu\n"
        "last_write_call_us=%lld\n"
        "last_block_wait_us=%lld\n"
        "max_block_wait_us=%lld\n"
        "last_input_ms=%lld\n"
        "last_write_ms=%lld\n"
        "pending_bytes=%d\n"
        "pace_enabled=%d\n"
        "pace_fps=%d\n"
        "pace_buffer_target=%d\n"
        "pace_queue_depth=%d\n"
        "pace_queue_max=%d\n"
        "pace_underflows=%llu\n"
        "pace_late_frames=%llu\n"
        "pace_backpressure_waits=%llu\n"
        "last_input_interval_us=%lld\n"
        "min_input_interval_us=%lld\n"
        "max_input_interval_us=%lld\n"
        "last_emit_interval_us=%lld\n"
        "max_emit_jitter_us=%lld\n"
        "input_mode=%s\n"
        "m1au_records=%llu\n"
        "m1au_stream=%llu\n"
        "m1au_codec=%llu\n"
        "m1au_consumer=%llu\n"
        "m1au_sequence=%llu\n"
        "m1au_sequence_gaps=%llu\n"
        "m1au_flags=0x%08x\n"
        "m1au_ts_raw=%02x%02x%02x%02x%02x%02x%02x%02x\n"
        "m1au_ts_word1_le=%u\n"
        "m1au_ts_word2_le=%u\n"
        "m1au_ts_word1_delta=%lld\n"
        "m1au_ts_word2_delta=%lld\n"
        "elapsed_ms=%lld\n"
        "rc=%d\n",
        state?state:"unknown",(int)getpid(),
        (unsigned long long)g_status_seq,(long long)frame_no,
        (unsigned long long)(o?o->packets:0),
        (unsigned long long)(o?o->blocks:0),
        (unsigned long long)(o?o->blocks*(uint64_t)MOST_BLOCK_BYTES:0),
        (unsigned long long)(o?o->input_h264_bytes:0),
        (unsigned long long)(o?o->input_bps:0),
        (unsigned long long)(o?o->most_bps:0),
        (unsigned long long)(o?o->write_attempts:0),
        (unsigned long long)(o?o->write_eagain:0),
        (unsigned long long)(o?o->write_timeouts:0),
        (unsigned long long)(o?o->write_errors:0),
        (unsigned long long)(o?o->short_writes:0),
        (unsigned long long)(o?o->over20ms_blocks:0),
        (long long)(o?o->last_write_call_us:0),
        (long long)(o?o->last_block_wait_us:0),
        (long long)(o?o->max_block_wait_us:0),
        (long long)(last_input_us>0?last_input_us/1000LL:0),
        (long long)(o&&o->last_write_us>0?o->last_write_us/1000LL:0),
        o?o->pending_len:0,
        o?o->pace_enabled:0,
        o?o->pace_fps:0,
        o?o->pace_buffer_target:0,
        o?o->pace_queue_depth:0,
        o?o->pace_queue_max:0,
        (unsigned long long)(o?o->pace_underflows:0),
        (unsigned long long)(o?o->pace_late_frames:0),
        (unsigned long long)(o?o->pace_backpressure_waits:0),
        (long long)(o?o->last_input_interval_us:0),
        (long long)(o?o->min_input_interval_us:0),
        (long long)(o?o->max_input_interval_us:0),
        (long long)(o?o->last_emit_interval_us:0),
        (long long)(o?o->max_emit_jitter_us:0),
        (o&&o->input_framed)?"m1au-v1":"raw-annexb",
        (unsigned long long)(o?o->m1au_records:0),
        (unsigned long long)(o?o->m1au_stream:0),
        (unsigned long long)(o?o->m1au_codec:0),
        (unsigned long long)(o?o->m1au_consumer:0),
        (unsigned long long)(o?o->m1au_sequence:0),
        (unsigned long long)(o?o->m1au_sequence_gaps:0),
        (unsigned)(o?o->m1au_flags:0),
        o?o->m1au_ts_raw[0]:0,o?o->m1au_ts_raw[1]:0,
        o?o->m1au_ts_raw[2]:0,o?o->m1au_ts_raw[3]:0,
        o?o->m1au_ts_raw[4]:0,o?o->m1au_ts_raw[5]:0,
        o?o->m1au_ts_raw[6]:0,o?o->m1au_ts_raw[7]:0,
        (unsigned)(o?o->m1au_ts_word1_le:0),
        (unsigned)(o?o->m1au_ts_word2_le:0),
        (long long)(o?o->m1au_ts_word1_delta:0),
        (long long)(o?o->m1au_ts_word2_delta:0),
        (long long)(start_us>0?(now-start_us)/1000LL:0),rc);
    if(n<=0) return;
    if((size_t)n>=sizeof(buf)) n=(int)sizeof(buf)-1;
    snprintf(tmp,sizeof(tmp),"%s.tmp.%d",REMUX_STATUS_PATH,(int)getpid());
    fd=open(tmp,O_WRONLY|O_CREAT|O_TRUNC,0644);
    if(fd<0) return;
    if(write(fd,buf,(size_t)n)!=(ssize_t)n) {
        close(fd);
        unlink(tmp);
        return;
    }
    close(fd);
    if(rename(tmp,REMUX_STATUS_PATH)!=0) {
        int saved=errno;
        /*
         * Exact QNX target fallback: the first vehicle run showed that the
         * temp+rename publication path could silently leave no status file.
         * Status is diagnostics only, so prefer a brief non-atomic snapshot
         * over losing the evidence entirely.
         */
        fd=open(REMUX_STATUS_PATH,O_WRONLY|O_CREAT|O_TRUNC,0644);
        if(fd>=0) {
            ssize_t wr=write(fd,buf,(size_t)n);
            close(fd);
            unlink(tmp);
            if(wr==(ssize_t)n) {
                if(!g_status_error_logged) {
                    fprintf(stderr,
                            "REMUX_STATUS_FALLBACK rename_errno=%d (%s) direct_write=ok\n",
                            saved,strerror(saved));
                    g_status_error_logged=1;
                }
                return;
            }
        }
        unlink(tmp);
        if(!g_status_error_logged) {
            fprintf(stderr,
                    "REMUX_STATUS_ERROR rename_errno=%d (%s) direct_write_failed errno=%d (%s)\n",
                    saved,strerror(saved),errno,strerror(errno));
            g_status_error_logged=1;
        }
    }
}

static int interrupt_cb(void *opaque) {
    int64_t *deadline=(int64_t *)opaque;
    return (*deadline>0 && av_gettime_relative()>=*deadline);
}

static int write_all(int fd,const uint8_t *p,int n) {
    int off=0;
    int64_t deadline=av_gettime_relative()+2000000LL;
    while(off<n) {
        int w=(int)write(fd,p+off,(size_t)(n-off));
        if(w>0){off+=w;continue;}
        if(w<0 && errno==EINTR) continue;
        if(w<0 && (errno==EAGAIN || errno==EWOULDBLOCK)) {
            if(av_gettime_relative()>=deadline) return AVERROR(EAGAIN);
            usleep(5000); continue;
        }
        return AVERROR(errno?errno:EIO);
    }
    return 0;
}

static void make_null_packet(uint8_t *p) {
    memset(p,0xff,TS_SIZE);
    p[0]=0x47;
    p[1]=0x1f;
    p[2]=0xff;
    p[3]=0x10;
}

/*
 * Exact-unit vehicle contract:
 *   one application write to /dev/mlb/isoTX2 = 64 MPEG-TS packets = 12032 B.
 *
 * A positive short write is a hard failure. Never follow it with a short
 * remainder write, because that would violate the resource-manager message
 * boundary that produced the visible TEST9 stream.
 */
static int emit_most_block(OutCtx *o) {
    int i;
    int64_t block_start_us=av_gettime_relative();
    int64_t deadline=block_start_us+2000000LL;

    if(o->pending_len!=MOST_BLOCK_BYTES) return AVERROR_INVALIDDATA;
    for(i=0;i<MOST_BLOCK_PACKETS;i++) {
        if(o->pending[i*TS_SIZE]!=0x47) {
            fprintf(stderr,"ERROR TS sync lost inside MOST block=%llu packet=%d\n",
                    (unsigned long long)o->blocks,i);
            return AVERROR_INVALIDDATA;
        }
    }

    for(;;) {
        int w;
        int64_t call_start_us,call_end_us,wait_us;
        errno=0;
        call_start_us=av_gettime_relative();
        w=(int)write(o->fd,o->pending,MOST_BLOCK_BYTES);
        call_end_us=av_gettime_relative();
        ++o->write_attempts;
        o->last_write_call_us=call_end_us-call_start_us;
        wait_us=call_end_us-block_start_us;

        if(w==MOST_BLOCK_BYTES) {
            o->packets+=MOST_BLOCK_PACKETS;
            ++o->blocks;
            o->last_write_us=call_end_us;
            o->last_block_wait_us=wait_us;
            if(wait_us>o->max_block_wait_us) o->max_block_wait_us=wait_us;
            if(wait_us>=20000LL) ++o->over20ms_blocks;
            o->pending_len=0;
            return 0;
        }
        if(w<0 && errno==EINTR) continue;
        if(w<0 && (errno==EAGAIN || errno==EWOULDBLOCK)) {
            ++o->write_eagain;
            if(call_end_us>=deadline) {
                ++o->write_timeouts;
                o->last_block_wait_us=wait_us;
                if(wait_us>o->max_block_wait_us) o->max_block_wait_us=wait_us;
                fprintf(stderr,
                        "ERROR MOST EAGAIN timeout block=%llu wait_us=%lld attempts=%llu eagain=%llu\n",
                        (unsigned long long)o->blocks,(long long)wait_us,
                        (unsigned long long)o->write_attempts,
                        (unsigned long long)o->write_eagain);
                return AVERROR(EAGAIN);
            }
            usleep(5000);
            continue;
        }
        if(w>=0) {
            ++o->short_writes;
            o->last_block_wait_us=wait_us;
            if(wait_us>o->max_block_wait_us) o->max_block_wait_us=wait_us;
            fprintf(stderr,
                    "ERROR MOST strict short write block=%llu rc=%d expected=%d short_writes=%llu wait_us=%lld\n",
                    (unsigned long long)o->blocks,w,MOST_BLOCK_BYTES,
                    (unsigned long long)o->short_writes,(long long)wait_us);
            return AVERROR(EIO);
        }
        ++o->write_errors;
        o->last_block_wait_us=wait_us;
        if(wait_us>o->max_block_wait_us) o->max_block_wait_us=wait_us;
        fprintf(stderr,
                "ERROR MOST strict write block=%llu bytes=%d errno=%d (%s) write_errors=%llu wait_us=%lld\n",
                (unsigned long long)o->blocks,MOST_BLOCK_BYTES,errno,strerror(errno),
                (unsigned long long)o->write_errors,(long long)wait_us);
        return AVERROR(errno?errno:EIO);
    }
}

static int flush_most_tail(OutCtx *o) {
    int payload_packets,pad,i;

    if(!o->device_mode || o->pending_len==0) return 0;
    if((o->pending_len%TS_SIZE)!=0) {
        fprintf(stderr,"ERROR MOST tail is not TS aligned: pending=%d\n",o->pending_len);
        return AVERROR_INVALIDDATA;
    }

    payload_packets=o->pending_len/TS_SIZE;
    if(payload_packets<1 || payload_packets>=MOST_BLOCK_PACKETS) return AVERROR_INVALIDDATA;

    pad=MOST_BLOCK_PACKETS-payload_packets;
    for(i=payload_packets;i<MOST_BLOCK_PACKETS;i++) {
        make_null_packet(o->pending+i*TS_SIZE);
    }
    o->pending_len=MOST_BLOCK_BYTES;
    o->pad_packets+=(uint64_t)pad;

    fprintf(stderr,
            "MOST_TAIL payload_packets=%d pad_null_packets=%d write_size=%d\n",
            payload_packets,pad,MOST_BLOCK_BYTES);
    return emit_most_block(o);
}

static int write_cb(void *opaque,const uint8_t *buf,int size) {
    OutCtx *o=(OutCtx *)opaque;
    if(!o->device_mode) {
        int rc=write_all(o->fd,buf,size);
        return rc<0?rc:size;
    }
    {
        int pos=0;
        while(pos<size) {
            int need=MOST_BLOCK_BYTES-o->pending_len;
            int take=(size-pos<need)?(size-pos):need;
            memcpy(o->pending+o->pending_len,buf+pos,(size_t)take);
            o->pending_len+=take;
            pos+=take;
            if(o->pending_len==MOST_BLOCK_BYTES) {
                int rc=emit_most_block(o);
                if(rc<0) return rc;
            }
        }
    }
    return size;
}

static void errstr(int e,char *buf,size_t n) {
    if(av_strerror(e,buf,n)<0) snprintf(buf,n,"err=%d",e);
}

static int framed_deadline_expired(const FramedInput *f) {
    return f && f->deadline && *f->deadline>0 &&
           av_gettime_relative()>=*f->deadline;
}

static int framed_recv_wait(FramedInput *f,uint8_t *p,size_t n,int exact) {
    size_t off=0;
    for(;;) {
        ssize_t r;
        if(framed_deadline_expired(f))return AVERROR_EXIT;
        r=recv(f->fd,p+off,n-off,0);
        if(r>0) {
            off+=(size_t)r;
            if(!exact || off==n)return (int)off;
            continue;
        }
        if(r==0)return off?AVERROR_INVALIDDATA:AVERROR_EOF;
        if(errno==EINTR)continue;
        if(errno==EAGAIN || errno==EWOULDBLOCK) {
            usleep(5000);
            continue;
        }
        return AVERROR(errno?errno:EIO);
    }
}

static void framed_note_header(FramedInput *f,const uint8_t h[M1AU_HEADER_BYTES]) {
    uint32_t w1=m1au_get_le32(h+48);
    uint32_t w2=m1au_get_le32(h+52);
    uint64_t seq=m1au_get_be64(h+40);

    pthread_mutex_lock(&f->lock);
    ++f->records;
    f->stream=m1au_get_be64(h+16);
    f->codec=m1au_get_be64(h+24);
    f->consumer=m1au_get_be64(h+32);
    f->flags=m1au_get_be32(h+8);
    if(f->previous_sequence && seq!=f->previous_sequence+1u)++f->sequence_gaps;
    f->previous_sequence=seq;
    f->sequence=seq;
    memcpy(f->ts_raw,h+48,8u);
    f->ts_word1_le=w1;
    f->ts_word2_le=w2;
    if(f->have_prev_ts) {
        f->ts_word1_delta=(int64_t)(int32_t)(w1-f->prev_ts_word1_le);
        f->ts_word2_delta=(int64_t)(int32_t)(w2-f->prev_ts_word2_le);
    } else {
        f->ts_word1_delta=0;
        f->ts_word2_delta=0;
        f->have_prev_ts=1;
    }
    f->prev_ts_word1_le=w1;
    f->prev_ts_word2_le=w2;
    pthread_mutex_unlock(&f->lock);
}

static int framed_read_cb(void *opaque,uint8_t *buf,int buf_size) {
    FramedInput *f=(FramedInput *)opaque;
    uint8_t h[M1AU_HEADER_BYTES];
    int rc;
    size_t want;

    if(!f || f->fd<0 || !buf || buf_size<=0)return AVERROR(EINVAL);

    if(f->payload_remaining==0) {
        rc=framed_recv_wait(f,h,sizeof(h),1);
        if(rc<0)return rc;
        if(memcmp(h,"M1AU",4u)!=0 ||
           m1au_get_be16(h+4)!=1u ||
           m1au_get_be16(h+6)!=M1AU_HEADER_BYTES) {
            fprintf(stderr,
                    "ERROR M1AU header magic/version/size invalid magic=%02x%02x%02x%02x version=%u header=%u\n",
                    h[0],h[1],h[2],h[3],
                    (unsigned)m1au_get_be16(h+4),
                    (unsigned)m1au_get_be16(h+6));
            return AVERROR_INVALIDDATA;
        }
        f->payload_remaining=(size_t)m1au_get_be32(h+12);
        if(!f->payload_remaining || f->payload_remaining>M1AU_MAX_PAYLOAD) {
            fprintf(stderr,"ERROR M1AU payload invalid bytes=%zu\n",f->payload_remaining);
            return AVERROR_INVALIDDATA;
        }
        framed_note_header(f,h);
    }

    want=f->payload_remaining<(size_t)buf_size?f->payload_remaining:(size_t)buf_size;
    rc=framed_recv_wait(f,buf,want,0);
    if(rc<0)return rc;
    if((size_t)rc>f->payload_remaining)return AVERROR_INVALIDDATA;
    f->payload_remaining-=(size_t)rc;
    return rc;
}

static int framed_parse_loopback_url(const char *url,int *port) {
    const char *pfx="tcp://127.0.0.1:";
    char *end=NULL;
    long v;
    if(!url||strncmp(url,pfx,strlen(pfx))!=0)return -1;
    v=strtol(url+strlen(pfx),&end,10);
    if(end==url+strlen(pfx)||*end!='\0'||v<1||v>65535)return -1;
    *port=(int)v;
    return 0;
}

static int framed_connect_retry(const char *url,int wait_seconds,int64_t *deadline) {
    int port,attempt=0;
    int64_t until=wait_seconds>0?av_gettime_relative()+(int64_t)wait_seconds*1000000LL:0;
    if(framed_parse_loopback_url(url,&port)!=0) {
        fprintf(stderr,"ERROR M1AU supports only tcp://127.0.0.1:PORT input, got %s\n",url?url:"<null>");
        return -1;
    }
    for(;;) {
        int fd=socket(AF_INET,SOCK_STREAM,0);
        struct sockaddr_in a;
        if(fd<0)return -1;
        memset(&a,0,sizeof(a));
        a.sin_family=AF_INET;
        a.sin_port=htons((uint16_t)port);
        a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        if(connect(fd,(struct sockaddr *)&a,sizeof(a))==0) {
            int flags=fcntl(fd,F_GETFL,0);
            if(flags>=0)(void)fcntl(fd,F_SETFL,flags|O_NONBLOCK);
            *deadline=until;
            fprintf(stderr,"M1AU_CONNECT_OK attempt=%d url=%s\n",attempt+1,url);
            return fd;
        }
        close(fd);
        if(wait_seconds<=0 || av_gettime_relative()>=until)return -1;
        ++attempt;
        usleep(1000000);
    }
}

static AVFormatContext *open_m1au_h264(const char *url,int fps,int wait_seconds,
                                      int64_t *deadline,FramedInput *f,
                                      AVIOContext **pb_out) {
    AVFormatContext *ic=NULL;
    AVIOContext *pb=NULL;
    uint8_t *buf=NULL;
    const AVInputFormat *fmt=av_find_input_format("h264");
    AVDictionary *opts=NULL;
    char fpsbuf[32],ebuf[128];
    int fd,rc;

    if(!f||!pb_out||!fmt)return NULL;
    memset(f,0,sizeof(*f));
    f->fd=-1;
    pthread_mutex_init(&f->lock,NULL);
    fd=framed_connect_retry(url,wait_seconds,deadline);
    if(fd<0)goto fail;
    f->fd=fd;
    f->deadline=deadline;

    buf=av_malloc(32768);
    if(!buf)goto fail;
    pb=avio_alloc_context(buf,32768,0,f,framed_read_cb,NULL,NULL);
    if(!pb)goto fail;
    buf=NULL;

    ic=avformat_alloc_context();
    if(!ic)goto fail;
    ic->pb=pb;
    ic->flags|=AVFMT_FLAG_CUSTOM_IO;
    ic->interrupt_callback.callback=interrupt_cb;
    ic->interrupt_callback.opaque=deadline;

    snprintf(fpsbuf,sizeof(fpsbuf),"%d",fps);
    av_dict_set(&opts,"framerate",fpsbuf,0);
    rc=avformat_open_input(&ic,NULL,fmt,&opts);
    av_dict_free(&opts);
    if(rc<0) {
        errstr(rc,ebuf,sizeof(ebuf));
        fprintf(stderr,"ERROR M1AU H264 open rc=%d %s\n",rc,ebuf);
        goto fail;
    }
    *pb_out=pb;
    *deadline=0;
    fprintf(stderr,"INPUT_OPEN_OK mode=m1au-v1 url=%s\n",url);
    return ic;

fail:
    if(opts)av_dict_free(&opts);
    if(ic)avformat_free_context(ic);
    if(pb) {
        av_freep(&pb->buffer);
        avio_context_free(&pb);
    } else if(buf) av_free(buf);
    if(f->fd>=0)close(f->fd);
    f->fd=-1;
    pthread_mutex_destroy(&f->lock);
    return NULL;
}

static AVFormatContext *open_h264_retry(const char *url,int fps,int wait_seconds,int64_t *deadline) {
    int attempt=0;
    int64_t until=wait_seconds>0?av_gettime_relative()+(int64_t)wait_seconds*1000000LL:0;
    for(;;) {
        AVFormatContext *ic=avformat_alloc_context();
        const AVInputFormat *fmt=av_find_input_format("h264");
        AVDictionary *opts=NULL;
        char fpsbuf[32],ebuf[128];
        int rc;
        if(!ic || !fmt){if(ic)avformat_free_context(ic);return NULL;}
        snprintf(fpsbuf,sizeof(fpsbuf),"%d",fps);
        av_dict_set(&opts,"framerate",fpsbuf,0);
        *deadline=until;
        ic->interrupt_callback.callback=interrupt_cb;
        ic->interrupt_callback.opaque=deadline;
        rc=avformat_open_input(&ic,url,fmt,&opts);
        av_dict_free(&opts);
        if(rc>=0) {
            *deadline=0;
            fprintf(stderr,"INPUT_OPEN_OK attempt=%d url=%s\n",attempt+1,url);
            return ic;
        }
        errstr(rc,ebuf,sizeof(ebuf));
        fprintf(stderr,"INPUT_OPEN_RETRY attempt=%d rc=%d %s\n",attempt+1,rc,ebuf);
        if(wait_seconds<=0 || av_gettime_relative()>=until) {
            if(ic) avformat_free_context(ic);
            return NULL;
        }
        if(ic) avformat_free_context(ic);
        ++attempt;
        usleep(1000000);
    }
}

static int open_out(const char *path,int *device_mode) {
    int fd;
    *device_mode=(strncmp(path,"/dev/",5)==0);
    if(*device_mode) {
        fd=open(path,O_WRONLY|O_NONBLOCK);
        if(fd<0) {
            fprintf(stderr,"OUTPUT_OPEN nonblock failed errno=%d (%s); retry blocking\n",errno,strerror(errno));
            fd=open(path,O_WRONLY);
        }
    } else {
        fd=open(path,O_WRONLY|O_CREAT|O_TRUNC,0644);
    }
    return fd;
}

int main(int argc,char **argv) {
    const char *in_url,*out_path;
    int fps,max_seconds,wait_seconds,pid;
    int pace_enabled,pace_buffer,input_m1au;
    AVFormatContext *ic=NULL,*oc=NULL;
    AVStream *is=NULL,*os=NULL;
    AVDictionary *mux_opts=NULL;
    AVIOContext *avio=NULL,*input_avio=NULL;
    unsigned char *avio_buf=NULL;
    FramedInput framed;
    int framed_active=0;
    OutCtx out;
    int64_t deadline=0,start_us=0,frame_no=0,last_input_us=0;
    int video=-1,rc=0;
    char ebuf[128];

    memset(&out,0,sizeof(out));
    memset(&framed,0,sizeof(framed));
    framed.fd=-1;
    out.fd=-1;
    (void)unlink(REMUX_STATUS_PATH);

    if(argc!=7) {
        fprintf(stderr,"usage: %s INPUT OUTPUT FPS MAX_SECONDS WAIT_SECONDS VIDEO_PID\n",argv[0]);
        return 64;
    }
    in_url=argv[1]; out_path=argv[2];
    fps=atoi(argv[3]); max_seconds=atoi(argv[4]); wait_seconds=atoi(argv[5]);
    pid=(int)strtol(argv[6],NULL,0);
    if(fps<1||fps>60||max_seconds<0||max_seconds>600||wait_seconds<0||wait_seconds>120||pid<1||pid>0x1ffe) return 65;

    pace_enabled=env_int("MIBR_PACE",0)?1:0;
    input_m1au=env_int("MIBR_INPUT_M1AU",0)?1:0;
    pace_buffer=env_int("MIBR_PACE_BUFFER",3);
    if(pace_buffer<1)pace_buffer=1;
    if(pace_buffer>6)pace_buffer=6;
    out.pace_enabled=pace_enabled;
    out.pace_fps=pace_enabled?fps:0;
    out.pace_buffer_target=pace_enabled?pace_buffer:0;

    avformat_network_init();
    if(input_m1au) {
        ic=open_m1au_h264(in_url,fps,wait_seconds,&deadline,&framed,&input_avio);
        if(ic) {
            framed_active=1;
            g_framed_status=&framed;
            out.input_framed=1;
        }
    } else {
        ic=open_h264_retry(in_url,fps,wait_seconds,&deadline);
    }
    if(!ic){fprintf(stderr,"ERROR cannot open H264 input mode=%s\n",input_m1au?"m1au-v1":"raw-annexb");return 2;}
    rc=avformat_find_stream_info(ic,NULL);
    if(rc<0){errstr(rc,ebuf,sizeof(ebuf));fprintf(stderr,"ERROR stream info: %s\n",ebuf);goto done;}
    for(unsigned i=0;i<ic->nb_streams;i++) if(ic->streams[i]->codecpar->codec_type==AVMEDIA_TYPE_VIDEO){video=(int)i;break;}
    if(video<0){fprintf(stderr,"ERROR no video stream\n");rc=AVERROR_STREAM_NOT_FOUND;goto done;}
    is=ic->streams[video];

    rc=avformat_alloc_output_context2(&oc,NULL,"mpegts",NULL);
    if(rc<0||!oc){fprintf(stderr,"ERROR no mpegts muxer\n");goto done;}
    os=avformat_new_stream(oc,NULL);
    if(!os){rc=AVERROR(ENOMEM);goto done;}
    rc=avcodec_parameters_copy(os->codecpar,is->codecpar);
    if(rc<0) goto done;
    os->codecpar->codec_tag=0;
    os->id=pid;
    os->time_base=(AVRational){1,90000};

    out.fd=open_out(out_path,&out.device_mode);
    if(out.fd<0){fprintf(stderr,"ERROR open output %s errno=%d (%s)\n",out_path,errno,strerror(errno));rc=AVERROR(errno);goto done;}
    avio_buf=av_malloc(32768);
    if(!avio_buf){rc=AVERROR(ENOMEM);goto done;}
    avio=avio_alloc_context(avio_buf,32768,1,&out,NULL,write_cb,NULL);
    if(!avio){rc=AVERROR(ENOMEM);goto done;}
    avio_buf=NULL;
    oc->pb=avio;
    oc->flags|=AVFMT_FLAG_CUSTOM_IO;

    av_dict_set(&mux_opts,"mpegts_flags","resend_headers+initial_discontinuity",0);
    av_dict_set(&mux_opts,"mpegts_pmt_start_pid","4096",0);
    av_dict_set(&mux_opts,"pcr_period","20",0);
    av_dict_set(&mux_opts,"pat_period","0.1",0);
    rc=avformat_write_header(oc,&mux_opts);
    av_dict_free(&mux_opts);
    if(rc<0){errstr(rc,ebuf,sizeof(ebuf));fprintf(stderr,"ERROR write header: %s\n",ebuf);goto done;}

    fprintf(stderr,"REMUX_START input=%s input_mode=%s output=%s fps=%d max_seconds=%d pid=0x%x device=%d most_block_packets=%d write_size=%d pace=%d pace_buffer=%d\n",
            in_url,input_m1au?"m1au-v1":"raw-annexb",out_path,fps,max_seconds,pid,out.device_mode,
            out.device_mode?MOST_BLOCK_PACKETS:0,
            out.device_mode?MOST_BLOCK_BYTES:0,
            pace_enabled,pace_enabled?pace_buffer:0);
    start_us=av_gettime_relative();
    deadline=max_seconds>0?start_us+(int64_t)max_seconds*1000000LL:0;
    publish_remux_status(&out,frame_no,start_us,last_input_us,"running",0,1);
    ic->interrupt_callback.opaque=&deadline;

    if(pace_enabled) {
        PaceQueue pq;
        pthread_t reader;
        int reader_started=0;
        int max_depth=pace_buffer+3;
        int64_t pace_epoch_us=0;
        int64_t frame_period_us=1000000LL/fps;

        if(max_depth>PACE_QUEUE_CAP)max_depth=PACE_QUEUE_CAP;
        pace_queue_init(&pq,ic,video,max_depth);
        rc=pthread_create(&reader,NULL,pace_reader_main,&pq);
        if(rc!=0) {
            fprintf(stderr,"ERROR pace reader pthread_create rc=%d\n",rc);
            pace_queue_destroy(&pq);
            rc=AVERROR(rc);
        } else {
            reader_started=1;
            fprintf(stderr,"PACE_START fps=%d frame_period_us=%lld prebuffer=%d queue_max=%d\n",
                    fps,(long long)frame_period_us,pace_buffer,max_depth);

            for(;;) {
                AVPacket pkt;
                AVRational frame_tb={1,fps};
                int waited=0;
                int pr;
                int64_t arrival_us=0;
                int64_t due_us,now_us,emit_us;

                pr=pace_pop(&pq,&pkt,&arrival_us,&waited,&out);
                if(pr<0) { rc=pr; break; }
                last_input_us=arrival_us;

                if(frame_no==0) {
                    if(pace_buffer>1)
                        usleep((unsigned int)(((int64_t)(pace_buffer-1)*1000000LL)/fps));
                    pace_epoch_us=av_gettime_relative();
                    due_us=pace_epoch_us;
                } else {
                    now_us=av_gettime_relative();
                    due_us=pace_epoch_us+(frame_no*1000000LL)/fps;
                    if(waited) {
                        ++out.pace_underflows;
                        pace_epoch_us=now_us-(frame_no*1000000LL)/fps;
                        due_us=now_us;
                    }
                    if(now_us<due_us) {
                        pace_sleep_until(due_us);
                    } else if(now_us-due_us>1000LL) {
                        ++out.pace_late_frames;
                    }
                }

                pkt.pts=frame_no;
                pkt.dts=frame_no;
                pkt.duration=1;
                av_packet_rescale_ts(&pkt,frame_tb,os->time_base);
                pkt.stream_index=os->index;
                pkt.pos=-1;
                rc=av_interleaved_write_frame(oc,&pkt);
                av_packet_unref(&pkt);
                emit_us=av_gettime_relative();
                if(out.last_emit_us>0) {
                    int64_t jitter;
                    out.last_emit_interval_us=emit_us-out.last_emit_us;
                    jitter=abs_i64(out.last_emit_interval_us-frame_period_us);
                    if(jitter>out.max_emit_jitter_us)out.max_emit_jitter_us=jitter;
                }
                out.last_emit_us=emit_us;

                if(rc<0) {
                    errstr(rc,ebuf,sizeof(ebuf));
                    fprintf(stderr,"ERROR mux/write frame=%lld %s\n",(long long)frame_no,ebuf);
                    break;
                }
                ++frame_no;
                publish_remux_status(&out,frame_no,start_us,last_input_us,"running",0,0);
                if(max_seconds>0 && av_gettime_relative()>=deadline){rc=0;break;}
            }

            /*
             * Stop a blocked TCP read if the output side failed before the
             * normal deadline. The FFmpeg interrupt callback observes this.
             */
            if(rc<0 && rc!=AVERROR_EOF) deadline=av_gettime_relative();
            pace_queue_stop(&pq);
            if(reader_started)pthread_join(reader,NULL);
            pthread_mutex_lock(&pq.lock);
            pace_queue_snapshot_locked(&pq,&out);
            pthread_mutex_unlock(&pq.lock);
            pace_queue_destroy(&pq);
        }
    } else {
        for(;;) {
            AVPacket pkt;
            AVRational frame_tb={1,fps};
            rc=av_read_frame(ic,&pkt);
            if(rc<0) break;
            if(pkt.stream_index!=video){av_packet_unref(&pkt);continue;}
            last_input_us=av_gettime_relative();
            out.input_h264_bytes+=(uint64_t)(pkt.size>0?pkt.size:0);
            pkt.pts=frame_no;
            pkt.dts=frame_no;
            pkt.duration=1;
            av_packet_rescale_ts(&pkt,frame_tb,os->time_base);
            pkt.stream_index=os->index;
            pkt.pos=-1;
            rc=av_interleaved_write_frame(oc,&pkt);
            av_packet_unref(&pkt);
            if(rc<0){errstr(rc,ebuf,sizeof(ebuf));fprintf(stderr,"ERROR mux/write frame=%lld %s\n",(long long)frame_no,ebuf);break;}
            ++frame_no;
            publish_remux_status(&out,frame_no,start_us,last_input_us,"running",0,0);
            if(max_seconds>0 && av_gettime_relative()>=deadline){rc=0;break;}
        }
    }
    /* A finite raw-H264 file ends with AVERROR_EOF after all frames were read.
     * Treat that as successful completion when at least one frame was muxed. */
    if((rc==AVERROR_EOF && frame_no>0) || rc==AVERROR_EXIT || rc==AVERROR(EINTR) ||
       (max_seconds>0 && av_gettime_relative()>=deadline)) rc=0;
    if(frame_no>0) {
        int tr=av_write_trailer(oc);
        if(rc>=0 && tr<0) rc=tr;
    }

    /*
     * Flush libavformat's AVIO bytes first, then close the MU1440 message
     * contract with one final 12032-byte block padded only with null TS.
     */
    if(avio) {
        avio_flush(avio);
        if(rc>=0 && avio->error<0) rc=avio->error;
    }
    if(rc>=0 && out.device_mode) {
        int fr=flush_most_tail(&out);
        if(fr<0) rc=fr;
    }

    publish_remux_status(&out,frame_no,start_us,last_input_us,"done",rc,1);

    fprintf(stderr,
            "REMUX_DONE frames=%lld ts_packets_out=%llu most_blocks=%llu pad_null_packets=%llu write_size=%d input_h264_bytes=%llu write_attempts=%llu write_eagain=%llu write_timeouts=%llu write_errors=%llu short_writes=%llu over20ms_blocks=%llu max_block_wait_us=%lld pace=%d pace_fps=%d pace_underflows=%llu pace_late_frames=%llu pace_backpressure_waits=%llu max_emit_jitter_us=%lld elapsed_ms=%lld rc=%d pending=%d\n",
            (long long)frame_no,
            (unsigned long long)out.packets,
            (unsigned long long)out.blocks,
            (unsigned long long)out.pad_packets,
            out.device_mode?MOST_BLOCK_BYTES:0,
            (unsigned long long)out.input_h264_bytes,
            (unsigned long long)out.write_attempts,
            (unsigned long long)out.write_eagain,
            (unsigned long long)out.write_timeouts,
            (unsigned long long)out.write_errors,
            (unsigned long long)out.short_writes,
            (unsigned long long)out.over20ms_blocks,
            (long long)out.max_block_wait_us,
            out.pace_enabled,out.pace_fps,
            (unsigned long long)out.pace_underflows,
            (unsigned long long)out.pace_late_frames,
            (unsigned long long)out.pace_backpressure_waits,
            (long long)out.max_emit_jitter_us,
            (long long)((av_gettime_relative()-start_us)/1000LL),rc,out.pending_len);

done:
    if(mux_opts) av_dict_free(&mux_opts);
    if(avio) {
        avio_flush(avio);
        av_freep(&avio->buffer);
        avio_context_free(&avio);
    } else if(avio_buf) av_free(avio_buf);
    if(out.fd>=0) close(out.fd);
    if(oc) avformat_free_context(oc);
    if(ic) avformat_close_input(&ic);
    if(input_avio) {
        av_freep(&input_avio->buffer);
        avio_context_free(&input_avio);
    }
    if(framed_active) {
        if(framed.fd>=0) close(framed.fd);
        g_framed_status=NULL;
        pthread_mutex_destroy(&framed.lock);
    }
    avformat_network_deinit();
    return rc<0?10:0;
}
