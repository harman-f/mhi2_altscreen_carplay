"""Immediate EOF, transfer deadlines and malformed-input regression tests."""
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from direct_ts_parity_host_integration import SPS, PPS, sc, m1au, pid, payload_offset, parse_pts

def run(binary, record):
    with tempfile.TemporaryDirectory() as td:
        listener=socket.socket()
        listener.bind(("127.0.0.1",0));listener.listen(1)
        port=listener.getsockname()[1]
        def serve():
            conn,_=listener.accept()
            with conn: conn.sendall(record)
            listener.close()
        th=threading.Thread(target=serve,daemon=True);th.start()
        out=Path(td)/"out.ts"
        started=time.monotonic()
        cp=subprocess.run([binary,f"tcp://127.0.0.1:{port}",str(out)],capture_output=True,timeout=5)
        elapsed=time.monotonic()-started;th.join(1)
        return cp,out.read_bytes(),elapsed

binary=sys.argv[1]
large=SPS+PPS+sc(b"\x65"+b"\x55"*250000+b"\x7b\x7c\x7d")
for i in range(12):
    cp,data,elapsed=run(binary,m1au(1,large,idr=True))
    assert cp.returncode==0,cp.stderr.decode()
    assert len(data)%12032==0
    packets=[data[j:j+188] for j in range(0,len(data),188)]
    video=[p for p in packets if pid(p)==0x11]
    assert sum(bool(p[1]&0x40) for p in video)==1
    raw=b"".join(p[payload_offset(p):] for p in video)
    assert raw[14:]==sc(b"\x09\xf0")+large,"EOF truncated/modified the final PES"
    pts=parse_pts(raw)
    end_index=max(j for j,p in enumerate(packets) if pid(p)==0x11)
    end_pcr=45000+(end_index*705)//64
    assert pts-end_pcr>=4500,(pts,end_pcr,"complete PES misses presentation deadline")
    duration=len(data)*8/12288000
    assert elapsed>=duration-0.04,(elapsed,duration,"transport clock runs ahead")
valid=m1au(1,SPS+PPS+sc(b"\x65\x88"),idr=True)
for invalid in (valid[:20],valid[:-2],b"BAD!"+valid[4:]):
    cp,_,_=run(binary,invalid)
    assert cp.returncode!=0,"malformed/partial input was reported successful"
print("PARITY_EOF_INTEGRATION=PASS immediate_eof=12 large_pes_deadline malformed_input=3 paced_output")
