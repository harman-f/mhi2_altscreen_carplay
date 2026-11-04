"""The parity supervisor honours the "Logs auf SD-Karte" switch. Host-only."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SUPERVISOR = ROOT / "modules/carplay/runtime/parity/parity_drive_supervisor.sh"
SWITCH = "/mnt/app/root/mibr/config/features/sd-log.conf"
BASH = os.environ.get("DELTA_SHELL", shutil.which("bash"))


def function_source(text, name):
    start = text.index(name + "(){")
    return text[start:text.index("\n}", start) + 2]


class SwitchPath(unittest.TestCase):
    def test_same_file_as_menu_and_broker(self):
        self.assertIn('SD_SWITCH=$MIBR_ROOT/config/features/sd-log.conf', SUPERVISOR.read_text())
        java = (ROOT / "modules/menu/source/java/de/mibr/hmi/MibrDurableSwitch.java").read_text()
        self.assertIn('"' + SWITCH + '","MIBR_SD_LOG/1"', java)
        broker = (ROOT / "modules/broker/source/mibr-control/mibr_durable_switch.c").read_text()
        self.assertIn('MIBR_CONFIG_DIR "/features/sd-log.conf"', broker)
        paths = (ROOT / "modules/carplay/source/alt111-settings/include/mibr_paths.h").read_text()
        self.assertIn('#define MIBR_ROOT_DIR "/mnt/app/root/mibr"', paths)

    def test_sd_is_not_made_writable_unconditionally(self):
        text = SUPERVISOR.read_text()
        self.assertIn("if ! sd_enable_logs; then", text)
        self.assertNotIn("if sd_make_rw; then\n  SD_LOG=1", text)


@unittest.skipUnless(BASH, "bash required")
class SwitchBehaviour(unittest.TestCase):
    def run_script(self, tmp, body):
        text = SUPERVISOR.read_text()
        funcs = "\n".join(function_source(text, n) for n in
                          ("sd_wanted", "sd_enable_logs", "sd_disable_logs", "sd_prune"))
        script = f"""
SD_SWITCH='{tmp}/sd-log.conf'
LOGROOT='{tmp}/logs'
SD_KEEP_SESSIONS=3
SD_MASTER_MAX=10
SD_LOG=0
CALLS=
sd_make_rw(){{ CALLS="$CALLS rw"; return 0; }}
sd_make_ro(){{ CALLS="$CALLS ro"; return 0; }}
{funcs}
mkdir -p "$LOGROOT"
{body}
"""
        r = subprocess.run([BASH, "-c", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def switch(self, tmp, value):
        Path(tmp, "sd-log.conf").write_text("MIBR_SD_LOG/1\nrevision=1\nvalue=%s\n" % value)

    def test_missing_and_off_never_touch_the_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_script(tmp, 'sd_enable_logs; echo "rc=$? log=$SD_LOG calls=$CALLS"')
            self.assertEqual(out, "rc=1 log=0 calls=")
            self.switch(tmp, "off")
            out = self.run_script(tmp, 'sd_enable_logs; echo "rc=$? log=$SD_LOG calls=$CALLS"')
            self.assertEqual(out, "rc=1 log=0 calls=")

    def test_on_enables_and_off_again_returns_card_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.switch(tmp, "on")
            out = self.run_script(tmp, 'sd_enable_logs; echo "rc=$? log=$SD_LOG calls=$CALLS master=$MASTER_LOG"')
            self.assertEqual(out, "rc=0 log=1 calls= rw master=%s/logs/drive-supervisor.log" % tmp)
            out = self.run_script(tmp, 'sd_disable_logs; echo "log=$SD_LOG calls=$CALLS master=$MASTER_LOG"')
            self.assertEqual(out, "log=0 calls= ro master=/dev/null")

    def test_prune_keeps_newest_sessions_and_rotates_master(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = """
for i in 1 2 3 4 5; do mkdir "$LOGROOT/2026110$i-000000-session-$i"; done
MASTER_LOG="$LOGROOT/drive-supervisor.log"
echo 0123456789abcdef > "$MASTER_LOG"
sd_prune
ls "$LOGROOT" | tr '\\n' ' '
"""
            out = self.run_script(tmp, body)
            self.assertEqual(out, "20261103-000000-session-3 20261104-000000-session-4 "
                                  "20261105-000000-session-5 drive-supervisor.log.1")


if __name__ == "__main__":
    unittest.main()
