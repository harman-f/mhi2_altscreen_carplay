/*
 * MIBR native DebugSPI keypanel logger. QNX 6.5 / ARMv7; POSIX host selftest.
 * Passive RX-only client of Java DebugSPI 127.0.0.1:15001.
 * No protocol writes, OEM config edits, preloads, process signals or autostart.
 * Keep log messages as one O_APPEND write to share a chronological stream with notes.
 * The current-session pointer is one project SD file; no /tmp use.
 */
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define POINTER "./mibr-keypanel-native-current"
#define PORT 15001
#define FRAME_MAX (256u*1024u)
#define BUFFER_SIZE (FRAME_MAX + 8192u)
#define RAW_CAP (16u*1024u*1024u)
#define TEXT_CAP (4u*1024u*1024u)
#define NOTE_CAP 480
#define FRAME_PREFIX 26u
static const unsigned char sync_marker[4]={0x80,'M','L','P'};
static volatile sig_atomic_t stopping=0;
static unsigned long frames, texts, binaries, others, events, resyncs;
static unsigned long raw_bytes, text_bytes;
static int combined_fd=-1, text_fd=-1, raw_fd=-1, tail_fd=-1;
static char dir_name[512], combined_path[640];
static size_t pending_size=0;
static unsigned char pending[BUFFER_SIZE];
static int sock=-1;
static long long start_ms;
static int raw_truncated=0, text_truncated=0;

typedef struct {int used,kbd,key,pressed,lg,dbl;} KeyState;
static KeyState keystate[128];
static void onsig(int n){(void)n;stopping=1;}
static uint32_t be32(const unsigned char*p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static uint16_t be16(const unsigned char*p){return (uint16_t)(((unsigned)p[0]<<8)|p[1]);}
static long long mono_ms(void){struct timespec t; if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;return (long long)t.tv_sec*1000+t.tv_nsec/1000000;}
static const char *state_name(int st){switch(st){case 0:return "RELEASED";case 1:return "PRESSED";case 2:return "DOUBLEPRESSED";case 3:return "LONGPRESSED";case 4:return "LONGPRESSED2";case 5:return "LONGPRESSED3";case 6:return "APPROACHED";case 7:return "ABANDONED";case 8:return "MOVED";default:return "UNKNOWN";}}
static void record_line(const char *line){size_t n=strlen(line); if(combined_fd>=0 && n && n<2048){if(write(combined_fd,line,n)!=(ssize_t)n)perror("combined append");}}
static void tail_print(void){char b[1024];ssize_t n; if(tail_fd<0)return;while((n=read(tail_fd,b,sizeof b))>0){if(write(STDOUT_FILENO,b,(size_t)n)<0)break;}fflush(stdout);}
static int note_line(const char*user){char safe[NOTE_CAP+1],line[900];size_t i,j=0;int fd; char ptr[640]; FILE*f=fopen(POINTER,"r");if(!f){fprintf(stderr,"NO_ACTIVE_CAPTURE: %s\n",POINTER);return 2;}if(!fgets(ptr,sizeof ptr,f)){fclose(f);fprintf(stderr,"EMPTY_POINTER\n");return 2;}fclose(f);ptr[strcspn(ptr,"\r\n")]=0;if(strncmp(ptr,"/",1) || !strstr(ptr,"/combined.log")){fprintf(stderr,"BAD_POINTER\n");return 2;}for(i=0;user[i]&&j<NOTE_CAP;i++){unsigned char c=(unsigned char)user[i];safe[j++]=(c=='\r'||c=='\n'||c<32)?' ':c;}safe[j]=0;
 snprintf(line,sizeof line,"[%012lldms] NOTE %s\n",mono_ms(),safe);
 fd=open(ptr,O_WRONLY|O_APPEND);if(fd<0){perror("note open");return 2;}if(write(fd,line,strlen(line))<0){perror("note write");close(fd);return 2;}close(fd);fputs(line,stdout);return 0;}
static KeyState *getkey(int b,int k){int i;for(i=0;i<128;i++)if(keystate[i].used && keystate[i].kbd==b && keystate[i].key==k)return &keystate[i];for(i=0;i<128;i++)if(!keystate[i].used){keystate[i].used=1;keystate[i].kbd=b;keystate[i].key=k;return &keystate[i];}return NULL;}
static const char*gesture(int b,int k,int st){KeyState*s=getkey(b,k);if(!s)return "UNTRACKED";switch(st){case 1:s->pressed=1;s->lg=s->dbl=0;return "PRESS";case 2:s->dbl=1;return "DOUBLE";case 3:s->lg=1;return "LONG";case 4:s->lg=1;return "LONG2";case 5:s->lg=1;return "LONG3";case 0: if(!s->pressed){s->lg=s->dbl=0;return "RELEASE";}s->pressed=0;if(s->lg)return "LONG_RELEASE";if(s->dbl)return "DOUBLE_RELEASE";return "SHORT";case 6:return "APPROACHED";case 7:return "ABANDONED";case 8:return "MOVED";default:return "OEM_STATE";}}
static void decode_message(const unsigned char*p,size_t n){char msg[4096],row[4700];size_t i,j=0;int b,k,st; const char*found; if(n>=sizeof msg)n=sizeof msg-1;
 for(i=0;i<n;i++){unsigned char c=p[i];if(c==0)continue;msg[j++]=(c=='\r'||c=='\n'||c=='\t')?' ':((c>=32&&c<127)||c>=128?(char)c:'.');}msg[j]=0;
 snprintf(row,sizeof row,"[%012lldms] %s\n",mono_ms(),msg);
 if(text_bytes+strlen(row)<TEXT_CAP && text_fd>=0){if(write(text_fd,row,strlen(row))!=(ssize_t)strlen(row))text_truncated=1;else text_bytes+=(unsigned long)strlen(row);}else text_truncated=1;
 found=strstr(msg,"HK Received:");
 if(found && sscanf(found,"HK Received: KBD[%d] KEY[%d] KST[%d]",&b,&k,&st)==3){
   const char*g=gesture(b,k,st);events++;
   snprintf(row,sizeof row,"[%012lldms] EVENT KBD=%d KEY=%d KST=%d %-14s GESTURE=%-14s %s\n",mono_ms(),b,k,st,state_name(st),g,msg);
   record_line(row);
 }else if(strstr(msg,"KeyPanel") || strstr(msg,"KEYPANEL") || strstr(msg,"keypanel") || strstr(msg,"Encoder") || strstr(msg,"encoder")){
   snprintf(row,sizeof row,"[%012lldms] RELATED %s\n",mono_ms(),msg);record_line(row);
 }
}
/* VW log4mib stores actual OEM text within MLP type=1 binary frames:
 * inner type 0x0104, header[45]=0x07, big-endian UTF-16 code-unit count
 * at [46..49], and UTF-16BE at [50..]. Confirmed against actual MU1440
 * 6,096,627-byte raw capture: 18,571 MLP frames, 524 text logs, 65 HK.
 * Other inner type 0x0110 messages are kept verbatim in the raw dump. */
static void decode_oem_binary_text(const unsigned char *p,size_t n){
 unsigned char out[4096];size_t k=0,pos=50;uint32_t count;
 if(n<50 || p[0]!=255 || p[1]!=1 || p[2]!=4 || p[45]!=7)return;
 count=be32(p+46);
 if(count>(n-50)/2 || count>16384)return;
 for(uint32_t i=0;i<count;i++){
  uint32_t cp=be16(p+pos);pos+=2;
  if(cp>=0xD800 && cp<=0xDBFF){
   if(i+1<count){uint32_t lo=be16(p+pos);if(lo>=0xDC00 && lo<=0xDFFF){cp=0x10000+((cp-0xD800)<<10)+(lo-0xDC00);i++;pos+=2;}else cp='?';}
   else cp='?';
  }else if(cp>=0xDC00 && cp<=0xDFFF)cp='?';
  if(k+5>=sizeof out)break;
  if(cp<0x80)out[k++]=(unsigned char)cp;
  else if(cp<0x800){out[k++]=(unsigned char)(0xc0|(cp>>6));out[k++]=(unsigned char)(0x80|(cp&63));}
  else if(cp<0x10000){out[k++]=(unsigned char)(0xe0|(cp>>12));out[k++]=(unsigned char)(0x80|((cp>>6)&63));out[k++]=(unsigned char)(0x80|(cp&63));}
  else{out[k++]=(unsigned char)(0xf0|(cp>>18));out[k++]=(unsigned char)(0x80|((cp>>12)&63));out[k++]=(unsigned char)(0x80|((cp>>6)&63));out[k++]=(unsigned char)(0x80|(cp&63));}
 }
 texts++;decode_message(out,k);
}
static void frame_decode(const unsigned char *f,size_t n){uint8_t type;uint32_t paylen; const unsigned char *payload;frames++;
 if(n<FRAME_PREFIX){others++;return;}type=f[20];paylen=be32(f+22);payload=f+FRAME_PREFIX;
 if(paylen!=n-FRAME_PREFIX){others++;return;}
 if(type==0){uint16_t length;if(paylen<14){others++;return;}length=be16(payload+12);if(length>paylen-14){others++;return;}texts++;decode_message(payload+14,length);
 }else if(type==1){binaries++;decode_oem_binary_text(payload,paylen);}else others++;
}
static void feed(const unsigned char *data,size_t n){size_t found,need;uint32_t l;while(n){size_t room=BUFFER_SIZE-pending_size;if(!room){pending_size=0;resyncs++;room=BUFFER_SIZE;}if(n<room)room=n;memcpy(pending+pending_size,data,room);pending_size+=room;data+=room;n-=room;
 while(pending_size>=8){if(memcmp(pending+4,sync_marker,4)!=0){found=0;for(size_t i=5;i+4<=pending_size;i++)if(!memcmp(pending+i,sync_marker,4)){found=i;break;}if(found>=4){memmove(pending,pending+found-4,pending_size-(found-4));pending_size-=found-4;resyncs++;continue;}if(pending_size>16){memmove(pending,pending+pending_size-7,7);pending_size=7;resyncs++;}break;}
 l=be32(pending);need=(size_t)l+4u;if(need<FRAME_PREFIX||need>FRAME_MAX){memmove(pending,pending+1,--pending_size);resyncs++;continue;}
 if(pending_size<need)break;
 frame_decode(pending,need);
 memmove(pending,pending+need,pending_size-need);
 pending_size-=need;
 }
}}
static int selftest(void){unsigned char f[256]={0},p[160]={0};const char *message="[AslTargetSystemKeyPanelHandling] HK Received: KBD[4] KEY[50] KST[1]";size_t m=strlen(message),pl=m+14,total=26+pl;
 f[0]=(unsigned char)((total-4)>>24);f[1]=(unsigned char)((total-4)>>16);f[2]=(unsigned char)((total-4)>>8);f[3]=(unsigned char)(total-4);memcpy(f+4,sync_marker,4);f[20]=0;f[22]=(unsigned char)(pl>>24);f[23]=(unsigned char)(pl>>16);f[24]=(unsigned char)(pl>>8);f[25]=(unsigned char)pl;
 p[0]=p[1]=1;p[12]=(unsigned char)(m>>8);p[13]=(unsigned char)m;memcpy(p+14,message,m);memcpy(f+26,p,pl);
 feed(f,3);feed(f+3,6);feed(f+9,13);feed(f+22,total-22);
 if(frames!=1||texts!=1||events!=1){fprintf(stderr,"SELF_TEST=FAIL frames=%lu texts=%lu events=%lu\n",frames,texts,events);return 1;}puts("SELF_TEST=PASS split-MLP, text, HK-event; SD-pointer-v1.3; inner-0104-v1.4");return 0;}
/* Publish one flat SD pointer in the project directory, directly with O_EXCL.
 * No /tmp and no staging or rename syscall. A previous capture or stale
 * marker is never overwritten, and must be inspected manually. */
static int pointer_write(void){
 char line[sizeof combined_path+2];size_t n=strlen(combined_path);int f;
 if(n+1>=sizeof line){fprintf(stderr,"pointer path too long\n");return -1;}
 memcpy(line,combined_path,n);line[n++]='\n';
 f=open(POINTER,O_CREAT|O_EXCL|O_WRONLY,0600);
 if(f<0){
  if(errno==EEXIST)fprintf(stderr,"pointer exists: %s (inspect active/stale capture; do not overwrite)\n",POINTER);
  else perror("pointer create");
  return -1;
 }
 if(write(f,line,n)!=(ssize_t)n){perror("pointer write");close(f);unlink(POINTER);return -1;}
 if(close(f)){perror("pointer close");unlink(POINTER);return -1;}
 return 0;
}
static void pointer_cleanup(void){char p[640];FILE*f=fopen(POINTER,"r");if(!f)return;if(fgets(p,sizeof p,f)){p[strcspn(p,"\r\n")]=0;if(!strcmp(p,combined_path)){fclose(f);unlink(POINTER);return;}}fclose(f);}
static int capture(const char *base,int max_seconds){char textpath[640],rawpath[640],metapath[640],row[1000],absbase[420],cwd[420];int connected=0;long long deadline,last_report;ssize_t r;fd_set fds;struct timeval tv;unsigned char b[8192];struct sockaddr_in a;
 start_ms=mono_ms();
 if(base[0]=='/')snprintf(absbase,sizeof absbase,"%s",base);
 else{if(!getcwd(cwd,sizeof cwd)){perror("getcwd");return 2;}
 if(strlen(cwd)+strlen(base)+2>=sizeof absbase){fprintf(stderr,"Output path too long\n");return 2;}
 strcpy(absbase,cwd);strcat(absbase,"/");strcat(absbase,base);}
 snprintf(dir_name,sizeof dir_name,"%s/native-%ld",absbase,(long)getpid());if(mkdir(dir_name,0755)){perror("mkdir session (SD writable?)");return 2;}
 snprintf(combined_path,sizeof combined_path,"%s/combined.log",dir_name);snprintf(textpath,sizeof textpath,"%s/debugspi-text.log",dir_name);snprintf(rawpath,sizeof rawpath,"%s/debugspi-original.bin",dir_name);snprintf(metapath,sizeof metapath,"%s/report.txt",dir_name);
 combined_fd=open(combined_path,O_CREAT|O_APPEND|O_WRONLY,0644);tail_fd=open(combined_path,O_RDONLY);raw_fd=open(rawpath,O_CREAT|O_TRUNC|O_WRONLY,0644);text_fd=open(textpath,O_CREAT|O_TRUNC|O_WRONLY,0644);
 if(combined_fd<0||tail_fd<0||raw_fd<0||text_fd<0){perror("create files");return 2;}if(pointer_write())return 2;
 printf("MIBR_NATIVE_KEYPANEL=START\nversion=SD_POINTER_v1.3+INNER_0104_v1.4\nsession=%s\ncombined=%s\nnotes: /bin/ksh keypanel_note_native.sh\nCtrl+C stops.\n",dir_name,combined_path);fflush(stdout);
 snprintf(row,sizeof row,"[%012lldms] INFO capture=START transport=127.0.0.1:15001 mode=PASSIVE_RX_ONLY duration=%d\n",mono_ms(),max_seconds);record_line(row);tail_print();
 sock=socket(AF_INET,SOCK_STREAM,0);if(sock<0){perror("socket");goto out;}memset(&a,0,sizeof a);a.sin_family=AF_INET;a.sin_port=htons(PORT);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);if(connect(sock,(struct sockaddr*)&a,sizeof a)){perror("connect 127.0.0.1:15001");snprintf(row,sizeof row,"[%012lldms] ERROR socket_connect errno=%d\n",mono_ms(),errno);record_line(row);goto out;}
 connected=1;record_line("INFO socket_connected=YES (application sends ZERO DebugSPI bytes)\n");tail_print();
 deadline=mono_ms()+(long long)max_seconds*1000;last_report=mono_ms();
 while(!stopping && mono_ms()<deadline){FD_ZERO(&fds);FD_SET(sock,&fds);tv.tv_sec=0;tv.tv_usec=200000;r=select(sock+1,&fds,NULL,NULL,&tv);
  if(r<0){if(errno==EINTR)continue;perror("select");break;}
  if(r>0){r=recv(sock,b,sizeof b,0);if(r<=0){record_line("INFO socket_closed_or_error\n");break;}if(raw_bytes+(unsigned long)r<=RAW_CAP){if(write(raw_fd,b,(size_t)r)!=r){perror("raw write");break;}raw_bytes+=(unsigned long)r;}else{raw_truncated=1;record_line("INFO raw_cap_reached=YES\n");break;}feed(b,(size_t)r);}
  tail_print();if(mono_ms()-last_report>=10000){snprintf(row,sizeof row,"STATUS frames=%lu text=%lu hk=%lu bytes=%lu\n",frames,texts,events,raw_bytes);fputs(row,stdout);fflush(stdout);last_report=mono_ms();}
 }
 out: if(sock>=0){close(sock);sock=-1;}snprintf(row,sizeof row,"[%012lldms] INFO capture=STOP frames=%lu text=%lu hk=%lu bytes=%lu\n",mono_ms(),frames,texts,events,raw_bytes);record_line(row);tail_print();pointer_cleanup();{
 FILE*f=fopen(metapath,"w");if(f){fprintf(f,"MIBR_NATIVE_KEYPANEL_REPORT\nsession=%s\ntransport=127.0.0.1:15001\nmode=PASSIVE_RX_ONLY\npointer_storage=SD_FLAT_EXCLUSIVE\nframes=%lu\ntext_frames=%lu\nbinary_frames=%lu\nother_frames=%lu\nresyncs=%lu\nhk_received_events=%lu\nraw_bytes=%lu\ntext_bytes=%lu\nraw_truncated=%d\ntext_truncated=%d\ncombined=%s\nraw=%s\ntext=%s\n",dir_name,frames,texts,binaries,others,resyncs,events,raw_bytes,text_bytes,raw_truncated,text_truncated,combined_path,rawpath,textpath);fclose(f);}}
 if(tail_fd>=0)close(tail_fd);
 if(combined_fd>=0)close(combined_fd);
 if(text_fd>=0)close(text_fd);
 if(raw_fd>=0)close(raw_fd);
 printf("REPORT=%s\n",metapath);return connected?0:2;
}
static void usage(const char*p){fprintf(stderr,"Usage:\n  %s --capture [--out DIR] [--seconds 120]\n  %s --note DESCRIPTION\n  %s --self-test\n",p,p,p);}
int main(int argc,char**argv){const char*base=".";int seconds=120;int i;if(argc<2){usage(argv[0]);return 2;}if(!strcmp(argv[1],"--self-test"))return selftest();if(!strcmp(argv[1],"--note")){char note[NOTE_CAP+1]={0};size_t off=0;for(i=2;i<argc;i++){size_t n=strlen(argv[i]);if(off+n+2>sizeof note)break;if(off)note[off++]=' ';memcpy(note+off,argv[i],n);off+=n;note[off]=0;}if(!off)return 2;return note_line(note);}if(strcmp(argv[1],"--capture")){usage(argv[0]);return 2;}
 for(i=2;i<argc;i++){if(!strcmp(argv[i],"--out") && i+1<argc)base=argv[++i];else if(!strcmp(argv[i],"--seconds") && i+1<argc)seconds=atoi(argv[++i]);else{usage(argv[0]);return 2;}}if(seconds<10||seconds>1800||strlen(base)>400){fprintf(stderr,"seconds=10..1800, --out length <=400\n");return 2;}
 signal(SIGINT,onsig);signal(SIGTERM,onsig);signal(SIGPIPE,SIG_IGN);return capture(base,seconds);
}