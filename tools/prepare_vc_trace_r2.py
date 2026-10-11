#!/usr/bin/env python3
"""Stage, NEVER INSTALL, a six-interface OEM DSITracer R2 configuration.

Inputs MUST be user-exported original MU1440 files. No on-unit writes here.
Output is two staged text files, original SHA256 manifest, and a unified diff.
A maintainer must review the exact boot path, complete rollback and client
protocol before applying anything to the actual headunit.
"""
import argparse
import difflib
import hashlib
from pathlib import Path

INTERFACES = (
    'org.dsi.ifc.carkombi.DSICarKombi',
    'org.dsi.ifc.bap.DSIBAP',
    'org.dsi.ifc.kombifastlist.DSIFastListScrollingAudio',
    'org.dsi.ifc.kombifastlist.DSIFastListScrollingNavigation',
    'org.dsi.ifc.kombifastlist.DSIFastListScrollingTelephone',
    'org.dsi.ifc.kombipictureserver.DSIKombiPictureServer',
)


def stage(lsd: str, trace: str) -> tuple[str, str]:
    old = 'DSITRACER_ACTIVATED=no'
    if lsd.count(old) != 1:
        raise ValueError('Expected exactly one original disabled GEM DSITracer switch')
    if 'MIBR-NavIgnore.jar' not in lsd or 'MIBR-Most20FPS.jar' not in lsd:
        raise ValueError('Existing vehicle bootclasspath extensions not detected: abort')
    for token in ('-Dde.vw.mib.startup.flag=DSITRACER',
                  'DSITracer-VW-H29.319.93.jar', 'DSITracer.jar'):
        if token not in lsd:
            raise ValueError(f'Unexpected launch layout: {token} absent')
    new_lsd = lsd.replace(old, 'DSITRACER_ACTIVATED=yes', 1)
    if trace.count('use.appender=client') != 1:
        raise ValueError('Unexpected client appender configuration')
    if trace.count('activate.extension=ctrl\n') != 1:
        raise ValueError('Unexpected extension configuration')
    if 'activate.extension=ctrl,DSIKeyPanelEx' in [x for x in trace.splitlines() if not x.startswith('#')]:
        raise ValueError('KeyPanel emulator must be disabled')
    new_trace = trace
    for dsi in INTERFACES:
        wanted = f'#{dsi}=full'
        if new_trace.count(wanted) != 1:
            raise ValueError(f'Expected exactly one commented full trace line: {wanted}')
        if any(x == f'{dsi}=full' for x in new_trace.splitlines()):
            raise ValueError(f'Already active: {dsi}')
        new_trace = new_trace.replace(wanted, f'{dsi}=full', 1)
    return new_lsd, new_trace


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('original_lsd', type=Path)
    ap.add_argument('original_trace_config', type=Path)
    ap.add_argument('output_directory', type=Path)
    a = ap.parse_args()
    lsd = a.original_lsd.read_bytes()
    trace = a.original_trace_config.read_bytes()
    if any(b'\r' in d for d in (lsd, trace)):
        raise ValueError('CR or CRLF file; review manually instead of normalizing line endings')
    new_lsd, new_trace = stage(lsd.decode('utf-8'), trace.decode('utf-8'))
    if a.output_directory.exists() and any(a.output_directory.iterdir()):
        raise ValueError('Output directory must be absent or empty; no overwrites')
    a.output_directory.mkdir(parents=True, exist_ok=True)
    (a.output_directory/'lsd.sh.STAGED_NOT_FOR_INSTALL').write_bytes(new_lsd.encode())
    (a.output_directory/'traceConfig.properties.STAGED_NOT_FOR_INSTALL').write_bytes(new_trace.encode())
    (a.output_directory/'original-sha256.txt').write_text(
        f'{hashlib.sha256(lsd).hexdigest()}  {a.original_lsd.name}\n'
        f'{hashlib.sha256(trace).hexdigest()}  {a.original_trace_config.name}\n')
    diff=''.join(difflib.unified_diff(lsd.decode().splitlines(keepends=True),new_lsd.splitlines(keepends=True),fromfile='lsd.ORIGINAL',tofile='lsd.STAGED'))
    diff+=''.join(difflib.unified_diff(trace.decode().splitlines(keepends=True),new_trace.splitlines(keepends=True),fromfile='trace.ORIGINAL',tofile='trace.STAGED'))
    (a.output_directory/'review.diff').write_text(diff)
    print('STAGED_ONLY=PASS; no headunit modified; review.diff required before any vehicle activation')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
