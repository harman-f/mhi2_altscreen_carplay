/*
 * Bounded MU1440 parity-session owner.
 *
 * Snapshots the selected backend and owns a bounded start/stop/restore.
 * DMDT remains a routing-only probe until independent target ownership proof.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include "bound_process.h"
#include "alt111_native_gate.h"
#include "alt111_settings.h"

#define DMDT "/eso/bin/apps/dmdt"
#define IPL_CONFIG "/etc/eso/production"
#define STATE_PATH "/tmp/mibr-parity-session.state"
#define PID_PATH "/tmp/mibr-parity-session.pid"
#define BRIDGE_PID_PATH "/tmp/mibr-parity-session-bridge.pid"
#define LOCK_PATH "/tmp/mibr-parity-session.lock"
#define WATCHDOG_PID_PATH "/tmp/mibr-parity-session-watchdog.pid"
#define AU_MARKER "/tmp/mibr-alt111-au-framing.enabled"
#define OLD_DIRECT_MARKER "/tmp/mibr-isotx2-gate.direct"
#define SOURCE_STATE "/tmp/mibr-carplay111.state"
#define SOURCE_HB "/tmp/mibr-carplay111.heartbeat"
#define OLD_AUTO_PID "/tmp/mibr-direct-auto-supervisor.pid"
#define OLD_AUTO_TEMP "/tmp/mibr-carplay-autodirect"
#define OLD_AUTO_PERSIST "/mnt/app/root/mibr-carplay-autodirect"
#define SETTINGS_TEMP_ROOT "/tmp"
#define SETTINGS_PERSIST_ROOT "/mnt/app/root"
#define GATE_STATUS_PATH "/tmp/mibr-alt111-native-gate.status"
#define BACKEND_STATE_PATH "/tmp/mibr-parity-session.backend"
#define OWNER_TICKET_PATH "/tmp/mibr-parity-session.ticket"
#define STOP_REQUEST_PATH "/tmp/mibr-parity-session.stop"
#define DMDT_TIMEOUT_MS 5000u
#define DMDT_TERM_GRACE_MS 500u
#define WATCHDOG_MARGIN_SECONDS 20u

static volatile sig_atomic_t g_stop;
static int session_lock_fd=-1;
static pid_t owner_process_pid=-1;
static int bridge_handle=-1;
static unsigned gate_backend,bridge_created;
static uint64_t gate_token,native_process,gate_dropped_before,gate_request_ms;
static uint64_t owner_token;
static uint64_t monotonic_ms(void);
static int route_restore(void);

static int gate_snapshot_once(struct alt111_native_gate_status *out)
{
    char data[ALT111_NATIVE_GATE_CAP];struct stat before,after;ssize_t n;int fd;
    uint64_t now=monotonic_ms();
    if(lstat(GATE_STATUS_PATH,&before)||!S_ISREG(before.st_mode)||
       before.st_size<=0||before.st_size>=(off_t)sizeof(data))return -1;
    fd=open(GATE_STATUS_PATH,O_RDONLY|O_NONBLOCK);if(fd<0)return -1;
    if(fstat(fd,&after)||!S_ISREG(after.st_mode)||before.st_dev!=after.st_dev||
       before.st_ino!=after.st_ino){close(fd);return -1;}
    n=read(fd,data,sizeof(data));close(fd);
    if(n<=0||alt111_native_gate_parse(data,(size_t)n,out)||
       !out->heartbeat||out->heartbeat>now||now-out->heartbeat>250u)return -1;
    return 0;
}

static int gate_snapshot(struct alt111_native_gate_status *out)
{
    uint64_t until=monotonic_ms()+100u;
    do {
        if(!gate_snapshot_once(out))return 0;
        usleep(1000);
    } while(monotonic_ms()<until);
    return -1;
}

static uint64_t monotonic_ms(void) {
    struct timespec ts;
    if(clock_gettime(CLOCK_MONOTONIC,&ts)!=0)return 0;
    return (uint64_t)ts.tv_sec*1000u+(uint64_t)ts.tv_nsec/1000000u;
}

static int lock_fd_matches_path(int fd) {
    struct stat held,path;
    if(fd<0 || fstat(fd,&held)!=0 || lstat(LOCK_PATH,&path)!=0)return 0;
    return S_ISREG(held.st_mode) && S_ISREG(path.st_mode) &&
           held.st_dev==path.st_dev && held.st_ino==path.st_ino;
}

static int acquire_lock(void) {
    char record[80];
    size_t n;
    int fd=open(LOCK_PATH,O_RDWR|O_CREAT|O_EXCL,0600);
    if(fd<0)return -1;
    if(fcntl(fd,F_SETFD,FD_CLOEXEC)!=0) {close(fd);unlink(LOCK_PATH);return -1;}
    n=(size_t)snprintf(record,sizeof(record),"M1PLOCK1 %ld %llu\n",
                      (long)owner_process_pid,(unsigned long long)owner_token);
    if(n==0u || n>=sizeof(record) || write(fd,record,n)!=(ssize_t)n) {
        close(fd);unlink(LOCK_PATH);return -1;
    }
    if(!lock_fd_matches_path(fd)) {close(fd);unlink(LOCK_PATH);return -1;}
    session_lock_fd=fd;return 0;
}

static void on_signal(int sig) { (void)sig; g_stop = 1; }

static int write_text(const char *path, const char *text) {
    char tmp[192];
    int fd;
    size_t n = strlen(text);
    snprintf(tmp, sizeof(tmp), "%s.new.%ld", path, (long)getpid());
    fd = open(tmp, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return -1;
    if (write(fd, text, n) != (ssize_t)n) { close(fd); unlink(tmp); return -1; }
    if (close(fd) != 0) { unlink(tmp); return -1; }
    if (rename(tmp, path) != 0) { unlink(tmp); return -1; }
    return 0;
}

static int touch_file(const char *path) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return -1;
    return close(fd);
}

static int read_trimmed(const char *path, char *out, size_t cap) {
    int fd;
    ssize_t n;
    if (!out || cap < 2u) return -1;
    out[0] = 0;
    fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    n = read(fd, out, cap - 1u);
    close(fd);
    if (n <= 0) return -1;
    out[n] = 0;
    while (n > 0 && (out[n-1] == '\n' || out[n-1] == '\r' ||
                     out[n-1] == ' ' || out[n-1] == '\t'))
        out[--n] = 0;
    return n > 0 ? 0 : -1;
}

static uint64_t read_ticket(const char *path) {
    char data[24],*end;struct stat st;ssize_t n;uint64_t value;int fd;
    if(lstat(path,&st)||!S_ISREG(st.st_mode)||st.st_size<2||st.st_size>21)return 0;
    fd=open(path,O_RDONLY|O_NONBLOCK);if(fd<0)return 0;
    if(fstat(fd,&st)||!S_ISREG(st.st_mode)){close(fd);return 0;}
    n=read(fd,data,sizeof(data));close(fd);
    if(n<2||n>21||data[n-1]!='\n'||data[0]<'1'||data[0]>'9'||memchr(data,0,(size_t)n))return 0;
    data[n-1]=0;errno=0;value=strtoull(data,&end,10);
    return errno || *end ? 0 : value;
}

static int request_stop(void) {
    uint64_t ticket,until;char text[48];
    if(access(LOCK_PATH,F_OK)!=0) {
        if(access(BRIDGE_PID_PATH,F_OK)==0 || access(OLD_DIRECT_MARKER,F_OK)==0)return 19;
        puts("owner_result=NO_ACTIVE_OWNER");return 0;
    }
    ticket=read_ticket(OWNER_TICKET_PATH);if(!ticket)return 19;
    snprintf(text,sizeof(text),"%llu\n",(unsigned long long)ticket);
    if(write_text(STOP_REQUEST_PATH,text))return 19;
    until=monotonic_ms()+15000u;
    do {
        if(access(LOCK_PATH,F_OK)!=0 && access(BRIDGE_PID_PATH,F_OK)!=0 &&
           access(OLD_DIRECT_MARKER,F_OK)!=0) {
            puts("owner_result=STOPPED_AND_HAND_BACK_CONFIRMED");return 0;
        }
        if(read_ticket(OWNER_TICKET_PATH)!=ticket)return 19;
        usleep(100000);
    } while(monotonic_ms()<until);
    fprintf(stderr,"ERROR stop remains unconfirmed/quarantined; no PID-file signal issued\n");
    return 19;
}

static int pid_alive_from_file(const char *path) {
    char b[48], *end = NULL;
    long pid;
    if (read_trimmed(path, b, sizeof(b)) != 0) return 0;
    errno = 0;
    pid = strtol(b, &end, 10);
    if (errno || end == b || *end || pid <= 1) return 0;
    return kill((pid_t)pid, 0) == 0 || errno == EPERM;
}

static int settings_backend(void) {
    struct alt111_settings_paths paths={SETTINGS_TEMP_ROOT,SETTINGS_PERSIST_ROOT};
    struct alt111_settings *settings=malloc(sizeof(*settings));char error[192];
    int rc=-1;
    if(!settings)return -1;
    if(alt111_settings_load(&paths,settings,error,sizeof(error))) {
        fprintf(stderr,"ERROR settings preflight: %s\n",error);goto done;
    }
    if(alt111_setting_integer(settings,ALTSET_LEGACY_AUTODIRECT)) {
        fprintf(stderr,"ERROR legacy Auto-Direct must be disabled\n");goto done;
    }
    gate_backend=!strcmp(settings->value[ALTSET_OWNERSHIP_BACKEND],"writev_gate");
    printf("ownership_backend=%s\nsettings_revision=%llu\n",
        settings->value[ALTSET_OWNERSHIP_BACKEND],(unsigned long long)settings->revision);
    rc=0;
done:
    free(settings);return rc;
}

static int gate_take(void) {
    struct alt111_native_gate_status status;char text[48];uint64_t until;
    if(access(OLD_DIRECT_MARKER,F_OK)==0 || gate_snapshot(&status) ||
       status.state!=0u || !status.tracked)return -1;
    native_process=status.process;gate_dropped_before=status.dropped;
    gate_request_ms=monotonic_ms();
    gate_token=((gate_request_ms<<20)^((uint64_t)getpid()<<3))|1u;
    snprintf(text,sizeof(text),"%llu\n",(unsigned long long)gate_token);
    if(write_text(OLD_DIRECT_MARKER,text))return -1;
    until=gate_request_ms+5000u;
    do {
        if(!gate_snapshot(&status) && status.token==gate_token &&
           status.process==native_process && status.heartbeat>=gate_request_ms &&
           status.state==2u && status.tracked && !status.inflight &&
           status.dropped>gate_dropped_before)return 0;
        if(g_stop)break;
        usleep(10000);
    } while(monotonic_ms()<until);
    return -1;
}

static int gate_owned(void) {
    struct alt111_native_gate_status status;
    return !gate_snapshot(&status) && status.token==gate_token &&
        status.process==native_process && status.state==2u && status.tracked &&
        !status.inflight && status.dropped>=gate_dropped_before;
}

static int backend_restore(void) {
    uint64_t until;struct alt111_native_gate_status status;
    if(!gate_backend)return route_restore();
    if(unlink(OLD_DIRECT_MARKER) && errno!=ENOENT)return -1;
    until=monotonic_ms()+2000u;
    do {
        if(!gate_snapshot(&status) && status.state==0u && !status.token &&
           (!native_process || status.process==native_process))return 0;
        usleep(10000);
    } while(monotonic_ms()<until);
    return -1;
}

static int wait_child_bounded(pid_t p, unsigned timeout_ms, int *status) {
    unsigned elapsed = 0;
    int st = 0;
    while (elapsed < timeout_ms) {
        pid_t w = waitpid(p, &st, WNOHANG);
        if (w == p) {
            if (status) *status = st;
            return 0;
        }
        if (w < 0 && errno != EINTR) return -1;
        usleep(100000);
        elapsed += 100u;
    }

    (void)kill(p, SIGTERM);
    elapsed = 0;
    while (elapsed < DMDT_TERM_GRACE_MS) {
        pid_t w = waitpid(p, &st, WNOHANG);
        if (w == p) {
            if (status) *status = st;
            return -1;
        }
        if (w < 0 && errno != EINTR) return -1;
        usleep(100000);
        elapsed += 100u;
    }

    (void)kill(p, SIGKILL);
    elapsed=0;
    while(elapsed<DMDT_TERM_GRACE_MS) {
        pid_t w=waitpid(p,&st,WNOHANG);
        if(w==p || (w<0 && errno==ECHILD))break;
        usleep(100000); elapsed+=100u;
    }
    if (status) *status = st;
    return -1;
}

static int run_argv(char *const argv[]) {
    pid_t p;
    int st = 0;
    p = fork();
    if (p < 0) return -1;
    if (p == 0) {
        setenv("IPL_CONFIG_DIR", IPL_CONFIG, 1);
        execv(DMDT, argv);
        _exit(127);
    }
    if (wait_child_bounded(p, DMDT_TIMEOUT_MS, &st) != 0) return -1;
    return WIFEXITED(st) && WEXITSTATUS(st) == 0 ? 0 : -1;
}

static int dmdt_dc72(void) {
    char *argv[] = { (char *)DMDT, "dc", "72", NULL };
    return run_argv(argv);
}
static int dmdt_sc4_72(void) {
    char *argv[] = { (char *)DMDT, "sc", "4", "72", NULL };
    return run_argv(argv);
}
static int dmdt_dc70_33(void) {
    char *argv[] = { (char *)DMDT, "dc", "70", "33", NULL };
    return run_argv(argv);
}
static int dmdt_sc4_70(void) {
    char *argv[] = { (char *)DMDT, "sc", "4", "70", NULL };
    return run_argv(argv);
}

static int route_release(void) {
    if (dmdt_dc72() != 0) return -1;
    if (dmdt_sc4_72() != 0) return -1;
    return 0;
}

static int route_restore(void) {
    int a = dmdt_dc70_33();
    int b = dmdt_sc4_70();
    return (a == 0 && b == 0) ? 0 : -1;
}

static int stop_bound_bridge(void) {
    unsigned i;
    if(!bridge_created)return 0;
    if(bound_process_dead(bridge_handle))return 0;
    if(bridge_handle<0)return -1;
    (void)bound_process_signal(bridge_handle,SIGTERM);
    for(i=0;i<20u;++i){
        if(bound_process_dead(bridge_handle))return 0;
        usleep(100000);
    }
    (void)bound_process_signal(bridge_handle,SIGKILL);
    for(i=0;i<5u;++i){
        if(bound_process_dead(bridge_handle))return 0;
        usleep(100000);
    }
    return -1;
}

static int emergency_restore(void) {
    int restored;
    if(stop_bound_bridge()){
        (void)write_text(STATE_PATH,"blocked_stop_unconfirmed\n");
        return -1; /* Keep markers/lock; never restore over an unknown writer. */
    }
    unlink(AU_MARKER);
    restored=backend_restore()==0;
    (void)write_text(STATE_PATH,restored ? "emergency_restored\n" : "emergency_restore_failed\n");
    unlink(BRIDGE_PID_PATH);
    if(!pid_alive_from_file(PID_PATH))unlink(PID_PATH);
    /* Keep the lock after an emergency. A stale session must be explicitly
     * restored/reconciled before another owner may acquire the route. */
    return restored ? 0 : -1;
}

static void watchdog_main(int fd, unsigned timeout_seconds) {
    char token = 0;
    ssize_t n = -1;
    unsigned elapsed_seconds = 0;
    char b[48];
    /*
     * Exact MU1440 /tmp == /dev/shmem does not implement POSIX F_SETLK.
     * The parent-created O_EXCL lock inode is inherited across fork; require
     * that the pathname still names that exact inode before the watchdog may
     * participate in recovery.
     */
    if(!lock_fd_matches_path(session_lock_fd))_exit(18);
    snprintf(b,sizeof(b),"%ld\n",(long)getpid());
    if(write_text(WATCHDOG_PID_PATH,b)!=0)_exit(18);
    signal(SIGINT,SIG_IGN); signal(SIGTERM,SIG_IGN); signal(SIGHUP,SIG_IGN);

    while (elapsed_seconds < timeout_seconds) {
        fd_set rfds;
        struct timeval tv;
        int rc;
        unsigned slice = timeout_seconds - elapsed_seconds;
        if (slice > 1u) slice = 1u;

        FD_ZERO(&rfds);
        FD_SET(fd, &rfds);
        tv.tv_sec = (long)slice;
        tv.tv_usec = 0;
        rc = select(fd + 1, &rfds, NULL, NULL, &tv);
        if (rc > 0 && FD_ISSET(fd, &rfds)) {
            do { n = read(fd, &token, 1); } while (n < 0 && errno == EINTR);
            close(fd);
            if (n == 1 && token == 'R') { unlink(WATCHDOG_PID_PATH); _exit(0); }
            rc=emergency_restore(); unlink(WATCHDOG_PID_PATH); _exit(rc ? 20 : 0);
        }
        if (rc < 0 && errno != EINTR) {
            close(fd);
            rc=emergency_restore(); unlink(WATCHDOG_PID_PATH); _exit(rc ? 20 : 0);
        }
        if (rc == 0) elapsed_seconds += slice;
    }

    close(fd);
    { int rc=emergency_restore(); unlink(WATCHDOG_PID_PATH); _exit(rc ? 20 : 0); }
}

static int source_ready(void) {
    char b[64];
    if (read_trimmed(SOURCE_STATE, b, sizeof(b)) != 0 || strcmp(b, "streaming"))
        return 0;
    return access(SOURCE_HB, R_OK) == 0;
}

static int bridge_identity(const char *path) {
#ifdef ALT111_SESSION_TEST
    /* Lifecycle fixtures exercise fork/exec/signals without shipping an OEM
     * or native bridge. This bypass is never compiled into target builds. */
    (void)path;return 0;
#elif defined(MIBR_EXPECTED_BRIDGE_SHA256)
    struct stat st;char hash[65];uint8_t *bytes;size_t used=0;int fd,rc=-1;
    fd=open(path,O_RDONLY|O_NONBLOCK);if(fd<0)return -1;
    if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_size<=0||st.st_size>4*1024*1024){close(fd);return -1;}
    bytes=malloc((size_t)st.st_size);if(!bytes){close(fd);return -1;}
    while(used<(size_t)st.st_size) {
        ssize_t n=read(fd,bytes+used,(size_t)st.st_size-used);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)goto done;
        used+=(size_t)n;
    }
    mibr_sha256_bytes(bytes,used,hash);
    rc=strcmp(hash,MIBR_EXPECTED_BRIDGE_SHA256) ? -1 : 0;
done:
    free(bytes);close(fd);return rc;
#else
    (void)path;return -1; /* A build without an exact bridge identity cannot run. */
#endif
}

static int bridge_spawn(const char *bridge, const char *input, const char *output,
                        pid_t *out_pid,int *exec_gate) {
    int gate[2];
    char token='G', b[48];
    if(pipe(gate)!=0)return -1;
    pid_t p = fork();
    if (p < 0) {close(gate[0]);close(gate[1]);return -1;}
    if (p == 0) {
        ssize_t n;
        close(gate[1]);
        do { n=read(gate[0],&token,1); } while(n<0&&errno==EINTR);
        close(gate[0]);
        if(n!=1||token!='G')_exit(126);
        execl(bridge, bridge, input, output, (char *)NULL);
        _exit(127);
    }
    *out_pid = p;
    close(gate[0]);
    snprintf(b,sizeof(b),"%ld\n",(long)p);
    bridge_handle=bound_process_open(p);
    if(bridge_handle<0 || write_text(BRIDGE_PID_PATH,b)!=0) {
        close(gate[1]); return -1;
    }
    *exec_gate=gate[1]; /* Parent/watchdog must bind before releasing this. */
    return 0;
}

static int stop_bridge(pid_t p) {
    int i, st;pid_t first;
    if (p <= 1) return -1;
    first=waitpid(p,&st,WNOHANG);
    if(first==p)return 0;
    if(first<0 && errno!=EINTR)return bound_process_dead(bridge_handle) ? 0 : -1;
    if(bound_process_dead(bridge_handle))return 0;
    if(bridge_handle>=0)(void)bound_process_signal(bridge_handle,SIGTERM);
    else (void)kill(p,SIGTERM); /* Still our unreaped direct child. */
    for (i = 0; i < 20; ++i) {
        pid_t w = waitpid(p, &st, WNOHANG);
        if (w == p) return 0;
        if(bound_process_dead(bridge_handle))return 0;
        if (w < 0 && errno == ECHILD) return -1;
        if (w < 0 && errno != EINTR) return -1;
        usleep(100000);
    }
    if(bridge_handle>=0)(void)bound_process_signal(bridge_handle,SIGKILL);
    else (void)kill(p,SIGKILL);
    for(i=0;i<5;++i) {
        pid_t w=waitpid(p,&st,WNOHANG);
        if(w==p)return 0;
        if(bound_process_dead(bridge_handle))return 0;
        if(w<0&&errno==ECHILD)return -1;
        if(w<0&&errno!=EINTR)return -1;
        usleep(100000);
    }
    return -1;
}

static int identity_self_test(void) {
    pid_t child,observer;int fd,st=0,observer_status=0,ok,child_rc,observer_rc;
    int ready[2];char token=0;
    if(pipe(ready))return 1;
    child=fork();if(child<0){close(ready[0]);close(ready[1]);return 1;}
    if(!child){
        close(ready[0]);signal(SIGTERM,SIG_DFL);
        token='R';if(write(ready[1],&token,1)!=1)_exit(1);
        close(ready[1]);for(;;)pause();
    }
    close(ready[1]);
    {
        fd_set rfds;struct timeval timeout={2,0};
        FD_ZERO(&rfds);FD_SET(ready[0],&rfds);
        ok=select(ready[0]+1,&rfds,NULL,NULL,&timeout)>0 && read(ready[0],&token,1)==1 && token=='R';
    }
    close(ready[0]);
    if(!ok){kill(child,SIGKILL);waitpid(child,&st,0);return 1;}
    fd=bound_process_open(child);
    if(fd<0){kill(child,SIGKILL);waitpid(child,&st,0);return 1;}
    observer=fork();
    if(!observer){
        unsigned i;
        if(bound_process_signal(fd,SIGTERM))_exit(1);
        for(i=0;i<30u;++i){if(bound_process_dead(fd))_exit(0);usleep(100000);}
        _exit(2);
    }
    if(observer<0){kill(child,SIGKILL);waitpid(child,&st,0);close(fd);return 1;}
    observer_rc=wait_child_bounded(observer,4000u,&observer_status);
    /*
     * On QNX an O_RDWR /proc/<pid>/as handle sets Run-on-Last-Close.
     * The stock SignalKill path moves the exact bound child to the procfs
     * TERMINATED point while the inherited RLC handles keep its process
     * object present.  First prove that terminal/quiescent state on the bound
     * object, then release the final parent handle and require a bounded reap.
     *
     * Exact MU1440 vehicle evidence shows that last-close reaps this terminal
     * child as WIFEXITED(status)==1 / WEXITSTATUS(status)==0 rather than
     * preserving WIFSIGNALED(SIGTERM).  The termination proof therefore comes
     * from the bound procfs handle before close; the post-close requirement is
     * successful reap, not a Linux-style signal wait status.
     */
    ok=!observer_rc &&
       WIFEXITED(observer_status) && WEXITSTATUS(observer_status)==0 &&
       bound_process_dead(fd);
    close(fd);fd=-1;
    child_rc=wait_child_bounded(child,3000u,&st);
#ifdef __QNXNTO__
    ok=ok && !child_rc;
#else
    ok=ok && !child_rc &&
       WIFSIGNALED(st) && WTERMSIG(st)==SIGTERM;
#endif
    if(ok)puts("PARITY_PROCESS_IDENTITY_SELFTEST=PASS inherited_handle_signal_and_exit no_most_io");
    return ok ? 0 : 1;
}

static int self_test(void) {
    if (strcmp(DMDT, "/eso/bin/apps/dmdt")) return 1;
    if (strcmp(IPL_CONFIG, "/etc/eso/production")) return 2;
    if (strcmp(AU_MARKER, "/tmp/mibr-alt111-au-framing.enabled")) return 3;
    puts("PARITY_SESSION_SELFTEST=PASS");
    puts("release=/eso/bin/apps/dmdt dc 72 ; /eso/bin/apps/dmdt sc 4 72");
    puts("release_delay_us=500000");
    puts("restore=/eso/bin/apps/dmdt dc 70 33 ; /eso/bin/apps/dmdt sc 4 70");
    printf("dmdt_timeout_ms=%u\n", DMDT_TIMEOUT_MS);
    printf("watchdog_margin_seconds=%u\n", WATCHDOG_MARGIN_SECONDS);
    return 0;
}

int main(int argc, char **argv) {
    const char *bridge, *input, *output;
    long max_seconds;
    char *end = NULL, b[64];
    int pipefd[2] = {-1,-1}, st = 0, rc = 1, route_owned = 0, restore_ok = 0;
    int exec_gate=-1,bridge_stopped=1;
    pid_t watchdog = -1, bridge_pid = -1;
    uint64_t deadline = 0;
    int watchdog_reaped=0, lock_owned=0;

    if (argc == 2 && !strcmp(argv[1], "--self-test")) return self_test();
    if (argc == 2 && !strcmp(argv[1], "--identity-self-test")) return identity_self_test();
    if (argc == 2 && !strcmp(argv[1], "--stop")) return request_stop();
    if (argc == 2 && !strcmp(argv[1], "--restore-stock")) {
        int rr;
        struct alt111_native_gate_status gs;
        if(access(LOCK_PATH,F_OK)!=0 && access(BRIDGE_PID_PATH,F_OK)!=0 &&
           access(OLD_DIRECT_MARKER,F_OK)!=0) {puts("owner_result=NO_ACTIVE_OWNER");return 0;}
        if(pid_alive_from_file(PID_PATH) || pid_alive_from_file(WATCHDOG_PID_PATH)) {
            fprintf(stderr,"ERROR active parity owner; stop it before restoring\n"); return 18;
        }

        owner_process_pid=getpid();
        owner_token=((monotonic_ms()<<20)^((uint64_t)getpid()<<3))|1u;
        if(access(LOCK_PATH,F_OK)!=0) {
            if(acquire_lock()!=0)return 18;
        } else {
            session_lock_fd=open(LOCK_PATH,O_RDWR);
            if(session_lock_fd<0 || fcntl(session_lock_fd,F_SETFD,FD_CLOEXEC)!=0 ||
               !lock_fd_matches_path(session_lock_fd)) {
                if(session_lock_fd>=0)close(session_lock_fd);
                session_lock_fd=-1;return 18;
            }
        }

        if(access(BRIDGE_PID_PATH,F_OK)==0){
            fprintf(stderr,"ERROR unconfirmed writer identity; reboot/reconcile required\n");
            close(session_lock_fd);session_lock_fd=-1;return 19;
        }

        /*
         * Recover the exact stale-preflight case proven on MU1440: an older
         * session created LOCK_PATH, then F_SETLK returned ENOSYS before PID,
         * ticket, backend, AU marker or route ownership existed.  Only clear
         * it when the live native gate proves stock state and every ownership
         * artifact is absent.
         */
        if(access(PID_PATH,F_OK)!=0 && access(WATCHDOG_PID_PATH,F_OK)!=0 &&
           access(BACKEND_STATE_PATH,F_OK)!=0 && access(OWNER_TICKET_PATH,F_OK)!=0 &&
           access(AU_MARKER,F_OK)!=0 && access(OLD_DIRECT_MARKER,F_OK)!=0 &&
           gate_snapshot(&gs)==0 && gs.state==0u) {
            if(lock_fd_matches_path(session_lock_fd))unlink(LOCK_PATH);
            unlink(STOP_REQUEST_PATH);
            close(session_lock_fd);session_lock_fd=-1;
            puts("owner_result=STALE_PREFLIGHT_LOCK_CLEARED_STOCK_CONFIRMED");
            return 0;
        }

        if(read_trimmed(BACKEND_STATE_PATH,b,sizeof(b)) ||
           (strcmp(b,"writev_gate") && strcmp(b,"dmdt_reference"))) {
            fprintf(stderr,"ERROR missing/invalid original ownership backend; reconcile required\n");
            close(session_lock_fd);session_lock_fd=-1;return 21;
        }
        gate_backend=!strcmp(b,"writev_gate");
        (void)write_text(STATE_PATH, "manual_restoring_backend\n");
        rr=backend_restore();
        unlink(AU_MARKER);
        (void)write_text(STATE_PATH, rr==0 ? "manual_stock\n" : "manual_restore_failed\n");
        if(rr==0 && lock_fd_matches_path(session_lock_fd)) {
            unlink(LOCK_PATH); unlink(BRIDGE_PID_PATH); unlink(PID_PATH);
        }
        close(session_lock_fd);session_lock_fd=-1;
        return rr==0 ? 0 : 20;
    }
    if (argc != 5) {
        fprintf(stderr, "usage: %s BRIDGE INPUT OUTPUT MAX_SECONDS\n", argv[0]);
        return 64;
    }
    bridge = argv[1]; input = argv[2]; output = argv[3];
    errno = 0; max_seconds = strtol(argv[4], &end, 10);
    if (errno || end == argv[4] || *end || max_seconds < 5 || max_seconds > 600)
        return 65;

    if(settings_backend())return 13;
    if (!gate_backend && access(DMDT, X_OK) != 0) { fprintf(stderr, "ERROR missing dmdt\n"); return 10; }
    if (access(bridge, X_OK) != 0) { fprintf(stderr, "ERROR missing bridge\n"); return 11; }
    if(bridge_identity(bridge)) {
        fprintf(stderr,"ERROR bridge does not match this owner build; no ownership mutation\n");return 11;
    }
    if (!source_ready()) { fprintf(stderr, "ERROR stream111 not ready\n"); return 12; }
    if (pid_alive_from_file(OLD_AUTO_PID) ||
        pid_alive_from_file("/tmp/mibr-direct-auto-watchdog.pid") ||
        pid_alive_from_file("/tmp/mibr-direct-auto-bridge.pid")) {
        fprintf(stderr, "ERROR legacy Auto-Direct must be disabled/stopped\n");
        return 13;
    }
    if(access(OLD_DIRECT_MARKER,F_OK)==0) {
        fprintf(stderr,"ERROR existing native gate request; reconcile its owner first\n");return 18;
    }
    if(identity_self_test()){
        fprintf(stderr,"ERROR bound process-handle target qualification failed\n");return 19;
    }

    owner_process_pid=getpid();
    owner_token=((monotonic_ms()<<20)^((uint64_t)getpid()<<3))|1u;
    if(acquire_lock()!=0) { fprintf(stderr,"ERROR parity owner lock exists; reconcile stock first\n"); return 18; }
    lock_owned=1;

    signal(SIGINT, on_signal); signal(SIGTERM, on_signal); signal(SIGHUP, on_signal); signal(SIGPIPE,SIG_IGN);
    snprintf(b, sizeof(b), "%ld\n", (long)getpid());
    if (write_text(PID_PATH, b) != 0) {
        if(lock_fd_matches_path(session_lock_fd))unlink(LOCK_PATH);
        close(session_lock_fd);session_lock_fd=-1;return 14;
    }
    snprintf(b,sizeof(b),"%llu\n",(unsigned long long)owner_token);
    if(write_text(OWNER_TICKET_PATH,b))goto done;
    if(write_text(BACKEND_STATE_PATH,gate_backend ? "writev_gate\n" : "dmdt_reference\n"))goto done;
    (void)write_text(STATE_PATH, "preflight\n");

    if (pipe(pipefd) != 0) goto done;
    if(fcntl(pipefd[0],F_SETFD,FD_CLOEXEC)!=0 || fcntl(pipefd[1],F_SETFD,FD_CLOEXEC)!=0)goto done;
    if(gate_backend) {
        if(bridge_spawn(bridge,input,output,&bridge_pid,&exec_gate)){
            if(bridge_pid>1)bridge_stopped=0;
            goto done;
        }
        bridge_stopped=0;bridge_created=1u;
    }
    watchdog = fork();
    if (watchdog < 0) goto done;
    if (watchdog == 0) {
        close(pipefd[1]);
        if(exec_gate>=0)close(exec_gate);
        watchdog_main(pipefd[0], (unsigned)max_seconds + WATCHDOG_MARGIN_SECONDS);
    }
    close(pipefd[0]); pipefd[0] = -1;
    {
        char expected[48], actual[48];
        uint64_t until=monotonic_ms()+2000u;
        snprintf(expected,sizeof(expected),"%ld",(long)watchdog);
        do {
            if(read_trimmed(WATCHDOG_PID_PATH,actual,sizeof(actual))==0 && !strcmp(actual,expected))break;
            usleep(10000);
        } while(monotonic_ms()<until);
        if(read_trimmed(WATCHDOG_PID_PATH,actual,sizeof(actual))!=0 || strcmp(actual,expected))goto done;
    }

    if (gate_backend && touch_file(AU_MARKER) != 0) {
        fprintf(stderr, "ERROR cannot arm M1AU marker\n");
        goto done;
    }

    if(g_stop)goto done;
    if(!gate_backend) {
        struct alt111_native_gate_status before,after;
        int observed=!gate_snapshot(&before) && before.state==0u && before.tracked;
        (void)write_text(STATE_PATH,"probing_dmdt_no_custom_payload\n");
        if(route_release()) { fprintf(stderr,"ERROR DMDT release failed\n");goto done; }
        route_owned=1;
        usleep(500000);
        observed=observed && !gate_snapshot(&after) && after.process==before.process &&
            after.state==0u && !after.inflight;
        printf("ownership_result=OWNERSHIP_UNPROVEN\nnative_probe_snapshot=%s\ncustom_payload=NEVER_STARTED\n",
            observed ? "QUIET_SNAPSHOT_NOT_EXCLUSIVITY_PROOF" : "ACTIVE_OR_UNKNOWN");
        rc=21;goto done;
    }
    (void)write_text(STATE_PATH,"waiting_native_gate_drain\n");
    if(gate_take()) {
        fprintf(stderr,"ERROR native gate ownership unproven; custom payload not started\n");
        rc=21;goto done;
    }
    route_owned=1;
    if(g_stop)goto done;

    (void)write_text(STATE_PATH, "starting_bridge\n");
    {
        char token='G';
        if(write(exec_gate,&token,1)!=1){
        fprintf(stderr, "ERROR bridge spawn failed\n");
        goto done;
        }
        close(exec_gate);exec_gate=-1;
    }
    (void)write_text(STATE_PATH, "direct\n");

    rc = 0;
    deadline=monotonic_ms()+(uint64_t)max_seconds*1000u;
    while (!g_stop && monotonic_ms() < deadline) {
        if(read_ticket(STOP_REQUEST_PATH)==owner_token){g_stop=1;break;}
        if(!gate_owned()) {fprintf(stderr,"ERROR native gate proof lost; stopping custom writer\n");rc=23;break;}
        pid_t ww=waitpid(watchdog,&st,WNOHANG);
        if(ww==watchdog || (ww<0&&errno!=EINTR)) {watchdog_reaped=1;rc=17;break;}
        pid_t w = waitpid(bridge_pid, &st, WNOHANG);
        if (w == bridge_pid) {
            bridge_stopped=1;
            bridge_pid = -1;
            if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) rc = 15;
            break;
        }
        if (w < 0 && errno != EINTR) {
            rc = 16;
            break;
        }
        /*
         * QNX O_RDWR procfs handles hold a terminating process at the
         * debugger termination point until last-close. Treat that state as
         * an early bridge exit even though waitpid() cannot reap it yet.
         */
        if(bridge_handle>=0 && bound_process_dead(bridge_handle)) {
            bridge_stopped=1;
            rc=15;
            break;
        }
        usleep(100000);
    }
    if (g_stop && rc == 0) rc = 130;

done:
    if(exec_gate>=0){close(exec_gate);exec_gate=-1;}
    if (bridge_pid > 1) bridge_stopped=stop_bridge(bridge_pid)==0;
    if(bridge_stopped)unlink(BRIDGE_PID_PATH);
    if(!bridge_stopped){
        (void)write_text(STATE_PATH,"blocked_stop_unconfirmed\n");
        rc=19;
    }else if (route_owned) {
        (void)write_text(STATE_PATH, "restoring_backend\n");
        restore_ok = backend_restore() == 0;
    } else {
        /* A partial release can still leave routing inconsistent. */
        restore_ok = backend_restore() == 0;
    }
    if(bridge_stopped)unlink(AU_MARKER);

    if (restore_ok) {
        (void)write_text(STATE_PATH, rc == 0 ? "complete_stock\n" : rc==21 ? "ownership_unproven_stock\n" : "failed_stock\n");
        if (pipefd[1] >= 0) {
            char token = 'R';
            if (write(pipefd[1], &token, 1) != 1) {
                /* Recovery is already complete; the watchdog will time out and
                 * issue the same stock-route restore again if this signal fails. */
            }
        }
    } else {
        (void)write_text(STATE_PATH, "restore_retry_by_watchdog\n");
        rc = 20;
    }
    if (pipefd[1] >= 0) close(pipefd[1]);
    if (watchdog > 1 && !watchdog_reaped) {
        uint64_t until=monotonic_ms()+15000u;
        while(monotonic_ms()<until) {
            pid_t w=waitpid(watchdog,&st,WNOHANG);
            if(w==watchdog || (w<0&&errno==ECHILD)) {
                watchdog_reaped=1;
                if(w==watchdog && WIFEXITED(st) && WEXITSTATUS(st)!=0) { rc=20;restore_ok=0; }
                break;
            }
            usleep(100000);
        }
        if(!watchdog_reaped)rc=20;
    }
    unlink(PID_PATH);
    if(bridge_stopped)unlink(BRIDGE_PID_PATH);
    if(watchdog_reaped)unlink(WATCHDOG_PID_PATH);
    if(restore_ok && (watchdog<=1 || watchdog_reaped) && lock_owned &&
       lock_fd_matches_path(session_lock_fd))unlink(LOCK_PATH);
    if(session_lock_fd>=0)close(session_lock_fd);
    if(bridge_handle>=0)close(bridge_handle);
    return rc;
}
