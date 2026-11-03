"""lsd.sh writers stage on /mnt/app (atomic rename); uninstall removes the persistent D2 marker. Host-only."""
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
            if not value.startswith("/mnt/app/root/"):
                problems.append("%s: %s=%s is not staged under /mnt/app/root/" % (name, var, value))
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

    def test_no_lsd_stage_in_tmp(self):
        for path in (UNINSTALL, INSTALL, ENABLE, RESTORE):
            self.assertIsNone(re.search(r'^\s*\w*TMP=/tmp/lsd\.sh', path.read_text(), re.M), path.name)

    def test_checker_flags_tmp_stage(self):
        bad = 'TMP=/tmp/lsd.sh.x.$$\nmv "$TMP" "$LSD"\n'
        self.assertTrue(any("not staged under /mnt/app/root/" in v for v in violations(bad)))
        literal_dollar = 'TMP=/mnt/app/root/lsd.sh.x.$\nmv "$TMP" "$LSD"\n'
        self.assertTrue(any("does not end with" in v for v in violations(literal_dollar)))
        good = 'TMP=/mnt/app/root/lsd.sh.x.$$\nmv "$TMP" "$LSD"\n'
        self.assertEqual(violations(good), [])


def d2_block():
    lines = UNINSTALL.read_text().splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("D2_MARKER=")), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i] == "fi"), None)
    return None if end is None else "\n".join(lines[start:end + 1])


@unittest.skipUnless(SHELL, "no POSIX shell on host")
class D2MarkerRemoval(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="mibr-d2-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.log = self.root / "mount.log"
        self.put("mount", '#!/bin/sh\necho "$*" >> "$MOUNT_LOG"\n[ "${MOUNT_FAIL:-0}" != 1 ] || exit 1\n')
        self.put("sync", "#!/bin/sh\nexit 0\n")
        self.marker = self.root / "mnt/app/root/mibr-alt111-keyframe-policy.enabled"
        self.marker.parent.mkdir(parents=True)

    def put(self, name, text):
        p = self.tools / name
        p.write_text(text)
        p.chmod(0o755)

    def run_block(self, fail_mount=False, refuse_rm=False):
        block = d2_block()
        self.assertIsNotNone(block, "D2_MARKER block not found in uninstall.sh")
        script = "FAIL=0\n" + block.replace("/mnt/app", str(self.root / "mnt/app")) + "\necho FAIL=$FAIL\n"
        if refuse_rm:
            self.put("rm", "#!/bin/sh\nexit 1\n")
        env = dict(os.environ, PATH=str(self.tools) + os.pathsep + os.environ["PATH"], MOUNT_LOG=str(self.log))
        if fail_mount:
            env["MOUNT_FAIL"] = "1"
        # The block references the mount point as an argument; the rewrite keeps the fake log readable.
        return subprocess.run([SHELL, "-c", script], env=env, capture_output=True, text=True, timeout=10)

    def mounts(self):
        return [l.replace(str(self.root / "mnt/app"), "/mnt/app") for l in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_block_extracted(self):
        block = d2_block()
        self.assertIsNotNone(block)
        self.assertIn("mount -uw /mnt/app", block)
        self.assertIn("mount -ur /mnt/app", block)
        self.assertIn("ERROR persistent D2 marker survived uninstall", block)

    def test_marker_removed_in_own_rw_window(self):
        self.marker.write_text("1\n")
        r = self.run_block()
        self.assertFalse(self.marker.exists(), r.stdout + r.stderr)
        self.assertIn("FAIL=0", r.stdout)
        self.assertNotIn("ERROR", r.stdout)
        self.assertEqual(self.mounts(), ["-uw /mnt/app", "-ur /mnt/app"])

    def test_marker_survives_when_mount_and_rm_fail(self):
        self.marker.write_text("1\n")
        r = self.run_block(fail_mount=True, refuse_rm=True)
        self.assertTrue(self.marker.exists())
        self.assertIn("ERROR persistent D2 marker survived uninstall", r.stdout)
        self.assertIn("FAIL=1", r.stdout)
        self.assertEqual(self.mounts(), ["-uw /mnt/app"])  # no remount-ro without a successful -uw

    def test_marker_survives_when_rm_refused_despite_mount(self):
        self.marker.write_text("1\n")
        r = self.run_block(refuse_rm=True)
        self.assertIn("ERROR persistent D2 marker survived uninstall", r.stdout)
        self.assertIn("FAIL=1", r.stdout)
        self.assertEqual(self.mounts(), ["-uw /mnt/app", "-ur /mnt/app"])

    def test_marker_absent_makes_no_mount_call(self):
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
        self.put("mount", '#!/bin/sh\necho "$*" >> "$MOUNT_LOG"\nexit 0\n')
        self.put("sync", "#!/bin/sh\nexit 0\n")
        self.dst = self.root / "dst"
        (self.dst / "scripts").mkdir(parents=True)
        self.stage = self.app / "root/lsd.sh.mibr-deploy-java-remove.1"
        self.marker = self.app / "root/mibr-parity-drive.enabled"

    def put(self, name, text):
        p = self.tools / name
        p.write_text(text)
        p.chmod(0o755)

    def run_block(self, block, extra=""):
        self.assertIsNotNone(block, "block not found in uninstall.sh")
        a = str(self.app)
        script = ('FAIL=0\nDST=%s\nLSD=%s\nTMP=%s\nOWNED=%s\nMOSTOWNED=%s\nBASE_DIR=/base\n%s\n%s\necho FAIL=$FAIL\n'
                  % (self.dst, self.lsd, self.stage, self.app / "root/owned", self.app / "root/mostowned",
                     extra, block.replace("/mnt/app", a)))
        env = dict(os.environ, PATH=str(self.tools) + os.pathsep + os.environ["PATH"], MOUNT_LOG=str(self.log))
        return subprocess.run([SHELL, "-c", script], env=env, capture_output=True, text=True, timeout=10)

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
        self.assertIn("grep '^\\$J9' \"$AUTO_TMP\"", between)
        self.assertIn('[ "$ARC" -eq 0 ]', between)
        self.assertEqual(t.count("ARC=43"), 1)
        self.assertIn("malformed Auto-Direct boot hook", t[branch:])


def install_apply_text():
    t = INSTALL.read_text()
    i = t.index("\napply(){")
    return t[i:]


class InstallPriorInstallStatic(unittest.TestCase):
    def test_prior_install_computed_before_stage_runtime(self):
        a = install_apply_text()
        p = a.index("PRIOR_INSTALL=0\n")
        r = a.index('[ -r "$DST/scripts/gen2_nav_config.sh" ] && PRIOR_INSTALL=1')
        reset = a.index('[ "${MIBR_RESET_DEFAULTS:-0}" = "1" ] && PRIOR_INSTALL=0')
        stage = a.index("\n  stage_runtime\n")
        self.assertTrue(p < r < reset < stage)

    def test_defaults_only_in_else_branch(self):
        a = install_apply_text()
        i = a.index('  if [ "$PRIOR_INSTALL" -eq 1 ]; then\n')
        e = a.index("\n  else\n", i)
        f = a.index("\n  fi\n", e)
        then_part, else_part = a[i:e], a[e:f]
        marker = ": > /mnt/app/root/mibr-alt111-keyframe-policy.enabled"
        nav = 'gen2_nav_config.sh" profile map-rich'
        for needle in (marker, nav):
            self.assertEqual(INSTALL.read_text().count(needle), 1, needle)
            self.assertIn(needle, else_part)
            self.assertNotIn(needle, then_part)
        self.assertNotIn("keyframe-policy.enabled ||", then_part)
        self.assertIn("D2_KEYFRAMES=PRESERVED state=$D2_RESULT", then_part)
        self.assertIn("NAVIGATION_PROFILE=PRESERVED", then_part)
        tail = a[f:]
        self.assertIn('echo "navigation_profile=$NAV_RESULT"', tail)
        self.assertIn('echo "d2_keyframes=$D2_RESULT"', tail)


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
        self.marker = self.app / "root/mibr-alt111-keyframe-policy.enabled"

    def nav_script(self):
        p = self.dst / "scripts/gen2_nav_config.sh"
        p.write_text('#!/bin/sh\necho "$*" >> %s\n' % self.nav_log)
        p.chmod(0o755)

    def run_apply_part(self, reset=None, nav_after=False):
        a = install_apply_text()
        s = a.index("  PRIOR_INSTALL=0\n")
        s_end = a.index("\n  stage_runtime\n")
        compute = a[s:s_end]
        i = a.index('  if [ "$PRIOR_INSTALL" -eq 1 ]; then\n')
        f = a.index("\n  fi\n", a.index("\n  else\n", i)) + len("\n  fi")
        branch = a[i:f].replace("/mnt/app", str(self.app))
        stage = "\n".join(l for l in ["  :"] if not nav_after)
        after = ""
        if nav_after:  # stage_runtime installs the helper between the check and the branch
            after = 'printf "#!/bin/sh\\necho \\"\\$*\\" >> %s\\n" > %s/scripts/gen2_nav_config.sh; chmod 755 %s/scripts/gen2_nav_config.sh\n' % (self.nav_log, self.dst, self.dst)
        script = ('DST=%s\napp_rw(){ echo app_rw; }\napp_ro(){ echo app_ro; }\nfail(){ echo "FAILED $1"; exit 9; }\n'
                  '%s\n%s\n%s\necho "PRIOR=$PRIOR_INSTALL D2=$D2_RESULT NAV=$NAV_RESULT"\n' % (self.dst, compute, after, branch))
        env = dict(os.environ)
        env.pop("MIBR_RESET_DEFAULTS", None)
        if reset is not None:
            env["MIBR_RESET_DEFAULTS"] = reset
        return subprocess.run([SHELL, "-c", script], env=env, capture_output=True, text=True, timeout=10)

    def navs(self):
        return self.nav_log.read_text().splitlines() if self.nav_log.exists() else []

    def test_fresh_install_applies_defaults(self):
        # No gen2_nav_config.sh before stage_runtime: PRIOR_INSTALL=0; the script exists by the time it runs.
        compute_only = self.run_apply_part(nav_after=True)
        self.assertIn("PRIOR=0 D2=persistent_default NAV=map-rich", compute_only.stdout, compute_only.stdout + compute_only.stderr)
        self.assertTrue(self.marker.exists())
        self.assertIn("D2_KEYFRAMES=PERSISTENT_DEFAULT", compute_only.stdout)
        self.assertEqual(self.navs(), ["profile map-rich"])

    def test_prior_install_preserves_d2_off(self):
        self.nav_script()
        r = self.run_apply_part()
        self.assertIn("PRIOR=1 D2=preserved_off NAV=preserved", r.stdout, r.stdout + r.stderr)
        self.assertIn("D2_KEYFRAMES=PRESERVED state=preserved_off", r.stdout)
        self.assertIn("NAVIGATION_PROFILE=PRESERVED", r.stdout)
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.navs(), [])
        self.assertNotIn("app_rw", r.stdout)

    def test_prior_install_preserves_d2_on(self):
        self.nav_script()
        self.marker.write_text("")
        r = self.run_apply_part()
        self.assertIn("PRIOR=1 D2=preserved_on NAV=preserved", r.stdout, r.stdout + r.stderr)
        self.assertIn("D2_KEYFRAMES=PRESERVED state=preserved_on", r.stdout)
        self.assertTrue(self.marker.exists())
        self.assertEqual(self.navs(), [])

    def test_reset_defaults_overrides_prior_install(self):
        self.nav_script()
        r = self.run_apply_part(reset="1")
        self.assertIn("PRIOR=0 D2=persistent_default NAV=map-rich", r.stdout, r.stdout + r.stderr)
        self.assertTrue(self.marker.exists())
        self.assertEqual(self.navs(), ["profile map-rich"])


if __name__ == "__main__":
    unittest.main()
