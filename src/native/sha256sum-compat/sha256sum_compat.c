/*
 * Minimal SHA-256 file utility for MU1440/QNX 6.5.
 *
 * Runtime role: deployment-local compatibility helper for QNX 6.5 ARMv7.
 *
 * Interface intentionally matches the subset U2 needs:
 *   sha256sum FILE [FILE ...]
 * Output:
 *   <64 lowercase hex chars><two spaces><path>
 *
 * No -c/--check support is required by the developer deployment.
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t data[64];
    uint32_t datalen;
    uint64_t bitlen;
    uint32_t state[8];
} sha256_ctx;

#define ROTR(a,b) (((a) >> (b)) | ((a) << (32-(b))))
#define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x) (ROTR((x),2) ^ ROTR((x),13) ^ ROTR((x),22))
#define EP1(x) (ROTR((x),6) ^ ROTR((x),11) ^ ROTR((x),25))
#define SIG0(x) (ROTR((x),7) ^ ROTR((x),18) ^ ((x) >> 3))
#define SIG1(x) (ROTR((x),17) ^ ROTR((x),19) ^ ((x) >> 10))

static const uint32_t k[64] = {
  0x428a2f98U,0x71374491U,0xb5c0fbcfU,0xe9b5dba5U,0x3956c25bU,0x59f111f1U,0x923f82a4U,0xab1c5ed5U,
  0xd807aa98U,0x12835b01U,0x243185beU,0x550c7dc3U,0x72be5d74U,0x80deb1feU,0x9bdc06a7U,0xc19bf174U,
  0xe49b69c1U,0xefbe4786U,0x0fc19dc6U,0x240ca1ccU,0x2de92c6fU,0x4a7484aaU,0x5cb0a9dcU,0x76f988daU,
  0x983e5152U,0xa831c66dU,0xb00327c8U,0xbf597fc7U,0xc6e00bf3U,0xd5a79147U,0x06ca6351U,0x14292967U,
  0x27b70a85U,0x2e1b2138U,0x4d2c6dfcU,0x53380d13U,0x650a7354U,0x766a0abbU,0x81c2c92eU,0x92722c85U,
  0xa2bfe8a1U,0xa81a664bU,0xc24b8b70U,0xc76c51a3U,0xd192e819U,0xd6990624U,0xf40e3585U,0x106aa070U,
  0x19a4c116U,0x1e376c08U,0x2748774cU,0x34b0bcb5U,0x391c0cb3U,0x4ed8aa4aU,0x5b9cca4fU,0x682e6ff3U,
  0x748f82eeU,0x78a5636fU,0x84c87814U,0x8cc70208U,0x90befffaU,0xa4506cebU,0xbef9a3f7U,0xc67178f2U
};

static void transform(sha256_ctx *c, const uint8_t data[64]) {
    uint32_t a,b,cc,d,e,f,g,h,i,j,t1,t2,m[64];
    for (i=0,j=0; i<16; ++i,j+=4)
        m[i]=((uint32_t)data[j]<<24)|((uint32_t)data[j+1]<<16)|((uint32_t)data[j+2]<<8)|data[j+3];
    for (; i<64; ++i) m[i]=SIG1(m[i-2])+m[i-7]+SIG0(m[i-15])+m[i-16];
    a=c->state[0]; b=c->state[1]; cc=c->state[2]; d=c->state[3];
    e=c->state[4]; f=c->state[5]; g=c->state[6]; h=c->state[7];
    for (i=0; i<64; ++i) {
        t1=h+EP1(e)+CH(e,f,g)+k[i]+m[i];
        t2=EP0(a)+MAJ(a,b,cc);
        h=g; g=f; f=e; e=d+t1; d=cc; cc=b; b=a; a=t1+t2;
    }
    c->state[0]+=a; c->state[1]+=b; c->state[2]+=cc; c->state[3]+=d;
    c->state[4]+=e; c->state[5]+=f; c->state[6]+=g; c->state[7]+=h;
}

static void init(sha256_ctx *c) {
    c->datalen=0; c->bitlen=0;
    c->state[0]=0x6a09e667U; c->state[1]=0xbb67ae85U; c->state[2]=0x3c6ef372U; c->state[3]=0xa54ff53aU;
    c->state[4]=0x510e527fU; c->state[5]=0x9b05688cU; c->state[6]=0x1f83d9abU; c->state[7]=0x5be0cd19U;
}

static void update(sha256_ctx *c, const uint8_t *data, size_t len) {
    size_t i;
    for (i=0; i<len; ++i) {
        c->data[c->datalen++]=data[i];
        if (c->datalen==64) {
            transform(c,c->data);
            c->bitlen += 512;
            c->datalen=0;
        }
    }
}

static void final(sha256_ctx *c, uint8_t out[32]) {
    uint32_t i=c->datalen;
    c->data[i++]=0x80;
    if (i>56) {
        while (i<64) c->data[i++]=0;
        transform(c,c->data);
        i=0;
    }
    while (i<56) c->data[i++]=0;
    c->bitlen += (uint64_t)c->datalen * 8U;
    c->data[63]=(uint8_t)c->bitlen;
    c->data[62]=(uint8_t)(c->bitlen>>8);
    c->data[61]=(uint8_t)(c->bitlen>>16);
    c->data[60]=(uint8_t)(c->bitlen>>24);
    c->data[59]=(uint8_t)(c->bitlen>>32);
    c->data[58]=(uint8_t)(c->bitlen>>40);
    c->data[57]=(uint8_t)(c->bitlen>>48);
    c->data[56]=(uint8_t)(c->bitlen>>56);
    transform(c,c->data);
    for (i=0;i<4;++i) {
        out[i]      =(uint8_t)(c->state[0]>>(24-i*8));
        out[i+4]    =(uint8_t)(c->state[1]>>(24-i*8));
        out[i+8]    =(uint8_t)(c->state[2]>>(24-i*8));
        out[i+12]   =(uint8_t)(c->state[3]>>(24-i*8));
        out[i+16]   =(uint8_t)(c->state[4]>>(24-i*8));
        out[i+20]   =(uint8_t)(c->state[5]>>(24-i*8));
        out[i+24]   =(uint8_t)(c->state[6]>>(24-i*8));
        out[i+28]   =(uint8_t)(c->state[7]>>(24-i*8));
    }
}

void mibr_sha256_bytes(const void *data, size_t size, char hex[65]) {
    sha256_ctx c;
    uint8_t digest[32];
    unsigned i;
    init(&c); update(&c, data, size); final(&c, digest);
    for (i=0;i<32;++i) sprintf(hex+i*2,"%02x",digest[i]);
    hex[64]=0;
}

#ifndef MIBR_SHA256_LIBRARY_ONLY
static int hash_file(const char *path, char hex[65]) {
    FILE *f=fopen(path,"rb");
    uint8_t buf[4096], digest[32];
    size_t n, i;
    sha256_ctx c;

    if (!f) {
        fprintf(stderr,"sha256sum: %s: %s\n",path,strerror(errno));
        return 1;
    }

    init(&c);
    while ((n=fread(buf,1,sizeof(buf),f))>0) update(&c,buf,n);
    if (ferror(f)) {
        fprintf(stderr,"sha256sum: %s: read error\n",path);
        fclose(f);
        return 1;
    }
    fclose(f);

    final(&c,digest);
    for (i=0;i<32;++i) sprintf(hex+i*2,"%02x",digest[i]);
    hex[64]='\0';
    return 0;
}

int main(int argc, char **argv) {
    int rc=0, i;
    char hex[65];

    if (argc<2) {
        fprintf(stderr,"usage: sha256sum FILE [FILE ...]\n");
        return 2;
    }

    for (i=1;i<argc;++i) {
        if (hash_file(argv[i],hex)!=0) {
            rc=1;
            continue;
        }
        printf("%s  %s\n",hex,argv[i]);
    }
    return rc;
}
#endif
