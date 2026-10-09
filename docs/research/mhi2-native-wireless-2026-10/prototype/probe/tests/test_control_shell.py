#!/usr/bin/env python3
"""Fault-inject actual shell entry points in a disposable, isolated namespace.

Only fixed unit path prefixes are rewritten. Every native process/mount/signal
command is a mock. No unit firmware, credentials, host mounts or signals.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

PROBE = Path(__file__).resolve().parents[1]
HASHES = {
    "btstack": "d2b55046b8f22302c27811ab2070dc87f0408702c8764b43ad2ff135a66444a0",
    "bluetooth": "d3efa55f8bd089c027c89e84fda3e8f5136afd22f7e11862acd4f305d3dd5995",
    "connectivity_launcher": "13586753493d9cb4709196c672f81cbbf81ebfe44ae655a330d98324e04d8bb8",
    "mm-ipod": "de99a7f4dd941589c6d5173b7601856275c4ea615229058ec84b8e3efa748d27",
}


def mock(cmd, args):
    root = Path(os.environ["WCP_TEST_ROOT"])
    state = json.loads((root / "mock.json").read_text())
    with (root / "calls.jsonl").open("a") as f:
        f.write(json.dumps([cmd, *args]) + "\n")
    if cmd == "ps":
        if state.get("ps_fail"):
            return 7
        print(state.get("ps", "UID PID PPID C STIME TTY TIME CMD\nroot 1 0 0 00:00 ? 00:00 init"))
    elif cmd == "sha256sum":
        data = Path(args[0]).read_bytes()
        digest = HASHES.get(data.decode(errors="replace")) or hashlib.sha256(data).hexdigest()
        print(digest, args[0])
    elif cmd == "mount":
        if args:
            return 99  # Test never permits an unplanned mount.
        if state.get("mount_fail"):
            return 8
        print(state["mounts"])
    elif cmd == "umount":
        if state.get("umount_fail"):
            return 9
        state["mounts"] = "\n".join(x for x in state["mounts"].splitlines()
                                     if x.split()[2] != args[0])
        if args[0] == str(root / "eso/bin/apps"):
            (root / "eso/bin/apps/btstack").write_text("btstack")
    elif cmd == "slay":
        if state.get("signal_exits", True):
            state["ps"] = "\n".join(x for x in state["ps"].splitlines()
                                     if len(x.split()) < 2 or x.split()[1] != args[-1])
            for p in state.get("remove_on_signal", []):
                Path(p).unlink(missing_ok=True)
        (root / "mock.json").write_text(json.dumps(state))
        return state.get("slay_status", 1)  # QNX count: one signal != Unix success.
    elif cmd == "sleep":
        pass  # Polls remain finite even when readiness flaps forever.
    elif cmd in ("devb-ram", "pidin"):
        return 99
    else:
        raise AssertionError(cmd)
    (root / "mock.json").write_text(json.dumps(state))
    return 0


class Fixture:
    def __init__(self, parent):
        self.root = Path(tempfile.mkdtemp(prefix="control-shell-", dir=parent)).resolve()
        self.pkg = self.root / "pkg"
        for sub in ("btstack-preload", "runtime-launcher"):
            (self.pkg / sub).mkdir(parents=True)
            for src in (PROBE / sub).glob("*.sh"):
                text = src.read_text()
                for prefix in ("/tmp/mhi2-wcp", "/ramdisk", "/dev/", "/eso/", "/mnt/app/"):
                    text = re.sub(r"(?<!\\)" + re.escape(prefix),
                                  lambda match: self.path(prefix), text)
                # The two process-argument regexes use escaped slash literals.
                for prefix in (r"\/tmp\/mhi2-wcp-", r"\/ramdisk\/mhi2-wcp-stock"):
                    plain = prefix.replace(r"\/", "/")
                    text = text.replace(prefix, self.path(plain).replace("/", r"\/"))
                (self.pkg / sub / src.name).write_text(text)
        for p in ("/tmp", "/ramdisk", "/dev", "/eso/bin/apps", "/mnt/app/eso/bin/apps",
                  "/mnt/app/armle/usr/sbin"):
            Path(self.path(p)).mkdir(parents=True, exist_ok=True)
        for p, marker in (("/eso/bin/apps/btstack", "btstack"),
                          ("/mnt/app/eso/bin/apps/btstack", "btstack"),
                          ("/eso/bin/apps/bluetooth", "bluetooth"),
                          ("/eso/bin/apps/connectivity_launcher", "connectivity_launcher"),
                          ("/mnt/app/armle/usr/sbin/mm-ipod", "mm-ipod")):
            Path(self.path(p)).write_text(marker)
        self.state = {"ps": self.ps(), "mounts": "/dev/base on / type qnx6 (ro)"}
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for cmd in ("ps", "sha256sum", "mount", "umount", "slay", "sleep", "devb-ram", "pidin"):
            p = self.bin / cmd
            p.write_text(f'#!/bin/sh\nexec python3 "{Path(__file__).resolve()}" --mock {cmd} "$@"\n')
            p.chmod(0o755)

    def path(self, p):
        return str(self.root) + p

    def ps(self, extras=()):
        rows = [(100, 1, self.path("/eso/bin/apps/connectivity_launcher")),
                (200, 100, self.path("/eso/bin/apps/btstack")), *extras]
        return "UID PID PPID C STIME TTY TIME CMD\n" + "\n".join(
            f"root {pid} {ppid} 0 00:00 ? 00:00 {argv}" for pid, ppid, argv in rows)

    def put(self, p, text=""):
        q = Path(self.path(p))
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(text)
        return q

    def run(self, script, *args, extra=""):
        (self.root / "mock.json").write_text(json.dumps(self.state))
        env = dict(os.environ, WCP_TEST_ROOT=str(self.root), PATH=str(self.bin) + os.pathsep + os.environ["PATH"])
        env.pop("WCP_LOCK_OWNER", None)
        target = self.pkg / script
        if extra:
            target = self.root / "extracted.sh"
            target.write_text(extra)
        result = subprocess.run(["sh", str(target), *args], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        self.state = json.loads((self.root / "mock.json").read_text())
        return result

    def calls(self, cmd):
        p = self.root / "calls.jsonl"
        return [x for x in (json.loads(t) for t in p.read_text().splitlines()) if x[0] == cmd] if p.exists() else []

    def prepare_down(self):
        self.put("/ramdisk/mhi2-wcp-stock/btstack", "btstack")
        self.put("/tmp/mhi2-wcp-btstage/empty", "").unlink()
        self.put("/dev/wcpbtram0t77")
        wrapper = (self.pkg / "btstack-preload/mhi2_wcp_btstack_wrapper.sh").read_bytes()
        self.put("/eso/bin/apps/btstack").write_bytes(wrapper)
        self.put("/tmp/mhi2-wcp-btstack-overlay.state",
                 f"version=2\nphase=prepared\ntarget={self.path('/eso/bin/apps')}\n"
                 f"device={self.path('/dev/wcpbtram0t77')}\ndevb_pid=300\n"
                 f"stock_copy={self.path('/ramdisk/mhi2-wcp-stock/btstack')}\n"
                 f"wrapper_sha256={hashlib.sha256(wrapper).hexdigest()}\n")
        self.put("/tmp/mhi2-wcp-btstack-control.state",
                 "phase=prepared\nactivation=0\nrestoration=0\nhook_pid=0\nlauncher_pid=100\nbase_pid=200\n")
        self.state["ps"] = self.ps([(300, 1, "/sbin/devb-ram name=wcpbtram")])
        self.state["mounts"] += f"\n{self.path('/dev/wcpbtram0t77')} on {self.path('/eso/bin/apps')} type qnx4 (rw)"
        self.state["remove_on_signal"] = [self.path("/dev/wcpbtram0t77")]


def extracted(text, name):
    start = text.index(name + "()\n")
    end = text.index("\n}\n", start) + 3
    return text[start:end]


def main():
    parent = PROBE / "build"
    parent.mkdir(exist_ok=True)
    made = []
    def fixture():
        f = Fixture(parent)
        made.append(f)
        return f
    try:
        for fault in ("umount_fail", "ps_fail", "mount_fail", "foreign_mount", "duplicate_devb", "foreign_ipod"):
            f = fixture()
            f.prepare_down()
            if fault == "foreign_mount":
                f.state["mounts"] = f"/dev/foreign on {f.path('/eso/bin/apps')} type qnx4 (rw)"
            elif fault == "duplicate_devb":
                f.state["ps"] += "\nroot 301 1 0 00:00 ? 00:00 /sbin/devb-ram name=wcpbtram"
            elif fault == "foreign_ipod":
                f.state["ps"] += "\nroot 401 1 0 00:00 ? 00:00 /usr/sbin/mm-ipod -d stock"
            else:
                f.state[fault] = True
            r = f.run("btstack-preload/mhi2_wcp_btstack_overlay_down.sh", "--usb-lan-confirmed")
            assert r.returncode == 2, (fault, r.stdout)
            assert not f.calls("slay"), (fault, r.stdout)
            assert Path(f.path("/tmp/mhi2-wcp-btstack-overlay.state")).exists()
            assert Path(f.path("/dev/wcpbtram0t77")).exists()
        for status in (0, 1, 2):
            f = fixture()
            f.prepare_down()
            f.state["slay_status"] = status
            r = f.run("btstack-preload/mhi2_wcp_btstack_overlay_down.sh", "--usb-lan-confirmed")
            assert r.returncode == 0, r.stdout
            assert len(f.calls("slay")) == 1
            assert len(f.calls("umount")) == 1
            assert Path(f.path("/ramdisk/mhi2-wcp-stock/btstack")).exists()
            assert not Path(f.path("/tmp/mhi2-wcp-btstack-overlay.state")).exists()
            assert "phase=restored" in Path(f.path("/tmp/mhi2-wcp-btstack-control.state")).read_text()
        for foreign in (False, True):
            f = fixture()
            cfg = f.path("/tmp/mhi2-wcp-iap2.700.cfg")
            f.put("/tmp/mhi2-wcp-iap2.700.cfg", "TEST_ONLY_CONFIG")
            f.put("/tmp/mhi2-wcp-mm-ipod.state", f"phase=process-wait\nconfig={cfg}\npid=0\n")
            argv = f.path("/mnt/app/armle/usr/sbin/mm-ipod") + f" -d iap2,config={cfg} -m {f.path('/dev/ipod0')}"
            if foreign:
                argv = "/usr/sbin/mm-ipod -d stock"
            f.state["ps"] = f.ps([(400, 1, argv)])
            r = f.run("runtime-launcher/mhi2_wcp_mm_ipod_stop.sh", "--usb-lan-confirmed")
            assert r.returncode == (2 if foreign else 0), r.stdout
            assert len(f.calls("slay")) == (0 if foreign else 1)
            assert Path(cfg).exists() == foreign
        f = fixture()
        cfg = f.path("/tmp/mhi2-wcp-iap2.701.cfg")
        f.put("/tmp/mhi2-wcp-iap2.701.cfg", "TEST_ONLY_CONFIG")
        f.put("/tmp/mhi2-wcp-mm-ipod.state", f"phase=running\nconfig={cfg}\npid=400\n")
        f.put("/dev/ipod0")  # Process absent, namespace remains: no cleanup.
        r = f.run("runtime-launcher/mhi2_wcp_mm_ipod_stop.sh", "--usb-lan-confirmed")
        assert r.returncode == 2 and Path(cfg).exists() and not f.calls("slay"), r.stdout
        f = fixture()
        f.prepare_down()
        f.state["signal_exits"] = False
        r = f.run("btstack-preload/mhi2_wcp_btstack_overlay_down.sh", "--usb-lan-confirmed")
        assert r.returncode == 2 and "backing-exit-not-proven" in r.stdout, r.stdout
        assert len(f.calls("slay")) == 1
        assert Path(f.path("/tmp/mhi2-wcp-btstack-overlay.state")).exists()
        # Actual wait function, permanently absent readiness: finite even when
        # a matching new child exists. No SECONDS/builtin assumption.
        f = fixture()
        source = (f.pkg / "btstack-preload/mhi2_wcp_btstack_cycle.sh").read_text()
        common = f.pkg / "btstack-preload/mhi2_wcp_control_common.sh"
        f.state["ps"] = f.ps([(210, 100, f.path("/ramdisk/mhi2-wcp-stock/btstack"))])
        runtime = f.put("/tmp/mhi2-wcp-btstack-runtime.state",
                        f"mode=hooked\npid=210\nreal_sha256={HASHES['btstack']}\n")
        body = f'''#!/bin/sh
set -u
. "{common}"
WCP_PS="{f.root}/ps"; WCP_MOUNTS="{f.root}/mounts"
WCP_CONTROL="{f.root}/control"
WCP_LAUNCHER_PID=100; WCP_BASE_PID=200; WCP_HOOK_PID=0
WCP_ACTIVATION=1; WCP_RESTORATION=0
STOCK_COPY="{f.path('/ramdisk/mhi2-wcp-stock/btstack')}"
ENDPOINT="{f.path('/dev/mhi2-iap2-rfcomm')}"
RUNTIME_STATE="{runtime}"
EXPECTED_BTSTACK={HASHES['btstack']}; TIMEOUT=4
fail() {{ echo "$*"; exit 2; }}
{extracted(source, 'read_runtime')}
{extracted(source, 'check_launcher')}
{extracted(source, 'wait_for_ram_mode')}
if wait_for_ram_mode hooked 200; then exit 99; fi
'''
        r = f.run("", extra=body)
        assert r.returncode == 0 and len(f.calls("sleep")) == 4, r.stdout
        # Actual partial-cleanup body cannot detach, kill or erase evidence.
        source = (f.pkg / "btstack-preload/mhi2_wcp_btstack_overlay_up.sh").read_text()
        body = f'''#!/bin/sh
. "{common}"
MODE_STATE="{f.root}/mode"; STATE="{f.root}/intent"; PHASE=stage-detach-intent
echo retained > "$STATE"
{extracted(source, 'cleanup_partial')}
cleanup_partial
[ -r "$STATE" ] && [ "$(cat "$MODE_STATE")" = stock ]
'''
        r = f.run("", extra=body)
        assert r.returncode == 0 and not f.calls("slay") and not f.calls("umount"), r.stdout
        f = fixture()
        f.prepare_down()
        f.state["remove_on_signal"] = []
        r = f.run("btstack-preload/mhi2_wcp_btstack_cycle.sh", "--usb-lan-confirmed", "--activate", "--timeout", "2")
        assert r.returncode == 2 and len(f.calls("slay")) == 1, r.stdout
        journal = Path(f.path("/tmp/mhi2-wcp-btstack-control.state")).read_text()
        assert "activation=1" in journal and "restoration=0" in journal
        assert Path(f.path("/tmp/mhi2-wcp-btstack-preload.mode")).read_text().strip() == "stock"
        r = f.run("btstack-preload/mhi2_wcp_btstack_cycle.sh", "--usb-lan-confirmed", "--activate", "--timeout", "2")
        assert r.returncode == 2 and "activation-budget" in r.stdout and len(f.calls("slay")) == 1, r.stdout
        # Actual wrapper mode/preload-selection block. Never executes the
        # stock path or loads a library; shell builtins inspect then unset env.
        f = fixture()
        text = (f.pkg / "btstack-preload/mhi2_wcp_btstack_wrapper.sh").read_text()
        selection = text[text.index("MODE=stock\n"):text.index('tmp_state="$RUNTIME_STATE.$$"')]
        mode = f.put("/tmp/mhi2-wcp-btstack-preload.mode", "hooked\n")
        hook = f.put("/tmp/mhi2-wcp-test-placeholder.so", "TEST_NOT_A_LIBRARY")
        path_file = f.put("/tmp/mhi2-wcp-btstack-hook.path", str(hook) + "\n")
        body = f'''#!/bin/sh
set -u
umask 077
MODE_STATE="{mode}"; HOOK_FILE="{path_file}"
{selection}
[ "$MODE" = hooked ] && [ "$MHI2_IAP_RFCOMM_LAB" = 1 ] || exit 80
unset LD_PRELOAD MHI2_IAP_SERVICEGRAPH_LAB MHI2_IAP_RFCOMM_LAB MHI2_IAP_FORCE_CONNECTABLE_LAB
printf 'hooked\\n' > "$MODE_STATE"
{selection}
[ "$MODE" = stock ] && [ -z "${{MHI2_IAP_RFCOMM_LAB:-}}" ] && [ -z "${{LD_PRELOAD:-}}" ]
'''
        r = f.run("", extra=body)
        assert r.returncode == 0, r.stdout
        assert mode.read_text().strip() == "stock"
        print("control shell regressions: PASS (17 fault/ownership/count/readiness/budget/one-shot scenarios)")
    finally:
        for f in made:
            # Every deletion is restricted to the newly created test namespace.
            assert f.root.parent == parent.resolve() and f.root.name.startswith("control-shell-")
            shutil.rmtree(f.root)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        sys.exit(mock(sys.argv[2], sys.argv[3:]))
    main()
