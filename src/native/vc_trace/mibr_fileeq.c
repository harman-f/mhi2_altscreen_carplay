/* MU1440 VC R2 byte-exact file equality helper, read-only.
 * Exit 0=same, 1=different, 2=usage/I/O error. No writes to input files.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#define BLOCK 4096
static ssize_t read_some(int fd, unsigned char *b, size_t n) {
    ssize_t k;
    do { k = read(fd,b,n); } while(k<0 && errno==EINTR);
    return k;
}
int main(int argc,char **argv) {
    int a=-1,b=-1,rc=2;
    struct stat sa,sb;
    unsigned char x[BLOCK],y[BLOCK];
    if(argc!=3) { fprintf(stderr,"usage: mibr-fileeq FILE1 FILE2\n");return 2; }
    if((a=open(argv[1],O_RDONLY))<0 || (b=open(argv[2],O_RDONLY))<0) {
        perror("mibr-fileeq open");goto done;
    }
    if(fstat(a,&sa) || fstat(b,&sb) || !S_ISREG(sa.st_mode) || !S_ISREG(sb.st_mode)) {
        fprintf(stderr,"mibr-fileeq: inputs must be readable regular files\n");goto done;
    }
    if(sa.st_size!=sb.st_size) {rc=1;goto done;}
    for(;;) {
        ssize_t n=read_some(a,x,BLOCK);
        if(n<0) {perror("mibr-fileeq read first");goto done;}
        if(n==0) {unsigned char byte;ssize_t m=read_some(b,&byte,1);if(m<0){perror("mibr-fileeq read last");goto done;}rc=(m==0)?0:1;goto done;}
        size_t got=0;
        while(got<(size_t)n) {
            ssize_t m=read_some(b,y+got,(size_t)n-got);
            if(m<0) {perror("mibr-fileeq read second");goto done;}
            if(m==0) {rc=1;goto done;}
            got+=(size_t)m;
        }
        if(memcmp(x,y,(size_t)n)!=0) {rc=1;goto done;}
    }
done:
    if(a>=0)close(a);
    if(b>=0)close(b);
    return rc;
}
