/* SPDX-License-Identifier: GPL-3.0-or-later
 * Passive, exact-generation IDR bridge evidence. No write/transport control.
 */
#ifndef ALT111_BRIDGE_STATUS_H
#define ALT111_BRIDGE_STATUS_H
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
struct alt111_bridge_status {
    uint64_t snapshot_us,sequence,stream,codec,consumer,blocks,write_errors;
};
static int alt111_bridge_field(const char *p,const char *key,uint64_t *out)
{
    size_t n; const char *s;char *end;unsigned long long value;
    if(!p||!key||!out)return -1;
    n=strlen(key);
    s=p;
    while(*s){
        if(!strncmp(s,key,n) && s[n]=='='){
            s+=n+1;
            if(*s<'0'||*s>'9')return -1;
            errno=0;value=strtoull(s,&end,10);
            if(errno || (end==s) || (*end!='\n' && *end!='\0'))return -1;
            *out=(uint64_t)value;
            return 0;
        }
        s=strchr(s,'\n');
        if(!s)break;
        ++s;
    }
    return -1;
}
static int alt111_bridge_status_parse(const char *text,struct alt111_bridge_status *out)
{
    struct alt111_bridge_status value={0};
    if(!text||!out||strncmp(text,"state=running\n",14))return -1;
    if(alt111_bridge_field(text,"clock_snapshot_mono_us",&value.snapshot_us) ||
       alt111_bridge_field(text,"output_last_idr_completed_sequence",&value.sequence) ||
       alt111_bridge_field(text,"output_last_idr_completed_stream",&value.stream) ||
       alt111_bridge_field(text,"output_last_idr_completed_codec",&value.codec) ||
       alt111_bridge_field(text,"output_last_idr_completed_consumer",&value.consumer) ||
       alt111_bridge_field(text,"blocks_written",&value.blocks) ||
       alt111_bridge_field(text,"write_errors",&value.write_errors))return -1;
    *out=value;
    return 0;
}
static int alt111_bridge_status_matches(const struct alt111_bridge_status *b,
                                        uint64_t now_us,uint64_t stream,
                                        uint64_t codec,uint64_t consumer)
{
    return b && b->snapshot_us && b->snapshot_us<=now_us &&
           now_us-b->snapshot_us<=2500000ull && b->blocks &&
           !b->write_errors && b->sequence && b->stream==stream &&
           b->codec==codec && b->consumer==consumer;
}
#endif
