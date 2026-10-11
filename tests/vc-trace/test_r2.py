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

with tempfile.TemporaryDirectory(prefix='vc-r2-', dir='/mnt/data/') as td:
    out=Path(td)
    port_sock=socket.socket()
    port_sock.bind(('127.0.0.1',0))
    port=port_sock.getsockname()[1]
    port_sock.listen(1)
    sent=[False]
    payloads=[b'\x00\xff\x01FOO', b'DSI\x00\x12\x80', b'END']
    def server():
        port_sock.settimeout(8)
        conn,_=port_sock.accept()
        with conn:
            conn.settimeout(.2)
            try:
                if conn.recv(1): sent[0]=True
            except socket.timeout: pass
            for x in payloads:
                conn.sendall(x)
                time.sleep(.05)
        port_sock.close()
    t=threading.Thread(target=server,daemon=True); t.start()
    p=subprocess.run([str(BIN),'--capture','--out',str(out),'--seconds','10','--port',str(port)], capture_output=True, text=True,timeout=12)
    t.join(2)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert not sent[0], 'DSI probe sent data to socket'
    assert (out/'dsi-client-original.bin').read_bytes()==b''.join(payloads)
    index=(out/'dsi-chunks.tsv').read_text().splitlines()
    assert index[0]=='mono_ms\toffset\tbytes'
    assert len(index)>=2
    assert int((out/'dsi-report.txt').read_text().split('raw_bytes=')[1].splitlines()[0])==len(b''.join(payloads))
    key='[000000001000ms] NOTE RIGHT_WHEEL +1\n[000000001002ms] EVENT KBD=4 KEY=40\n'
    merged=merge.merged(key,(out/'dsi-chunks.tsv').read_text())
    assert merged[0][0]==1000 and merged[0][3]=='KEYPANEL_NOTE'
    assert any(x[3]=='DSI_RECV_CHUNK' and 'PROTOCOL_UNDECODED' in x[4] for x in merged)
    second=subprocess.run([str(BIN),'--capture','--out',str(out),'--seconds','10','--port',str(port)],capture_output=True,timeout=2)
    assert second.returncode!=0, 'must not overwrite previous capture'
    print('R2_HOST_TEST=PASS rx_only,raw_exact,chunk_clock,staging_guards,no_overwrite')
