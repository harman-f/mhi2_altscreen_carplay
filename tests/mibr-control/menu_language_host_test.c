#define _POSIX_C_SOURCE 200809L
#include "mibr_menu_language.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>
static int granted(void *x){(void)x;return 0;}
static int restored(void *x){(void)x;return 0;}
int main(void){
    char dir[]="/tmp/mibr-menu-host-XXXXXX",path[512],error[80];
    struct mibr_menu_language state,after;
    struct mibr_menu_language_guard guard={granted,restored,NULL};
    assert(mkdtemp(dir)!=NULL);
    assert(snprintf(path,sizeof(path),"%s/mibr-menu-language.conf",dir)>0);
    assert(mibr_menu_language_valid("AUTO")&&mibr_menu_language_valid("de")&&
           mibr_menu_language_valid("en")&&!mibr_menu_language_valid("fr"));
    assert(!mibr_menu_language_load(path,&state,error,sizeof(error)));
    assert(state.revision==0&&!state.stored&&!strcmp(state.value,"AUTO"));
    assert(!mibr_menu_language_set(path,&state,"en",0,&guard,error,sizeof(error)));
    assert(!mibr_menu_language_load(path,&after,error,sizeof(error)));
    assert(after.stored&&after.revision==1&&!strcmp(after.value,"en"));
    assert(mibr_menu_language_set(path,&state,"de",0,&guard,error,sizeof(error))!=0);
    assert(mibr_menu_language_set(path,&after,"unknown",1,&guard,error,sizeof(error))!=0);
    assert(!mibr_menu_language_set(path,&after,"de",1,&guard,error,sizeof(error)));
    assert(!mibr_menu_language_load(path,&state,error,sizeof(error)));
    assert(state.revision==2&&!strcmp(state.value,"de"));
    assert(mibr_menu_language_set(path,&state,"de",2,&guard,error,sizeof(error))==1);
    assert(!unlink(path));assert(!rmdir(dir));
    puts("MIBR_MENU_LANGUAGE_HOST_PASS");
    return 0;
}
