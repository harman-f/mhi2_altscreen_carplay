/* SPDX-License-Identifier: GPL-3.0-or-later
 * Real /tmp leaf mailbox protocol test: NO owner or unit involved.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_v3_parity_mailbox.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
int main(void){
    char path[256],line[256];FILE *f;
    struct mibr_v3_parity_mailbox m={0};
    assert(snprintf(path,sizeof(path),
        "/tmp/mibr-v3-mailbox-probe-%ld.req",(long)getpid())>0);
    assert(access(path,F_OK)!=0);
    m.request_path=path;m.session=7;m.stream_generation=20;
    assert(mibr_v3_parity_mailbox_start(&m,"first")==-1);
    m.qualified=1;
    assert(mibr_v3_parity_mailbox_start(&m,"invalid.rid")==-1);
    assert(mibr_v3_parity_mailbox_start(&m,"first")==0);
    f=fopen(path,"r");assert(f&&fgets(line,sizeof(line),f));fclose(f);
    assert(!strcmp(line,"MIBR3|START|first|7|20\n"));
    assert(mibr_v3_parity_mailbox_stop(&m,"second")==-2);
    assert(!unlink(path)); /* synthetic sole-owner consumed command */
    assert(mibr_v3_parity_mailbox_stop(&m,"second")==0);
    f=fopen(path,"r");assert(f&&fgets(line,sizeof(line),f));fclose(f);
    assert(!strcmp(line,"MIBR3|STOP|second|7|20\n"));
    assert(!unlink(path));
    /* Racing producers must not lose one already accepted request.
     * Old lstat+rename could return success TWICE by overwriting the
     * first request; hard-link publication admits exactly one writer. */
    {
        int gate[2],rc,status,accepted=0;
        pid_t child;
        char start;
        assert(!pipe(gate));
        child=fork();assert(child>=0);
        if(child==0){
            close(gate[1]);
            assert(read(gate[0],&start,1)==1&&start=='g');
            close(gate[0]);
            rc=mibr_v3_parity_mailbox_start(&m,"child");
            _exit(rc==0?0:(rc==-2?2:9));
        }
        close(gate[0]);
        assert(write(gate[1],"g",1)==1);
        close(gate[1]);
        rc=mibr_v3_parity_mailbox_start(&m,"parent");
        assert(rc==0||rc==-2);
        assert(waitpid(child,&status,0)==child&&WIFEXITED(status));
        assert(WEXITSTATUS(status)==0||WEXITSTATUS(status)==2);
        accepted=(rc==0)+(WEXITSTATUS(status)==0);
        assert(accepted==1);
        f=fopen(path,"r");assert(f&&fgets(line,sizeof(line),f));fclose(f);
        assert(!strcmp(line,"MIBR3|START|parent|7|20\n")||
               !strcmp(line,"MIBR3|START|child|7|20\n"));
        assert(!unlink(path));
    }
    puts("PARITY_MAILBOX_ONE_COMMAND_AT_A_TIME_HOST_PASS");
    return 0;
}
