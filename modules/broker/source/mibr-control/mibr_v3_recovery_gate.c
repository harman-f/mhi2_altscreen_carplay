/* SPDX-License-Identifier: GPL-3.0-or-later
 * No automatic rollback of potentially committed bytes after a power cut.
 * Verify BOTH candidate and last-good structures and refuse leftover stages.
 * An invalid live profile must remain STOCK_ONLY until manual offline recovery.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_v3_recovery_gate.h"
#include "alt111_settings.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define CAP 8192u
#define PATH_CAP 512u
static int valid_file(const char *path){
    struct stat pre,post;unsigned seen[ALTSET_COUNT]={0},count=0;
    char text[CAP+1];int fd;size_t used=0,offset=0;ssize_t n;
    if(lstat(path,&pre)||!S_ISREG(pre.st_mode)||pre.st_size<1||pre.st_size>CAP)return -1;
    fd=open(path,O_RDONLY);if(fd<0)return -1;
    if(fstat(fd,&post)||!S_ISREG(post.st_mode)||post.st_dev!=pre.st_dev||
       post.st_ino!=pre.st_ino||post.st_size!=pre.st_size){close(fd);return -1;}
    while(used<(size_t)post.st_size){
        n=read(fd,text+used,(size_t)post.st_size-used);
        if(n<0&&errno==EINTR)continue;
        if(n<=0){close(fd);return -1;}used+=(size_t)n;
    }
    if(close(fd)||!used||text[used-1]!='\n'||memchr(text,0,used)||memchr(text,'\r',used))return -1;
    text[used]=0;
    while(offset<used){
        char *end=memchr(text+offset,'\n',used-offset),*equal;
        int id;size_t len;
        if(!end||end==text+offset)return -1;
        *end=0;equal=strchr(text+offset,'=');
        if(!equal||equal==text+offset||!equal[1])return -1;
        len=(size_t)(equal-(text+offset));
        if(len>64)return -1;
        *equal=0;
        id=alt111_setting_find(text+offset);
        if(id<0||seen[id]++||alt111_setting_validate((unsigned)id,equal+1))return -1;
        count++;offset=(size_t)(end-text)+1;
    }
    return count==45?0:-1;
}
int mibr_v3_recovery_check(const char *profile_path){
    char parent[PATH_CAP],backup[PATH_CAP],base[PATH_CAP];
    const char *slash;DIR *directory;struct dirent *entry;size_t size;
    if(!profile_path||profile_path[0]!='/'||
       strlen(profile_path)>=PATH_CAP-32u||ALTSET_COUNT!=48u)return -1;
    slash=strrchr(profile_path,'/');if(!slash||!slash[1])return -1;
    size=(size_t)(slash-profile_path);
    if(size>=sizeof(parent)||strlen(slash+1)>=sizeof(base))return -1;
    if(!size)strcpy(parent,"/");else {memcpy(parent,profile_path,size);parent[size]=0;}
    strcpy(base,slash+1);
    if(snprintf(backup,sizeof(backup),"%s.lastgood",profile_path)>=(int)sizeof(backup))return -1;
    if(valid_file(profile_path))return -1;
    /* Missing lastgood is legitimate only before first successful mutation. */
    if(access(backup,F_OK)==0){
        if(valid_file(backup))return -1;
    }else if(errno!=ENOENT)return -1;
    directory=opendir(parent);if(!directory)return -1;
    while((entry=readdir(directory))!=NULL){
        size_t prefix=strlen(base);
        if(!strncmp(entry->d_name,base,prefix)&&
            (!strncmp(entry->d_name+prefix,".stage.",7)||
             !strncmp(entry->d_name+prefix,".lastgood.stage.",16))){
            closedir(directory);return -1;
        }
    }
    return closedir(directory)?-1:0;
}
