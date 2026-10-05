"""Run the shipped shell aliases against the real shared settings helper."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sources = [
    'src/native/alt111-settings/settings_cli.c',
    'src/native/alt111-settings/settings_core.c',
    'src/native/alt111-settings/settings_posix.c',
    'src/native/altscreen111-gen2/src/alt111_policy.c',
    'src/native/sha256sum-compat/sha256sum_compat.c',
]
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    for name in ('bin', 'scripts', 'temp', 'persistent'):
        (root/name).mkdir()
    binary = root/'bin/alt111-settings'
    subprocess.run(['cc', '-O2', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
                    '-DALT111_SETTINGS_TEST', '-DMIBR_SHA256_LIBRARY_ONLY',
                    '-Isrc/native/altscreen111-gen2/include', '-Isrc/native/alt111-settings/include',
                    *sources, '-o', str(binary)], cwd=ROOT, check=True)
    env = {**os.environ, 'ALT111_SETTINGS_TEMP_ROOT': str(root/'temp'),
           'ALT111_SETTINGS_PERSISTENT_ROOT': str(root/'persistent')}
    inventory = (ROOT/'runtime/parity/master-script-basenames.sh').read_text().split("'")[1].split()
    for name in inventory:
        candidates = list((ROOT/'runtime').rglob(name))
        assert len(candidates) == 1, name
        shutil.copyfile(candidates[0], root/'scripts'/name)
        subprocess.run(['bash', '-n', str(root/'scripts'/name)], check=True)

    def cli(*args):
        cp = subprocess.run([str(binary), *args], env=env, capture_output=True, text=True)
        assert cp.returncode == 0, (args, cp.stdout, cp.stderr)
        return cp.stdout

    def run(name, *args, success=True):
        cp = subprocess.run(['bash', str(root/'scripts'/name), *args],
                            env=env, capture_output=True, text=True, timeout=5)
        assert (cp.returncode == 0) == success, (name, args, cp.stdout, cp.stderr)
        return cp.stdout

    def snapshot():
        return {p.name: p.read_bytes() for p in (root/'temp').iterdir() if p.name != 'mibr-alt111-settings.lock'}

    cli('preset', '--preset', 'mibr_dual_view')
    run('direct_fps.sh', 'temp', '25')
    assert 'maxFPS.value=25' in cli('get', '--key', 'maxFPS')
    run('gen2_sourceversion.sh', 'temp', '950.7.2')
    before = snapshot()
    run('gen2_sourceversion.sh', 'temp', '65536.1', success=False)
    assert snapshot() == before
    run('gen2_safearea.sh', 'set', '202', '16', '606', '344')
    before = snapshot()
    run('gen2_safearea.sh', 'set', '202', '16', '900', '344', success=False)
    assert snapshot() == before, 'invalid rectangle partially changed a group'
    run('gen2_display.sh', 'temp', '1010', '376', '202', '75', 'bad-uuid', success=False)
    assert snapshot() == before, 'invalid display batch partially changed a group'
    run('gen2_nav_config.sh', 'temp-profile', 'map-clean')
    status = cli('status')
    assert 'navigation.surface.value=map' in status and 'navigation.ETA.value=no' in status
    run('gen2_keyframes.sh', 'temp', 'source-time', '2000')
    assert 'keyframe.mode.value=source_time' in cli('status')
    run('gen2_keyframes.sh', 'off')
    assert 'keyframe.mode.value=off' in cli('status')
    run('gen2_viewareas.sh', 'select', '1')
    assert 'viewarea.selected.value=1' in cli('status')
    run('gen2_enabled.sh', 'temp', 'off')
    run('gen2_enabled.sh', 'clear-temp')
    assert 'carplay.enabled.value=1' in cli('status')
    run('gen2_ui_urls.sh', 'temp', 'maps:/car/instrumentcluster/map', 'maps:/car/instrumentcluster')
    assert 'maps:/car/instrumentcluster/map|maps:/car/instrumentcluster' in cli('status')
    before = snapshot()
    run('gen2_display.sh', 'temp', '1010\nownership.backend=dmdt_reference', '376',
        '202', '75', 'b7e6c5a0-2222-4000-8000-000000000002', success=False)
    assert snapshot() == before
    for name in inventory:
        if name == 'master_settings.sh':
            continue
        assert 'POLICY_BLOCKED' in run(name, 'persist', success=False)
        assert snapshot() == before
    (root/'temp/mibr-parity-rollback.pending').write_text('canonical_reboot_required\n')
    assert 'rollback_requires_canonical_reboot' in run('direct_fps.sh', 'temp', '40', success=False)
    assert snapshot()['mibr-carplay111-fps'] == before['mibr-carplay111-fps']
print('ALT111_RUNTIME_WRAPPERS=PASS shared_registry atomic_groups policy_barrier no_line_injection')
