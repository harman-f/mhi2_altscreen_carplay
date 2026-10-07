"""Immediate EOF, transfer deadlines and malformed-input regression tests."""
import socket
import signal
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
cp,data,_=run(binary,m1au(1,large,idr=True)+m1au(2,sc(b"\x41\x91"))+m1au(3,sc(b"\x41\x92")))
assert cp.returncode==0,cp.stderr.decode()
video=[data[i:i+188] for i in range(0,len(data),188) if pid(data[i:i+188])==0x11]
assert sum(bool(p[1]&0x40) for p in video)==3,"large IDR incorrectly triggered IDR-only recovery"
assert b"PARITY_SAFE_RECOVERY reason=latency" not in cp.stderr
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
    start_index=min(j for j,p in enumerate(packets) if pid(p)==0x11)
    start_pcr=45000+(start_index*705)//64
    # Recovered Omonob semantics guard presentation lead when the AU/PTS is
    # assigned. They do not phase-shift PTS again so the *tail* of a large PES
    # must still finish 50 ms before presentation. The EOF test therefore
    # verifies lead at PES start and separately verifies that the full PES tail
    # is drained without truncation.
    assert pts-start_pcr>=4500,(pts,start_pcr,"PES starts below minimum presentation lead")
    duration=len(data)*8/12288000
    assert elapsed>=duration-0.04,(elapsed,duration,"transport clock runs ahead")
valid=m1au(1,SPS+PPS+sc(b"\x65\x88"),idr=True)
with tempfile.TemporaryDirectory() as td:
    listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1)
    port=listener.getsockname()[1];halt=threading.Event()
    def serve_stop():
        conn,_=listener.accept()
        with conn:
            conn.sendall(m1au(1,large,idr=True))
            halt.wait(4)
        listener.close()
    thread=threading.Thread(target=serve_stop,daemon=True);thread.start()
    output=Path(td)/"stop.ts"
    proc=subprocess.Popen([binary,f"tcp://127.0.0.1:{port}",str(output)],stderr=subprocess.PIPE)
    try:
        until=time.monotonic()+3
        checked=0
        began=False
        while time.monotonic()<until:
            try:size=output.stat().st_size
            except FileNotFoundError:size=0
            complete=size-(size%12032)
            if complete>checked:
                with output.open("rb") as fh:
                    fh.seek(checked)
                    chunk=fh.read(complete-checked)
                checked=complete
                if any(pid(chunk[i:i+188])==0x11 for i in range(0,len(chunk)-187,188)):
                    began=True
                    break
            time.sleep(.0005)
        if not began:raise AssertionError("large PES did not begin")
        # Trigger only after a physically written block contains video. The
        # remaining ~250 KiB PES is then still in flight under regular-file
        # pacing, making this a real started-PES shutdown test.
        assert checked<len(large),"stop test missed in-flight PES"
        proc.send_signal(signal.SIGTERM)
        _,errors=proc.communicate(timeout=3)
        assert proc.returncode in (1,130),errors  # Interrupted input is not clean EOF.
        data=output.read_bytes()
        video=[data[i:i+188] for i in range(0,len(data),188) if pid(data[i:i+188])==0x11]
        raw=b"".join(p[payload_offset(p):] for p in video)
        assert raw[14:]==sc(b"\x09\xf0")+large,"SIGTERM truncated an already-started PES"
        assert len(data)%12032==0
    finally:
        halt.set();thread.join(1)
        if proc.poll() is None:proc.kill();proc.wait(timeout=2)
for invalid in (valid[:20],valid[:-2],b"BAD!"+valid[4:]):
    cp,_,_=run(binary,invalid)
    assert cp.returncode!=0,"malformed/partial input was reported successful"
print("PARITY_EOF_INTEGRATION=PASS immediate_eof=12 large_idr_then_predictive large_pes_start_lead sigterm_PES_tail malformed_input=3 paced_output")
