import sys
src=sys.argv[1]; dst=sys.argv[2]
s=open(src,newline='').read()
CR='\r\n'
def crlf(t): return t.replace('\n',CR)
def rep(a,b):
    global s
    a=crlf(a); b=crlf(b)
    assert s.count(a)==1, a[:70]
    s=s.replace(a,b,1)

rep('''static int backend_restore(void) {''','''/*
 * r50: the OEM process closes and reopens its isoTX2 descriptor (voice/phone moment, reverse gear, view change).
 * Until now that ended the whole session (rc=23). Instead: pause the bridge (no mixed writers), wait up to
 * GATE_GRACE_MS for the proof to come back (same token) or, if the OEM side returned to the stock state with the
 * descriptor tracked again, request ownership once more. Only when that fails, stop as before.
 */
#define GATE_GRACE_MS 4000u
#define GATE_GRACE_MAX 40u
static unsigned gate_grace_count;
static int gate_regain(pid_t bridge_pid) {
    struct alt111_native_gate_status st;uint64_t t0=monotonic_ms(),until=t0+GATE_GRACE_MS;
    int ok=0,rearmed=0;
    if(g_stop || gate_grace_count>=GATE_GRACE_MAX)return 0;
    ++gate_grace_count;
    if(bridge_handle>=0)(void)bound_process_signal(bridge_handle,SIGSTOP);
    else if(bridge_pid>1)(void)kill(bridge_pid,SIGSTOP);
    (void)write_text(STATE_PATH,"gate_grace\\n");
    fprintf(stderr,"GATE_GRACE begin n=%u\\n",gate_grace_count);
    while(!g_stop && monotonic_ms()<until) {
        if(read_ticket(STOP_REQUEST_PATH)==owner_token){g_stop=1;break;}
        if(gate_owned()){ok=1;fprintf(stderr,"GATE_GRACE resumed same token ms=%llu\\n",(unsigned long long)(monotonic_ms()-t0));break;}
        if(!rearmed && !gate_snapshot(&st) && st.state==0u && !st.token && st.tracked) {
            rearmed=1;
            (void)unlink(OLD_DIRECT_MARKER);
            if(!gate_take()){ok=1;fprintf(stderr,"GATE_GRACE rearmed ms=%llu\\n",(unsigned long long)(monotonic_ms()-t0));break;}
            (void)unlink(OLD_DIRECT_MARKER);
        }
        usleep(20000);
    }
    if(bridge_handle>=0)(void)bound_process_signal(bridge_handle,SIGCONT);
    else if(bridge_pid>1)(void)kill(bridge_pid,SIGCONT);
    if(ok)(void)write_text(STATE_PATH,"direct\\n");
    else fprintf(stderr,"GATE_GRACE expired ms=%llu\\n",(unsigned long long)(monotonic_ms()-t0));
    return ok;
}

static int backend_restore(void) {''')
rep('''        if(!gate_owned()) {fprintf(stderr,"ERROR native gate proof lost; stopping custom writer\\n");rc=23;break;}''',
'''        if(!gate_owned() && !gate_regain(bridge_pid)) {fprintf(stderr,"ERROR native gate proof lost; stopping custom writer\\n");rc=23;break;}''')
open(dst,'w',newline='').write(s)
