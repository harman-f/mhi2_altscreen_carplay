#!/usr/bin/env python3
"""Host regression for r53's owned evidence-collector stop path."""

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import time
import unittest


from public_paths import ROOT
SUPERVISOR = ROOT / "runtime" / "parity" / "parity_drive_supervisor_r53.sh"


def find_bash() -> str | None:
    override = os.environ.get("R53_TEST_BASH")
    if override:
        return override
    if os.name == "nt":
        git_bash = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git/bin/bash.exe"
        if git_bash.is_file():
            return str(git_bash)
    return shutil.which("bash") or ("/bin/bash" if Path("/bin/bash").is_file() else None)


BASH = find_bash()


def function_source(source: str, name: str) -> str:
    start = source.index(f"{name}(){{")
    end = source.index("\n}", start) + 2
    return source[start:end]


@unittest.skipUnless(SUPERVISOR.is_file(), "Research-only R53 supervisor variant is omitted from the public source tree")
class CollectorLifecycleTests(unittest.TestCase):
    @unittest.skipUnless(BASH, "Bash is required for shell lifecycle regression")
    def test_only_owned_slow_collector_is_stopped_and_reaped(self) -> None:
        source = SUPERVISOR.read_text(encoding="utf-8")
        stop = function_source(source, "stop_evidence_collector")
        collector = function_source(source, "evidence_loop")
        self.assertIn("trap - 0 1 2 15", collector)
        self.assertIn("LOOP_T0=$SECONDS", collector)
        self.assertIn("ELAPSED=$((SECONDS-LOOP_T0))", collector)
        self.assertIn('echo "$N\\t$ELAPSED\\t$SS', collector)
        self.assertIn("GAFPS=$((GA-PREV_GA))", collector)
        with tempfile.TemporaryDirectory(prefix="r53-collector-") as temp_dir:
            marker = Path(temp_dir) / "cleanup-pids"
            shell_temp_dir = Path(temp_dir).as_posix()

            command = f"""
{stop}
{collector}
PARENT_BASHPID=$BASHPID
FOREIGN_PID=
OWNER_PID=
COLLECTOR_PID=
cleanup() {{
  echo "$BASHPID" >> '{marker.as_posix()}'
  if [ "$BASHPID" = "$PARENT_BASHPID" ]; then
    kill -TERM "$FOREIGN_PID" "$OWNER_PID" 2>/dev/null || true
  fi
}}
trap cleanup EXIT TERM
sleep 30 &
FOREIGN_PID=$!
sleep 30 &
OWNER_PID=$!
SESSION_LOCK='{shell_temp_dir}/missing-session-lock'
STATUS_ON=0
STATS_ON=0
evidence_loop '{shell_temp_dir}' &
EPID=$!
COLLECTOR_PID=$EPID
sleep 0.1
# Simulate the owner's early rc=21 return while the collector has never seen
# SESSION_LOCK. The old unconditional wait would keep sampling toward 20.
START=$SECONDS
stop_evidence_collector
ELAPSED=$((SECONDS-START))
kill -0 "$FOREIGN_PID" || exit 11
kill -0 "$OWNER_PID" || exit 12
kill -0 "$COLLECTOR_PID" 2>/dev/null && exit 13
[ "$ELAPSED" -le 1 ] || exit 14
[ ! -e '{marker.as_posix()}' ] || exit 15
EPID="$COLLECTOR_PID"
EPID=""
echo "collector_elapsed_s=$ELAPSED collector_pid_reaped=1 foreign_pid_alive=1 owner_pid_alive=1 child_cleanup_not_run=1"
"""
            start = time.monotonic()
            harness = Path(temp_dir) / "collector-lifecycle.sh"
            harness.write_text(command, encoding="utf-8")
            result = subprocess.run(
                [BASH, str(harness)], capture_output=True, text=True, timeout=5
            )
            elapsed = time.monotonic() - start
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertLess(elapsed, 3.0, result.stdout)
        self.assertIn(
            "collector_pid_reaped=1 foreign_pid_alive=1 owner_pid_alive=1 child_cleanup_not_run=1",
            result.stdout,
        )

    def test_retry_and_normal_reopen_delays_are_preserved(self) -> None:
        source = SUPERVISOR.read_text(encoding="utf-8")
        self.assertIn("OWN_RETRY_DELAY=3", source)
        self.assertIn('sleep "$OWN_RETRY_DELAY"', source)
        self.assertIn('REOPEN_COOLDOWN=2', source)
        self.assertIn('REOPEN_BACKOFF=10', source)


if __name__ == "__main__":
    unittest.main()
