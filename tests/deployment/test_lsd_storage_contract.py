"""lsd.sh writers stage in the lsd.sh directory (atomic rename) and gate on lsd_check; ownership/receipt handling. Host-only."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
UNINSTALL = ROOT / "deployment/mu1440/uninstall.sh"
INSTALL = ROOT / "deployment/mu1440/install.sh"
ENABLE = ROOT / "modules/carplay/runtime/auto-direct/direct_ts_auto_enable.sh"
RESTORE = ROOT / "modules/carplay/runtime/auto-direct/restore_stock.sh"
PARITY_ENABLE = ROOT / "modules/carplay/runtime/parity/parity_drive_enable.sh"
LSD_WRITERS = (INSTALL, UNINSTALL, RESTORE, ENABLE, PARITY_ENABLE)
STAGE_DIR = "/mnt/app/eso/hmi/lsd/"
SHELL = os.environ.get("DELTA_SHELL", shutil.which("ksh") or shutil.which("bash") or shutil.which("sh"))

MV = re.compile(r'^\s*(?:if\s+)?mv\s+"\$(\w+)"\s+(?:"\$LSD"|/mnt/app/eso/hmi/lsd/lsd\.sh)(?![\w/.])', re.M)


def violations(text, name="<text>"):
    """Problems with the temp variables that are moved over lsd.sh."""
    found = sorted(set(MV.findall(text)))
    if not found:
        return ["%s: no mv of a temp file onto lsd.sh found" % name]
    problems = []
    for var in found:
        assigns = re.findall(r'^\s*%s=(\S+)\s*$' % re.escape(var), text, re.M)
        if not assigns:
            problems.append("%s: no assignment of %s" % (name, var))
        for value in assigns:
            if not value.startswith(STAGE_DIR):
                problems.append("%s: %s=%s is not staged under %s" % (name, var, value, STAGE_DIR))
            if not value.endswith(".$$"):
                problems.append("%s: %s=%s does not end with .$$" % (name, var, value))
    return problems


class StaticStaging(unittest.TestCase):
    def check(self, path):
        self.assertEqual(violations(path.read_text(), path.name), [])

    def test_uninstall(self):
        self.check(UNINSTALL)

    def test_install(self):
        self.check(INSTALL)
        text = INSTALL.read_text()
        self.assertEqual(len(MV.findall(text)), 3)  # normalize, navignore, most20

    def test_auto_direct_enable(self):
        self.check(ENABLE)

    def test_auto_direct_restore(self):
        self.check(RESTORE)

    def test_parity_drive_enable(self):
        self.check(PARITY_ENABLE)

    def test_no_lsd_stage_in_tmp_or_app_root(self):
        for path in LSD_WRITERS:
            self.assertIsNone(re.search(r'^\s*\w*TMP=/(?:tmp|mnt/app/root)/\S*lsd\.sh', path.read_text(), re.M), path.name)

    def test_checker_flags_bad_stage(self):
        bad = 'TMP=/tmp/lsd.sh.x.$$\nmv "$TMP" "$LSD"\n'
        self.assertTrue(any("not staged under" in v for v in violations(bad)))
        app_root = 'TMP=/mnt/app/root/lsd.sh.x.$$\nmv "$TMP" "$LSD"\n'
        self.assertTrue(any("not staged under" in v for v in violations(app_root)))
        literal_dollar = 'TMP=/mnt/app/eso/hmi/lsd/lsd.sh.x.$\nmv "$TMP" "$LSD"\n'
        self.assertTrue(any("does not end with" in v for v in violations(literal_dollar)))
        good = 'TMP=/mnt/app/eso/hmi/lsd/lsd.sh.x.$$\nmv "$TMP" "$LSD"\n'
        self.assertEqual(violations(good), [])


LSD_FUNCS = re.compile(r'^lsd_check\(\)\{\n.*?^\}\nj9_count\(\)\{\n.*?^\}\n', re.M | re.S)


def lsd_funcs(path=UNINSTALL):
    m = LSD_FUNCS.search(path.read_text())
    return m.group(0) if m else None


class LsdCheckIdentical(unittest.TestCase):
    def test_function_text_identical_in_all_writers(self):
        ref = lsd_funcs(INSTALL)
        self.assertIsNotNone(ref)
        for path in LSD_WRITERS:
            self.assertEqual(lsd_funcs(path), ref, path.name)

    def test_every_writer_gates_before_mv(self):
        for path in LSD_WRITERS:
            self.assertIn('lsd_check "', path.read_text().split("j9_count(){", 1)[1], path.name)


@unittest.skipUnless(SHELL, "no POSIX shell on host")
class LsdCheckExec(unittest.TestCase):
    B = "# MIBR X BEGIN"
    E = "# MIBR X END"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="mibr-chk-")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def check(self, body, want, orig=1, b=None, e=None):
        f = self.dir / "lsd.sh"
        f.write_text(body)
        script = lsd_funcs() + 'lsd_check "$1" "$2" "$3" "$4" "$5"; echo rc=$?\n'
        r = subprocess.run([SHELL, "-c", script, "sh", str(f), b if b is not None else self.B,
                            e if e is not None else self.E, want, str(orig)],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() == "rc=0"

    J9 = "$J9 -jar start.jar\n"

    def test_j9_count_function(self):
        f = self.dir / "a"
        f.write_text("x\n" + self.J9 + self.J9 + "  $J9 indented\n")
        r = subprocess.run([SHELL, "-c", lsd_funcs() + 'j9_count "$1"', "sh", str(f)], capture_output=True, text=True, timeout=10)
        self.assertEqual(r.stdout.strip(), "2")
        f.write_text("nothing\n")
        r = subprocess.run([SHELL, "-c", lsd_funcs() + 'j9_count "$1"', "sh", str(f)], capture_output=True, text=True, timeout=10)
        self.assertEqual(r.stdout.strip(), "0")

    def test_j9_count_changed_fails(self):
        self.assertTrue(self.check("a\n" + self.J9, "-", orig=1))
        self.assertFalse(self.check("a\n" + self.J9, "-", orig=2))
        self.assertFalse(self.check("a\n" + self.J9 + self.J9, "-", orig=1))

    def test_no_j9_fails(self):
        self.assertFalse(self.check("a\nb\n", "-", orig=0))
        self.assertFalse(self.check("a\nb\n", "1", orig=0))

    def test_want_one_ordered_pair_passes(self):
        self.assertTrue(self.check("a\n%s\nhook\n%s\n%s" % (self.B, self.E, self.J9), "1"))

    def test_want_one_bad_shapes_fail(self):
        j = self.J9
        self.assertFalse(self.check("%s\n%s\n%s" % (self.E, self.B, j), "1"))  # END before BEGIN
        self.assertFalse(self.check("%s\n%s\n%s\n%s\n%s" % (self.B, self.E, self.B, self.E, j), "1"))  # two pairs
        self.assertFalse(self.check("%s\nhook\n%s" % (self.B, j), "1"))  # BEGIN without END
        self.assertFalse(self.check("hook\n%s" % j, "1"))  # no pair at all
        self.assertFalse(self.check("%s\n%s\n%s\n%s" % (self.B, self.B, self.E, j), "1"))  # nested BEGIN

    def test_want_zero(self):
        self.assertTrue(self.check(self.J9, "0"))
        self.assertFalse(self.check("%s\n%s" % (self.B, self.J9), "0"))
        self.assertFalse(self.check("%s\n%s" % (self.E, self.J9), "0"))
        self.assertFalse(self.check("%s\nx\n%s\n%s" % (self.B, self.E, self.J9), "0"))

    def test_want_dash_ignores_markers(self):
        self.assertTrue(self.check("%s\n%s\n%s" % (self.E, self.B, self.J9), "-"))
        self.assertTrue(self.check("%s\n%s" % (self.B, self.J9), "-"))
        self.assertTrue(self.check(self.J9, "-", b="", e=""))


def d2_block():
    """From D2_MARKER= through the end of the second (ownership/receipt) block."""
    lines = UNINSTALL.read_text().splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("D2_MARKER=")), None)
    stop = next((i for i, l in enumerate(lines) if l.startswith('if [ "$FAIL" -ne 0 ]')), None)
    if start is None or stop is None or lines[stop - 1] != "" or lines[stop - 2] != "fi":
        return None
    return "\n".join(lines[start:stop - 1])


RO_MSG = "ERROR /mnt/app did not return to read-only"
FAKE_MOUNT = ('#!/bin/sh\necho "$*" >> "$MOUNT_LOG"\n[ "${MOUNT_FAIL:-0}" != 1 ] || exit 1\n'
              '[ "${MOUNT_FAIL_UR:-0}" != 1 ] || [ "$1" != -ur ] || exit 1\n')


@unittest.skipUnless(SHELL, "no POSIX shell on host")
class D2MarkerRemoval(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="mibr-d2-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.log = self.root / "mount.log"
        self.put("mount", FAKE_MOUNT)
        self.put("sync", "#!/bin/sh\nexit 0\n")
        self.marker = self.root / "mnt/app/root/mibr-alt111-keyframe-policy.enabled"
        self.marker.parent.mkdir(parents=True)
        self.dst = self.root / "dst"
        self.owned = self.dst / "version/ownership/d2-marker.owned"
        self.receipt = self.dst / "version/install-defaults.receipt"
        self.owned.parent.mkdir(parents=True)

    def put(self, name, text):
        p = self.tools / name
        p.write_text(text)
        p.chmod(0o755)

    def run_block(self, fail_mount=False, refuse_rm=False, fail_ur=False):
        block = d2_block()
        self.assertIsNotNone(block, "D2 blocks not found in uninstall.sh")
        script = "FAIL=0\nDST=%s\n" % self.dst + block.replace("/mnt/app", str(self.root / "mnt/app")) + "\necho FAIL=$FAIL\n"
        if refuse_rm:
            self.put("rm", "#!/bin/sh\nexit 1\n")
        env = dict(os.environ, PATH=str(self.tools) + os.pathsep + os.environ["PATH"], MOUNT_LOG=str(self.log))
        if fail_mount:
            env["MOUNT_FAIL"] = "1"
        if fail_ur:
            env["MOUNT_FAIL_UR"] = "1"
        r = subprocess.run([SHELL, "-c", script], env=env, capture_output=True, text=True, timeout=10)
        r.stdout = r.stdout.replace(str(self.root / "mnt/app"), "/mnt/app")
        return r

    def mounts(self):
        return [l.replace(str(self.root / "mnt/app"), "/mnt/app") for l in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_block_extracted(self):
        block = d2_block()
        self.assertIsNotNone(block)
        self.assertTrue(block.startswith("D2_MARKER=") and block.endswith("\nfi"))
        self.assertIn("mount -uw /mnt/app", block)
        self.assertIn("mount -ur /mnt/app", block)
        self.assertIn("ERROR persistent D2 marker survived uninstall", block)
        self.assertIn("ERROR install-defaults receipt survived uninstall", block)

    def test_owned_marker_and_receipt_removed(self):
        self.marker.write_text("1\n")
        self.owned.write_text("")
        self.receipt.write_text("MIBR_INSTALL_DEFAULTS/1\n")
        r = self.run_block()
        self.assertFalse(self.marker.exists(), r.stdout + r.stderr)
        self.assertFalse(self.owned.exists())
        self.assertFalse(self.receipt.exists())
        self.assertIn("FAIL=0", r.stdout)
        self.assertNotIn("ERROR", r.stdout)
        self.assertIn("Persistent D2 marker removed", r.stdout)
        self.assertEqual(self.mounts(), ["-uw /mnt/app", "-ur /mnt/app"] * 2)

    def test_not_owned_marker_kept(self):
        self.marker.write_text("1\n")
        r = self.run_block()
        self.assertTrue(self.marker.exists())
        self.assertIn("Persistent D2 marker not created by the installer; left in place", r.stdout)
        self.assertIn("FAIL=0", r.stdout)
        self.assertNotIn("ERROR", r.stdout)
        self.assertEqual(self.mounts(), [])

    def test_receipt_removed_without_marker(self):
        self.receipt.write_text("MIBR_INSTALL_DEFAULTS/1\n")
        r = self.run_block()
        self.assertFalse(self.receipt.exists(), r.stdout + r.stderr)
        self.assertIn("FAIL=0", r.stdout)
        self.assertEqual(self.mounts(), ["-uw /mnt/app", "-ur /mnt/app"])

    def test_not_owned_marker_kept_but_receipt_removed(self):
        self.marker.write_text("1\n")
        self.receipt.write_text("x\n")
        r = self.run_block()
        self.assertTrue(self.marker.exists())
        self.assertFalse(self.receipt.exists())
        self.assertIn("FAIL=0", r.stdout)

    def test_ownership_file_kept_while_marker_survives(self):
        self.marker.write_text("1\n")
        self.owned.write_text("")
        r = self.run_block(refuse_rm=True)
        self.assertTrue(self.owned.exists())
        self.assertIn("FAIL=1", r.stdout)

    def test_marker_survives_when_mount_and_rm_fail(self):
        self.marker.write_text("1\n")
        self.owned.write_text("")
        r = self.run_block(fail_mount=True, refuse_rm=True)
        self.assertTrue(self.marker.exists())
        self.assertIn("ERROR persistent D2 marker survived uninstall", r.stdout)
        self.assertIn("FAIL=1", r.stdout)
        self.assertNotIn("-ur", " ".join(self.mounts()))  # no remount-ro without a successful -uw

    def test_marker_survives_when_rm_refused_despite_mount(self):
        self.marker.write_text("1\n")
        self.owned.write_text("")
        r = self.run_block(refuse_rm=True)
        self.assertIn("ERROR persistent D2 marker survived uninstall", r.stdout)
        self.assertIn("FAIL=1", r.stdout)
        self.assertEqual(self.mounts(), ["-uw /mnt/app", "-ur /mnt/app"] * 2)

    def test_receipt_survives_is_error(self):
        self.receipt.write_text("x\n")
        r = self.run_block(refuse_rm=True)
        self.assertIn("ERROR install-defaults receipt survived uninstall", r.stdout)
        self.assertIn("FAIL=1", r.stdout)

    def test_ro_failure_in_d2_block_sets_fail(self):
        self.marker.write_text("1\n")
        self.owned.write_text("")
        r = self.run_block(fail_ur=True)
        self.assertFalse(self.marker.exists())  # removal itself worked
        self.assertIn(RO_MSG, r.stdout)
        self.assertEqual(r.stdout.count(RO_MSG), 2)  # D2 block and ownership/receipt block
        self.assertIn("FAIL=1", r.stdout)

    def test_ro_failure_in_receipt_block_sets_fail(self):
        self.receipt.write_text("x\n")
        r = self.run_block(fail_ur=True)
        self.assertEqual(r.stdout.count(RO_MSG), 1)
        self.assertIn("FAIL=1", r.stdout)

    def test_nothing_to_do_makes_no_mount_call(self):
        r = self.run_block()
        self.assertIn("FAIL=0", r.stdout)
        self.assertEqual(self.mounts(), [])
        self.assertNotIn("ERROR", r.stdout)


STOCK = "#!/bin/sh\nline one\n$J9 -jar start.jar\nlast line\n"
PARITY = "# MIBR PARITY-DRIVE BEGIN\nparity hook\n# MIBR PARITY-DRIVE END\n"


def uninstall_block(start_prefix, end_marker=None):
    """Text from the line starting with start_prefix to the matching column-0 'fi'."""
    lines = UNINSTALL.read_text().splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(start_prefix)), None)
    if start is None:
        return None
    if end_marker is None:
        end = next((i for i in range(start + 1, len(lines)) if lines[i] == "fi"), None)
    else:  # the last column-0 'fi' before the marker line
        stop = next((i for i, l in enumerate(lines) if l.startswith(end_marker)), None)
        end = None if stop is None else max((i for i in range(start + 1, stop) if lines[i] == "fi"), default=None)
    return None if end is None else "\n".join(lines[start:end + 1])


@unittest.skipUnless(SHELL, "no POSIX shell on host")
class UninstallLsdBlocks(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="mibr-lsd-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.app = self.root / "mnt/app"
        (self.app / "root").mkdir(parents=True)
        (self.app / "eso/hmi/lsd/jars").mkdir(parents=True)
        self.lsd = self.app / "eso/hmi/lsd/lsd.sh"
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.log = self.root / "mount.log"
        self.put("mount", FAKE_MOUNT)
        self.put("sync", "#!/bin/sh\nexit 0\n")
        self.dst = self.root / "dst"
        (self.dst / "scripts").mkdir(parents=True)
        self.stage = self.app / "eso/hmi/lsd/lsd.sh.mibr-deploy-java-remove.1"
        self.marker = self.app / "root/mibr-parity-drive.enabled"

    def put(self, name, text):
        p = self.tools / name
        p.write_text(text)
        p.chmod(0o755)

    def run_block(self, block, extra="", fail_ur=False):
        self.assertIsNotNone(block, "block not found in uninstall.sh")
        a = str(self.app)
        script = ('FAIL=0\nDST=%s\nLSD=%s\nTMP=%s\nOWNED=%s\nMOSTOWNED=%s\nBASE_DIR=/base\n%s\n%s\n%s\necho FAIL=$FAIL\n'
                  % (self.dst, self.lsd, self.stage, self.app / "root/owned", self.app / "root/mostowned",
                     lsd_funcs(), extra, block.replace("/mnt/app", a)))
        env = dict(os.environ, PATH=str(self.tools) + os.pathsep + os.environ["PATH"], MOUNT_LOG=str(self.log))
        if fail_ur:
            env["MOUNT_FAIL_UR"] = "1"
        r = subprocess.run([SHELL, "-c", script], env=env, capture_output=True, text=True, timeout=10)
        r.stdout = r.stdout.replace(str(self.app), "/mnt/app")
        return r

    def mounts(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def parity(self, **kw):
        return self.run_block(uninstall_block("PARITY_BEGIN=", 'echo "Restoring DisplayManager startup"'), **kw)

    def test_parity_block_extracted(self):
        b = uninstall_block("PARITY_BEGIN=", 'echo "Restoring DisplayManager startup"')
        self.assertIsNotNone(b)
        self.assertIn("exit 42", b)
        self.assertIn("mibr-parity-drive.enabled", b)
        self.assertTrue(b.startswith("PARITY_BEGIN=") and b.endswith("\nfi"))

    def test_parity_block_stripped(self):
        self.lsd.write_text("#!/bin/sh\nline one\n" + PARITY + "$J9 -jar start.jar\nlast line\n")
        r = self.parity()
        self.assertEqual(self.lsd.read_text(), STOCK, r.stdout + r.stderr)
        self.assertEqual(self.marker.read_text().strip(), "0")
        self.assertIn("FAIL=0", r.stdout)
        self.assertNotIn("ERROR", r.stdout)
        self.assertFalse(self.stage.exists())
        self.assertEqual(self.mounts(), ["-uw %s" % self.app, "-ur %s" % self.app])

    def test_parity_calls_disable_script_when_executable(self):
        self.lsd.write_text(STOCK + PARITY)
        called = self.root / "called"
        d = self.dst / "scripts/parity_drive_disable.sh"
        d.write_text("#!/bin/sh\necho called > %s\n" % called)
        d.chmod(0o755)
        r = self.parity()
        self.assertTrue(called.exists(), r.stdout + r.stderr)
        self.assertEqual(self.lsd.read_text(), STOCK)
        self.assertIn("FAIL=0", r.stdout)

    def test_parity_disable_script_not_executable_is_skipped(self):
        self.lsd.write_text(STOCK + PARITY)
        called = self.root / "called"
        d = self.dst / "scripts/parity_drive_disable.sh"
        d.write_text("#!/bin/sh\necho called > %s\n" % called)
        d.chmod(0o644)
        r = self.parity()
        self.assertFalse(called.exists())
        self.assertIn("FAIL=0", r.stdout)

    def test_parity_disable_script_failure_sets_fail(self):
        self.lsd.write_text(STOCK + PARITY)
        d = self.dst / "scripts/parity_drive_disable.sh"
        d.write_text("#!/bin/sh\nexit 1\n")
        d.chmod(0o755)
        r = self.parity()
        self.assertIn("FAIL=1", r.stdout)

    def test_parity_begin_without_end_leaves_lsd_unchanged(self):
        text = STOCK + "# MIBR PARITY-DRIVE BEGIN\nparity hook\n"
        self.lsd.write_text(text)
        r = self.parity()
        self.assertEqual(self.lsd.read_text(), text)
        self.assertIn("ERROR malformed parity-drive boot hook", r.stdout)
        self.assertIn("FAIL=1", r.stdout)
        self.assertFalse(self.stage.exists())
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.mounts(), ["-uw %s" % self.app, "-ur %s" % self.app])

    def test_parity_only_j9_inside_block_leaves_lsd_unchanged(self):
        text = "#!/bin/sh\nline one\n# MIBR PARITY-DRIVE BEGIN\n$J9 -jar start.jar\n# MIBR PARITY-DRIVE END\nlast line\n"
        self.lsd.write_text(text)
        r = self.parity()
        self.assertEqual(self.lsd.read_text(), text)
        self.assertIn("ERROR malformed parity-drive boot hook", r.stdout)
        self.assertIn("FAIL=1", r.stdout)
        self.assertFalse(self.stage.exists())
        self.assertFalse(self.marker.exists())

    def test_parity_absent_runs_nothing(self):
        self.lsd.write_text(STOCK)
        called = self.root / "called"
        d = self.dst / "scripts/parity_drive_disable.sh"
        d.write_text("#!/bin/sh\necho called > %s\n" % called)
        d.chmod(0o755)
        r = self.parity()
        self.assertEqual(self.lsd.read_text(), STOCK)
        self.assertEqual(self.mounts(), [])
        self.assertFalse(called.exists())
        self.assertFalse(self.marker.exists())
        self.assertIn("FAIL=0", r.stdout)

    def strip_case(self, owned_name, start, jar, mark):
        self.assertIsNotNone(uninstall_block(start))
        owned = self.app / "root" / owned_name
        owned.write_text("")
        jarp = self.app / "eso/hmi/lsd/jars" / jar
        jarp.write_text("jar")
        return owned, jarp, uninstall_block(start), mark

    def check_strip(self, owned_name, start, jar, mark):
        owned, jarp, block, mark = self.strip_case(owned_name, start, jar, mark)
        hook = "-Xbootclasspath/p:$BASE_DIR/lsd/jars/%s" % jar
        # Stripped result keeps $J9: removed, jar and marker cleaned up.
        self.lsd.write_text("#!/bin/sh\n# %s\n%s\n$J9 -jar start.jar\n" % (mark, hook))
        r = self.run_block(block)
        self.assertEqual(self.lsd.read_text(), "#!/bin/sh\n$J9 -jar start.jar\n", r.stdout + r.stderr)
        self.assertFalse(owned.exists())
        self.assertFalse(jarp.exists())
        self.assertIn("FAIL=0", r.stdout)
        # Stripping would leave no $J9: lsd.sh unchanged, jar and marker kept.
        owned.write_text("")
        jarp.write_text("jar")
        text = "#!/bin/sh\nother\n# %s\n%s\n" % (mark, hook)
        self.lsd.write_text(text)
        r = self.run_block(block)
        self.assertEqual(self.lsd.read_text(), text, r.stdout + r.stderr)
        self.assertTrue(owned.exists())
        self.assertTrue(jarp.exists())
        self.assertIn("FAIL=1", r.stdout)
        self.assertFalse(self.stage.exists())

    def test_parity_block_ro_failure_sets_fail(self):
        self.lsd.write_text(STOCK + PARITY)
        r = self.parity(fail_ur=True)
        self.assertEqual(self.lsd.read_text(), STOCK)
        self.assertIn(RO_MSG, r.stdout)
        self.assertIn("FAIL=1", r.stdout)

    def test_navignore_and_most20_ro_failure_sets_fail(self):
        for owned_name, start, jar in (("owned", 'if [ -e "$OWNED" ]', "MIBR-NavIgnore.jar"),
                                       ("mostowned", 'if [ -e "$MOSTOWNED" ]', "MIBR-Most20FPS.jar")):
            (self.app / "root" / owned_name).write_text("")
            (self.app / "eso/hmi/lsd/jars" / jar).write_text("jar")
            self.lsd.write_text("#!/bin/sh\n# MIBR\n-Xbootclasspath/p:$BASE_DIR/lsd/jars/%s\n$J9 -jar s.jar\n" % jar)
            r = self.run_block(uninstall_block(start), fail_ur=True)
            self.assertIn(RO_MSG, r.stdout, owned_name)
            self.assertIn("FAIL=1", r.stdout, owned_name)

    def test_strip_blocks_use_lsd_check_not_grep(self):
        for start in ('if [ -e "$OWNED" ]', 'if [ -e "$MOSTOWNED" ]'):
            b = uninstall_block(start)
            self.assertIn('lsd_check "$TMP" "" "" - "$(j9_count "$LSD")"', b)
            self.assertNotIn("grep '^\\$J9'", b)

    def test_navignore_strip_requires_j9(self):
        self.check_strip("owned", 'if [ -e "$OWNED" ]', "MIBR-NavIgnore.jar", "MIBR NAVIGNORE")

    def test_most20_strip_requires_j9(self):
        self.check_strip("mostowned", 'if [ -e "$MOSTOWNED" ]', "MIBR-Most20FPS.jar", "MIBR MOST20FPS")


class RestoreStockGuard(unittest.TestCase):
    def test_arc_43_guard_between_strip_and_branch(self):
        t = RESTORE.read_text()
        strip = t.index("END { if (skip) exit 42 }")
        rc = t.index("ARC=$?", strip)
        guard = t.index("ARC=43", rc)
        branch = t.index('if [ "$ARC" -eq 0 ]; then\n        chmod', guard)
        self.assertLess(strip, rc)
        self.assertLess(rc, guard)
        self.assertLess(guard, branch)
        between = t[rc:branch]
        self.assertIn('lsd_check "$AUTO_TMP" "$AUTO_BEGIN" "$AUTO_END" 0', between)
        self.assertIn('"$(j9_count /mnt/app/eso/hmi/lsd/lsd.sh)"', between)
        self.assertNotIn("grep '^\\$J9'", between)
        self.assertIn('[ "$ARC" -eq 0 ]', between)
        self.assertEqual(t.count("ARC=43"), 1)
        self.assertIn("malformed Auto-Direct boot hook", t[branch:])


def install_apply_text():
    t = INSTALL.read_text()
    i = t.index("\napply(){")
    return t[i:]


class InstallPriorInstallStatic(unittest.TestCase):
    def test_prior_install_from_receipt_before_stage_runtime(self):
        a = install_apply_text()
        rc = a.index("RECEIPT=$DST/version/install-defaults.receipt\n")
        p = a.index("PRIOR_INSTALL=0\n")
        r = a.index('[ -r "$RECEIPT" ] && PRIOR_INSTALL=1')
        reset = a.index('[ "${MIBR_RESET_DEFAULTS:-0}" = "1" ] && PRIOR_INSTALL=0')
        stage = a.index("\n  stage_runtime\n")
        self.assertTrue(rc < p < r < reset < stage)
        self.assertNotIn("gen2_nav_config.sh\" ] && PRIOR_INSTALL", a)

    def test_defaults_only_in_else_branch(self):
        a = install_apply_text()
        i = a.index('  if [ "$PRIOR_INSTALL" -eq 1 ]; then\n')
        e = a.index("\n  else\n", i)
        f = a.index("\n  fi\n", e)
        then_part, else_part = a[i:e], a[e:f]
        marker = ": > /mnt/app/root/mibr-alt111-keyframe-policy.enabled"
        nav = 'gen2_nav_config.sh" profile map-rich'
        for needle in (marker, nav, ': > "$D2_OWNED"'):
            self.assertEqual(INSTALL.read_text().count(needle), 1, needle)
            self.assertIn(needle, else_part)
            self.assertNotIn(needle, then_part)
        self.assertIn('if [ ! -e /mnt/app/root/mibr-alt111-keyframe-policy.enabled ]; then', else_part)
        self.assertLess(else_part.index("if [ ! -e"), else_part.index(': > "$D2_OWNED"'))
        self.assertIn("D2_KEYFRAMES=PRESERVED state=$D2_RESULT", then_part)
        self.assertIn("NAVIGATION_PROFILE=PRESERVED", then_part)
        tail = a[f:]
        self.assertIn('echo "navigation_profile=$NAV_RESULT"', tail)
        self.assertIn('echo "d2_keyframes=$D2_RESULT"', tail)
        self.assertIn('echo "auto_direct=$AD_RESULT"', tail)

    def test_receipt_written_atomically_before_pass(self):
        a = install_apply_text()
        w = a.index('> "$RECEIPT.new" || fail "receipt_write"')
        m = a.index('mv "$RECEIPT.new" "$RECEIPT"')
        ro = a.index('[ "$RO_FAIL" -eq 0 ] || fail "app_ro_restore_failed_earlier"')
        p = a.index('echo "MIBR_INSTALL=PASS"')
        self.assertTrue(w < m < ro < p)
        for line in ('echo "MIBR_INSTALL_DEFAULTS/1"', 'echo "d2=$D2_RESULT"', 'echo "navigation=$NAV_RESULT"',
                     'echo "auto_direct=$AD_RESULT"'):
            self.assertIn(line, a[:w])


def app_ro_text():
    t = INSTALL.read_text()
    i = t.index("app_ro(){")
    return t[i:t.index("\n}\n", i) + 3]


@unittest.skipUnless(SHELL, "no POSIX shell on host")
class InstallAppRo(unittest.TestCase):
    def run_ro(self, mount_ok, app_rw=1):
        tmp = tempfile.TemporaryDirectory(prefix="mibr-ro-")
        self.addCleanup(tmp.cleanup)
        tools = Path(tmp.name)
        for name, body in (("mount", "#!/bin/sh\n%s\n" % ("exit 0" if mount_ok else "exit 1")), ("sync", "#!/bin/sh\nexit 0\n")):
            (tools / name).write_text(body)
            (tools / name).chmod(0o755)
        script = 'APP_RW=%d\nRO_FAIL=0\n%s\napp_ro; echo "rc=$? APP_RW=$APP_RW RO_FAIL=$RO_FAIL"\n' % (app_rw, app_ro_text())
        env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"])
        return subprocess.run([SHELL, "-c", script], env=env, capture_output=True, text=True, timeout=10).stdout

    def test_success(self):
        self.assertIn("rc=0 APP_RW=0 RO_FAIL=0", self.run_ro(True))

    def test_mount_failure_keeps_rw_and_flags(self):
        out = self.run_ro(False)
        self.assertIn("rc=1 APP_RW=1 RO_FAIL=1", out)
        self.assertIn(RO_MSG, out)

    def test_not_rw_is_noop(self):
        self.assertIn("rc=0 APP_RW=0 RO_FAIL=0", self.run_ro(False, app_rw=0))


@unittest.skipUnless(SHELL, "no POSIX shell on host")
class InstallPriorInstallExec(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="mibr-prior-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.app = self.root / "mnt/app"
        (self.app / "root").mkdir(parents=True)
        self.dst = self.root / "dst"
        (self.dst / "scripts").mkdir(parents=True)
        self.nav_log = self.root / "nav.log"
        self.enable_log = self.root / "enable.log"
        self.marker = self.app / "root/mibr-alt111-keyframe-policy.enabled"
        self.ad = self.app / "root/mibr-carplay-autodirect.enabled"
        self.owned = self.dst / "version/ownership/d2-marker.owned"
        self.receipt = self.dst / "version/install-defaults.receipt"
        (self.root / "rt/isotx2-gate").mkdir(parents=True)
        gate = self.root / "rt/isotx2-gate/install_preload.sh"
        gate.write_text("#!/bin/sh\nexit 0\n")
        gate.chmod(0o755)
        self.put("patch_carplay.sh", "#!/bin/sh\nexit 0\n")
        self.put("gen2_nav_config.sh", '#!/bin/sh\necho "$*" >> %s\n' % self.nav_log)
        # Like the real script: touch the enable marker unless told to keep its state.
        self.put("direct_ts_auto_enable.sh",
                 '#!/bin/sh\necho "KEEP=$MIBR_KEEP_MARKER_STATE PREPARE=$MIBR_PREPARE_ONLY" >> %s\n'
                 '{ [ "$MIBR_KEEP_MARKER_STATE" = 1 ] && [ ! -e %s ]; } || touch %s\n' % (self.enable_log, self.ad, self.ad))

    def put(self, name, text):
        p = self.dst / "scripts" / name
        p.write_text(text)
        p.chmod(0o755)

    def apply_block(self):
        a = install_apply_text()
        s = a.index("  RECEIPT=$DST/version/install-defaults.receipt\n")
        end_line = '  [ "$RO_FAIL" -eq 0 ] || fail "app_ro_restore_failed_earlier"'
        e = a.index(end_line) + len(end_line)
        return a[s:e].replace("/mnt/app", str(self.app))

    def run_apply_part(self, reset=None, ro_fail=False):
        script = ('DST=%s\nRO_FAIL=0\napp_rw(){ echo app_rw; }\napp_ro(){ echo app_ro; %s}\n'
                  'fail(){ echo "FAILED $1"; exit 9; }\nstage_runtime(){ :; }\ninstall_required_navignore(){ :; }\ninstall_required_most20(){ :; }\nRUNTIME=%s\nPAYLOAD=/p\nSHA=x\n%s\n'
                  'echo "PRIOR=$PRIOR_INSTALL D2=$D2_RESULT NAV=$NAV_RESULT AD_KEEP=$AD_KEEP AD=$AD_RESULT"\n'
                  % (self.dst, 'RO_FAIL=1; return 1; ' if ro_fail else "", self.root / "rt", self.apply_block()))
        env = dict(os.environ)
        env.pop("MIBR_RESET_DEFAULTS", None)
        if reset is not None:
            env["MIBR_RESET_DEFAULTS"] = reset
        return subprocess.run([SHELL, "-c", script], env=env, capture_output=True, text=True, timeout=10)

    def navs(self):
        return self.nav_log.read_text().splitlines() if self.nav_log.exists() else []

    def enables(self):
        return self.enable_log.read_text().splitlines() if self.enable_log.exists() else []

    def receipt_lines(self):
        return self.receipt.read_text().splitlines()

    def test_block_extracted(self):
        b = self.apply_block()
        self.assertTrue(b.startswith("  RECEIPT=$DST/version") and b.endswith('"app_ro_restore_failed_earlier"'))

    def test_fresh_install_applies_defaults(self):
        r = self.run_apply_part()
        self.assertIn("PRIOR=0 D2=persistent_default NAV=map-rich AD_KEEP=0 AD=enabled_default", r.stdout, r.stdout + r.stderr)
        self.assertTrue(self.marker.exists())
        self.assertTrue(self.owned.exists())
        self.assertIn("D2_KEYFRAMES=PERSISTENT_DEFAULT", r.stdout)
        self.assertEqual(self.navs(), ["profile map-rich"])
        self.assertEqual(self.enables(), ["KEEP=0 PREPARE=1"])
        self.assertEqual(self.receipt_lines(), ["MIBR_INSTALL_DEFAULTS/1", "d2=persistent_default", "navigation=map-rich",
                                                "auto_direct=enabled_default"])
        self.assertFalse(Path(str(self.receipt) + ".new").exists())
        self.assertTrue(self.ad.exists())

    def test_fresh_install_with_existing_marker_creates_no_ownership(self):
        self.marker.write_text("")
        r = self.run_apply_part()
        self.assertIn("PRIOR=0 D2=persistent_default", r.stdout, r.stdout + r.stderr)
        self.assertTrue(self.marker.exists())
        self.assertFalse(self.owned.exists())
        self.assertEqual(self.navs(), ["profile map-rich"])

    def seed_receipt(self):
        self.receipt.parent.mkdir(parents=True, exist_ok=True)
        self.receipt.write_text("MIBR_INSTALL_DEFAULTS/1\n")

    def test_helper_script_alone_is_not_a_prior_install(self):
        r = self.run_apply_part()  # gen2_nav_config.sh exists from setUp, no receipt
        self.assertIn("PRIOR=0", r.stdout)

    def test_upgrade_ad_off_preserved(self):
        self.seed_receipt()
        r = self.run_apply_part()
        self.assertIn("PRIOR=1 D2=preserved_off NAV=preserved AD_KEEP=1 AD=preserved_off", r.stdout, r.stdout + r.stderr)
        self.assertIn("D2_KEYFRAMES=PRESERVED state=preserved_off", r.stdout)
        self.assertIn("NAVIGATION_PROFILE=PRESERVED", r.stdout)
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.owned.exists())
        self.assertEqual(self.navs(), [])
        self.assertEqual(self.enables(), ["KEEP=1 PREPARE=1"])
        self.assertFalse(self.ad.exists())
        self.assertEqual(self.receipt_lines()[1:], ["d2=preserved_off", "navigation=preserved", "auto_direct=preserved_off"])

    def test_upgrade_ad_on_preserved(self):
        self.seed_receipt()
        self.marker.write_text("")
        self.ad.write_text("")
        r = self.run_apply_part()
        self.assertIn("PRIOR=1 D2=preserved_on NAV=preserved AD_KEEP=0 AD=preserved_on", r.stdout, r.stdout + r.stderr)
        self.assertTrue(self.marker.exists())
        self.assertFalse(self.owned.exists())
        self.assertEqual(self.navs(), [])
        self.assertEqual(self.enables(), ["KEEP=0 PREPARE=1"])
        self.assertTrue(self.ad.exists())
        self.assertEqual(self.receipt_lines()[-1], "auto_direct=preserved_on")

    def test_off_stays_off_over_two_upgrades(self):
        first = self.run_apply_part()  # fresh install: AD on
        self.assertTrue(self.ad.exists(), first.stdout + first.stderr)
        self.ad.unlink()  # user switches Auto-Direct off
        for _ in range(2):
            r = self.run_apply_part()
            self.assertIn("AD_KEEP=1 AD=preserved_off", r.stdout, r.stdout + r.stderr)
            self.assertFalse(self.ad.exists())
        self.assertEqual(self.enables(), ["KEEP=0 PREPARE=1", "KEEP=1 PREPARE=1", "KEEP=1 PREPARE=1"])
        self.assertEqual(self.navs(), ["profile map-rich"])  # only the fresh install

    def test_reset_defaults_overrides_receipt(self):
        self.seed_receipt()
        r = self.run_apply_part(reset="1")
        self.assertIn("PRIOR=0 D2=persistent_default NAV=map-rich AD_KEEP=0 AD=enabled_default", r.stdout, r.stdout + r.stderr)
        self.assertTrue(self.marker.exists())
        self.assertEqual(self.navs(), ["profile map-rich"])
        self.assertEqual(self.enables(), ["KEEP=0 PREPARE=1"])

    def test_ro_failure_fails_before_pass(self):
        r = self.run_apply_part(ro_fail=True)
        self.assertNotIn("PRIOR=", r.stdout)
        self.assertIn("FAILED d2_persistent_app_ro", r.stdout)
        self.assertEqual(r.returncode, 9)

    def test_earlier_ro_failure_detected_at_end(self):
        a = self.apply_block()
        script = ('DST=%s\nRO_FAIL=1\napp_rw(){ :; }\napp_ro(){ return 0; }\nfail(){ echo "FAILED $1"; exit 9; }\n'
                  'stage_runtime(){ :; }\ninstall_required_navignore(){ :; }\ninstall_required_most20(){ :; }\nRUNTIME=%s\nPAYLOAD=/p\nSHA=x\n%s\n' % (self.dst, self.root / "rt", a))
        r = subprocess.run([SHELL, "-c", script], capture_output=True, text=True, timeout=10)
        self.assertIn("FAILED app_ro_restore_failed_earlier", r.stdout)


class AutoDirectEnableStatic(unittest.TestCase):
    def test_keep_marker_state_skips_touch(self):
        t = ENABLE.read_text()
        i = t.index('if [ "${MIBR_KEEP_MARKER_STATE:-0}" = "1" ] && [ ! -e "$ENABLED" ]; then')
        e = t.index("\nelse\n", i)
        f = t.index("\nfi\n", e)
        self.assertNotIn("touch", t[i:e])
        self.assertIn('touch "$ENABLED" || fail 32 "enable_marker"', t[e:f])
        self.assertEqual(t.count('touch "$ENABLED"'), 1)

    def test_keep_marker_state_block_executes(self):
        t = ENABLE.read_text()
        i = t.index('if [ "${MIBR_KEEP_MARKER_STATE:-0}" = "1" ]')
        block = t[i:t.index("\nfi\n", i) + 3]
        for keep, present, touched in (("1", False, False), ("1", True, True), ("0", False, True)):
            with tempfile.TemporaryDirectory(prefix="mibr-ad-") as d:
                en = Path(d) / "enabled"
                if present:
                    en.write_text("")
                script = 'ENABLED=%s\nfail(){ echo FAIL; exit 9; }\n%s\n[ -e "$ENABLED" ] && echo EXISTS; echo "$MARKER_STATE"\n' % (en, block)
                r = subprocess.run([SHELL, "-c", script], env=dict(os.environ, MIBR_KEEP_MARKER_STATE=keep),
                                   capture_output=True, text=True, timeout=10)
                self.assertEqual(en.exists(), present or touched, (keep, present, r.stdout))
                self.assertIn("absent_preserved" if (keep == "1" and not present) else "present", r.stdout)

    def test_failed_ro_exits_33(self):
        t = ENABLE.read_text()
        self.assertIn('mount -ur /mnt/app 2>/dev/null || { APP_RW=0; echo "AUTO_DIRECT_ENABLE=FAIL app_ro"; exit 33; }', t)
        self.assertIn('echo "enabled_marker=$ENABLED state=$MARKER_STATE"', t)


class ParityEnableStatic(unittest.TestCase):
    def test_gate_and_ro_failure(self):
        t = PARITY_ENABLE.read_text()
        gate = t.index('lsd_check "$TMP" "$BEGIN" "$END" 1 "$(j9_count "$LSD")" || fail 27 "boot_patch_integrity"')
        self.assertLess(gate, t.index('mv "$TMP" "$LSD"'))
        self.assertIn('echo "PARITY_DRIVE_ENABLE=FAIL app_ro"; exit 28', t)


if __name__ == "__main__":
    unittest.main()
