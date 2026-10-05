"""Exercise real POSIX session lifecycle with temporary paths and fake DMDT.

Only filesystem constants and the DMDT timeout are changed in the test build;
the production control flow, pipes, fork/exec, locks and signals are unchanged.
"""
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

source=Path("src/native/parity-session/parity_session.c").read_text()
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    names=["DMDT","IPL_CONFIG","STATE_PATH","PID_PATH","BRIDGE_PID_PATH","LOCK_PATH",
           "WATCHDOG_PID_PATH","AU_MARKER","OLD_DIRECT_MARKER","SOURCE_STATE","SOURCE_HB",
           "OLD_AUTO_PID","OLD_AUTO_TEMP","OLD_AUTO_PERSIST"]
    paths={n:root/n.lower() for n in names}
    import re
    for name,path in paths.items():
        source,count=re.subn(r"^#define "+name+r" .+$",f'#define {name} "{path}"',source,flags=re.M)
        assert count==1,name
    source=source.replace("#define DMDT_TIMEOUT_MS 5000u","#define DMDT_TIMEOUT_MS 500u")
    (root/"session.c").write_text(source)
    binary=root/"session"
    subprocess.run(["cc","-std=gnu99","-Wall","-Wextra","-Werror",str(root/"session.c"),"-o",str(binary)],check=True)
    log=root/"commands"
    fail=root/"fail"
    paths["DMDT"].write_text(f'''#!{sys.executable}
import sys,time
from pathlib import Path
cmd=" ".join(sys.argv[1:])
with open({str(log)!r},"a") as f: f.write(cmd+"\\n")
mode=Path({str(fail)!r}).read_text().strip() if Path({str(fail)!r}).exists() else ""
if mode=="timeout" and cmd=="dc 72": time.sleep(3)
sys.exit(1 if mode and cmd==mode else 0)
''')
    paths["DMDT"].chmod(0o755)
    bridge=root/"bridge"
    def bridge_delay(seconds):
        bridge.write_text(f"#!{sys.executable}\nimport time\ntime.sleep({seconds})\n")
        bridge.chmod(0o755)
    paths["SOURCE_STATE"].write_text("streaming\n")
    paths["SOURCE_HB"].touch()
    paths["OLD_AUTO_TEMP"].write_text("0\n")
    command=[str(binary),str(bridge),"tcp://127.0.0.1:1",str(root/"output"),"5"]
    def wait_for(path,text=None,timeout=5):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            if path.exists() and (text is None or path.read_text().strip()==text): return
            time.sleep(0.02)
        raise AssertionError((str(path),text,"timeout"))
    def restored():
        cmds=log.read_text().splitlines()
        assert "dc 70 33" in cmds and "sc 4 70" in cmds,cmds
    bridge_delay(0.1)
    cp=subprocess.run(command,capture_output=True,timeout=7)
    assert cp.returncode==0,cp.stderr
    assert not paths["LOCK_PATH"].exists()
    assert log.read_text().splitlines()==["dc 72","sc 4 72","dc 70 33","sc 4 70"]

    # Concurrent and manual route owners are rejected before any DMDT mutation.
    log.write_text("");bridge_delay(60)
    parent=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    wait_for(paths["STATE_PATH"],"direct")
    cp=subprocess.run(command,capture_output=True,timeout=3)
    assert cp.returncode==18,cp.stderr
    cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=3)
    assert cp.returncode==18,cp.stderr
    assert log.read_text().splitlines()==["dc 72","sc 4 72"]
    parent.terminate();parent.communicate(timeout=7);restored()
    assert not paths["LOCK_PATH"].exists()

    # SIGKILL must expose pipe EOF even though the exec'ed bridge remains alive.
    log.write_text("")
    parent=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    wait_for(paths["STATE_PATH"],"direct")
    parent.kill();parent.communicate(timeout=2)
    wait_for(paths["STATE_PATH"],"emergency_restored",timeout=4)
    restored();assert paths["LOCK_PATH"].exists(),"emergency must quarantine stale ownership"
    until=time.monotonic()+2
    while paths["WATCHDOG_PID_PATH"].exists() and time.monotonic()<until:time.sleep(0.02)
    cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=4)
    assert cp.returncode==0,cp.stderr
    assert not paths["LOCK_PATH"].exists()

    # A dead watchdog is detected by the parent, which restores stock itself.
    log.write_text("")
    parent=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    wait_for(paths["STATE_PATH"],"direct")
    os.kill(int(paths["WATCHDOG_PID_PATH"].read_text()),signal.SIGKILL)
    parent.communicate(timeout=5)
    assert parent.returncode==17,parent.returncode
    restored()
    paths["WATCHDOG_PID_PATH"].unlink(missing_ok=True)

    # Partial release and restore failures never report success.
    bridge_delay(0.1)
    for failure in ("sc 4 72","dc 70 33","timeout"):
        log.write_text("");fail.write_text(failure)
        cp=subprocess.run(command,capture_output=True,timeout=8)
        assert cp.returncode!=0,(failure,cp.stderr)
        restored()
        fail.unlink()
        cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=5)
        assert cp.returncode==0,cp.stderr
print("PARITY_SESSION_LIFECYCLE=PASS normal parallel manual_busy parent_kill watchdog_kill partial_release restore_failure timeout")
