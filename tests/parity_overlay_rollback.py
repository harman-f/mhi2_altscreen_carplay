"""Run the real installer/restore in a disposable host filesystem sandbox.

Hardware commands and paths are substituted; copy/hash/error/rollback control
flow is retained. No target filesystem or DMDT is touched.
"""
import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()
for scenario in ("normal","interrupted"):
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);pkg=root/"package";app=root/"app";system=root/"system";state=root/"state";binpath=root/"host-bin"
        for p in (pkg,pkg/"payload",pkg/"runtime",app/"root/altscreen-u2/bin",app/"root/altscreen-u2/scripts",app/"eso/lib",system/"etc/eso/production",system/"etc/boot",state,binpath):p.mkdir(parents=True,exist_ok=True)
        dst=app/"root/altscreen-u2";backup=app/"root/mibr-omonob790-parity-v1-backup"
        old_gen=b"exact old GEN2";old_remux=b"exact old remux";airplay=b"exact target airplay";gate=b"exact stable gate"
        fixtures={dst/"bin/libaltscreen111.so":old_gen,app/"eso/lib/libmibr_carplay111.so":old_gen,
                  dst/"bin/direct-ts-remux":old_remux,app/"eso/lib/libairplay.so":airplay,
                  app/"eso/lib/libmibr_isotx2_gate.so":gate,app/"root/mibr-carplay-autodirect":b"1\n"}
        startup=b'#!/bin/sh\n        LD_PRELOAD=/mnt/app/eso/lib/libmibr_isotx2_gate.so MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager ${DM_EXTRA_OPTS} ${LVDS2} &\n'
        fixtures[system/"etc/boot/startup.sh"]=startup.replace(b"/mnt/app",str(app).encode())
        fixtures[state/"mibr-carplay111-fps"]=b"old valid legacy fps\n"
        fixtures[state/"mibr-carplay111-nav.conf"]=b"exact pre-install legacy nav\n"
        for path,data in fixtures.items():path.write_bytes(data)
        (app/"root/mibr-framing-v1-active").touch()
        (system/"etc/eso/production/smartphone_integrator.json").write_text(f"LD_PRELOAD={app}/eso/lib/libmibr_carplay111.so\n")
        (dst/"scripts/direct_ts_auto_stop.sh").write_text("#!/bin/sh\nexit 0\n");(dst/"scripts/direct_ts_auto_stop.sh").chmod(0o755)
        (pkg/"payload/libaltscreen111.so").write_bytes(b"new GEN2")
        (pkg/"payload/direct-ts-parity").write_bytes(b"new bridge")
        (pkg/"payload/parity-session").write_text("#!/bin/sh\nexit 0\n")
        (pkg/"payload/alt111-settings").write_text("#!/bin/sh\nexit 0\n")
        (pkg/"payload/libmibr_isotx2_guard.so").write_bytes(b"new standalone guard")
        (pkg/"payload/sha256sum").write_text("#!/bin/sh\nexec /usr/bin/sha256sum \"$@\"\n")
        for path in (pkg/"payload").iterdir():path.chmod(0o755)
        for name in ("omonob790_profile.sh","omonob790_session.sh","omonob790_status.sh",
                     "omonob790_drive_supervisor.sh","omonob790_drive_enable.sh",
                     "omonob790_drive_disable.sh","omonob790_drive_status.sh",
                     "gen2_compat_profile.sh"):
            (pkg/"runtime"/name).write_text("#!/bin/sh\nexit 0\n")
        script_inventory=Path("runtime/parity/master-script-basenames.sh").read_text()
        (pkg/"runtime/master-script-basenames.sh").write_text(script_inventory)
        for name in script_inventory.split("'")[1].split():
            (pkg/"runtime"/name).write_text("#!/bin/sh\nexit 0\n")
            fixtures[dst/"scripts"/name]=("exact old wrapper "+name+"\n").encode()
            (dst/"scripts"/name).write_bytes(fixtures[dst/"scripts"/name])
        (pkg/"runtime/settings-basenames.sh").write_text(Path("settings/runtime-basenames.generated.sh").read_text())
        for name in ("install.sh","uninstall.sh"):
            text=Path("deployment/mu1440-omonob790-parity-v1",name).read_text()
            text=re.sub(r"# BEGIN_TARGET_ENV.*?# END_TARGET_ENV\n", "", text, flags=re.S)
            for old,new in (("/tmp/",str(state)+"/"),("/mnt/app",str(app)),("/mnt/system",str(system))):text=text.replace(old,new)
            assert f"DST={dst}" in text,(name,"DST rewrite",dst)
            if name=="install.sh":
                expected_airplay=app/"eso/lib/libairplay.so"
                expected_target=system/"etc/eso/production/smartphone_integrator.json"
                assert f"AIRPLAY={expected_airplay}" in text,(name,"AIRPLAY rewrite",expected_airplay)
                assert f"TARGET={expected_target}" in text,(name,"TARGET rewrite",expected_target)
            for macro,data in (("EXPECTED_AIRPLAY",airplay),("EXPECTED_BASE_GEN2",old_gen),("EXPECTED_BASE_REMUX",old_remux),("EXPECTED_GATE",gate)):
                text=re.sub(r"^"+macro+r"=.+$",macro+"="+sha(data),text,flags=re.M)
            (pkg/name).write_text(text)
        (pkg/"collect-logs.sh").write_text("#!/bin/sh\nexit 0\n")
        (binpath/"mount").write_text("#!/bin/sh\nexit 0\n")
        (binpath/"ksh").write_text("#!/bin/sh\nexec /bin/bash \"$@\"\n")
        failure=root/"copy-failed"
        (binpath/"cp").write_text(f'''#!/bin/sh
case "$2" in
  */parity-session.new.*) if [ "${{PARITY_TEST_INTERRUPT:-0}}" = 1 ] && [ ! -e "{failure}" ]; then touch "{failure}"; exit 1; fi ;;
esac
exec /bin/cp "$@"
''')
        for path in binpath.iterdir():path.chmod(0o755)
        entries=[]
        for folder in (pkg/"payload",pkg/"runtime"):
            for path in folder.iterdir():entries.append(f"{sha(path.read_bytes())} {path.relative_to(pkg)}\n")
        (pkg/"PAYLOAD.sha256").write_text("".join(entries))
        env=dict(os.environ,PATH=str(binpath)+":"+os.environ["PATH"])
        def run(name,arg=None):
            return subprocess.run(["bash",str(pkg/name)]+([arg] if arg else []),env=env,capture_output=True,text=True,timeout=8)
        cp=run("install.sh","--check");assert cp.returncode==0,cp.stdout+cp.stderr
        (app/"eso/lib/libmibr_isotx2_gate.so").write_bytes(b"unknown gate")
        assert run("install.sh","--check").returncode!=0,"unidentified gate accepted"
        (app/"eso/lib/libmibr_isotx2_gate.so").write_bytes(gate)
        if scenario=="interrupted":env["PARITY_TEST_INTERRUPT"]="1"
        cp=run("install.sh","--apply")
        if scenario=="normal":
            assert cp.returncode==0,cp.stdout+cp.stderr
            assert b"libmibr_isotx2_guard.so:" in (system/"etc/boot/startup.sh").read_bytes()
            assert (backup/"temp/mibr-carplay111-fps").read_bytes()==fixtures[state/"mibr-carplay111-fps"]
            (state/"mibr-carplay111-fps").write_text("40\n")
            (state/"mibr-carplay111-ownership.conf").write_text("backend=writev_gate\n")
            cp=run("install.sh","--apply");assert cp.returncode==0 and "ALREADY_INSTALLED" in cp.stdout,cp.stdout+cp.stderr
            saved=(backup/"bin/libaltscreen111.so").read_bytes()
            (backup/"bin/libaltscreen111.so").write_bytes(b"corrupt backup")
            cp=run("uninstall.sh");assert cp.returncode!=0 and "backup_corrupt" in cp.stdout,cp.stdout
            assert (dst/"bin/libaltscreen111.so").read_bytes()==b"new GEN2"
            (backup/"bin/libaltscreen111.so").write_bytes(saved)
            cp=run("uninstall.sh");assert cp.returncode==0,cp.stdout+cp.stderr
        else:
            assert cp.returncode!=0 and "ROLLBACK_AFTER_FAILED_APPLY" in cp.stdout,cp.stdout+cp.stderr
        for path,data in fixtures.items():assert path.read_bytes()==data,(scenario,path)
        assert not (dst/"bin/direct-ts-parity").exists()
        assert not (dst/"bin/parity-session").exists()
        assert not (dst/"bin/alt111-settings").exists()
        assert not (app/"eso/lib/libmibr_isotx2_guard.so").exists()
        assert not (state/"mibr-carplay111-ownership.conf").exists()
        assert (state/"mibr-parity-rollback.pending").exists()
        assert (backup/"RESTORE_VERIFIED").exists()
        assert (backup/"bin/libaltscreen111.so").read_bytes()==old_gen
print("PARITY_OVERLAY_ROLLBACK=PASS base_gate standalone_guard boot_preload shared_helper idempotency corrupt_backup interrupted_apply exact_restore temp_ABSENT reader_barrier retained_evidence")
