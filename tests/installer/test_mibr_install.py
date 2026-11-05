"""Host tests for installer/mibr-install.ksh (check/apply/uninstall/rollback).

Everything is synthetic: a fake unit tree under a temp dir, synthetic "stock" files
(never OEM bytes), a synthetic package sealed with PACKAGE.sha256."""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROFILE = "skoda-mu1440-p4526"
TRAIN = "SYNTHETIC_TRAIN_A"
JXE = b"synthetic-jxe-bytes\n"
STARTUP_STOCK = b"#!/bin/sh\necho synthetic stock startup\n"
LSD_STOCK = (b"#!/bin/sh\n# synthetic lsd.sh\nDSITRACER_ACTIVATED=no\nBASE_DIR=/x\n"
             b"# FOREIGN BLOCK BEGIN\necho foreign\n# FOREIGN BLOCK END\n$J9 -jar x\n")
AWK = b'{ print } END { print "# patched-by-test" }\n'
INSTALLER_FILES = ["mibr-install.ksh", "mibr-uninstall.ksh", "mibr-status.ksh", "select-profile.ksh",
                   "lib/mibr-common.ksh", "lib/migrate-root.ksh", "config/root-migration.list",
                   "config/lsd-block.txt", "config/legacy-markers.list", "config/known-lsd-blocks.list"]
SHA_WRAPPER = ("#!/usr/bin/env python3\nimport hashlib,sys\n"
               "print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()+'  '+sys.argv[1])\n")


def sh(b):
    return hashlib.sha256(b).hexdigest()


def tree(path):
    out = {}
    for p in sorted(Path(path).rglob("*")):
        rel = str(p.relative_to(path))
        out[rel] = ("d", None) if p.is_dir() else ("f", sh(p.read_bytes()), p.stat().st_mode & 0o777)
    return out


class Base(unittest.TestCase):
    enabled = "1"
    train_listed = TRAIN
    shell = "sh"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mibrinst-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.unit = self.tmp / "unit"
        self.app = self.unit / "app"
        self.eso = self.app / "eso"
        self.system = self.unit / "system"
        self.ifs = self.unit / "ifs"
        self.work = self.tmp / "tmpd"
        self.work.mkdir()
        self.pkg = self.tmp / "pkg"
        self.lock = self.tmp / "install.lock"
        self.train_file = self.tmp / "train.sh"
        self.set_train(TRAIN)
        self.build_unit()
        self.build_package()

    # ---- fixtures
    def set_train(self, t):
        self.train_file.write_text("#!/bin/sh\necho %s\n" % t)
        self.train_file.chmod(0o755)

    def wr(self, path, data, mode=0o644):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
        path.chmod(mode)

    def build_unit(self):
        self.wr(self.ifs / "lsd.jxe", JXE)
        self.wr(self.system / "etc/boot/startup.sh", STARTUP_STOCK, 0o755)
        self.wr(self.eso / "hmi/lsd/lsd.sh", LSD_STOCK, 0o755)
        (self.app / "root").mkdir(parents=True)

    def build_package(self, extra=None):
        p = self.pkg
        shutil.rmtree(p, True)
        files = {}
        for rel in INSTALLER_FILES:
            files["installer/" + rel] = (REPO / "installer" / rel).read_bytes()
        files["installer/bin/sha256sum"] = SHA_WRAPPER.encode()
        self.patched = STARTUP_STOCK + b"# patched-by-test\n"
        files["installer/config/profiles.list"] = (
            "# test\n%s %s %s %s\n" % (sh(JXE), PROFILE, self.train_listed, self.enabled)).encode()
        files["common/carplay/bin/alt-tool"] = b"binary-v1\n"
        files["common/broker/scripts/boot-guard.ksh"] = b"#!/bin/ksh\nexit 0\n"
        files["common/menu/config/mibr-menu.conf"] = b"menu-default\n"
        root = "profiles/%s/" % PROFILE
        files[root + "integration/si.awk"] = AWK
        files[root + "integration/variants.list"] = (
            "# target stock patched transform transform_sha mode\n"
            "/mnt/system/etc/boot/startup.sh %s %s %sintegration/si.awk %s 755\n"
            % (sh(STARTUP_STOCK), sh(self.patched), root, sh(AWK))).encode()
        files[root + "integration/known-states.list"] = b"# header only\n"
        files.update(extra or {})
        self.files = files
        self.seal()

    def seal(self, files=None):
        files = files if files is not None else self.files
        shutil.rmtree(self.pkg, True)
        for rel, data in files.items():
            mode = 0o755 if rel.endswith(("ksh", "sha256sum")) else 0o644
            self.wr(self.pkg / rel, data, mode)
        lines = "".join("%s  %s\n" % (sh(d), r) for r, d in sorted(files.items()))
        self.wr(self.pkg / "PACKAGE.sha256", lines)

    # ---- running
    def env(self, extra=None):
        e = dict(os.environ, MIBR_APP=str(self.app), MIBR_ESO=str(self.eso), MIBR_SYSTEM=str(self.system),
                 MIBR_IFS=str(self.ifs), MIBR_NO_MOUNT="1", MIBR_LOCK_FILE=str(self.lock),
                 MIBR_TRAIN_CMD=str(self.train_file), TMPDIR=str(self.work), MIBR_FREE_KB="100000")
        for k in ("MIBR_INSTALL_FAIL_AT", "MIBR_MIGRATE_FAIL_AT", "MIBR_SHA256"):
            e.pop(k, None)
        e.update(extra or {})
        return e

    def run_inst(self, *args, env=None, script="mibr-install.ksh"):
        return subprocess.run([self.shell, str(self.pkg / "installer" / script), *args], env=self.env(env),
                              capture_output=True, text=True, timeout=120)

    def apply(self, **kw):
        return self.run_inst("--apply", **kw)

    @property
    def new(self):
        return self.app / "root/mibr"

    def unit_tree(self):
        return tree(self.unit)

    def lsd(self):
        return (self.eso / "hmi/lsd/lsd.sh").read_bytes()

    def startup(self):
        return (self.system / "etc/boot/startup.sh").read_bytes()

    def assertNoLeftovers(self):
        self.assertFalse(self.lock.exists())


class TestInstall(Base):
    def test_fresh_install(self):
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        n = self.new
        self.assertEqual((n / "bin/alt-tool").read_bytes(), b"binary-v1\n")
        self.assertTrue(os.access(n / "bin/alt-tool", os.X_OK))
        self.assertEqual((n / "scripts/boot-guard.ksh").read_bytes(), b"#!/bin/ksh\nexit 0\n")
        self.assertEqual((n / "config/mibr-menu.conf").read_bytes(), b"menu-default\n")
        self.assertEqual(self.startup(), self.patched)
        lsd = self.lsd().decode()
        self.assertEqual(lsd.count("# MIBR-RUNTIME BEGIN"), 1)
        self.assertEqual(lsd.count("# MIBR-RUNTIME END"), 1)
        self.assertIn("/mnt/app/root/mibr/scripts/boot-guard.ksh check", lsd)
        self.assertIn("DSITRACER_ACTIVATED=yes", lsd)
        self.assertIn("# FOREIGN BLOCK BEGIN\necho foreign\n# FOREIGN BLOCK END\n", lsd)
        self.assertLess(lsd.index("MIBR-RUNTIME END"), lsd.index("$J9 "))
        self.assertEqual(lsd.count("$J9 "), 1)
        v = n / "version"
        props = (v / "installed-version.properties").read_text()
        self.assertIn("product=MIBR-CarPlay", props)
        self.assertIn("target_profile_id=" + PROFILE, props)
        self.assertIn("state=complete", next(v.glob("install-p*.receipt")).read_text())
        self.assertTrue((v / "installed.manifest").is_file())
        self.assertTrue((v / "components.manifest").read_text().startswith("MIBR_COMPONENTS/1"))
        self.assertEqual(len(list((v / "ownership").glob("*.owned"))), 2)
        self.assertEqual((n / "config/features/mibr-cpvc.enabled").read_text(), "1\n")
        self.assertEqual((n / "config/features/mibr-parity-drive.enabled").read_text(), "1\n")
        bk = next((n / "backup").glob("p*/oem"))
        self.assertEqual((bk / "pre/mnt/system/etc/boot/startup.sh").read_bytes(), STARTUP_STOCK)
        self.assertEqual((bk / "pre/mnt/app/eso/hmi/lsd/lsd.sh").read_bytes(), LSD_STOCK)
        self.assertIn("REBOOT_REQUIRED=YES", r.stdout)
        self.assertNoLeftovers()
        self.assertTrue((self.pkg / "mibr-install.log").is_file())
        st = self.run_inst(script="mibr-status.ksh")
        self.assertEqual(st.returncode, 0, st.stdout)
        self.assertIn("drift=0", st.stdout)

    def test_check_writes_nothing(self):
        before = self.unit_tree()
        r = self.run_inst("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("CHECK_OK", r.stdout)
        self.assertEqual(before, self.unit_tree())
        r2 = self.run_inst()  # default is check
        self.assertEqual(r2.returncode, 0)
        self.assertEqual(before, self.unit_tree())
        self.assertFalse((self.pkg / "mibr-install.log").exists())

    def test_idempotent_second_apply(self):
        self.assertEqual(self.apply().returncode, 0)
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(before, self.unit_tree())

    def test_foreign_target_blocks(self):
        self.wr(self.system / "etc/boot/startup.sh", b"someone else's startup\n", 0o755)
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 10, r.stdout)
        self.assertIn("foreign state", r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_foreign_payload_blocks(self):
        self.wr(self.new / "bin/alt-tool", b"foreign binary\n", 0o755)
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 10, r.stdout)
        self.assertIn("foreign file", r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_unknown_jxe_no_write(self):
        self.wr(self.ifs / "lsd.jxe", b"other firmware\n")
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_train_mismatch_no_write(self):
        self.set_train("SOMETHING_ELSE")
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_train_unreadable_no_write(self):
        self.set_train("")
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_disabled_profile_no_write(self):
        self.enabled = "0"
        self.build_package()
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_package_tamper_no_write(self):
        before = self.unit_tree()
        (self.pkg / "common/carplay/bin/alt-tool").write_bytes(b"tampered\n")
        r = self.apply()
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertIn("PACKAGE_MISMATCH", r.stdout)
        self.assertEqual(before, self.unit_tree())
        self.build_package()
        (self.pkg / "common/carplay/bin/extra").write_bytes(b"unlisted\n")
        r = self.apply()
        self.assertEqual(r.returncode, 4)
        self.assertIn("PACKAGE_UNLISTED", r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_transform_wrong_result_blocks(self):
        files = dict(self.files)
        files["profiles/%s/integration/si.awk" % PROFILE] = b'{ print } END { print "# other" }\n'
        root = "profiles/%s/" % PROFILE
        files[root + "integration/variants.list"] = (
            "/mnt/system/etc/boot/startup.sh %s %s %sintegration/si.awk %s 755\n"
            % (sh(STARTUP_STOCK), sh(self.patched), root, sh(files[root + "integration/si.awk"]))).encode()
        self.seal(files)
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 10, r.stdout)
        self.assertIn("wrong hash", r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_lsd_problems_block(self):
        before_cases = [
            (LSD_STOCK + b"$J9 -again\n", "J9"),
            (LSD_STOCK.replace(b"$J9", b"# MIBR NAVIGNORE\n$J9"), "development-install marker"),
            (LSD_STOCK.replace(b"$J9", b"# MIBR-KIT BEGIN 1\necho unknown legacy\n# MIBR-KIT END\n$J9"), "ownership proof"),
            (LSD_STOCK.replace(b"$J9", b"# MIBR-RUNTIME BEGIN x\n$J9"), "broken"),
        ]
        for data, needle in before_cases:
            self.wr(self.eso / "hmi/lsd/lsd.sh", data, 0o755)
            before = self.unit_tree()
            r = self.apply()
            self.assertEqual(r.returncode, 10, (needle, r.stdout))
            self.assertIn(needle, r.stdout)
            self.assertEqual(before, self.unit_tree())

    def test_single_writer_flag_blocks(self):
        before = self.unit_tree()
        r = self.apply_with("--authorize-single-writer")
        self.assertEqual(r.returncode, 10, r.stdout)
        self.assertEqual(before, self.unit_tree())

    def apply_with(self, *a):
        return self.run_inst("--apply", *a)

    def test_user_config_never_overwritten(self):
        self.wr(self.new / "config/mibr-menu.conf", b"user edited\n")
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual((self.new / "config/mibr-menu.conf").read_bytes(), b"user edited\n")
        self.assertEqual(self.run_inst("--uninstall").returncode, 0)
        self.assertEqual((self.new / "config/mibr-menu.conf").read_bytes(), b"user edited\n")

    def test_lock_busy(self):
        self.lock.write_text(str(os.getpid()))
        before = self.unit_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 11)
        self.assertEqual(before, self.unit_tree())
        self.assertTrue(self.lock.exists())

    def test_bad_usage(self):
        self.assertEqual(self.run_inst("--bogus").returncode, 2)
        self.assertEqual(self.run_inst("--purge").returncode, 2)
        self.assertEqual(self.run_inst("--rollback").returncode, 2)


class TestInterrupted(Base):
    POINTS = ["after_migrate", "after_backup", "payload_mid", "after_payload", "variants_mid",
              "after_variants", "after_defaults", "after_receipts", "before_lsd_write", "after_lsd", "final"]

    def test_interrupt_each_step_then_rerun_matches_reference(self):
        self.assertEqual(self.apply().returncode, 0)
        reference = tree(self.new)
        ref_lsd, ref_startup = self.lsd(), self.startup()
        points = [("MIBR_INSTALL_FAIL_AT", p) for p in self.POINTS] + \
                 [("MIBR_MIGRATE_FAIL_AT", p) for p in ("c", "d", "e", "f", "h1", "h2")]
        for key, point in points:
            with self.subTest(point=point):
                self.tearDown_unit()
                r = self.apply(env={key: point})
                self.assertEqual(r.returncode, 99 if key == "MIBR_INSTALL_FAIL_AT" else 20, (point, r.stdout))
                self.assertNoLeftovers()
                if point not in ("after_lsd", "final"):
                    self.assertNotIn("MIBR_INSTALL=OK", r.stdout)
                # the hook is switched last: before that lsd.sh is untouched
                if point not in ("before_lsd_write",) and point not in ("after_lsd", "final"):
                    self.assertEqual(self.lsd(), LSD_STOCK, point)
                r2 = self.apply()
                self.assertEqual(r2.returncode, 0, (point, r2.stdout))
                self.assertEqual(tree(self.new), reference, point)
                self.assertEqual(self.lsd(), ref_lsd)
                self.assertEqual(self.startup(), ref_startup)

    def tearDown_unit(self):
        shutil.rmtree(self.unit, True)
        self.build_unit()
        self.lock.unlink(missing_ok=True)


class TestUninstallRollback(Base):
    def test_uninstall_restores_stock_exactly(self):
        pre = self.unit_tree()
        self.assertEqual(self.apply().returncode, 0)
        r = self.run_inst("--uninstall")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.startup(), STARTUP_STOCK)
        self.assertEqual(self.lsd(), LSD_STOCK)
        self.assertFalse((self.new / "bin").exists())
        self.assertFalse((self.new / "scripts").exists())
        self.assertFalse(list((self.new / "version/ownership").glob("*")) if (self.new / "version/ownership").exists() else False)
        self.assertTrue(list((self.new / "backup").glob("p*/oem/MANIFEST")))
        # second uninstall is a no-op
        self.assertEqual(self.run_inst("--uninstall").returncode, 0)
        r = self.run_inst("--uninstall", "--purge")
        self.assertEqual(r.returncode, 0)
        self.assertFalse(self.new.exists())
        post = self.unit_tree()
        self.assertEqual(pre, {k: v for k, v in post.items() if k in pre})

    def test_uninstall_blocks_on_foreign_modification(self):
        self.assertEqual(self.apply().returncode, 0)
        self.wr(self.system / "etc/boot/startup.sh", b"changed later\n", 0o755)
        before = self.unit_tree()
        r = self.run_inst("--uninstall")
        self.assertEqual(r.returncode, 10, r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_uninstall_interrupted_rerun(self):
        self.assertEqual(self.apply().returncode, 0)
        for point in ("un_after_lsd", "un_after_variants"):
            r = self.run_inst("--uninstall", env={"MIBR_INSTALL_FAIL_AT": point})
            self.assertEqual(r.returncode, 99, r.stdout)
            r = self.run_inst("--uninstall")
            self.assertEqual(r.returncode, 0, (point, r.stdout))
            self.assertEqual(self.startup(), STARTUP_STOCK)
            self.assertEqual(self.lsd(), LSD_STOCK)
            self.assertEqual(self.apply().returncode, 0)

    def test_uninstall_leaves_unproven_block(self):
        self.assertEqual(self.apply().returncode, 0)
        for f in (self.new / "version/ownership").glob("lsd-block*"):
            f.unlink()
        lsd = self.lsd()
        r = self.run_inst("--uninstall")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("left untouched", r.stdout)
        self.assertEqual(self.lsd(), lsd)

    def legacy_unit(self):
        self.wr(self.app / "root/altscreen-u2/config/mibr-menu-language.conf", "MAGIC lang=de\n")
        self.wr(self.app / "root/mibr-kit/boot-count", "2\n")
        self.wr(self.app / "root/mibr-kit/disabled", "boot loop detected\n")
        self.wr(self.app / "root/mibr-kit/installed.manifest", "abc /x\n")
        legacy = LSD_STOCK.replace(b"$J9", b"# MIBR-KIT BEGIN 1.4.0\necho legacy hook\n# MIBR-KIT END\n$J9") \
            .replace(b"DSITRACER_ACTIVATED=no", b"DSITRACER_ACTIVATED=yes")
        self.wr(self.eso / "hmi/lsd/lsd.sh", legacy, 0o755)
        return legacy

    def legacy_tree(self):
        return {k: v for k, v in tree(self.app / "root").items() if not k.startswith("mibr/") and k != "mibr"}

    def test_upgrade_from_legacy_preserves_disabled_and_trees(self):
        legacy = self.legacy_unit()
        before = self.legacy_tree()
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.legacy_tree(), before)
        dis = (self.new / "state/boot/disabled").read_text()
        self.assertTrue(dis.startswith("migrated-disabled"), dis)
        self.assertEqual((self.new / "config/menu/language.conf").read_text(), "MAGIC lang=de\n")
        lsd = self.lsd().decode()
        self.assertEqual(lsd.count("MIBR-KIT"), 0)
        self.assertEqual(lsd.count("# MIBR-RUNTIME BEGIN"), 1)
        self.assertNotIn("legacy hook", lsd)
        self.assertFalse((self.new / "config/features/mibr-cpvc.enabled").exists())  # no defaults on upgrade
        self.assertIn("legacy-install-present", (self.new / "version/install-defaults.receipt").read_text())
        # rollback restores the legacy hook bytes exactly, legacy trees untouched
        iid = next((self.new / "version").glob("install-p*.receipt")).name[len("install-"):-len(".receipt")]
        r = self.run_inst("--rollback", iid)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.lsd(), legacy)
        self.assertEqual(self.startup(), STARTUP_STOCK)
        self.assertEqual(self.legacy_tree(), before)
        self.assertEqual(list((self.new / "version/ownership").glob("*.owned")), [])
        self.assertIn("state=rolled-back", (self.new / "version" / ("install-%s.receipt" % iid)).read_text())
        # idempotent
        self.assertEqual(self.run_inst("--rollback", iid).returncode, 0)

    def test_rollback_blocks_when_changed(self):
        self.assertEqual(self.apply().returncode, 0)
        iid = next((self.new / "version").glob("install-p*.receipt")).name[len("install-"):-len(".receipt")]
        self.wr(self.eso / "hmi/lsd/lsd.sh", self.lsd() + b"# later edit\n", 0o755)
        before = self.unit_tree()
        r = self.run_inst("--rollback", iid)
        self.assertEqual(r.returncode, 10, r.stdout)
        self.assertEqual(before, self.unit_tree())

    def test_rollback_unknown_id(self):
        self.assertEqual(self.run_inst("--rollback", "nope").returncode, 10)

    def test_legacy_marker_uninstall_by_receipt(self):
        self.assertEqual(self.apply().returncode, 0)
        lsd = self.lsd().replace(b"# MIBR-RUNTIME", b"# MIBR-KIT")
        self.wr(self.eso / "hmi/lsd/lsd.sh", lsd, 0o755)
        # the receipt still names our block, so the old marker name is recognised
        r = self.run_inst("--uninstall")
        # lsd.sh no longer equals what the install wrote, startup.sh is still ours: lsd is removed by receipt
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn(b"MIBR-KIT", self.lsd())
        self.assertEqual(self.startup(), STARTUP_STOCK)

    def test_legacy_marker_uninstall_by_known_content(self):
        self.assertEqual(self.apply().returncode, 0)
        lsd = self.lsd().replace(b"# MIBR-RUNTIME", b"# MIBR-KIT")
        self.wr(self.eso / "hmi/lsd/lsd.sh", lsd, 0o755)
        body = b"".join(l + b"\n" for l in lsd.split(b"# MIBR-KIT BEGIN")[1].split(b"\n# MIBR-KIT END")[0].split(b"\n")[1:])
        for f in (self.new / "version/ownership").glob("lsd-block*"):
            f.unlink()
        kl = self.pkg / "installer/config/known-lsd-blocks.list"
        files = dict(self.files)
        files["installer/config/known-lsd-blocks.list"] = kl.read_bytes() + ("%s test-known\n" % sh(body)).encode()
        self.seal(files)
        r = self.run_inst("--uninstall")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn(b"MIBR-KIT", self.lsd())

    def test_upgrade_from_owned_previous_variant(self):
        self.assertEqual(self.apply().returncode, 0)
        # package v2: different patch result for the same stock
        awk2 = b'{ print } END { print "# patched-v2" }\n'
        patched2 = STARTUP_STOCK + b"# patched-v2\n"
        root = "profiles/%s/" % PROFILE
        files = dict(self.files)
        files[root + "integration/si.awk"] = awk2
        files[root + "integration/variants.list"] = (
            "/mnt/system/etc/boot/startup.sh %s %s %sintegration/si.awk %s 755\n"
            % (sh(STARTUP_STOCK), sh(patched2), root, sh(awk2))).encode()
        files["common/carplay/bin/alt-tool"] = b"binary-v2\n"
        self.seal(files)
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.startup(), patched2)
        self.assertEqual((self.new / "bin/alt-tool").read_bytes(), b"binary-v2\n")
        self.assertEqual(self.run_inst("--uninstall").returncode, 0)
        self.assertEqual(self.startup(), STARTUP_STOCK)
        self.assertEqual(self.lsd(), LSD_STOCK)


class TestManifestMode(Base):
    def test_payload_manifest_is_used(self):
        data = b"manifest-file\n"
        files = dict(self.files)
        files["common/carplay/bin/alt-tool"] = b"binary-v1\n"
        files["installer/config/payload.manifest"] = (
            "# sha256 mode target source\n%s 0755 /mnt/app/root/mibr/bin/from-manifest common/carplay/bin/alt-tool\n"
            % sh(b"binary-v1\n")).encode()
        self.seal(files)
        r = self.apply()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.new / "bin/from-manifest").read_bytes(), b"binary-v1\n")
        self.assertFalse((self.new / "bin/alt-tool").exists())

    def test_manifest_hash_mismatch_blocks(self):
        files = dict(self.files)
        files["installer/config/payload.manifest"] = (
            "%s 0755 /mnt/app/root/mibr/bin/x common/carplay/bin/alt-tool\n" % sh(b"wrong")).encode()
        self.seal(files)
        before = self.unit_tree()
        self.assertEqual(self.apply().returncode, 10)
        self.assertEqual(before, self.unit_tree())

    def test_manifest_target_outside_roots_blocks(self):
        files = dict(self.files)
        files["installer/config/payload.manifest"] = (
            "%s 0755 /mnt/system/etc/evil common/carplay/bin/alt-tool\n" % sh(b"binary-v1\n")).encode()
        self.seal(files)
        self.assertEqual(self.apply().returncode, 10)


if __name__ == "__main__":
    unittest.main()
