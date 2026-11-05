"""MU1440 stock-file transforms (preload block, smartphone integrator, usblauncher hook). Host-only.

All fixtures are SYNTHETIC: they reproduce only the line structure the transforms key
on. No OEM bytes are stored. Pinned stock/result SHA-256 values are checked by the
transform itself when it is given the real stock file (owner-local verification).
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PRELOAD = ROOT / "modules/carplay/runtime/isotx2-gate/install_preload.sh"
INTEG = ROOT / "modules/profiles/skoda-mu1440-p4526/integration"
SI_AWK = INTEG / "si-carplay.awk"
LUA_AWK = INTEG / "lua-rgi.awk"
SHELL = os.environ.get("DELTA_SHELL", shutil.which("ksh") or shutil.which("bash") or shutil.which("sh"))
AWK = shutil.which("awk")

STOCK_LINE = ('    MALLOC_ARENA_CACHE_MAXSZ=400000 on -p 15 /eso/bin/apps/displaymanager '
              '${DM_EXTRA_OPTS} ${LVDS2} &')
STARTUP = "#!/bin/sh\necho before\nif true; then\n%s\nfi\necho after\n" % STOCK_LINE

SI_STOCK = (
    '{\n'
    '  "children": [\n'
    '    {\n'
    '      "name": "gal",\n'
    '      "envs":["A=1"],\n'
    '    },\n'
    '    "carplay": {\n'
    '      "path": "/x",\n'
    '      "envs":["B=2"],\n'
    '    },\n'
    '    "carlife": {\n'
    '      "envs":["C=3"],\n'
    '    }\n'
    '  ]\n'
    '}\n'
)

LUA_STOCK = (
    'local function cmd(dev)\n'
    '  if dev.kind == "x" then\n'
    '    return "mm-ipod -d iap2,config=/etc/mm/iap2.cfg,foo=1 -v"\n'
    '  end\n'
    '  return "other"\n'
    'end\n'
)
MARKER = "-- MIBR-RGI"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)


class PreloadTransformTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mu1440-preload-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        helper = self.tmp / "sha256sum"
        helper.write_text('#!/bin/sh\nexec sha256sum "$@"\n')
        helper.chmod(0o755)
        self.env = dict(os.environ, MIBR_SHA256=str(helper))
        self.stock = self.tmp / "stock"
        self.stock.write_text(STARTUP)

    def emit(self, mode, src, dst):
        return run([SHELL, str(PRELOAD), mode, str(src), str(dst)], env=self.env)

    def test_guard_gate_block_forward_and_reverse_byte_exact(self):
        out = self.tmp / "gg"
        r = self.emit("--emit-guard-gate", self.stock, out)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = out.read_text()
        self.assertEqual(text.count("# MIBR ISOTX2 GATE BEGIN"), 1)
        self.assertEqual(text.count("# MIBR ISOTX2 GATE END"), 1)
        self.assertEqual(text.count("libmibr_isotx2_guard.so:/mnt/app/eso/lib/libmibr_isotx2_gate.so"), 1)
        self.assertEqual(text.count(STOCK_LINE), 1)  # exact stock fallback inside the block
        self.assertIn(b"pinned_match=n/a", r.stdout)  # synthetic input is not the pinned stock
        back = self.tmp / "back"
        r = self.emit("--emit-stock", out, back)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(back.read_bytes(), self.stock.read_bytes())

    def test_deterministic_and_idempotent_generation(self):
        a, b = self.tmp / "a", self.tmp / "b"
        self.assertEqual(self.emit("--emit-guard-gate", self.stock, a).returncode, 0)
        self.assertEqual(self.emit("--emit-guard-gate", self.stock, b).returncode, 0)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        # Re-applying to an already marked file is refused (never nests blocks).
        r = self.emit("--emit-guard-gate", a, self.tmp / "again")
        self.assertEqual(r.returncode, 41)

    def test_reverse_refuses_without_marker_or_with_stock_line_outside(self):
        self.assertEqual(self.emit("--emit-stock", self.stock, self.tmp / "o").returncode, 42)
        out = self.tmp / "gg"
        self.emit("--emit-guard-gate", self.stock, out)
        extra = self.tmp / "extra"
        extra.write_text(out.read_text() + STOCK_LINE + "\n")
        self.assertEqual(self.emit("--emit-stock", extra, self.tmp / "o2").returncode, 42)

    def test_foreign_marker_content_is_not_silently_replaced(self):
        out = self.tmp / "gg"
        self.emit("--emit-guard-gate", self.stock, out)
        text = out.read_text().replace("echo after", "    # MIBR ISOTX2 GATE BEGIN\necho after")
        bad = self.tmp / "bad"
        bad.write_text(text)
        self.assertEqual(self.emit("--emit-stock", bad, self.tmp / "o").returncode, 42)

    def test_generation_needs_exactly_one_stock_line(self):
        none = self.tmp / "none"
        none.write_text("#!/bin/sh\necho hi\n")
        self.assertEqual(self.emit("--emit-guard-gate", none, self.tmp / "o").returncode, 40)
        two = self.tmp / "two"
        two.write_text(STARTUP + STOCK_LINE + "\n")
        self.assertEqual(self.emit("--emit-guard-gate", two, self.tmp / "o").returncode, 40)

    def test_pins_are_declared(self):
        text = PRELOAD.read_text()
        self.assertIn("EXPECTED_STOCK=869a64efbb3c0423951c2c31899743f4c635871b8c81236a459df36ee41793b8", text)
        self.assertIn("EXPECTED_GUARDGATE=1ef33f6fa14dd2f19b23dfd6249c07b4ae478c3f73d3f0151639ace5f22fcd22", text)


@unittest.skipUnless(AWK, "awk not available")
class SmartphoneIntegratorTests(unittest.TestCase):
    def transform(self, text, *extra):
        return run([AWK, *extra, "-f", str(SI_AWK)], input=text.encode())

    def test_only_carplay_envs_line_changes(self):
        r = self.transform(SI_STOCK)
        self.assertEqual(r.returncode, 0, r.stderr)
        old, new = SI_STOCK.splitlines(), r.stdout.decode().splitlines()
        self.assertEqual(len(old), len(new))
        changed = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
        self.assertEqual(changed, [old.index('      "envs":["B=2"],')])
        line = new[changed[0]]
        self.assertTrue(line.startswith('      "envs":["LD_PRELOAD=/mnt/app/eso/lib/libmibr_carplay111.so"'))
        self.assertEqual(line.count('", "') + 1, 10)  # exactly ten env entries
        self.assertIn("ALTSCREEN111_WIDTH=1010", line)
        self.assertIn("ALTSCREEN111_URL=maps:/car/instrumentcluster", line)

    def test_values_overridable_and_deterministic(self):
        a = self.transform(SI_STOCK, "-v", "width=800")
        b = self.transform(SI_STOCK, "-v", "width=800")
        self.assertEqual(a.stdout, b.stdout)
        self.assertIn(b"ALTSCREEN111_WIDTH=800", a.stdout)

    def test_refuses_patched_and_missing_carplay(self):
        once = self.transform(SI_STOCK).stdout.decode()
        self.assertEqual(self.transform(once).returncode, 6)
        self.assertEqual(self.transform('{"children":[{"envs":["A=1"],\n}]}\n').returncode, 3)


@unittest.skipUnless(AWK, "awk not available")
class LuaRgiTests(unittest.TestCase):
    def transform(self, text):
        return run([AWK, "-f", str(LUA_AWK)], input=text.encode())

    def test_exactly_one_marked_line_and_grep_v_restores_stock(self):
        r = self.transform(LUA_STOCK)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout.decode()
        lines = out.splitlines()
        self.assertEqual(len(lines), len(LUA_STOCK.splitlines()) + 1)
        marked = [l for l in lines if MARKER in l]
        self.assertEqual(len(marked), 1)
        self.assertTrue(marked[0].endswith(" end " + MARKER))
        self.assertIn("config=/dev/shmem/mibr-rgi-iap2.cfg", marked[0])
        self.assertNotIn("/etc/mm/iap2.cfg", marked[0])
        self.assertIn('/mnt/app/root/mibr/bin/mm-ipod-rgi -d iap2,', marked[0])
        # additive: grep -v of the marker restores stock byte-exactly
        restored = "".join(l + "\n" for l in lines if MARKER not in l)
        self.assertEqual(sha(restored.encode()), sha(LUA_STOCK.encode()))
        # marked line sits directly before the stock line
        i = lines.index(marked[0])
        self.assertIn("config=/etc/mm/iap2.cfg", lines[i + 1])

    def test_grep_v_with_real_grep(self):
        out = self.transform(LUA_STOCK).stdout
        r = run(["grep", "-v", "--", MARKER], input=out)
        self.assertEqual(r.stdout, LUA_STOCK.encode())

    def test_deterministic(self):
        self.assertEqual(self.transform(LUA_STOCK).stdout, self.transform(LUA_STOCK).stdout)

    def test_refuses_foreign_or_existing_marker(self):
        patched = self.transform(LUA_STOCK).stdout.decode()
        self.assertEqual(self.transform(patched).returncode, 4)
        foreign = LUA_STOCK + "-- MIBR-RGI hand install\n"
        self.assertEqual(self.transform(foreign).returncode, 4)

    def test_refuses_missing_or_ambiguous_stock_line(self):
        self.assertEqual(self.transform("return \"other\"\n").returncode, 3)
        self.assertEqual(self.transform(LUA_STOCK + LUA_STOCK).returncode, 3)


if __name__ == "__main__":
    unittest.main()
