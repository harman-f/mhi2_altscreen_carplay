/* SPDX-License-Identifier: GPL-3.0-or-later - read-only CI fixture */
#include "mibr_v3_runtime_observer.h"
#include <stdio.h>
int main(int argc,char **argv){
    struct mibr_v3_runtime_observation state={0};
    if(argc!=2||mibr_v3_runtime_read(argv[1],&state)){
        puts("MIBR_GEN2=UNKNOWN");return 2;
    }
    printf("MIBR_GEN2=OBSERVED session=%llu stream=%llu desired=%llu active=%llu confirmed=%d correlated=0\n",
       (unsigned long long)state.session,(unsigned long long)state.stream_gen,
       (unsigned long long)state.desired_revision,(unsigned long long)state.active_revision,state.confirmed);
    return 0;
}
