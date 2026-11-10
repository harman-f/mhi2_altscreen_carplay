"""Host-only regression: QNX compiler image PATH survives full-rebuild shell invocation."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "release" / "build_hmi_and_package.sh"


class FullRebuildContainerShellTest(unittest.TestCase):
    def test_bash_script_is_syntactically_valid(self):
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)], text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_native_build_invocations_use_nonlogin_shell(self):
        prefix = '"${DOCKER_ARGS[@]}" bash '
        lines = [
            line.strip() for line in SCRIPT.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith(prefix)
        ]
        self.assertEqual(len(lines), 4, "all four native build commands must be checked")
        for line in lines:
            self.assertTrue(line.startswith(prefix + "-c '"), line)
            self.assertNotIn("bash -lc", line)


if __name__ == "__main__":
    unittest.main()
