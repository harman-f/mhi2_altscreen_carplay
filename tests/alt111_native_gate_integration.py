"""Real blocking writev, drain barrier and descriptor aliases, with both gates."""
import os
import select
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    guard = root / 'guard.so'
    subprocess.run(['cc', '-shared', '-fPIC', '-O2', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
                    '-DALT111_NATIVE_GATE_TEST', '-Isrc/native/altscreen111-gen2/include',
                    'src/native/altscreen111-gen2/src/alt111_native_gate.c', '-ldl', '-pthread',
                    '-o', str(guard)], cwd=ROOT, check=True)
    old = (ROOT / 'src/native/isotx2-gate/isotx2_gate.c').read_text()
    for name, value in [('DIRECT_MARKER', root/'request'), ('RESET_MARKER', root/'reset'),
                        ('STATS_PATH', root/'old.stats'), ('LOG_PATH', root/'old.log')]:
        import re
        old, count = re.subn(r'^#define '+name+r' .+$', '#define '+name+' "'+str(value)+'"', old, flags=re.M)
        assert count == 1
    (root/'old.c').write_text(old)
    subprocess.run(['cc', '-shared', '-fPIC', '-O2', '-std=gnu99', '-Wall', '-Wextra',
                    str(root/'old.c'), '-ldl', '-pthread', '-o', str(root/'old.so')], check=True)
    client = root/'client.c'
    client.write_text(r'''
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/uio.h>
#include <unistd.h>
static int fd;
static void *blocked(void *unused) {
    char bytes[65536];struct iovec vec;ssize_t rc;(void)unused;
    memset(bytes,'A',sizeof(bytes));vec.iov_base=bytes;vec.iov_len=sizeof(bytes);
    rc=writev(fd,&vec,1);
    if(rc!=(ssize_t)sizeof(bytes))return (void *)1;
    return NULL;
}
int main(int argc,char **argv) {
    char bytes[4096],command[32];pthread_t thread;void *result;int flags;
    if(argc!=2)return 1;
    fd=open(argv[1],O_WRONLY|O_NONBLOCK);if(fd<0)return 2;
    memset(bytes,'F',sizeof(bytes));while(write(fd,bytes,sizeof(bytes))>0){}
    flags=fcntl(fd,F_GETFL);if(fcntl(fd,F_SETFL,flags&~O_NONBLOCK))return 3;
    if(pthread_create(&thread,NULL,blocked,NULL))return 4;
    if(!fgets(command,sizeof(command),stdin))return 5;
    pthread_join(thread,&result);if(result)return 6;
    {
        struct iovec vec;int alias=dup(fd),alias2=dup2(fd,50);
        vec.iov_base=(void *)"X";vec.iov_len=1;
        if(alias<0||alias2!=50||writev(alias,&vec,1)!=1||write(alias2,"Y",1)!=1||write(fd,"Z",1)!=1)return 7;
        close(alias);close(alias2);
    }
    puts("SUPPRESSED");fflush(stdout);
    if(!fgets(command,sizeof(command),stdin))return 8;
    if(write(fd,"R",1)!=1)return 9;
    close(fd);return 0;
}
''')
    binary = root/'client'
    subprocess.run(['cc', '-std=gnu99', '-Wall', '-Wextra', '-Werror', str(client), '-pthread', '-o', str(binary)], check=True)
    fifo=root/'fifo';os.mkfifo(fifo)
    request=root/'request';status=root/'status'
    def snapshot():
        try:
            fields=status.read_text().strip().split(' ')
        except FileNotFoundError:
            return None
        assert len(fields)==8 and fields[0]=='M1GATE1', fields
        return [int(value) for value in fields[1:]]
    def until(predicate, seconds=4):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            value=snapshot()
            if value is not None and predicate(value):return value
            time.sleep(.01)
        raise AssertionError(('timeout',snapshot()))
    for downstream in ('', ':'+str(root/'old.so')):
        request.unlink(missing_ok=True);status.unlink(missing_ok=True)
        reader=os.open(fifo,os.O_RDONLY|os.O_NONBLOCK)
        env={**os.environ, 'LD_PRELOAD':str(guard)+downstream,
             'ALT111_NATIVE_GATE_TARGET':str(fifo),'MIBR_ISOTX2_GATE_TARGET':str(fifo),
             'ALT111_NATIVE_GATE_REQUEST':str(request),'ALT111_NATIVE_GATE_STATUS':str(status)}
        process=subprocess.Popen([str(binary),str(fifo)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        try:
            until(lambda s:s[3]>0)  # Real stock writev is still blocked in kernel.
            request.write_text('123456\n')
            until(lambda s:s[0]==123456 and s[6]==1)
            time.sleep(.1)
            assert snapshot()[3]>0 and snapshot()[6]==1,'false drain acknowledgement'
            end=time.monotonic()+4
            while time.monotonic()<end:
                try:os.read(reader,65536)
                except BlockingIOError:pass
                value=snapshot()
                if value and value[6]==2:break
                time.sleep(.005)
            else:raise AssertionError('writev did not drain')
            while True:
                try:
                    if not os.read(reader,65536):break
                except BlockingIOError:break
            process.stdin.write('continue\n');process.stdin.flush()
            assert select.select([process.stdout],[],[],4)[0], 'suppressed alias write hung'
            assert process.stdout.readline().strip()=='SUPPRESSED'
            until(lambda s:s[4]>=3 and s[2]==1 and s[6]==2)
            try:
                assert not os.read(reader,100),'native bytes leaked through suppressed aliases'
            except BlockingIOError:pass
            request.unlink()
            until(lambda s:s[0]==0 and s[6]==0)
            process.stdin.write('stock\n');process.stdin.flush()
            process.wait(timeout=4);assert process.returncode==0
            assert os.read(reader,100)==b'R','stock did not resume'
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=3)
            os.close(reader)
    print('ALT111_NATIVE_GATE_INTEGRATION=PASS blocking_writev drain aliases stock_resume frozen_gate_composition')
