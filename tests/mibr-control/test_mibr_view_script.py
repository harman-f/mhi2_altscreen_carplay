"""Host test of control/scripts/mibr-view.ksh (r55: safe area follows the cockpit view)."""
import os
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
SCRIPT = HERE / "runtime" / "mibr-control" / "mibr-view.ksh"


class Box:
    def __init__(self, tmp, sh):
        self.tmp, self.sh = tmp, sh
        self.cli = tmp / "cli"
        self.calls = tmp / "calls"
        self.area = tmp / "area"
        self.cli.write_text('#!/bin/sh\necho "$@" >> %s\n'
                            'while [ $# -gt 0 ]; do [ "$1" = --value ] && echo "$2" > %s; shift; done\n'
                            % (self.calls.as_posix(), self.area.as_posix()))
        self.cli.chmod(self.cli.stat().st_mode | stat.S_IEXEC)
        self.calls.write_text("")
        self.env = dict(os.environ, MIBR_VIEW_DIR=str(tmp / "d"), MIBR_VIEW_NOMOUNT="1", MIBR_VIEW_CLI=str(self.cli),
                        MIBR_VIEW_POS=str(tmp / "pos"), MIBR_VIEW_GEN=str(tmp / "gen"), MIBR_VIEW_LOCK=str(tmp / "lock"),
                        MIBR_VIEW_AREA=str(self.area), MIBR_VIEW_LOG=str(tmp / "log"), MIBR_VIEW_DEBOUNCE="1",
                        MIBR_VIEW_SHELL=os.path.basename(sh).split(".")[0], MIBR_VIEW_CLI_PREFIX=os.path.basename(sh).split(".")[0])
        (tmp / "d").mkdir()

    def run(self, *args):
        p = subprocess.run([self.sh, str(SCRIPT), *args], capture_output=True, text=True, env=self.env, timeout=20)
        return p.returncode, dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)

    def cli_values(self):
        return [l.split("--value")[1].split()[0] for l in self.calls.read_text().splitlines()]


class ViewScript(unittest.TestCase):
    def shells(self):
        return [s for s in (shutil.which("bash"), shutil.which("ksh")) if s]

    def test_defaults_and_validation(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                rc, o = b.run("get")
                self.assertEqual((rc, o["follow"], o["sport"], o["m0"], o["m1"], o["m4"], o["rs"], o["pos"], o["result"]),
                                 (0, "0", "1", "1", "0", "2", "0", "0", "OK"))
                for k, v in (("follow", "2"), ("sport", "x"), ("m0", "3"), ("pos", "5"), ("bogus", "1"), ("pos", "1;rm")):
                    rc, o = b.run("set", k, v)
                    self.assertEqual((rc, o["result"]), (1, "BAD_VALUE"), (k, v))
                self.assertEqual(b.cli_values(), [])

    def test_counts_without_follow_and_never_touches_cli(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                seen = []
                for _ in range(7):
                    self.assertEqual(b.run("step")[0], 0)
                    seen.append((Path(d) / "pos").read_text().strip())
                self.assertEqual(seen, ["1", "2", "3", "4", "0", "1", "2"])
                self.assertEqual(b.cli_values(), [])

    def test_follow_sets_area_for_map_views_only(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                self.assertEqual(b.run("set", "follow", "1")[0], 0)
                self.assertEqual(b.cli_values(), ["1"])            # pos 0 = Voll -> area 1, applied on switch-on
                for _ in range(5):
                    b.run("step")
                # positions 1..4,0: Wide->0, Reichweite none, Tacho none, Center->2, Voll->1
                self.assertEqual(b.cli_values(), ["1", "0", "2", "1"])
                args = b.calls.read_text().splitlines()[0]
                self.assertIn("set --key viewarea.selected --value 1 --layer temp", args)

    def test_sport_off_skips_speedometer_and_mapping_is_used(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                b.run("set", "sport", "0")
                b.run("set", "follow", "1")
                b.run("set", "m4", "1")                           # Center view uses area Voll
                b.calls.write_text("")
                seen = []
                for _ in range(5):
                    b.run("step")
                    seen.append((Path(d) / "pos").read_text().strip())
                self.assertEqual(seen, ["1", "2", "4", "0", "1"])
                # Wide->0, Reichweite none, Center->1 (mapped), Voll->1 (area unchanged, no call), Wide->0
                self.assertEqual(b.cli_values(), ["0", "1", "0"])

    def test_resync_sets_position_and_applies(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                b.run("set", "follow", "1")
                b.calls.write_text("")
                rc, o = b.run("set", "pos", "4")
                self.assertEqual((rc, o["pos"], o["result"]), (0, "4", "OK"))
                self.assertEqual(b.cli_values(), ["2"])
                self.assertEqual((Path(d) / "d" / "pos").read_text().strip(), "4")
                b.run("set", "sport", "0")
                rc, o = b.run("set", "pos", "3")
                self.assertEqual((rc, o["result"]), (1, "BAD_VALUE"))

    def test_resync_long_press_sets_the_view_after_the_chosen_one(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                rc, o = b.run("set", "rs", "0")                       # Voll chosen (default)
                self.assertEqual((rc, o["rs"]), (0, "0"))
                for _ in range(3):
                    b.run("step")                                     # drifted: counter says 3
                rc, o = b.run("resync")
                self.assertEqual((rc, o["pos"], o["result"]), (0, "1", "OK"))   # long press stepped Voll -> Wide
                self.assertEqual((Path(d) / "d" / "pos").read_text().strip(), "1")
                b.run("set", "rs", "4")                               # Center chosen: next view is Voll
                rc, o = b.run("resync")
                self.assertEqual(o["pos"], "0")
                b.run("set", "rs", "2")                               # Reichweite chosen: next is Sporttacho ...
                self.assertEqual(b.run("resync")[1]["pos"], "3")
                b.run("set", "sport", "0")                            # ... or Center when the car has none
                self.assertEqual(b.run("resync")[1]["pos"], "4")
                self.assertEqual(b.run("set", "rs", "5")[1]["result"], "BAD_VALUE")

    def test_resync_applies_the_area_when_follow_is_on(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                b.run("set", "follow", "1")
                b.run("set", "rs", "0")
                b.calls.write_text("")
                b.run("resync")                                       # position 1 = Wide -> area 0
                self.assertEqual(b.cli_values(), ["0"])

    def test_sport_off_on_speedometer_moves_to_center(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                b.run("set", "pos", "3")
                rc, o = b.run("set", "sport", "0")
                self.assertEqual((rc, o["pos"]), (0, "4"))

    def test_debounced_persist_writes_flash_copy_once(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                for _ in range(3):
                    b.run("step")
                self.assertFalse((Path(d) / "d" / "pos").exists())      # nothing written during the burst
                time.sleep(2.5)
                self.assertEqual((Path(d) / "d" / "pos").read_text().strip(), "3")
                log = (Path(d) / "log").read_text()
                self.assertEqual(log.count("PERSIST"), 1)

    def test_pos_survives_restart_from_flash_copy(self):
        for sh in self.shells():
            with self.subTest(shell=sh), tempfile.TemporaryDirectory() as d:
                b = Box(Path(d), sh)
                b.run("set", "pos", "2")
                (Path(d) / "pos").unlink()                              # RAM copy gone after a restart
                rc, o = b.run("get")
                self.assertEqual(o["pos"], "2")
                b.run("step")
                self.assertEqual((Path(d) / "pos").read_text().strip(), "3")


if __name__ == "__main__":
    unittest.main()
