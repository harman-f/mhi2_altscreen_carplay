/* Host-only direct probe of the portable scaling parser/store. */
#include "mibr_display_scaling.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int enter(void *p){(void)p;return 0;}
static int restore_ro(void *p){(void)p;return 0;}
int main(int argc,char **argv){
    struct mibr_display_scaling_state s,advertised;
    char err[80]={0};int rc;
    if(argc==3&&!strcmp(argv[1],"read")){
        rc=mibr_display_scaling_load(argv[2],&s,err,sizeof(err));
        if(rc){fprintf(stderr,"%s\n",err);return 2;}
        printf("%llu|%s|%s|%s|%s|%d\n",(unsigned long long)s.revision,s.main,s.cluster,s.physical,s.main_physical,s.stored);return 0;
    }
    if(argc==6&&!strcmp(argv[1],"set")){
        uint64_t revision=(uint64_t)strtoull(argv[5],NULL,10);
        struct mibr_display_scaling_guard guard={enter,restore_ro,NULL};
        if(mibr_display_scaling_load(argv[2],&s,err,sizeof(err))){fprintf(stderr,"%s\n",err);return 2;}
        rc=mibr_display_scaling_set(argv[2],&s,argv[3],argv[4],revision,&guard,err,sizeof(err));
        if(rc<0){fprintf(stderr,"%s\n",err);return 3;}
        if(mibr_display_scaling_load(argv[2],&s,err,sizeof(err))){fprintf(stderr,"%s\n",err);return 4;}
        printf("%d|%llu|%s|%s|%s|%s|%d\n",rc,(unsigned long long)s.revision,s.main,s.cluster,s.physical,s.main_physical,s.stored);return 0;
    }
    if(argc==4&&!strcmp(argv[1],"advertised")){
        if(mibr_display_scaling_load(argv[2],&s,err,sizeof(err))){fprintf(stderr,"%s\n",err);return 2;}
        rc=mibr_display_scaling_advertised_load(argv[3],&s,&advertised);
        printf("%d|%s|%s|%s|%s\n",rc,rc?advertised.main:"UNKNOWN",rc?advertised.cluster:"UNKNOWN",rc?advertised.physical:"UNKNOWN",rc?advertised.main_physical:"UNKNOWN");return 0;
    }
    if(argc==5&&!strcmp(argv[1],"dimensions")){
        int w=0,h=0;
        rc=mibr_display_main_physical_dimensions(argv[2],atoi(argv[3]),atoi(argv[4]),&w,&h);
        if(rc){fputs("INVALID_DIMENSIONS\n",stderr);return 5;}
        printf("%d|%d\n",w,h);return 0;
    }
    return 64;
}
