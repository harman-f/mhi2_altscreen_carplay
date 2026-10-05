/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MIBR_ALT111_NATIVE_GATE_H
#define MIBR_ALT111_NATIVE_GATE_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define ALT111_NATIVE_GATE_REQUEST "/tmp/mibr-isotx2-gate.direct"
#define ALT111_NATIVE_GATE_STATUS "/tmp/mibr-alt111-native-gate.status"
#define ALT111_NATIVE_GATE_CAP 256u
struct alt111_native_gate_status {
    uint64_t token,process,tracked,inflight,dropped,heartbeat,state;
};
/* state=0 stock, 1 blocked pending drain, 2 blocked and drained,
 * 3 unsupported tracking/control operation. No PID is signal authority. */
static inline int alt111_native_gate_parse(const char *data,size_t size,
                                           struct alt111_native_gate_status *out)
{
    char copy[ALT111_NATIVE_GATE_CAP],*p;uint64_t value[7];unsigned i;
    if(!data||!out||size<10u||size>=sizeof(copy)||data[size-1]!='\n'||
       memchr(data,0,size)||memcmp(data,"M1GATE1 ",8))return -1;
    memcpy(copy,data,size);copy[size-1]=0;p=copy+8;
    for(i=0;i<7u;++i){
        if(*p<'0'||*p>'9'||(*p=='0'&&p[1]>='0'&&p[1]<='9'))return -1;
        value[i]=0;
        while(*p>='0'&&*p<='9'){
            unsigned digit=(unsigned)(*p-'0');
            if(value[i]>(UINT64_MAX-digit)/10u)return -1;
            value[i]=value[i]*10u+digit;++p;
        }
        if(i<6u ? *p!=' ' : *p!=0)return -1;
        p+=(i<6u);
    }
    if(!value[1]||value[6]>3u)return -1;
    out->token=value[0];out->process=value[1];out->tracked=value[2];
    out->inflight=value[3];out->dropped=value[4];out->heartbeat=value[5];out->state=value[6];
    return 0;
}
#endif
