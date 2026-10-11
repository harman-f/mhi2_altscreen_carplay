#!/usr/bin/env python3
"""Host-only R2 regression: RX-only stream, bounded output, staged diff, chronology."""
import importlib.util
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
BIN = Path(__file__).parent/'mibr-dsi-rx-host'

def mod(path, name):
    spec=importlib.util.spec_from_file_location(name, path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

stage=mod(ROOT/'tools/prepare_vc_trace_r2.py', 'prepare')
merge=mod(ROOT/'tools/merge_vc_r2_timeline.py', 'timeline')

lsd='DSITRACER_ACTIVATED=no\nMIBR-NavIgnore.jar\nMIBR-Most20FPS.jar\n-Dde.vw.mib.startup.flag=DSITRACER\nDSITracer-VW-H29.319.93.jar DSITracer.jar\n'
conf='use.appender=client\nactivate.extension=ctrl\n'+''.join(f'#{x}=full\n' for x in stage.INTERFACES)
a,b=stage.stage(lsd,conf)
assert a.replace('DSITRACER_ACTIVATED=yes','DSITRACER_ACTIVATED=no')==lsd
assert b.count('=full')==6
assert b.count('org.dsi.ifc.')==6
assert 'activate.extension=ctrl,DSIKeyPanelEx' not in b
for x in stage.INTERFACES: assert (x+'=full') in b
try:
    stage.stage(lsd.replace('MIBR-NavIgnore.jar',''),conf)
except ValueError: pass
else: raise AssertionError('missing extension must fail closed')

# Synthetic OEM 1.3.17 handshake. Never use or publish the proprietary lib.
import struct
LIB=b'BZh'+bytes(range(128))*50
TRACE=b'@m'+struct.pack('>I',4)+b'TEST\n'+b'\xbe\x00\x00\x00\x01\n\x00\xff\n'+b'@a\n'
def recvn(sock,n):
    out=b''
    while len(out)<n:
        x=sock.recv(n-len(out))
        if not x:raise AssertionError('premature EOF')
        out+=x
    return out
def run_case(case):
    with tempfile.TemporaryDirectory(prefix='vc-r2-') as td:
        out=Path(td);srv=socket.socket();srv.bind(('127.0.0.1',0))
        port=srv.getsockname()[1];srv.listen(1);errors=[]
        def server():
            try:
                srv.settimeout(5);conn,_=srv.accept()
                with conn:
                    conn.settimeout(5)
                    count=struct.unpack('>H',recvn(conn,2))[0]
                    assert recvn(conn,count)==b'VersionInfo client=1.3.17'
                    header=b'@d'+struct.pack('>Q',len(LIB))+b'\n'
                    if case=='bad-header':conn.sendall(b'@x'+header[2:]);return
                    if case=='oversize':conn.sendall(b'@d'+struct.pack('>Q',16*1024*1024+1)+b'\n');return
                    if case=='eof':conn.sendall(header+LIB[:10]);return
                    if case=='bad-magic':conn.sendall(b'@d'+struct.pack('>Q',3)+b'\nBAD');return
                    if case=='split':
                        for x in (b'@',b'd',header[2:5],header[5:],LIB[:1],LIB[1:3],LIB[3:90],LIB[90:]):
                            conn.sendall(x);time.sleep(.002)
                    else:conn.sendall(header+LIB)
                    assert recvn(conn,2)==b'\x00\x04'
                    assert recvn(conn,4)==b'>OK<'
                    if case=='split':
                        for x in (TRACE[:1],TRACE[1:9],TRACE[9:]):conn.sendall(x);time.sleep(.003)
                    else:conn.sendall(TRACE)
                    time.sleep(.05)
            except BaseException as exc:errors.append(exc)
            finally:srv.close()
        t=threading.Thread(target=server,daemon=True);t.start()
        p=subprocess.run([str(BIN),'--capture','--out',str(out),'--seconds','10','--port',str(port)],capture_output=True,text=True,timeout=8)
        t.join(3);assert not errors,(case,errors,p.stdout,p.stderr)
        report=(out/'dsi-report.txt').read_text()
        if case in ('bad-header','oversize','eof','bad-magic'):
            assert p.returncode==5,(case,p.stdout,p.stderr)
            assert 'ok_sent=0' in report and 'raw_bytes=0\n' in report
        else:
            assert p.returncode==0,(case,p.stdout,p.stderr)
            assert 'ok_sent=1' in report and f'lib_bytes={len(LIB)}' in report
            assert (out/'dsi-client-original.bin').read_bytes()==TRACE
            assert not (out/'client-lib.bin').exists()
            index=(out/'dsi-chunks.tsv').read_text().splitlines()
            assert index[0]=='mono_ms\toffset\tbytes' and len(index)>1
            key='[000000001000ms] NOTE RIGHT_WHEEL +1\n[000000001002ms] EVENT KBD=4 KEY=40\n'
            merged=merge.merged(key,(out/'dsi-chunks.tsv').read_text())
            assert merged[0][0]==1000 and merged[0][3]=='KEYPANEL_NOTE'
            assert any(x[3]=='DSI_RECV_CHUNK' for x in merged)
            again=subprocess.run([str(BIN),'--capture','--out',str(out),'--seconds','10','--port',str(port)],capture_output=True,timeout=2)
            assert again.returncode!=0
for case in ('normal','split','bad-header','oversize','eof','bad-magic'):run_case(case)
print('R2_1_HOST_TEST=PASS handshake,segmentation,raw_exact,no_library_persistence,malformed,eof,cap,staging,no_overwrite')
