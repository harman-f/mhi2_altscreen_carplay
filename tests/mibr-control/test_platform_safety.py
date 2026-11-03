"""Watchdog, boot guard, shared /mnt/app write window and unit tool limits; host-only, real scripts."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
from public_paths import ROOT, RUNTIME
IMPL = ROOT
CONTROL = ROOT
WATCH = RUNTIME / "mibr-watch.ksh"
BOOT = RUNTIME / "mibr-v3-boot.ksh"
VIEW = RUNTIME / "mibr-view.ksh"
KIT = IMPL / "distribution/mibr-carplay-kit/kit"
GUARD = KIT / "files/boot-guard.ksh"
R2 = IMPL / "carplay-rgi/release/r2"
SHELL = os.environ.get("DELTA_SHELL", shutil.which("bash") or "/bin/sh")
FAKE_MOUNT = '#!/bin/sh\necho "$*" >> "$MOUNT_LOG"\n[ "${MOUNT_FAIL:-0}" != 1 ]\n'
# Unit limits from distribution/mibr-carplay-kit/BUILD.md: these do not exist on the MU1440.
MISSING_ON_UNIT = ("tr", "od", "printf", "rmdir", "diff", "cmp", "xargs", "md5", "cksum", "hexdump", "tar", "pax")


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mibr-platform-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.script(self.tools / "mount", FAKE_MOUNT)
        self.script(self.tools / "sync", "#!/bin/sh\nexit 0\n")
        self.env = dict(os.environ, PATH=str(self.tools) + os.pathsep + os.environ["PATH"],
                        MOUNT_LOG=str(self.root / "mount.log"))

    @staticmethod
    def script(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o755)

    def mounts(self):
        log = self.root / "mount.log"
        return log.read_text().splitlines() if log.exists() else []


@unittest.skipUnless(GUARD.is_file(), "research-only packaged boot guard is omitted from the public source tree")
class BootGuard(Sandbox):
    def setUp(self):
        super().setUp()
        self.app = self.root / "app"
        (self.app / "root/mibr-kit").mkdir(parents=True)
        self.env.update(MIBR_GUARD_APP=str(self.app), MIBR_APP_RW_LOCK=str(self.root / "lease"))
        self.disabled = self.app / "root/mibr-kit/disabled"
        self.count = self.app / "root/mibr-kit/boot-count"

    def run_guard(self, verb):
        return subprocess.run([SHELL, str(GUARD), verb], env=self.env, capture_output=True, text=True)

    def test_loads_until_limit_then_disables_itself(self):
        for expected in ("1", "2", "3", "4"):
            self.assertEqual(self.run_guard("check").returncode, 0)
            self.assertEqual(self.count.read_text().strip(), expected)
        result = self.run_guard("check")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("AUTO_DISABLED", result.stdout)
        self.assertTrue(self.disabled.exists())
        self.assertEqual(self.run_guard("check").returncode, 1)
        # Deleting the switch gives four fresh boots.
        self.disabled.unlink()
        self.assertEqual(self.run_guard("check").returncode, 0)
        self.assertEqual(self.count.read_text().strip(), "1")

    def test_clear_resets_and_returns_to_read_only(self):
        self.run_guard("check")
        self.assertEqual(self.run_guard("clear").returncode, 0)
        self.assertEqual(self.count.read_text().strip(), "0")
        self.assertTrue(self.mounts()[-1].startswith("-ur"))
        self.assertFalse((self.root / "lease").exists())
        before = len(self.mounts())
        self.assertEqual(self.run_guard("clear").returncode, 0)
        self.assertEqual(len(self.mounts()), before, "nothing to clear must not remount")

    def test_guard_failure_never_blocks_mibr(self):
        self.env["MOUNT_FAIL"] = "1"
        for _ in range(6):
            self.assertEqual(self.run_guard("check").returncode, 0)
        self.assertFalse(self.disabled.exists())
        self.count.parent.mkdir(exist_ok=True)
        self.count.write_text("garbage\n")
        self.assertEqual(self.run_guard("check").returncode, 0)

    def test_lsd_block_gates_everything(self):
        lines = (KIT / "config/lsd-block.txt").read_text().splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith("if "))
        end = lines.index("fi")
        guarded = "\n".join(lines[start:end])
        for needed in ("MIBR-CarPlay.jar", "MIBR-NavIgnore.jar", "VMOPTIONS", "boot.ksh"):
            self.assertIn(needed, guarded)
        self.assertEqual("\n".join(lines).count("MIBR-CarPlay.jar"), 1)

    def test_block_runs_without_mibr_when_disabled(self):
        block = (KIT / "config/lsd-block.txt").read_text().replace("/mnt/app/root/mibr-kit", str(self.app / "root/mibr-kit"))
        shutil.copy(GUARD, self.app / "root/mibr-kit/boot-guard.ksh")
        self.script(self.app / "root/mibr-kit/boot.ksh", "#!/bin/sh\nexit 0\n")
        probe = 'BOOTCLASSPATH=base; VMOPTIONS=; BASE_DIR=x\n' + block.replace("/bin/ksh ", SHELL + " ") + '\necho "CP=$BOOTCLASSPATH"\n'
        run = lambda: subprocess.run([SHELL, "-c", probe], env=self.env, capture_output=True, text=True).stdout
        self.assertIn("MIBR-CarPlay.jar", run())
        self.disabled.write_text("x\n")
        self.assertIn("CP=base\n", run())


class Watchdog(Sandbox):
    def setUp(self):
        super().setUp()
        self.app = self.root / "app"
        self.tmp = self.root / "tmp"
        self.tmp.mkdir()
        self.script(self.app / "root/mibr-v3/bin/mibr-v3-service", "#!/bin/sh\nexit 0\n")
        self.script(self.app / "root/mibr-v3/bin/mibr-key40d", "#!/bin/sh\nexit 0\n")
        self.env.update(MIBR_WATCH_APP=str(self.app), MIBR_WATCH_TMP=str(self.tmp), MIBR_WATCH_SHELL=SHELL,
                        MIBR_WATCH_TICK="1", MIBR_WATCH_INITIAL="0", MIBR_WATCH_MAX="2", MIBR_WATCH_HMI_STABLE="1",
                        RESTARTS=str(self.root / "restarts"), SUP_RUNS=str(self.root / "sup"))
        # The fake boot script records the call and does not bring the broker back.
        self.script(self.app / "root/mibr-v3/mibr-v3-boot.ksh", '#!/bin/sh\necho "$1" >> "$RESTARTS"\n')
        self.script(self.app / "root/altscreen-u2/scripts/parity_drive_supervisor.sh", '#!/bin/sh\necho run >> "$SUP_RUNS"\n')
        self.sleeper = subprocess.Popen(["sleep", "120"])
        self.addCleanup(self.sleeper.kill)
        (self.tmp / "mibr-key40d.pid").write_text(f"{self.sleeper.pid}\n")
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen([SHELL, str(WATCH)], env=self.env, stdout=subprocess.DEVNULL)
        self.addCleanup(self.stop)

    def stop(self):
        (self.tmp / "mibr-watch.stop").touch()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def wait_state(self, wanted, seconds=12):
        state = self.tmp / "mibr-watch.state"
        end = time.time() + seconds
        text = ""
        while time.time() < end:
            text = state.read_text() if state.exists() else ""
            if wanted in text:
                return text
            time.sleep(0.2)
        self.fail(f"state never showed {wanted}: {text!r}")

    def test_dead_broker_restart_is_bounded_and_reported(self):
        self.start()
        self.wait_state("broker=gaveup:2")
        self.assertEqual((self.root / "restarts").read_text().split(), ["--from-watch", "--from-watch"])
        self.assertIn("key40d=ok", self.wait_state("key40d=ok"))

    def test_live_services_are_left_alone(self):
        (self.tmp / "mibr-v3-service.pid").write_text(f"{self.sleeper.pid}\n")
        self.start()
        self.wait_state("broker=ok")
        self.assertFalse((self.root / "restarts").exists())

    def test_supervisor_only_when_enabled_and_profile_ready(self):
        (self.tmp / "mibr-v3-service.pid").write_text(f"{self.sleeper.pid}\n")
        self.start()
        self.wait_state("supervisor=off")
        self.assertFalse((self.root / "sup").exists())
        (self.app / "root/mibr-parity-drive.enabled").write_text("1\n")
        (self.tmp / "mibr-cpvc-profile-ready").touch()
        self.wait_state("supervisor=gaveup:2")
        self.assertEqual(len((self.root / "sup").read_text().split()), 2)

    def test_stop_file_ends_it(self):
        (self.tmp / "mibr-v3-service.pid").write_text(f"{self.sleeper.pid}\n")
        self.start()
        self.wait_state("broker=ok")
        self.stop()
        self.assertEqual(self.proc.returncode, 0)
        self.assertFalse((self.tmp / "mibr-watch.pid").exists())

    def test_clears_boot_guard_after_hmi_up(self):
        (self.tmp / "mibr-v3-service.pid").write_text(f"{self.sleeper.pid}\n")
        self.script(self.app / "root/mibr-kit/boot-guard.ksh", '#!/bin/sh\necho "$1" >> "$RESTARTS"\n')
        (self.tmp / "mibr-hmi-up").touch()
        self.start()
        end = time.time() + 10
        while time.time() < end and not (self.root / "restarts").exists():
            time.sleep(0.2)
        self.assertEqual((self.root / "restarts").read_text().split(), ["clear"])

    def test_boot_script_starts_watch_once_and_not_from_watch(self):
        text = BOOT.read_text()
        self.assertIn('[ "$1" != --from-watch ]', text)
        self.assertLess(text.index("mibr-watch.ksh"), text.index("mibr-v3-genkey"))


class SharedWriteWindow(Sandbox):
    def setUp(self):
        super().setUp()
        self.view_dir = self.root / "view"
        self.lease = self.root / "lease"
        self.env.update(MIBR_VIEW_DIR=str(self.view_dir), MIBR_VIEW_MOUNT=str(self.root), MIBR_VIEW_NOMOUNT="0",
                        MIBR_APP_RW_LOCK=str(self.lease), MIBR_VIEW_LOCK=str(self.root / "view.lock"),
                        MIBR_VIEW_POS=str(self.root / "pos"), MIBR_VIEW_GEN=str(self.root / "gen"),
                        MIBR_VIEW_AREA=str(self.root / "area"), MIBR_VIEW_LOG=str(self.root / "log"),
                        MIBR_VIEW_CLI=str(self.root / "nocli"), MIBR_VIEW_SHELL=SHELL)

    def view_set(self):
        return subprocess.run([SHELL, str(VIEW), "set", "pos", "1"], env=self.env, capture_output=True, text=True)

    def test_write_takes_and_releases_the_lease(self):
        result = self.view_set()
        self.assertIn("result=OK", result.stdout, result.stderr)
        self.assertFalse(self.lease.exists())
        self.assertEqual([m.split()[0] for m in self.mounts()], ["-uw", "-ur"])

    def test_write_waits_for_a_live_holder_and_never_remounts_under_it(self):
        holder = subprocess.Popen(["sleep", "30"])
        self.addCleanup(holder.kill)
        self.lease.write_text(f"{holder.pid}\n")
        result = self.view_set()
        self.assertIn("result=WRITE_FAILED", result.stdout, result.stderr)
        self.assertEqual(self.mounts(), [], "another writer's window must stay untouched")
        self.assertEqual(self.lease.read_text().strip(), str(holder.pid))

    def test_dead_holder_is_taken_over(self):
        gone = subprocess.Popen(["true"])
        gone.wait()
        self.lease.write_text(f"{gone.pid}\n")
        self.assertIn("result=OK", self.view_set().stdout)
        self.assertFalse(self.lease.exists())


class UnitTools(Sandbox):
    def scripts(self):
        names = ["install-skin-icons-r2.ksh", "install-rgi-r2.ksh", "write-components-manifest.ksh",
                 "mibr-r2-delta.deploy", "mibr-watch.ksh", "mibr-v3-boot.ksh", "mibr-view.ksh", "mm-ipod-rgi"]
        return [R2 / n for n in names] + [GUARD]

    @unittest.skipUnless(R2.is_dir() and GUARD.is_file(), "research-only R2 release package is omitted from the public source tree")
    def test_no_command_the_unit_does_not_have(self):
        pattern = re.compile(r"(?:^|[;&|({]\s*|\b(?:then|do|else|if|until|while)\s+|&&\s*|\|\|\s*)("
                             + "|".join(MISSING_ON_UNIT) + r")\s")
        for script in self.scripts():
            for number, line in enumerate(script.read_text().splitlines(), 1):
                code = line.split(" #")[0]
                if code.lstrip().startswith("#"):
                    continue
                self.assertIsNone(pattern.search(code), f"{script.name}:{number}: {line}")

    @unittest.skipUnless(R2.is_dir() and GUARD.is_file(), "research-only R2 release package is omitted from the public source tree")
    def test_wc_output_is_never_compared_as_text(self):
        # QNX wc pads its count with spaces; the first R2 install stopped on exactly this.
        for script in self.scripts():
            self.assertNotIn('"$(wc ', script.read_text(), script.name)

    def test_rgi_helper_does_not_rename_on_shmem(self):
        # rename() fails on /dev/shmem on the unit; the first R2 install never published guidance.
        source = (IMPL / "modules/navigation/source/src/helper/mibr_rgi.c").read_text()
        self.assertNotIn("rename(", source)
        self.assertIn("iap2_connect(IAP2_DEVICE, 0)", source)

    @unittest.skipUnless(R2.is_dir(), "research-only R2 release package is omitted from the public source tree")
    def test_release_copies_match_their_sources(self):
        for release, source in (("mibr-watch.ksh", WATCH), ("mibr-v3-boot.ksh", BOOT), ("mibr-view.ksh", VIEW),
                                ("mm-ipod-rgi", IMPL / "carplay-rgi/kit/mm-ipod-rgi"),
                                ("install-skin-icons-r2.ksh", IMPL / "carplay-rgi/kit/install-skin-icons-r2.ksh"),
                                ("install-rgi-r2.ksh", IMPL / "carplay-rgi/kit/install-rgi-r2.ksh"),
                                ("write-components-manifest.ksh", IMPL / "carplay-rgi/kit/write-components-manifest.ksh")):
            self.assertEqual((R2 / release).read_bytes(), source.read_bytes(), release)

    @unittest.skipUnless(R2.is_dir(), "research-only R2 release package is omitted from the public source tree")
    def test_skin_icon_install_verifies_and_restores_without_cmp_or_rmdir(self):
        root = self.root / "unit"
        icons = root / "mnt/app/eso/hmi/lsd/mibr/icons"
        icons.mkdir(parents=True)
        names = ["mibr_vc_settings_dark_normal_235x154_rgba.png", "mibr_vc_settings_skin1_dark_normal_235x151_rgba.png",
                 "mibr_vc_settings_skin1_light_active_235x151_rgba.png"]
        for name in names:
            (icons / name).write_bytes(name.encode())
        (root / "mnt/app/eso/hmi/lsd/Resources/skin0").mkdir(parents=True)
        for missing in ("cmp", "rmdir"):
            self.script(self.tools / missing, f'#!/bin/sh\necho used-{missing} >> "{self.root}/used"\nexit 127\n')
        # A copy without bin/: the release hash tool is a QNX binary, here sha256sum comes from PATH.
        stage = self.root / "stage"
        stage.mkdir()
        script = stage / "install-skin-icons-r2.ksh"
        shutil.copy(R2 / "install-skin-icons-r2.ksh", script)
        env = dict(self.env, MIBR_ICON_TEST_ROOT=str(root))
        done = subprocess.run([SHELL, str(script), "--install"], env=env, capture_output=True, text=True)
        self.assertIn("INSTALLED files=3", done.stdout, done.stderr)
        images = root / "mnt/app/eso/hmi/lsd/Resources/skin0/Images"
        for name in names:
            self.assertEqual(hashlib.sha256((images / name).read_bytes()).digest(),
                             hashlib.sha256(name.encode()).digest())
        undone = subprocess.run([SHELL, str(script), "--restore"], env=env, capture_output=True, text=True)
        self.assertIn("RESTORED", undone.stdout, undone.stderr)
        self.assertFalse(images.exists())
        self.assertFalse((self.root / "used").exists(), "must not call tools the unit does not have")


if __name__ == "__main__":
    unittest.main()
