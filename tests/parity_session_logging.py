"""The real package logger preserves child failures and detects tee failure."""
import os
import subprocess
import tempfile
from pathlib import Path

source = Path('deployment/mu1440-parity-drive-v1/session-logging.sh').resolve()
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    child = root/'action'
    child.write_text('#!/bin/sh\necho mutation-trace\nexit "${ACTION_RC:-0}"\n')
    child.chmod(0o755)
    tee = root/'broken-tee'
    tee.write_text('#!/bin/sh\ncat >/dev/null\nexit 7\n')
    tee.chmod(0o755)
    harness = root/'harness'
    harness.write_text('''#!/bin/sh
. "$LOGGER"
mibr_prepare_session host-test "$MEDIA" "$TEE" /usr/bin/sha256sum || exit 90
mibr_run_logged "$CHILD"
exit $?
''')
    def run(action, logger):
        return subprocess.run(['bash', str(harness)], env={**os.environ,
            'LOGGER': str(source), 'MEDIA': str(root), 'TEE': logger,
            'CHILD': str(child), 'ACTION_RC': str(action)}, capture_output=True, text=True, timeout=5)
    cp = run(0, '/usr/bin/tee')
    assert cp.returncode == 0 and 'mutation-trace' in cp.stdout, cp
    logs = list(root.rglob('session.log'))
    assert logs and 'mutation-trace' in logs[0].read_text()
    cp = run(23, '/usr/bin/tee')
    assert cp.returncode == 23, cp
    cp = run(0, str(tee))
    assert cp.returncode == 98, cp
    cp = run(0, str(root/'missing-tee'))
    assert cp.returncode == 90 and 'mutation-trace' not in cp.stdout, cp
print('PARITY_SESSION_LOGGING=PASS console_and_SD child_rc tee_failure bootstrap_failure')
