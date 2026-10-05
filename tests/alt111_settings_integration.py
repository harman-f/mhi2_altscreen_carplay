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
    barrier=temp/'mibr-parity-rollback.pending'
    barrier.write_text('canonical_reboot_required\n')
    before = snapshot()
    for args in [('status',), ('preset','--preset','omonob790'),
                 ('set','--key','maxFPS','--value','40'),
                 ('clear','--key','maxFPS'), ('clear-temp',), ('reconcile',)]:
        assert 'rollback_requires_canonical_reboot' in run(*args,success=False).stdout
        assert snapshot() == before
        assert not (temp/'mibr-alt111-settings.journal').exists()
        assert not (temp/'mibr-alt111-settings.journal-armed').exists()
    barrier.unlink()
    barrier.symlink_to(temp/'absent-rollback-target')
    assert 'rollback_requires_canonical_reboot' in run('preset','--preset','omonob790',success=False).stdout
    assert snapshot() == before
    barrier.unlink()
    run('status')
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

    # The target cannot rename() inside /tmp -> /dev/shmem. Transactions use
    # direct rewrites only after journal+armed have established rollback state.
    # Inject a real SIGKILL after each active direct rewrite.
    run('clear', '--key', 'maxFPS')
    run('clear', '--key', 'ownership.backend')
    for after in range(1, len(basenames) + 1):
        before = snapshot()
        rc = run('preset', '--preset', 'omonob790', success=False,
                 extra={'ALT111_SETTINGS_TEST_CRASH_AFTER_ACTIVE_WRITE': str(after)})
        assert rc.returncode == -signal.SIGKILL
        assert (temp / 'mibr-alt111-settings.journal').exists()
        assert (temp / 'mibr-alt111-settings.journal-armed').exists()
        assert 'reconcile_required' in run('status', success=False).stdout
        run('reconcile')
        assert snapshot() == before, after
        assert not (temp / 'mibr-alt111-settings.journal').exists()
        assert not (temp / 'mibr-alt111-settings.journal-armed').exists()
        run('status')

    # schema=2 journal without armed means the process died before active
    # mutation was permitted. Reconcile may discard it without touching settings.
    before = snapshot()
    (temp / 'mibr-alt111-settings.journal').write_text(
        'schema=2\nmask=1\nabsent=1\n')
    run('reconcile')
    assert snapshot() == before
    assert not (temp / 'mibr-alt111-settings.journal').exists()

    # Legacy schema=1 had no armed barrier and may already have mutated active
    # files. Preserve upgrade safety by forcing the old rollback semantics.
    legacy_active = temp / 'mibr-carplay111-compat-profile'
    legacy_original = legacy_active.read_bytes()
    legacy_hash = hashlib.sha256(legacy_original).hexdigest()
    (temp / 'mibr-alt111-settings.backup-0').write_bytes(legacy_original)
    legacy_active.write_bytes(b'corrupt\n')
    (temp / 'mibr-alt111-settings.journal').write_text(
        'schema=1\nmask=1\nabsent=0\n0:' + legacy_hash + '\n')
    run('reconcile')
    assert legacy_active.read_bytes() == legacy_original
    assert not (temp / 'mibr-alt111-settings.journal').exists()

    # Armed without journal means journal removal already committed the batch;
    # only marker cleanup was interrupted.
    (temp / 'mibr-alt111-settings.journal-armed').write_text('armed\n')
    run('reconcile')
    assert snapshot() == before
    assert not (temp / 'mibr-alt111-settings.journal-armed').exists()

    # An altered backup must stop BEFORE any restore mutation, retaining the
    # armed journal and remaining secured originals for inspection/retry.
    rc = run('preset', '--preset', 'omonob790', success=False,
             extra={'ALT111_SETTINGS_TEST_CRASH_AFTER_ACTIVE_WRITE': '1'})
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
    assert (temp / 'mibr-alt111-settings.journal-armed').exists()
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
