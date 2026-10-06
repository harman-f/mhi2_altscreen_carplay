"""Real owner lifecycle with a simulated native observer and fake DMDT.
The separate native-gate integration test exercises actual blocked writev.
Here only paths, bounded command timing and bridge-fixture identity change.
"""
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/"src/native/parity-session/parity_session.c").read_text()
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    names=["DMDT","IPL_CONFIG","STATE_PATH","PID_PATH","BRIDGE_PID_PATH","LOCK_PATH",
           "WATCHDOG_PID_PATH","AU_MARKER","OLD_DIRECT_MARKER","SOURCE_STATE","SOURCE_HB",
           "OLD_AUTO_PID","OLD_AUTO_TEMP","OLD_AUTO_PERSIST","SETTINGS_TEMP_ROOT",
           "SETTINGS_PERSIST_ROOT","GATE_STATUS_PATH","BACKEND_STATE_PATH",
           "OWNER_TICKET_PATH","STOP_REQUEST_PATH"]
    paths={n:root/n.lower() for n in names}
    paths["SETTINGS_TEMP_ROOT"]=root
    paths["SETTINGS_PERSIST_ROOT"]=root/"persistent"
    paths["SETTINGS_PERSIST_ROOT"].mkdir()
    for name,path in paths.items():
        source,count=re.subn(r"^#define "+name+r" .+$",f'#define {name} "{path}"',source,flags=re.M)
        assert count==1,name
    source=source.replace("#define DMDT_TIMEOUT_MS 5000u","#define DMDT_TIMEOUT_MS 500u")
    (root/"session.c").write_text(source)
    (root/"bound_process.h").write_text((ROOT/"src/native/parity-session/bound_process.h").read_text())
    binary=root/"session";settings=root/"settings"
    shared=["src/native/alt111-settings/settings_core.c","src/native/alt111-settings/settings_posix.c",
            "src/native/altscreen111-gen2/src/alt111_policy.c",
            "src/native/sha256sum-compat/sha256sum_compat.c"]
    common=["cc","-std=gnu99","-Wall","-Wextra","-Werror","-DMIBR_SHA256_LIBRARY_ONLY",
            "-Isrc/native/altscreen111-gen2/include","-Isrc/native/alt111-settings/include"]
    subprocess.run(common+["-DALT111_SESSION_TEST",str(root/"session.c"),*shared,"-o",str(binary)],cwd=ROOT,check=True)
    subprocess.run(common+["-DALT111_SETTINGS_TEST","src/native/alt111-settings/settings_cli.c",*shared,
                   "-o",str(settings)],cwd=ROOT,check=True)
    env={**os.environ,"ALT111_SETTINGS_TEMP_ROOT":str(root),"ALT111_SETTINGS_PERSISTENT_ROOT":str(root/"persistent")}
    def cfg(*args):
        cp=subprocess.run([str(settings),*args],env=env,capture_output=True,text=True,timeout=3)
        assert cp.returncode==0,(args,cp.stdout,cp.stderr)
    cfg("preset","--preset","mibr_dual_view")
    log=root/"commands";log.write_text("");fail=root/"fail";started=root/"bridge_started"
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
        bridge.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nimport time\nPath({str(started)!r}).touch()\ntime.sleep({seconds})\n")
        bridge.chmod(0o755)
        started.unlink(missing_ok=True)
    paths["SOURCE_STATE"].write_text("streaming\n");paths["SOURCE_HB"].touch()
    command=[str(binary),str(bridge),"tcp://127.0.0.1:1",str(root/"output"),"5"]
    mode=["healthy"];halt=threading.Event()
    def observer():
        drops=0
        while not halt.is_set():
            if mode[0]=="stale":
                time.sleep(.01);continue
            try:token=int(paths["OLD_DIRECT_MARKER"].read_text().strip())
            except (FileNotFoundError,ValueError):token=0
            state=2 if token else 0;inflight=0
            if token and mode[0]=="draining":state=1;inflight=1
            if token and mode[0]=="healthy":drops+=1
            now=int(time.monotonic()*1000)
            temp=root/"gate.new"
            temp.write_text(f"M1GATE1 {token} {os.getpid()} 1 {inflight} {drops} {now} {state}\n")
            temp.replace(paths["GATE_STATUS_PATH"])
            time.sleep(.01)
    thread=threading.Thread(target=observer,daemon=True);thread.start()
    def wait_for(path,text=None,timeout=5):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            if path.exists() and (text is None or path.read_text().strip()==text):return
            time.sleep(.01)
        raise AssertionError((str(path),text,"timeout"))
    def stock():
        assert not paths["OLD_DIRECT_MARKER"].exists()
        assert not paths["BRIDGE_PID_PATH"].exists()
        assert log.read_text()=="","gate backend must not issue DMDT"
    def run_probe():
        cp=subprocess.run(command,capture_output=True,text=True,timeout=8)
        assert cp.returncode==21,(cp.returncode,cp.stderr)
        assert "custom_payload=NEVER_STARTED" in cp.stdout
        assert not started.exists() and not paths["AU_MARKER"].exists()
        assert log.read_text().splitlines()==["dc 72","sc 4 72","dc 70 33","sc 4 70"]
    try:
        wait_for(paths["GATE_STATUS_PATH"])
        bridge_delay(.1)
        cp=subprocess.run(command,capture_output=True,timeout=7)
        assert cp.returncode==0,cp.stderr
        assert started.exists() and not paths["LOCK_PATH"].exists();stock()

        # Retain the initial backend across settings changes and native stop.
        bridge_delay(60)
        parent=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        wait_for(paths["STATE_PATH"],"direct")
        cp=subprocess.run(command,capture_output=True,timeout=3)
        assert cp.returncode==18,cp.stderr
        cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=3)
        assert cp.returncode==18,cp.stderr
        cfg("set","--key","ownership.backend","--value","dmdt_reference")
        cp=subprocess.run([str(binary),"--stop"],capture_output=True,timeout=5)
        assert cp.returncode==0,cp.stderr
        parent.communicate(timeout=5)
        assert parent.returncode==130 and not paths["LOCK_PATH"].exists();stock()

        # Zero means until-stop: no deadline-driven handback, but the same
        # token-bound stop path must restore stock and reap the watchdog.
        # The previous frozen-backend case deliberately changed the desired
        # setting while its writev session was live. Restore writev_gate for
        # this new session before expecting the direct state.
        cfg("set","--key","ownership.backend","--value","writev_gate")
        bridge_delay(60)
        zero_command=command[:-1]+["0"]
        parent=subprocess.Popen(zero_command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        wait_for(paths["STATE_PATH"],"direct")
        time.sleep(1.2)
        assert parent.poll() is None,"until-stop session exited without an explicit/failure stop"
        cp=subprocess.run([str(binary),"--stop"],capture_output=True,timeout=5)
        assert cp.returncode==0,cp.stderr
        parent.communicate(timeout=5)
        assert parent.returncode==130 and not paths["LOCK_PATH"].exists();stock()

        cfg("set","--key","ownership.backend","--value","dmdt_reference")
        bridge_delay(.1);run_probe()
        cfg("set","--key","ownership.backend","--value","writev_gate")
        log.write_text("")

        # Parent kill: retained child identity, independent restore, quarantine.
        bridge_delay(60)
        parent=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        wait_for(paths["STATE_PATH"],"direct")
        parent.kill();parent.communicate(timeout=2)
        wait_for(paths["STATE_PATH"],"emergency_restored",timeout=4);stock()
        assert paths["LOCK_PATH"].exists()
        end=time.monotonic()+2
        while paths["WATCHDOG_PID_PATH"].exists() and time.monotonic()<end:time.sleep(.01)
        cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=4)
        assert cp.returncode==0,cp.stderr
        assert not paths["LOCK_PATH"].exists()

        # Watchdog kill is detected; parent restores without PID-file authority.
        parent=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        wait_for(paths["STATE_PATH"],"direct")
        os.kill(int(paths["WATCHDOG_PID_PATH"].read_text()),signal.SIGKILL)
        parent.communicate(timeout=5)
        assert parent.returncode==17,parent.returncode
        stock();paths["WATCHDOG_PID_PATH"].unlink(missing_ok=True)

        # A foreign PID hint never authorizes a signal or handback over a writer.
        unrelated=subprocess.Popen(["sleep","30"])
        try:
            paths["LOCK_PATH"].touch()
            paths["BRIDGE_PID_PATH"].write_text(str(unrelated.pid)+"\n")
            cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=3)
            assert cp.returncode==19 and unrelated.poll() is None,cp.stderr
            paths["BRIDGE_PID_PATH"].unlink()
            cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=4)
            assert cp.returncode==0,cp.stderr
        finally:unrelated.terminate();unrelated.wait(timeout=3)

        # In-flight native writes cannot release the exec barrier.
        mode[0]="draining";bridge_delay(.1)
        parent=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        wait_for(paths["STATE_PATH"],"waiting_native_gate_drain")
        time.sleep(.15);assert not started.exists()
        mode[0]="healthy";parent.communicate(timeout=5)
        assert parent.returncode==0 and started.exists();stock()

        # Freshness failure rejects a start, then explicit reconcile restores.
        mode[0]="stale";time.sleep(.3);bridge_delay(.1)
        cp=subprocess.run(command,capture_output=True,timeout=5)
        assert cp.returncode!=0 and not started.exists(),cp.stderr
        mode[0]="healthy";time.sleep(.05)
        cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=4)
        assert cp.returncode==0,cp.stderr

        # Losing the live proof terminates the custom writer; restored guard ack
        # is required before the quarantined owner can be reconciled.
        bridge_delay(60)
        parent=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        wait_for(paths["STATE_PATH"],"direct")
        mode[0]="stale";time.sleep(.5);mode[0]="healthy"
        parent.communicate(timeout=6)
        assert parent.returncode==23,(parent.returncode,parent.stderr)
        stock()

        # DMDT remains a no-payload probe, including command failures.
        cfg("set","--key","ownership.backend","--value","dmdt_reference")
        bridge_delay(.1);log.write_text("");run_probe()
        for failure in ("sc 4 72","dc 70 33","timeout"):
            log.write_text("");fail.write_text(failure)
            cp=subprocess.run(command,capture_output=True,timeout=8)
            assert cp.returncode!=0 and not started.exists(),(failure,cp.stderr)
            cmds=log.read_text().splitlines()
            assert "dc 70 33" in cmds and "sc 4 70" in cmds,cmds
            fail.unlink()
            cp=subprocess.run([str(binary),"--restore-stock"],capture_output=True,timeout=4)
            assert cp.returncode==0,cp.stderr
    finally:halt.set();thread.join(timeout=2)
print("PARITY_SESSION_LIFECYCLE=PASS gate_only dmdt_probe_no_writer frozen_backend typed_stop until_stop parallel parent_kill watchdog_kill foreign_pid inflight_barrier stale_proof proof_loss partial_release restore_failure timeout")
