/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define TS_SIZE 188
#define MAX_PROBE_PACKETS 64
#define STRICT_BLOCK_PACKETS 64
#define STRICT_BLOCK_BYTES (STRICT_BLOCK_PACKETS * TS_SIZE)

static uint64_t mono_ns(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return 0;
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

static void sleep_ns(uint64_t ns) {
    struct timespec ts;
    ts.tv_sec=(time_t)(ns/1000000000ULL);
    ts.tv_nsec=(long)(ns%1000000000ULL);
    while (nanosleep(&ts,&ts) != 0 && errno == EINTR) {}
}

static int validate(FILE *f, uint64_t *packets, uint64_t *pid11) {
    uint8_t p[TS_SIZE];
    uint64_t n=0, v11=0;
    for (;;) {
        size_t got=fread(p,1,sizeof(p),f);
        if (got==0) break;
        if (got!=sizeof(p)) {
            fprintf(stderr,"ERROR partial TS packet at EOF: %lu bytes\n",(unsigned long)got);
            return 2;
        }
        if (p[0]!=0x47) {
            fprintf(stderr,"ERROR bad TS sync at packet %llu: 0x%02x\n",
                    (unsigned long long)n,(unsigned)p[0]);
            return 3;
        }
        {
            unsigned pid=((unsigned)(p[1]&0x1f)<<8)|p[2];
            if(pid==0x11) ++v11;
        }
        ++n;
    }
    if (!n) { fprintf(stderr,"ERROR empty TS input\n"); return 4; }
    if (packets) *packets=n;
    if (pid11) *pid11=v11;
    return 0;
}

static int open_output(const char *path) {
    int fd=open(path,O_WRONLY|O_NONBLOCK);
    if(fd>=0) return fd;
    fprintf(stderr,"open nonblock failed path=%s errno=%d (%s); retry blocking\n",
            path,errno,strerror(errno));
    return open(path,O_WRONLY);
}

static int write_all(int fd,const uint8_t *p,size_t total) {
    size_t off=0;
    uint64_t deadline=mono_ns()+2000000000ULL;
    while(off<total) {
        ssize_t n=write(fd,p+off,total-off);
        if(n>0){off+=(size_t)n;continue;}
        if(n<0 && errno==EINTR) continue;
        if(n<0 && (errno==EAGAIN || errno==EWOULDBLOCK)) {
            if(mono_ns()>=deadline){errno=EAGAIN;return -1;}
            sleep_ns(5000000ULL);
            continue;
        }
        return -1;
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
 * Strict TEST8 contract: one application write is always exactly 64 MPEG-TS
 * packets / 12032 bytes. EINTR/EAGAIN may retry the same complete block, but
 * a positive short write is a hard failure and is never followed by a short
 * remainder write.
 */
static ssize_t write_strict_block(int fd,const uint8_t *p) {
    uint64_t deadline=mono_ns()+2000000000ULL;
    for (;;) {
        ssize_t n;
        errno=0;
        n=write(fd,p,STRICT_BLOCK_BYTES);
        if(n==(ssize_t)STRICT_BLOCK_BYTES) return n;
        if(n<0 && errno==EINTR) continue;
        if(n<0 && (errno==EAGAIN || errno==EWOULDBLOCK)) {
            if(mono_ns()>=deadline){errno=EAGAIN;return -1;}
            sleep_ns(5000000ULL);
            continue;
        }
        return n;
    }
}

static void print_strict_plan(uint64_t packets,uint64_t pid11) {
    uint64_t full=packets/STRICT_BLOCK_PACKETS;
    uint64_t rem=packets%STRICT_BLOCK_PACKETS;
    uint64_t pad=rem ? (STRICT_BLOCK_PACKETS-rem) : 0;
    uint64_t blocks=full+(rem ? 1 : 0);
    printf("STRICT_DRY_RUN packets_in=%llu pid0x11_packets=%llu full_blocks=%llu remainder_packets=%llu pad_null_packets=%llu blocks_out=%llu write_size=%u short_blocks=0\n",
           (unsigned long long)packets,
           (unsigned long long)pid11,
           (unsigned long long)full,
           (unsigned long long)rem,
           (unsigned long long)pad,
           (unsigned long long)blocks,
           (unsigned)STRICT_BLOCK_BYTES);
}

static int strict64_stream(const char *in,const char *out,uint64_t bps) {
    FILE *f;
    int fd;
    uint8_t p[STRICT_BLOCK_BYTES];
    uint64_t packets=0,pid11=0,input_sent=0,output_sent=0,blocks=0,pad_total=0,start;

    if(bps<100000ULL || bps>12288000ULL) {
        fprintf(stderr,"ERROR pace_bps out of range: %llu\n",(unsigned long long)bps);
        return 65;
    }

    f=fopen(in,"rb");
    if(!f){perror("fopen input");return 1;}
    if(validate(f,&packets,&pid11)!=0){fclose(f);return 2;}
    rewind(f);

    printf("STRICT_INPUT packets=%llu pid0x11=%llu pace_bps=%llu block_packets=%u write_size=%u output=%s\n",
           (unsigned long long)packets,(unsigned long long)pid11,
           (unsigned long long)bps,(unsigned)STRICT_BLOCK_PACKETS,
           (unsigned)STRICT_BLOCK_BYTES,out);
    print_strict_plan(packets,pid11);
    fflush(stdout);

    fd=open_output(out);
    if(fd<0){
        fprintf(stderr,"ERROR open output %s errno=%d (%s)\n",out,errno,strerror(errno));
        fclose(f);return 10;
    }

    start=mono_ns();
    for (;;) {
        size_t got=fread(p,TS_SIZE,STRICT_BLOCK_PACKETS,f);
        uint64_t expected_ns,elapsed;
        unsigned j;
        ssize_t n;
        unsigned pad=0;

        if(got==0) break;
        for(j=0;j<got;j++) {
            if(p[j*TS_SIZE]!=0x47) {
                fprintf(stderr,"ERROR sync lost at input packet %llu\n",
                        (unsigned long long)(input_sent+j));
                close(fd);fclose(f);return 11;
            }
        }

        if(got<STRICT_BLOCK_PACKETS) {
            pad=STRICT_BLOCK_PACKETS-(unsigned)got;
            for(j=(unsigned)got;j<STRICT_BLOCK_PACKETS;j++) {
                make_null_packet(p+(size_t)j*TS_SIZE);
            }
        }

        n=write_strict_block(fd,p);
        if(n!=(ssize_t)STRICT_BLOCK_BYTES) {
            if(n>=0) {
                fprintf(stderr,"ERROR strict short write block=%llu input_packet=%llu rc=%ld expected=%u short_blocks=1\n",
                        (unsigned long long)blocks,
                        (unsigned long long)input_sent,
                        (long)n,(unsigned)STRICT_BLOCK_BYTES);
            } else {
                fprintf(stderr,"ERROR strict write block=%llu input_packet=%llu bytes=%u errno=%d (%s)\n",
                        (unsigned long long)blocks,
                        (unsigned long long)input_sent,
                        (unsigned)STRICT_BLOCK_BYTES,errno,strerror(errno));
            }
            close(fd);fclose(f);return 12;
        }

        input_sent+=got;
        output_sent+=STRICT_BLOCK_PACKETS;
        pad_total+=pad;
        ++blocks;

        expected_ns=(output_sent*TS_SIZE*8ULL*1000000000ULL)/bps;
        elapsed=mono_ns()-start;
        if(expected_ns>elapsed) sleep_ns(expected_ns-elapsed);
    }

    if(ferror(f)) {
        fprintf(stderr,"ERROR input read failure\n");
        close(fd);fclose(f);return 14;
    }

    close(fd);fclose(f);
    printf("DONE_STRICT packets_in=%llu blocks_out=%llu packets_out=%llu pad_null_packets=%llu write_size=%u short_blocks=0 elapsed_ms=%llu\n",
           (unsigned long long)input_sent,
           (unsigned long long)blocks,
           (unsigned long long)output_sent,
           (unsigned long long)pad_total,
           (unsigned)STRICT_BLOCK_BYTES,
           (unsigned long long)((mono_ns()-start)/1000000ULL));
    return input_sent==packets?0:13;
}

/*
 * Exact-unit vehicle run 1 proved that a single 188-byte write opens the
 * correct /dev/mlb/isoTX2 node but is rejected with errno 240/EMSGSIZE.
 *
 * The stock TX driver is launched with -S188 -P64. Before inventing devctl
 * semantics or writing the RCC-side split-partner node directly, probe a
 * bounded set of whole-TS-packet message sizes up to the observed P64 bound.
 * Each candidate is one write on a fresh fd; no persistent state is changed.
 */
static int probe_write_sizes(const char *input,const char *out) {
    static const unsigned candidates[]={1,2,4,8,16,32,64};
    uint8_t buf[MAX_PROBE_PACKETS*TS_SIZE];
    FILE *f=fopen(input,"rb");
    size_t got;
    unsigned i;
    int accepted=0;

    if(!f){perror("fopen probe input");return 1;}
    got=fread(buf,1,sizeof(buf),f);
    fclose(f);
    if(got<sizeof(buf)) {
        fprintf(stderr,"ERROR probe input too short: got=%lu need=%lu\n",
                (unsigned long)got,(unsigned long)sizeof(buf));
        return 2;
    }

    for(i=0;i<sizeof(candidates)/sizeof(candidates[0]);++i) {
        unsigned packets=candidates[i];
        size_t bytes=(size_t)packets*TS_SIZE;
        int fd=open_output(out);
        ssize_t n;

        if(fd<0) {
            printf("PROBE packets=%u bytes=%lu open=FAIL errno=%d (%s)\n",
                   packets,(unsigned long)bytes,errno,strerror(errno));
            continue;
        }

        errno=0;
        n=write(fd,buf,bytes);
        if(n==(ssize_t)bytes) {
            printf("PROBE packets=%u bytes=%lu write=ACCEPTED rc=%ld\n",
                   packets,(unsigned long)bytes,(long)n);
            accepted=(int)packets;
        } else if(n>=0) {
            printf("PROBE packets=%u bytes=%lu write=PARTIAL rc=%ld errno=%d (%s)\n",
                   packets,(unsigned long)bytes,(long)n,errno,strerror(errno));
        } else {
            printf("PROBE packets=%u bytes=%lu write=REJECTED rc=%ld errno=%d (%s)\n",
                   packets,(unsigned long)bytes,(long)n,errno,strerror(errno));
        }
        close(fd);
        sleep_ns(50000000ULL);
    }

    if(accepted) {
        printf("PROBE_RESULT accepted_packets=%d accepted_bytes=%d\n",
               accepted,accepted*TS_SIZE);
        return 0;
    }
    printf("PROBE_RESULT no_candidate_accepted max_packets=%d\n",MAX_PROBE_PACKETS);
    return 12;
}

int main(int argc,char **argv) {
    const char *in;
    FILE *f;
    uint64_t packets=0,pid11=0;

    if(argc==3 && strcmp(argv[1],"--strict-dry-run")==0) {
        f=fopen(argv[2],"rb");
        if(!f){perror("fopen");return 1;}
        {
            int rc=validate(f,&packets,&pid11);
            fclose(f);
            if(rc) return rc;
        }
        print_strict_plan(packets,pid11);
        return pid11?0:5;
    }

    if(argc>=4 && argc<=5 && strcmp(argv[1],"--strict64")==0) {
        uint64_t bps=(argc==5)?strtoull(argv[4],NULL,0):2000000ULL;
        return strict64_stream(argv[2],argv[3],bps);
    }

    if(argc==4 && strcmp(argv[1],"--probe-sizes")==0) {
        f=fopen(argv[2],"rb");
        if(!f){perror("fopen");return 1;}
        {
            int rc=validate(f,&packets,&pid11);
            fclose(f);
            if(rc) return rc;
        }
        printf("PROBE_INPUT packets=%llu pid0x11=%llu output=%s\n",
               (unsigned long long)packets,(unsigned long long)pid11,argv[3]);
        fflush(stdout);
        return probe_write_sizes(argv[2],argv[3]);
    }

    if(argc<3 || strcmp(argv[1],"--validate")==0) {
        if(argc!=3 || strcmp(argv[1],"--validate")!=0) {
            fprintf(stderr,"usage: %s --validate file.ts\n"
                           "       %s --strict-dry-run file.ts\n"
                           "       %s --strict64 file.ts /dev/mlb/isoTX2 [pace_bps]\n"
                           "       %s --probe-sizes file.ts /dev/mlb/isoTX2\n"
                           "       %s file.ts /dev/mlb/isoTX2 [pace_bps] [block_packets]\n",
                    argv[0],argv[0],argv[0],argv[0],argv[0]);
            return 64;
        }
        f=fopen(argv[2],"rb");
        if(!f){perror("fopen");return 1;}
        {
            int rc=validate(f,&packets,&pid11);
            fclose(f);
            if(rc) return rc;
        }
        printf("VALID packets=%llu bytes=%llu pid0x11_packets=%llu\n",
               (unsigned long long)packets,
               (unsigned long long)(packets*TS_SIZE),
               (unsigned long long)pid11);
        return pid11?0:5;
    }

    in=argv[1];
    {
        const char *out=argv[2];
        uint64_t bps=(argc>=4)?strtoull(argv[3],NULL,0):3600000ULL;
        unsigned block_packets=(argc>=5)?(unsigned)strtoul(argv[4],NULL,0):1U;
        int fd;
        uint8_t p[MAX_PROBE_PACKETS*TS_SIZE];
        uint64_t sent=0,start;

        if(bps<100000ULL || bps>12288000ULL) {
            fprintf(stderr,"ERROR pace_bps out of range: %llu\n",(unsigned long long)bps);
            return 65;
        }
        if(block_packets<1 || block_packets>MAX_PROBE_PACKETS) {
            fprintf(stderr,"ERROR block_packets out of range: %u\n",block_packets);
            return 66;
        }
        f=fopen(in,"rb");
        if(!f){perror("fopen input");return 1;}
        if(validate(f,&packets,&pid11)!=0){fclose(f);return 2;}
        rewind(f);
        printf("INPUT packets=%llu pid0x11=%llu pace_bps=%llu block_packets=%u output=%s\n",
               (unsigned long long)packets,(unsigned long long)pid11,
               (unsigned long long)bps,block_packets,out);
        fflush(stdout);

        fd=open_output(out);
        if(fd<0){
            fprintf(stderr,"ERROR open output %s errno=%d (%s)\n",out,errno,strerror(errno));
            fclose(f);return 10;
        }
        start=mono_ns();
        for (;;) {
            size_t got=fread(p,TS_SIZE,block_packets,f);
            uint64_t expected_ns,elapsed;
            size_t bytes;
            unsigned j;
            if(got==0) break;
            bytes=got*TS_SIZE;
            for(j=0;j<got;j++) {
                if(p[j*TS_SIZE]!=0x47) {
                    fprintf(stderr,"ERROR sync lost at packet %llu\n",(unsigned long long)(sent+j));
                    close(fd);fclose(f);return 11;
                }
            }
            if(write_all(fd,p,bytes)!=0){
                fprintf(stderr,"ERROR write block at packet %llu packets=%lu bytes=%lu errno=%d (%s)\n",
                        (unsigned long long)sent,(unsigned long)got,(unsigned long)bytes,
                        errno,strerror(errno));
                close(fd);fclose(f);return 12;
            }
            sent+=got;
            expected_ns=(sent*TS_SIZE*8ULL*1000000000ULL)/bps;
            elapsed=mono_ns()-start;
            if(expected_ns>elapsed) sleep_ns(expected_ns-elapsed);
        }
        close(fd);fclose(f);
        printf("DONE sent_packets=%llu sent_bytes=%llu elapsed_ms=%llu\n",
               (unsigned long long)sent,
               (unsigned long long)(sent*TS_SIZE),
               (unsigned long long)((mono_ns()-start)/1000000ULL));
        return sent==packets?0:13;
    }
}
