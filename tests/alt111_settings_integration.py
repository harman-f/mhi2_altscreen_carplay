"""Exercise real POSIX settings locks, snapshots, crash journal and exact restore."""
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    'src/native/alt111-settings/settings_cli.c',
    'src/native/alt111-settings/settings_core.c',
    'src/native/alt111-settings/settings_posix.c',
    'src/native/altscreen111-gen2/src/alt111_policy.c',
    'src/native/sha256sum-compat/sha256sum_compat.c',
]

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    temp = root / 'temp'; persistent = root / 'persistent'
    temp.mkdir(); persistent.mkdir()
    binary = root / 'alt111-settings'
    subprocess.run(['cc', '-O2', '-g', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
                    '-DALT111_SETTINGS_TEST', '-DMIBR_SHA256_LIBRARY_ONLY',
                    '-Isrc/native/altscreen111-gen2/include', '-Isrc/native/alt111-settings/include',
                    *SOURCES, '-o', str(binary)], cwd=ROOT, check=True)
    env = {**os.environ, 'ALT111_SETTINGS_TEMP_ROOT': str(temp),
           'ALT111_SETTINGS_PERSISTENT_ROOT': str(persistent)}

    def run(*args, success=True, extra=None):
        result = subprocess.run([str(binary), *args], env={**env, **(extra or {})},
                                capture_output=True, text=True, timeout=5)
        if success:
            assert result.returncode == 0, (args, result.stdout, result.stderr)
        else:
            assert result.returncode != 0, (args, result.stdout)
        return result

    schema = json.loads((ROOT / 'settings/registry.json').read_text())
    basenames = list(dict.fromkeys(x['basename'] for x in schema['settings']))
    def snapshot():
        return {name: (temp/name).read_bytes() if (temp/name).exists() else None for name in basenames}

    assert 'preset.id.value=mibr_legacy' in run('status').stdout
    (persistent / 'mibr-carplay111-fps').write_text('25\n')
    assert 'maxFPS.value=25' in run('get', '--key', 'maxFPS').stdout
    assert 'RECONNECT_REQUIRED' in run('preset', '--preset', 'mibr_dual_view').stdout
    assert 'maxFPS.value=40' in run('get', '--key', 'maxFPS').stdout
    assert 'maxFPS.value=25' in run('clear', '--key', 'maxFPS').stdout
    assert 'persistent' in run('get', '--key', 'maxFPS').stdout
    result = run('set', '--key', 'keyframe.interval_frames', '--value', '30').stdout
    assert 'QUEUED' in result
    before = snapshot()
    assert 'INVALID_VALUE' in run('set', '--key', 'keyframe.interval_frames', '--value', '0', success=False).stdout
    assert snapshot() == before
    assert 'POLICY_BLOCKED' in run('set', '--layer', 'persistent', '--key', 'maxFPS', '--value', '30', success=False).stdout
    revision = run('status').stdout.split('revision=')[1].splitlines()[0]
    run('set', '--key', 'keyframe.interval_ms', '--value', '3000', '--expected-revision', revision)
    assert 'STALE_REVISION' in run('set', '--key', 'keyframe.interval_ms', '--value', '4000', '--expected-revision', revision, success=False).stdout

    # Invalid top layer must not silently reveal the valid persistent value.
    (temp / 'mibr-carplay111-fps').write_text('20junk\n')
    assert 'INVALID_VALUE' in run('status', success=False).stdout
    run('preset', '--preset', 'mibr_dual_view')  # explicit complete replacement

    # A complete group change is one transaction; duplicate keys never mutate.
    batch = root / 'batch'
    batch.write_text('keyframe.mode=source_time\nkeyframe.interval_ms=2500\n')
    run('batch', '--input', str(batch))
    before = snapshot()
    batch.write_text('keyframe.mode=off\nkeyframe.mode=source_frames\n')
    run('batch', '--input', str(batch), success=False)
    assert snapshot() == before

    # Inject a real SIGKILL after each active settings-file rename. The CLI
    # control flow, lock, backups, journal and reconciliation are unchanged.
    preload_source = root / 'inject.c'
    preload_source.write_text(r'''
#define _GNU_SOURCE
#include <dlfcn.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int rename(const char *a, const char *b) {
    static int count;
    int (*real_rename)(const char *, const char *) = dlsym(RTLD_NEXT, "rename");
    int rc = real_rename(a, b);
    const char *setting = getenv("INJECT_AFTER");
    if (!rc && setting && strstr(b, "/mibr-carplay") && ++count == atoi(setting))
        kill(getpid(), SIGKILL);
    return rc;
}
''')
    preload = root / 'inject.so'
    subprocess.run(['cc', '-shared', '-fPIC', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
                    str(preload_source), '-ldl', '-o', str(preload)], check=True)
    # Start with both existing and absent files so ABSENT restore is exercised.
    run('clear', '--key', 'maxFPS')
    run('clear', '--key', 'ownership.backend')
    for after in range(1, len(basenames) + 1):
        before = snapshot()
        rc = run('preset', '--preset', 'omonob790', success=False,
                 extra={'LD_PRELOAD': str(preload), 'INJECT_AFTER': str(after)})
        assert rc.returncode == -signal.SIGKILL
        assert 'reconcile_required' in run('status', success=False).stdout
        run('reconcile')
        assert snapshot() == before, after
        run('status')

    # An altered backup must stop BEFORE any restore mutation, retaining the
    # journal and remaining secured originals for inspection/retry.
    rc = run('preset', '--preset', 'omonob790', success=False,
             extra={'LD_PRELOAD': str(preload), 'INJECT_AFTER': '1'})
    journal = temp / 'mibr-alt111-settings.journal'
    hash_line = next(line for line in journal.read_text().splitlines() if ':' in line)
    group, original_hash = hash_line.split(':')
    backup = temp / ('mibr-alt111-settings.backup-' + group)
    original = backup.read_bytes()
    assert hashlib.sha256(original).hexdigest() == original_hash
    backup.write_bytes(original + b'changed\n')
    before = snapshot()
    assert 'backup_hash' in run('reconcile', success=False).stdout
    assert snapshot() == before and journal.exists()
    backup.write_bytes(original)
    run('reconcile')
    # Clearing the full temporary layer validates every lower value first.
    before = snapshot()
    (persistent / 'mibr-carplay111-fps').write_text('invalid\n')
    assert 'INVALID_VALUE' in run('clear-temp', success=False).stdout
    assert snapshot() == before
    (persistent / 'mibr-carplay111-fps').write_text('25\n')
    run('clear-temp')
    assert all(value is None for value in snapshot().values())
    assert 'maxFPS.value=25' in run('status').stdout
    assert 'preset.id.value=mibr_legacy' in run('status').stdout
    print('ALT111_SETTINGS_INTEGRATION=PASS crash_points=' + str(len(basenames)))
