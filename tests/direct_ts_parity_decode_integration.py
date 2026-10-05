"""Independent H.264 decode proof: generated IDR + P pictures survive parity.
This proves host codec continuity, not MOST/cluster decoder compatibility.
"""
import hashlib
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

binary=Path(sys.argv[1]).resolve()
root=Path(sys.argv[2]);root.mkdir(parents=True,exist_ok=True)
source=root/"synthetic-moving-source.h264";output=root/"synthetic-parity.ts"
version=subprocess.check_output(["ffmpeg","-version"],text=True)
(root/"ffmpeg-version.txt").write_text(version)
subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
    "-f","lavfi","-i","testsrc2=size=1010x376:rate=40","-frames:v","40",
    "-c:v","libx264","-profile:v","baseline","-preset","ultrafast",
    "-tune","zerolatency","-bf","0","-x264-params",
    "aud=1:repeat-headers=1:keyint=20:min-keyint=20:scenecut=0",
    "-f","h264",str(source)],check=True,timeout=30)
raw=source.read_bytes()
nals=[part for part in re.split(b"\x00\x00\x00?\x01",raw) if part]
aus=[]
for nal in nals:
    if nal[0]&31==9:aus.append([])
    assert aus,"Encoder must emit an AUD before its first AU"
    aus[-1].append(nal)
assert len(aus)==40
assert sum(any(n[0]&31==1 for n in au) for au in aus)>=30
listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1)
port=listener.getsockname()[1];errors=[]
def serve():
    try:
        conn,_=listener.accept()
        with conn:
            epoch=time.monotonic()
            for i,au in enumerate(aus):
                delay=epoch+i/40-time.monotonic()
                if delay>0:time.sleep(delay)
                idr=any(n[0]&31==5 for n in au)
                payload=b"".join(b"\x00\x00\x00\x01"+nal for nal in au)
                flags=12|int(idr)|(2 if i==0 else 0)  # Present initial zero.
                record=struct.pack(">4sHHIIQQQQ",b"M1AU",1,56,flags,len(payload),1,1,1,i+1)
                record+=struct.pack("<II",((i%40)<<32)//40,i//40)+payload
                conn.sendall(record)
            time.sleep(.12)
    except Exception as error:errors.append(repr(error))
    finally:listener.close()
thread=threading.Thread(target=serve,daemon=True);thread.start()
env={**os.environ,"MIBR_PARITY_STATUS":str(root/"bridge.status")}
cp=subprocess.run([str(binary),f"tcp://127.0.0.1:{port}",str(output)],
    env=env,capture_output=True,text=True,timeout=15)
(root/"bridge.stdout.txt").write_text(cp.stdout)
(root/"bridge.stderr.txt").write_text(cp.stderr)
thread.join(2)
assert cp.returncode==0 and not errors,(cp.returncode,cp.stderr,errors)
def hashes(path,destination):
    cp=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-xerror",
        "-err_detect","explode","-i",str(path),"-map","0:v:0","-fps_mode",
        "passthrough","-f","framehash","-"],capture_output=True,text=True,timeout=20)
    assert cp.returncode==0,(path,cp.stderr)
    destination.write_text(cp.stdout)
    return [line.split(",")[-1].strip() for line in cp.stdout.splitlines() if not line.startswith("#")]
expected=hashes(source,root/"source.framehash")
actual=hashes(output,root/"parity.framehash")
assert len(expected)==40 and actual==expected,(len(expected),len(actual),"decoded frame mismatch")
assert len(set(actual))>30,"Footage must prove motion between keyframes"
manifest=[]
for path in sorted(root.iterdir()):
    if path.is_file():
        manifest.append(hashlib.sha256(path.read_bytes()).hexdigest()+" "+path.name+"\n")
(root/"SHA256SUMS.txt").write_text("".join(manifest))
print("PARITY_DECODE_INTEGRATION=PASS frames=40 predictive_at_least=30 decoded_hashes_identical moving_between_IDRs initial_zero_present")
