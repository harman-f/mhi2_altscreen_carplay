#define _POSIX_C_SOURCE 200809L
#include "../native/mibr_gps_demo_mode.h"
#include "../native/mibr_gps_demo_ipc.h"
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static void put(const char *path,const char *text,mode_t mode){int fd=open(path,O_WRONLY|O_CREAT|O_TRUNC,mode);assert(fd>=0);assert(write(fd,text,strlen(text))==(ssize_t)strlen(text));assert(fchmod(fd,mode)==0);close(fd);}
static void writer(const char *mode){unsigned i;for(i=0;i<200;i++)if(mibr_gps_demo_mode_write(mode))_exit(2);_exit(0);}
int main(void){
    char mode[32],reply[128],buf[64];struct stat st;int fd,status;ssize_t n;pid_t a,b;
    const char *path=MIBR_GPS_DEMO_MODE_FILE;const char *other="/tmp/mibr-gps-demo-choice-test-target";
    unlink(path);unlink(other);
    assert(mibr_gps_demo_mode_read(mode)==0&&!strcmp(mode,"OFF"));
    assert(mibr_gps_demo_mode_write("BERLIN_DEMO")==0);
    assert(mibr_gps_demo_mode_read(mode)==0&&!strcmp(mode,"BERLIN_DEMO"));
    assert(stat(path,&st)==0&&S_ISREG(st.st_mode)&&st.st_uid==0&&(st.st_mode&0777)==0600);
    fd=open(path,O_RDONLY);assert(fd>=0);n=read(fd,buf,sizeof(buf)-1);close(fd);assert(n>0);buf[n]=0;
    assert(!strcmp(buf,"MIBR_GPS_DEMO/1\nBERLIN_DEMO\n"));
    /* SET stores a manual choice without an owner socket and ignores old epoch. */
    assert(mibr_gps_demo_ipc(NULL,"SET","HAMBURG_DEMO","legacy-epoch",reply,sizeof(reply))==0);
    assert(!strcmp(reply,"OK HAMBURG_DEMO 0 0 0"));
    assert(mibr_gps_demo_ipc(NULL,"GET",NULL,NULL,reply,sizeof(reply))==0);
    assert(!strcmp(reply,"OK HAMBURG_DEMO 0 0 0"));
    assert(mibr_gps_demo_mode_write("OFF")==0);
    assert(mibr_gps_demo_mode_read(mode)==0&&!strcmp(mode,"OFF"));
    assert(mibr_gps_demo_ipc(NULL,"SET","SCHWALEFELD_DEMO",NULL,reply,sizeof(reply))==0);
    assert(!strcmp(reply,"OK SCHWALEFELD_DEMO 0 0 0"));
    assert(mibr_gps_demo_ipc(NULL,"GET",NULL,NULL,reply,sizeof(reply))==0);
    assert(!strcmp(reply,"OK SCHWALEFELD_DEMO 0 0 0"));
    assert(mibr_gps_demo_ipc(NULL,"SET","WINTERBERG_DEMO",NULL,reply,sizeof(reply))==0);
    assert(!strcmp(reply,"OK WINTERBERG_DEMO 0 0 0"));
    assert(mibr_gps_demo_mode_read(mode)==0&&!strcmp(mode,"WINTERBERG_DEMO"));
    assert(mibr_gps_demo_mode_write("SCHWALEFELD_DEMO")==0);
    assert(mibr_gps_demo_mode_read(mode)==0&&!strcmp(mode,"SCHWALEFELD_DEMO"));
    assert(mibr_gps_demo_mode_write("WINTERBERG_DEMO")==0);
    assert(mibr_gps_demo_mode_read(mode)==0&&!strcmp(mode,"WINTERBERG_DEMO"));
    assert(mibr_gps_demo_mode_write("OFF")==0);
    assert(mibr_gps_demo_mode_write("UNKNOWN")!=0);
    /* Malformed content is rejected, not interpreted as OFF. */
    put(path,"MIBR_GPS_DEMO/2\nBERLIN_DEMO\n",0600);
    assert(mibr_gps_demo_mode_read(mode)!=0);
    /* Group/world-readable or writable files are not trusted or replaced. */
    put(path,"MIBR_GPS_DEMO/1\nOFF\n",0644);
    assert(mibr_gps_demo_mode_read(mode)!=0);
    assert(mibr_gps_demo_mode_write("OFF")!=0);
    unlink(path);
    put(other,"MIBR_GPS_DEMO/1\nOFF\n",0600);
    assert(symlink(other,path)==0);
    assert(mibr_gps_demo_mode_read(mode)!=0);
    assert(mibr_gps_demo_mode_write("BERLIN_DEMO")!=0);
    unlink(path);unlink(other);
    /* QNX direct-flat-file behavior: concurrent readers/writers must only
       observe complete records despite the underlying file being truncated. */
    assert(mibr_gps_demo_mode_write("HAMBURG_DEMO")==0);
    assert(mibr_gps_demo_mode_write("BERLIN_DEMO")==0);
    assert(mibr_gps_demo_mode_read(mode)==0&&!strcmp(mode,"BERLIN_DEMO"));
    assert(stat(path,&st)==0&&(st.st_mode&0777)==0600);
    a=fork();assert(a>=0);if(!a)writer("BERLIN_DEMO");
    b=fork();assert(b>=0);if(!b)writer("HAMBURG_DEMO");
    {
        unsigned i;for(i=0;i<1000;i++){
            assert(mibr_gps_demo_mode_read(mode)==0);
            assert(!strcmp(mode,"BERLIN_DEMO")||!strcmp(mode,"HAMBURG_DEMO"));
        }
    }
    assert(waitpid(a,&status,0)==a&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
    assert(waitpid(b,&status,0)==b&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
    assert(mibr_gps_demo_mode_read(mode)==0);
    assert(!strcmp(mode,"BERLIN_DEMO")||!strcmp(mode,"HAMBURG_DEMO"));
    /* A well-formed lock from a process that has exited is reclaimable. */
    {
        char lock[512],owner[48];pid_t dead=fork();
        assert(dead>=0);if(!dead)_exit(0);
        assert(waitpid(dead,&status,0)==dead&&WIFEXITED(status));
        assert(snprintf(lock,sizeof(lock),"%s.lock",path)>0);
        assert(snprintf(owner,sizeof(owner),"%ld\n",(long)dead)>0);
        put(lock,owner,0600);
        assert(mibr_gps_demo_mode_write("OFF")==0);
    }
    unlink(path);
    puts("MIBR_GPS_DEMO_MODE_TEST_PASS");return 0;
}
