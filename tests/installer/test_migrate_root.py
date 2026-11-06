"""Host tests for installer/lib/migrate-root.ksh (M1 root migration)."""
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "installer/lib/migrate-root.ksh"
REAL_MAP = REPO / "installer/config/root-migration.list"
SHELLS = [s for s in ("sh", "ksh") if shutil.which(s)]


def tree(path):
    """Relative path -> (is_dir, sha) of everything below path."""
    out = {}
    for p in sorted(Path(path).rglob("*")):
        rel = str(p.relative_to(path))
        out[rel] = (p.is_dir(), None if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest())
    return out


class Base(unittest.TestCase):
    shell = "sh"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="m1test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.app = self.tmp / "app"
        self.root = self.app / "root"
        self.new = self.root / "mibr"
        self.root.mkdir(parents=True)
        self.lock = self.tmp / "install.lock"
        self.sha = shutil.which("sha256sum")
        if not self.sha:
            w = self.tmp / "sha256sum"
            w.write_text("#!/usr/bin/env python3\nimport hashlib,sys\n"
                         "print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()+'  '+sys.argv[1])\n")
            w.chmod(0o755)
            self.sha = str(w)
        self.tmpd = self.tmp / "tmpd"
        self.tmpd.mkdir()

    def w(self, rel, data="x\n"):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data)
        return p

    def run_cmd(self, cmd, id_="T1", extra=None, env=None, mapf=None):
        e = dict(os.environ, MIBR_SHA256=self.sha, MIBR_MIGRATE_NO_MOUNT="1",
                 MIBR_LOCK_FILE=str(self.lock), TMPDIR=str(self.tmpd))
        e.pop("MIBR_MIGRATE_FAIL_AT", None)
        e.update(env or {})
        args = [self.shell, str(SCRIPT), cmd, "--app", str(self.app)]
        if id_:
            args += ["--id", id_]
        if mapf:
            args += ["--map", str(mapf)]
        args += extra or []
        return subprocess.run(args, env=e, capture_output=True, text=True, timeout=60)

    def legacy_snapshot(self):
        return {k: v for k, v in tree(self.root).items()
                if k != "mibr" and not k.startswith("mibr/")}

    def populate(self, disabled=False):
        self.w("altscreen-u2/config/mibr-menu.conf", "menu-bytes\n")
        self.w("altscreen-u2/config/mibr-nav-side.conf", "MAGIC rev=3\n")
        self.w("altscreen-u2/bin/binary", "binary\n")
        self.w("mibr-kit/boot-count", "2\n")
        self.w("mibr-v3/data", "v3\n")
        self.w("mibr-carplay-autodirect.enabled", "")
        if disabled:
            self.w("mibr-kit/disabled", "boot loop detected\n")

    def disabled(self):
        p = self.new / "state/boot/disabled"
        return p.read_text() if p.exists() else None


class Cases(Base):
    def test_fresh_unit(self):
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("MIBR_MIGRATE=OK", r.stdout)
        self.assertIsNone(self.disabled())
        rc = (self.new / "version/migration-T1.receipt").read_text()
        self.assertIn("state=complete", rc)
        self.assertIn("legacy_disabled=0", rc)
        self.assertFalse((self.new / ".staging-T1").exists())
        self.assertEqual(self.run_cmd("verify").returncode, 0)

    def test_legacy_enabled(self):
        self.populate()
        before = self.legacy_snapshot()
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.legacy_snapshot(), before)
        self.assertEqual((self.new / "config/menu/layout.conf").read_text(), "menu-bytes\n")
        self.assertEqual((self.new / "config/navigation/nav-side.conf").read_text(), "MAGIC rev=3\n")
        self.assertIsNone(self.disabled())
        rc = (self.new / "version/migration-T1.receipt").read_text()
        self.assertIn("unmapped altscreen-u2/bin/binary", rc)
        self.assertIn("unmapped mibr-v3/data", rc)
        self.assertIn("migrated mibr-carplay-autodirect.enabled config/features/mibr-carplay-autodirect.enabled", rc)
        self.assertTrue((self.new / "config/features/mibr-carplay-autodirect.enabled").exists())
        self.assertNotIn("unmapped mibr-kit/disabled", rc)
        self.assertFalse((self.new / "bin").exists())
        self.assertTrue((self.new / "backup/T1/legacy/mibr-v3/data").exists())
        self.assertTrue((self.new / "backup/T1/SHA256SUMS").exists())
        self.assertEqual(self.run_cmd("verify").returncode, 0)

    def test_legacy_disabled_preserved(self):
        self.populate(disabled=True)
        before = self.legacy_snapshot()
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.disabled(), "migrated-disabled T1: boot loop detected\n")
        self.assertEqual(self.legacy_snapshot(), before)
        self.assertIn("legacy_disabled=1", (self.new / "version/migration-T1.receipt").read_text())

    def test_boot_count_carried(self):
        self.populate()
        self.assertEqual(self.run_cmd("run").returncode, 0)
        self.assertEqual((self.new / "state/boot/boot-count").read_text(), "2\n")
        self.assertEqual((self.root / "mibr-kit/boot-count").read_text(), "2\n")

    def test_failure_injection_then_rerun(self):
        for disabled in (False, True):
            for step in ("c", "d", "e", "f", "h1", "h2"):
                with self.subTest(step=step, disabled=disabled):
                    shutil.rmtree(self.root)
                    self.root.mkdir(parents=True)
                    self.populate(disabled=disabled)
                    before = self.legacy_snapshot()
                    r = self.run_cmd("run", env={"MIBR_MIGRATE_FAIL_AT": step})
                    self.assertEqual(r.returncode, 99, r.stdout)
                    self.assertFalse(self.lock.exists(), "trap must unlock")
                    d = self.disabled()
                    if step == "h2":  # after the final kill-switch state
                        self.assertEqual(d, "migrated-disabled T1: boot loop detected\n" if disabled else None)
                    else:
                        self.assertIsNotNone(d)
                        self.assertTrue(d.startswith("install-in-progress") or d.startswith("migrated"), d)
                    self.assertEqual(self.legacy_snapshot(), before)
                    r = self.run_cmd("run")
                    self.assertEqual(r.returncode, 0, r.stdout)
                    if disabled:
                        self.assertEqual(self.disabled(), "migrated-disabled T1: boot loop detected\n")
                    else:
                        self.assertIsNone(self.disabled())
                    self.assertEqual(self.legacy_snapshot(), before)
                    self.assertEqual(self.run_cmd("verify").returncode, 0)
                    self.assertFalse((self.new / ".staging-T1").exists())
                    self.assertEqual((self.new / "state/boot/boot-count").read_text(), "2\n")

    def test_prior_new_disabled_survives_crash(self):
        p = self.new / "state/boot"
        p.mkdir(parents=True)
        (p / "disabled").write_text("manual stop\n")
        r = self.run_cmd("run", env={"MIBR_MIGRATE_FAIL_AT": "e"})
        self.assertEqual(r.returncode, 99)
        self.assertTrue(self.disabled().startswith("install-in-progress T1"))
        self.assertEqual(self.run_cmd("run").returncode, 0)
        self.assertEqual(self.disabled(), "migrated-disabled T1: manual stop\n")

    def test_conflict_keeps_disabled(self):
        self.populate()
        t = self.new / "config/menu/layout.conf"
        t.parent.mkdir(parents=True)
        t.write_text("different\n")
        before = self.legacy_snapshot()
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 20, r.stdout)
        self.assertTrue(self.disabled().startswith("install-in-progress"))
        self.assertEqual(t.read_text(), "different\n")
        self.assertEqual(self.legacy_snapshot(), before)
        self.assertFalse((self.new / "version/migration-T1.receipt").exists())
        self.assertFalse((self.new / "config/navigation/nav-side.conf").exists())

    def test_equal_target_is_skipped(self):
        self.populate()
        t = self.new / "config/menu/layout.conf"
        t.parent.mkdir(parents=True)
        t.write_text("menu-bytes\n")
        self.assertEqual(self.run_cmd("run").returncode, 0)

    def test_idempotent_second_run(self):
        self.populate()
        self.assertEqual(self.run_cmd("run").returncode, 0)
        snap = tree(self.new)
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 0)
        self.assertIn("MIBR_MIGRATE=ALREADY_COMPLETE", r.stdout)
        self.assertEqual(tree(self.new), snap)

    def test_plan_read_only(self):
        self.populate(disabled=True)
        snap = tree(self.tmp / "app")
        r = self.run_cmd("plan", id_=None)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("migrate altscreen-u2/config/mibr-menu.conf config/menu/layout.conf", r.stdout)
        self.assertIn("unmapped mibr-v3/data", r.stdout)
        self.assertIn("legacy_disabled=1", r.stdout)
        self.assertEqual(tree(self.tmp / "app"), snap)
        self.assertFalse(self.new.exists())
        self.assertFalse(self.lock.exists())

    def test_plan_reports_conflict(self):
        self.populate()
        t = self.new / "config/menu/layout.conf"
        t.parent.mkdir(parents=True)
        t.write_text("different\n")
        r = self.run_cmd("plan", id_=None)
        self.assertEqual(r.returncode, 20)
        self.assertIn("conflict altscreen-u2/config/mibr-menu.conf", r.stdout)

    def test_verify_detects_tampering(self):
        self.populate()
        self.assertEqual(self.run_cmd("run").returncode, 0)
        t = self.new / "config/menu/layout.conf"
        t.write_text("tampered\n")
        r = self.run_cmd("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("target mismatch config/menu/layout.conf", r.stdout)
        t.write_text("menu-bytes\n")
        self.assertEqual(self.run_cmd("verify").returncode, 0)
        (self.root / "mibr-v3/data").write_text("changed\n")
        r = self.run_cmd("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("mismatch mibr-v3/data", r.stdout)

    def test_verify_without_receipt(self):
        self.assertEqual(self.run_cmd("verify").returncode, 1)

    def test_rollback(self):
        self.populate()
        self.assertEqual(self.run_cmd("run", env={"MIBR_MIGRATE_FAIL_AT": "e"}).returncode, 99)
        self.assertTrue((self.new / ".staging-T1").exists())
        before = self.legacy_snapshot()
        r = self.run_cmd("rollback")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("legacy trees intact", r.stdout)
        self.assertFalse((self.new / ".staging-T1").exists())
        self.assertEqual(self.legacy_snapshot(), before)
        (self.root / "mibr-v3/data").write_text("changed\n")
        self.assertEqual(self.run_cmd("rollback").returncode, 1)

    def test_state_is_file_aborts(self):
        self.populate()
        self.new.mkdir(parents=True)
        (self.new / "state").write_text("junk")
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 10, r.stdout)
        self.assertFalse((self.new / "backup").exists())
        self.assertFalse(self.lock.exists())

    def test_live_lock_refuses(self):
        self.populate()
        self.lock.write_text("%d\n" % os.getpid())
        before = tree(self.tmp / "app")
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 11, r.stdout)
        self.assertEqual(tree(self.tmp / "app"), before)
        self.assertEqual(self.lock.read_text(), "%d\n" % os.getpid())

    def test_stale_lock_recovered(self):
        self.populate()
        p = subprocess.Popen(["true"])
        p.wait()
        self.lock.write_text("%d\n" % p.pid)
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(self.lock.exists())

    def test_bad_maps_refused_before_writing(self):
        self.populate()
        cases = {
            "kind": "altscreen-u2/config/mibr-menu.conf config/menu/layout.conf symlink\n",
            "fields": "altscreen-u2/config/mibr-menu.conf config/menu/layout.conf\n",
            "dotdot": "altscreen-u2/config/mibr-menu.conf ../../evil file\n",
            "abs": "altscreen-u2/config/mibr-menu.conf /etc/evil file\n",
            "outside": "mibr/state/x state/x file\n",
            "dup": "mibr-v3/data a file\nmibr-kit/boot-count a file\n",
        }
        for name, text in cases.items():
            with self.subTest(name):
                m = self.tmp / ("bad-%s.map" % name)
                m.write_text(text)
                before = tree(self.tmp / "app")
                r = self.run_cmd("run", mapf=m)
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertEqual(tree(self.tmp / "app"), before)
                self.assertFalse(self.lock.exists())

    def test_bad_id(self):
        self.assertEqual(self.run_cmd("run", id_="../x").returncode, 2)
        self.assertEqual(self.run_cmd("run", id_=None).returncode, 2)

    def test_real_map_is_valid(self):
        self.assertTrue(REAL_MAP.exists())
        self.assertEqual(self.run_cmd("plan", id_=None).returncode, 0)
        lines = [l.split() for l in REAL_MAP.read_text().splitlines()
                 if l.strip() and not l.startswith("#")]
        self.assertTrue(all(len(l) in (3, 4) and l[2] in ("file", "presence") for l in lines))
        self.assertNotIn("mibr-kit/disabled", [l[0] for l in lines])
        self.assertIn(["mibr-kit/boot-count", "state/boot/boot-count", "file"], lines)
        self.assertTrue(all(len(l) == 3 or l[3] == "m2-pending" for l in lines))

    def test_boot_count_excluded_from_legacy_checks(self):
        self.populate()
        self.assertEqual(self.run_cmd("run").returncode, 0)
        (self.root / "mibr-kit/boot-count").write_text("3\n")
        self.assertEqual(self.run_cmd("verify").returncode, 0)
        self.assertEqual(self.run_cmd("rollback").returncode, 0)
        self.assertEqual((self.new / "backup/T1/legacy/mibr-kit/boot-count").read_text(), "2\n")

    def test_allowlisted_singles_and_m2_pending(self):
        self.w("mibr-deploy-most20-owned", "")
        self.w("mibr-rgi/rgi.on", "1\n")
        self.w("mibr-parity-status-enabled", "0\n")
        self.w("mibr-unlisted-thing", "no\n")
        r = self.run_cmd("run")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue((self.new / "version/ownership/mibr-deploy-most20-owned").exists())
        self.assertEqual((self.new / "config/features/rgi.on").read_text(), "1\n")
        self.assertEqual((self.new / "config/features/mibr-parity-status-enabled").read_text(), "0\n")
        self.assertFalse((self.new / "mibr-unlisted-thing").exists())
        self.assertNotIn("mibr-unlisted-thing", (self.new / "backup/T1/SHA256SUMS").read_text())

    def test_every_plan_candidate_is_mapped_or_not_migrated(self):
        import json
        out = self.tmp / "plan.json"
        subprocess.run([sys.executable, "-I", "-B", str(REPO / "tools/release/storage_destination_plan.py"),
                        "--json-out", str(out)], check=True, capture_output=True, cwd=str(REPO))
        recs = json.loads(out.read_text())["records"]
        prefix = "/mnt/app/root/"
        cands = [r["current_path_candidate"][len(prefix):] for r in recs
                 if r["source_kind"] != "carplay-registry-group"
                 and r["current_path_candidate"].startswith(prefix)]
        self.assertGreater(len(cands), 40)
        text = REAL_MAP.read_text()
        mapped = {l.split()[0] for l in text.splitlines() if l.strip() and not l.startswith("#")}
        not_mig = {}
        for l in text.splitlines():
            if l.startswith("# not_migrated:"):
                path, _, reason = l[len("# not_migrated:"):].partition("|")
                self.assertTrue(reason.strip(), l)
                not_mig[path.strip()] = reason.strip()
        for c in cands:
            self.assertTrue((c in mapped) != (c in not_mig), "neither or both: " + c)
        marked = [l for l in text.splitlines() if l.endswith("m2-pending")]
        self.assertTrue(marked)

    def test_script_has_no_gnu_only_calls(self):
        text = SCRIPT.read_text()
        for bad in ("cp -a", "readlink -f", "stat -c", "mktemp", "[[", "local "):
            self.assertNotIn(bad, text)


def make(shell):
    return type("Cases_" + shell, (Cases,), {"shell": shell})


for _s in SHELLS:
    globals()["Cases_" + _s] = make(_s)
del Cases  # only the per-shell classes run
Base = None

if __name__ == "__main__":
    unittest.main()
