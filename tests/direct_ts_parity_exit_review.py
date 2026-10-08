#!/usr/bin/env python3
"""Real processes: distinguish SIGTERM, clean EOF, partial reads and writer EIO."""
import argparse
import signal
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from direct_ts_parity_host_integration import m1au, SPS, PPS, IDR
p=argparse.ArgumentParser();p.add_argument("binary");p.add_argument("--baseline",action="store_true");a=p.parse_args()
valid=m1au(1,SPS+PPS+IDR,idr=True)
for mode,data in (("idle",valid),("partial_header",valid[:20]),("partial_payload",valid[:-2])):
    with tempfile.TemporaryDirectory() as td:
        listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1)
        halt=threading.Event()
        def serve():
            conn,_=listener.accept()
            with conn:conn.sendall(data);halt.wait(5)
            listener.close()
        thread=threading.Thread(target=serve,daemon=True);thread.start()
        output=Path(td)/"out.ts"
        proc=subprocess.Popen([a.binary,f"tcp://127.0.0.1:{listener.getsockname()[1]}",str(output)],stderr=subprocess.PIPE)
        try:
            until=time.monotonic()+3
            while time.monotonic()<until:
                if output.exists() and output.stat().st_size>=12032:break
                time.sleep(.005)
            assert output.exists() and output.stat().st_size>=12032,"writer did not start"
            proc.send_signal(signal.SIGTERM)
            _,errors=proc.communicate(timeout=3)
            expected=1 if a.baseline else 128+signal.SIGTERM
            assert proc.returncode==expected,(mode,proc.returncode,errors)
            if not a.baseline:
                assert b"PARITY_EXIT reason=signal_stop signal=15 rc=143 write_errors=0" in errors,errors
                assert "state=stopped" in Path("/tmp/mibr-parity-ts.status").read_text(), "signal stop must not be a transport failure"
            print(f"SIGNAL_EXIT={mode} rc={proc.returncode} PASS")
        finally:
            halt.set();thread.join(1)
            if proc.poll() is None:proc.kill();proc.wait(timeout=2)
listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1)
def serve_failure():
    conn,_=listener.accept()
    with conn:
        try:conn.sendall(valid);time.sleep(.1)
        except OSError:pass
    listener.close()
thread=threading.Thread(target=serve_failure,daemon=True);thread.start()
cp=subprocess.run([a.binary,f"tcp://127.0.0.1:{listener.getsockname()[1]}","/dev/full"],capture_output=True,timeout=3)
thread.join(1)
assert cp.returncode==1,cp.stderr
if not a.baseline:assert b"PARITY_EXIT reason=writer_error" in cp.stderr,cp.stderr
print("WRITER_ERROR=PASS rc=1 preserved")
