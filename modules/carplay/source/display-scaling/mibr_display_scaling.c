/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded parser and guarded CAS store for ZoomFactor and physical-size presets.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_display_scaling.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define FILE_CAP 256u
#define PATH_CAP 512u
static const char *const ids[] = {
    "scaling.main.zoomFactor", "scaling.cluster.zoomFactor",
    "scaling.cluster.physicalSize", "scaling.main.physicalSize"
};
static const char *const values[] = {"AUTO","70","85","100","125","150"};
static const char *const physicals[] = {"BASE","P20","P30","P50"}; /* = 100/120/130/150 % */
static int fail(char *e,size_t cap,const char *s){
    if(e&&cap)snprintf(e,cap,"%s",s);
    return -1;
}
int mibr_display_scaling_id_valid(const char *id){
    return id&&(!strcmp(id,ids[0])||!strcmp(id,ids[1])||!strcmp(id,ids[2])||!strcmp(id,ids[3]));
}
int mibr_display_scaling_value_valid(const char *value){
    unsigned i;if(!value)return 0;
    for(i=0;i<sizeof(values)/sizeof(values[0]);i++)if(!strcmp(value,values[i]))return 1;
    return 0;
}
/* r15j: physical size = percent of the display's base millimetres, 50..200 in 10 % steps.
 * The legacy presets stay the canonical spelling of their percentages (BASE=100, P20=120,
 * P30=130, P50=150), so every file an older build wrote stays valid and every value an
 * older build can read is still written in its old spelling. The other twelve steps are
 * the plain percentage ("50".."200"); "100"/"120"/"130"/"150" are non-canonical. */
int mibr_display_physical_percent(const char *value){
    unsigned i;int p=0;
    if(!value)return -1;
    for(i=0;i<sizeof(physicals)/sizeof(physicals[0]);i++)
        if(!strcmp(value,physicals[i]))return i==0?100:i==1?120:i==2?130:150;
    if(!value[0]||value[0]=='0'||strlen(value)>3)return -1;
    for(i=0;value[i];i++){if(value[i]<'0'||value[i]>'9')return -1;p=p*10+(value[i]-'0');}
    if(p<MIBR_DISPLAY_PHYSICAL_PERCENT_MIN||p>MIBR_DISPLAY_PHYSICAL_PERCENT_MAX||p%10)return -1;
    if(p==100||p==120||p==130||p==150)return -1;
    return p;
}
int mibr_display_physical_value_valid(const char *value){
    return mibr_display_physical_percent(value)>0;
}
static int scale_mm(int base,int percent,int *out){
    int64_t v;
    if(base<=0||percent<=0)return -1;
    /* Nearest integer, half up. 100 % is exact. */
    v=((int64_t)base*percent+50)/100;
    if(v<=0||v>INT32_MAX)return -1;
    *out=(int)v;return 0;
}
int mibr_display_physical_dimensions(const char *value,int *width_mm,int *height_mm){
    int percent=mibr_display_physical_percent(value),w,h;
    if(percent<=0||!width_mm||!height_mm)return -1;
    /* Synthetic cluster baseline 200x74 mm; the presets keep their values
     * (P20 240x89, P30 260x96, P50 300x111). */
    if(scale_mm(200,percent,&w)||scale_mm(74,percent,&h))return -1;
    *width_mm=w;*height_mm=h;
    return 0;
}
int mibr_display_main_physical_dimensions(const char *value,int original_width_mm,int original_height_mm,
    int *width_mm,int *height_mm){
    int percent=mibr_display_physical_percent(value),w,h;
    if(percent<=0||original_width_mm<=0||original_height_mm<=0||!width_mm||!height_mm)return -1;
    if(scale_mm(original_width_mm,percent,&w)||scale_mm(original_height_mm,percent,&h))return -1;
    *width_mm=w;*height_mm=h;
    return 0;
}
static int parse_revision(const char *p,size_t n,uint64_t *out){
    uint64_t v=0;size_t i;unsigned d;
    if(!n||(n>1&&p[0]=='0'))return -1;
    for(i=0;i<n;i++){
        if(p[i]<'0'||p[i]>'9')return -1;
        d=(unsigned)(p[i]-'0');if(v>(UINT64_MAX-d)/10u)return -1;
        v=v*10u+d;
    }
    *out=v;return 0;
}
static int read_exact_file(const char *path,char data[FILE_CAP+1],size_t *length){
    struct stat before,after;ssize_t got;size_t used=0;int fd;
    if(lstat(path,&before))return errno==ENOENT?1:-1;
    if(!S_ISREG(before.st_mode)||before.st_size<1||before.st_size>(off_t)FILE_CAP||
       (before.st_mode&022)!=0)return -1;
    fd=open(path,O_RDONLY);if(fd<0)return -1;
    if(fstat(fd,&after)||!S_ISREG(after.st_mode)||before.st_dev!=after.st_dev||
       before.st_ino!=after.st_ino||after.st_size!=before.st_size){close(fd);return -1;}
    while(used<(size_t)after.st_size){
        got=read(fd,data+used,(size_t)after.st_size-used);
        if(got<0&&errno==EINTR)continue;
        if(got<=0){close(fd);return -1;}used+=(size_t)got;
    }
    if(close(fd)||used!=(size_t)before.st_size)return -1;
    data[used]=0;*length=used;return 0;
}
static int decode_file(const char *data,size_t n,struct mibr_display_scaling_state *out){
    const char *line[6];size_t width[6],at=0,i=0;uint64_t rev;
    char canonical[FILE_CAP+1];int written,v2;
    while(at<n&&i<6){
        const char *end=(const char*)memchr(data+at,'\n',n-at);
        if(!end)return -1;
        line[i]=data+at;width[i]=(size_t)(end-(data+at));at=(size_t)(end-data)+1;i++;
    }
    if(at!=n||memchr(data,0,n)||memchr(data,'\r',n)||!i)return -1;
    {int v3=width[0]==14&&!memcmp(line[0],"MIBR_SCALING/3",14);
    v2=width[0]==14&&!memcmp(line[0],"MIBR_SCALING/2",14);
    if(!v3&&!v2&&(width[0]!=14||memcmp(line[0],"MIBR_SCALING/1",14)))return -1;
    if(i!=(size_t)(v3?6:v2?5:4)||width[1]<10||memcmp(line[1],"revision=",9)||
       width[2]<6||memcmp(line[2],"main=",5)||
       width[3]<8||memcmp(line[3],"cluster=",8)||
       ((v2||v3)&&(width[4]<10||memcmp(line[4],"physical=",9)))||
       (v3&&(width[5]<15||memcmp(line[5],"main_physical=",14))))return -1;
    if(parse_revision(line[1]+9,width[1]-9,&rev)||
       width[2]-5>=MIBR_DISPLAY_SCALING_VALUE_CAP||
       width[3]-8>=MIBR_DISPLAY_SCALING_VALUE_CAP||
       ((v2||v3)&&width[4]-9>=MIBR_DISPLAY_SCALING_VALUE_CAP)||
       (v3&&width[5]-14>=MIBR_DISPLAY_SCALING_VALUE_CAP))return -1;
    memcpy(out->main,line[2]+5,width[2]-5);out->main[width[2]-5]=0;
    memcpy(out->cluster,line[3]+8,width[3]-8);out->cluster[width[3]-8]=0;
    if(v2||v3){memcpy(out->physical,line[4]+9,width[4]-9);out->physical[width[4]-9]=0;}
    else strcpy(out->physical,"BASE");
    if(v3){memcpy(out->main_physical,line[5]+14,width[5]-14);out->main_physical[width[5]-14]=0;}
    else strcpy(out->main_physical,"BASE");
    if(!mibr_display_scaling_value_valid(out->main)||
       !mibr_display_scaling_value_valid(out->cluster)||
       !mibr_display_physical_value_valid(out->physical)||!mibr_display_physical_value_valid(out->main_physical))return -1;
    written=v3?snprintf(canonical,sizeof(canonical),
        "MIBR_SCALING/3\nrevision=%llu\nmain=%s\ncluster=%s\nphysical=%s\nmain_physical=%s\n",
        (unsigned long long)rev,out->main,out->cluster,out->physical,out->main_physical):
        v2?snprintf(canonical,sizeof(canonical),
        "MIBR_SCALING/2\nrevision=%llu\nmain=%s\ncluster=%s\nphysical=%s\n",
        (unsigned long long)rev,out->main,out->cluster,out->physical):
        snprintf(canonical,sizeof(canonical),
        "MIBR_SCALING/1\nrevision=%llu\nmain=%s\ncluster=%s\n",
        (unsigned long long)rev,out->main,out->cluster);
    if(written<0||(size_t)written!=n||memcmp(canonical,data,n))return -1;
    out->revision=rev;out->stored=1;return 0;}
}
int mibr_display_scaling_load(const char *path,
    struct mibr_display_scaling_state *out,char *error,size_t error_cap){
    char data[FILE_CAP+1];size_t n=0;int rc;
    if(!path||path[0]!='/'||strlen(path)>=PATH_CAP||!out)
        return fail(error,error_cap,"INVALID_PATH");
    memset(out,0,sizeof(*out));strcpy(out->main,"AUTO");strcpy(out->cluster,"AUTO");strcpy(out->physical,"BASE");strcpy(out->main_physical,"BASE");
    rc=read_exact_file(path,data,&n);
    if(rc==1){if(error&&error_cap)error[0]=0;return 0;}
    if(rc<0)return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    if(decode_file(data,n,out))return fail(error,error_cap,"INVALID_SCALING_FILE");
    if(error&&error_cap)error[0]=0;
    return 0;
}
int mibr_display_scaling_advertised_load(const char *path,
    const struct mibr_display_scaling_state *desired,
    struct mibr_display_scaling_state *advertised){
    char data[FILE_CAP+1],canonical[FILE_CAP+1];
    const char *line[6];size_t width[6],at=0,i=0,n=0;
    struct mibr_display_scaling_state out;uint64_t rev;int written,v2,v3;
    if(!path||!desired||!advertised)return 0;
    memset(advertised,0,sizeof(*advertised));
    if(read_exact_file(path,data,&n))return 0;
    while(at<n&&i<6){const char *end=(const char*)memchr(data+at,'\n',n-at);
        if(!end)return 0;
        line[i]=data+at;width[i]=(size_t)(end-(data+at));at=(size_t)(end-data)+1;i++;}
    if(at!=n||memchr(data,0,n)||memchr(data,'\r',n)||!i)return 0;
    v3=width[0]==25&&!memcmp(line[0],"MIBR_SCALING_ADVERTISED/3",25);
    v2=width[0]==25&&!memcmp(line[0],"MIBR_SCALING_ADVERTISED/2",25);
    if(!v3&&!v2&&(width[0]!=25||memcmp(line[0],"MIBR_SCALING_ADVERTISED/1",25)))return 0;
    if(i!=(size_t)(v3?6:v2?5:4)||width[1]<10||memcmp(line[1],"revision=",9)||
       width[2]<6||memcmp(line[2],"main=",5)||width[3]<8||
       memcmp(line[3],"cluster=",8)||
       ((v2||v3)&&(width[4]<10||memcmp(line[4],"physical=",9)))||
       (v3&&(width[5]<15||memcmp(line[5],"main_physical=",14)))||
       parse_revision(line[1]+9,width[1]-9,&rev)||
       width[2]-5>=MIBR_DISPLAY_SCALING_VALUE_CAP||
       width[3]-8>=MIBR_DISPLAY_SCALING_VALUE_CAP||
       ((v2||v3)&&width[4]-9>=MIBR_DISPLAY_SCALING_VALUE_CAP)||
       (v3&&width[5]-14>=MIBR_DISPLAY_SCALING_VALUE_CAP))return 0;
    memset(&out,0,sizeof(out));
    memcpy(out.main,line[2]+5,width[2]-5);out.main[width[2]-5]=0;
    memcpy(out.cluster,line[3]+8,width[3]-8);out.cluster[width[3]-8]=0;
    if(v2||v3){memcpy(out.physical,line[4]+9,width[4]-9);out.physical[width[4]-9]=0;}
    else strcpy(out.physical,"BASE");
    if(v3){memcpy(out.main_physical,line[5]+14,width[5]-14);out.main_physical[width[5]-14]=0;}
    else strcpy(out.main_physical,"BASE");
    if(!mibr_display_scaling_value_valid(out.main)||
       !mibr_display_scaling_value_valid(out.cluster)||
       !mibr_display_physical_value_valid(out.physical)||!mibr_display_physical_value_valid(out.main_physical))return 0;
    written=v3?snprintf(canonical,sizeof(canonical),
        "MIBR_SCALING_ADVERTISED/3\nrevision=%llu\nmain=%s\ncluster=%s\nphysical=%s\nmain_physical=%s\n",
        (unsigned long long)rev,out.main,out.cluster,out.physical,out.main_physical):
        v2?snprintf(canonical,sizeof(canonical),
        "MIBR_SCALING_ADVERTISED/2\nrevision=%llu\nmain=%s\ncluster=%s\nphysical=%s\n",
        (unsigned long long)rev,out.main,out.cluster,out.physical):
        snprintf(canonical,sizeof(canonical),
        "MIBR_SCALING_ADVERTISED/1\nrevision=%llu\nmain=%s\ncluster=%s\n",
        (unsigned long long)rev,out.main,out.cluster);
    if(written<0||(size_t)written!=n||memcmp(canonical,data,n)||
       rev!=desired->revision||strcmp(out.main,desired->main)||
       strcmp(out.cluster,desired->cluster)||
       strcmp(out.physical,desired->physical)||strcmp(out.main_physical,desired->main_physical))return 0;
    out.revision=rev;out.stored=1;*advertised=out;return 1;
}
static int write_exclusive(const char *path,const char *data,size_t n){
    int fd,synced,closed;size_t used=0;ssize_t k;
    fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);if(fd<0)return -1;
    while(used<n){k=write(fd,data+used,n-used);
        if(k<0&&errno==EINTR)continue;
        if(k<=0){close(fd);return -1;}used+=(size_t)k;}
    synced=fsync(fd);closed=close(fd);return synced||closed?-1:0;
}
static int sync_parent(const char *path){
    char parent[PATH_CAP];char *slash;int fd,rc;
    if(strlen(path)>=sizeof(parent))return -1;
    strcpy(parent,path);slash=strrchr(parent,'/');if(!slash)return -1;
    if(slash==parent)slash[1]=0;else *slash=0;
    fd=open(parent,O_RDONLY);if(fd<0)return -1;
    rc=fsync(fd);if(close(fd))rc=-1;return rc;
}
static void temp_path(char *out,size_t cap,const char *path,const char *suffix){
    if(snprintf(out,cap,"%s.%s.%ld",path,suffix,(long)getpid())>=(int)cap)out[0]=0;
}
static int state_equal(const struct mibr_display_scaling_state *a,
                       const struct mibr_display_scaling_state *b){
    return a->revision==b->revision&&a->stored==b->stored&&
           !strcmp(a->main,b->main)&&!strcmp(a->cluster,b->cluster)&&
           !strcmp(a->physical,b->physical)&&!strcmp(a->main_physical,b->main_physical);
}
int mibr_display_scaling_set(const char *path,
    const struct mibr_display_scaling_state *observed,const char *id,
    const char *value,uint64_t expected_revision,
    const struct mibr_display_scaling_guard *guard,char *error,size_t error_cap){
    struct mibr_display_scaling_state current,after;char err[80]={0};
    char old[FILE_CAP+1],next[FILE_CAP+1],verify[FILE_CAP+1];
    char stage[PATH_CAP],backup_stage[PATH_CAP],backup[PATH_CAP];
    size_t oldn=0,newn;const char *selected;uint64_t rev;int rc=-1,ro=0,renamed=0;
    if(!path||path[0]!='/'||!observed||!mibr_display_scaling_id_valid(id)||
       !((!strcmp(id,ids[2])||!strcmp(id,ids[3]))?
         mibr_display_physical_value_valid(value):mibr_display_scaling_value_valid(value))||
       !guard||!guard->enter_rw||
       !guard->restore_verified_ro)return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    if(observed->revision!=expected_revision)return fail(error,error_cap,"STALE_REVISION");
    if(mibr_display_scaling_load(path,&current,err,sizeof(err)))return fail(error,error_cap,err);
    if(current.revision!=expected_revision||!state_equal(&current,observed))
        return fail(error,error_cap,"STALE_REVISION");
    selected=!strcmp(id,ids[0])?current.main:!strcmp(id,ids[1])?current.cluster:
        !strcmp(id,ids[2])?current.physical:current.main_physical;
    if(!strcmp(selected,value)){if(error&&error_cap)error[0]=0;return 1;}
    if(current.revision==UINT64_MAX)return fail(error,error_cap,"REVISION_EXHAUSTED");
    rev=current.revision+1;
    if(current.stored){
        int readrc=read_exact_file(path,old,&oldn);
        if(readrc!=0)return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    }
    after=current;after.revision=rev;after.stored=1;
    if(!strcmp(id,ids[0]))snprintf(after.main,sizeof(after.main),"%s",value);
    else if(!strcmp(id,ids[1]))snprintf(after.cluster,sizeof(after.cluster),"%s",value);
    else if(!strcmp(id,ids[2]))snprintf(after.physical,sizeof(after.physical),"%s",value);
    else snprintf(after.main_physical,sizeof(after.main_physical),"%s",value);
    {int n=snprintf(next,sizeof(next),"MIBR_SCALING/3\nrevision=%llu\nmain=%s\ncluster=%s\nphysical=%s\nmain_physical=%s\n",
                     (unsigned long long)rev,after.main,after.cluster,after.physical,after.main_physical);
     if(n<0||(size_t)n>=sizeof(next))return fail(error,error_cap,"INVALID_SCALING_FILE");
     newn=(size_t)n;}
    temp_path(stage,sizeof(stage),path,"stage");
    temp_path(backup_stage,sizeof(backup_stage),path,"lastgood.stage");
    if(!stage[0]||!backup_stage[0]||snprintf(backup,sizeof(backup),"%s.lastgood",path)>=(int)sizeof(backup))
        return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    if(guard->enter_rw(guard->context))return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    /* Re-read under the guarded transaction so a stale caller cannot overwrite
     * a value changed since its last GET. */
    if(mibr_display_scaling_load(path,&current,err,sizeof(err))||
       current.revision!=expected_revision||!state_equal(&current,observed))
        goto done;
    if(current.stored){
        if(read_exact_file(path,old,&oldn)||write_exclusive(backup_stage,old,oldn)||
           rename(backup_stage,backup)||sync_parent(path))goto done;
    }
    if(write_exclusive(stage,next,newn)||rename(stage,path))goto done;
    renamed=1;
    if(sync_parent(path))goto done;
    {size_t n=0;if(read_exact_file(path,verify,&n)||n!=newn||memcmp(verify,next,n))goto done;}
    rc=0;
done:
    ro=guard->restore_verified_ro(guard->context);
    if(ro){if(error&&error_cap)snprintf(error,error_cap,"RO_RESTORE_FAILED");return -2;}
    if(renamed&&rc<0){if(error&&error_cap)snprintf(error,error_cap,"UNKNOWN_COMMIT");return -2;}
    if(rc<0){(void)unlink(stage);(void)unlink(backup_stage);return fail(error,error_cap,"DURABILITY_UNCONFIRMED");}
    {size_t n=0;if(read_exact_file(path,verify,&n)||n!=newn||memcmp(verify,next,n)){
        if(error&&error_cap)snprintf(error,error_cap,"UNKNOWN_COMMIT");
        return -2;}}
    if(error&&error_cap)error[0]=0;
    return 0;
}
