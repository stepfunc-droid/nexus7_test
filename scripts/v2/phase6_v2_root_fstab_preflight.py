#!/usr/bin/env python3
"""Compose unchanged original gates with explicit Phase6 derivative validation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BOOT_SHA = '09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491'
DISK_SHA = '060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a'
SYSTEM_SHA = 'd004e3186585a57991c8e291cd7abf2c1cad7eb2c82b0c055de82894e0d3c795'
MANIFEST_SHA = 'e307d3285e61fc0a4419bdb6a89d672a45792ab65da39bfdddfaa61bed33b3a3'


def step(output, name, command, marker=None, env=None):
    with (output / (name + '.stdout')).open('xb') as stdout, (output / (name + '.stderr')).open('xb') as stderr:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
    (output / (name + '.status')).write_text(str(result.returncode) + '\n')
    if result.returncode or (marker and marker not in (output / (name + '.stdout')).read_text().splitlines()):
        raise RuntimeError(f'{name} failed; inspect saved output')
    print(name + '=PASS', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    output = args.output.resolve()
    if output.exists():
        ap.error('fresh output directory required')
    output.mkdir(parents=True)
    home = Path.home()
    golden_disk = home / 'nexus7-diskless-v2/diskless-v2-android.raw.img'
    golden_system = home / 'system.raw.img'
    baseline = ROOT / 'out/phase6-v2-host-20261030-C'
    derivative = ROOT / 'out/phase6-v2-root-fstab-I'
    disk = derivative / 'disk-root-fstab.raw.img'
    system = derivative / 'system-root-fstab.raw.img'
    manifest = Path(str(disk) + '.manifest.json')
    env = dict(os.environ)
    # Override original gate inputs explicitly. Never feed the derivative into
    # its clean-system contract or treat its historical binary question as ours.
    env.update(OUT=str(ROOT / 'out/diskless-v2-android'),
               STOCK_BOOT=str(ROOT / 'lineage-flox-boot.img'),
               ANDROID_BOOT=str(ROOT / 'out/diskless-v2-android/boot-fstab-only.img'),
               STOCK_VENDOR=str(home / 'vendor.raw.img'),
               PATCHED_VENDOR=str(ROOT / 'out/diskless-v2-android/vendor-fstab.raw.img'),
               STOCK_FSTAB=str(ROOT / 'diskless-v2/fstab.flox.stock'),
               GENERATED_FSTAB=str(ROOT / 'out/diskless-v2-android/fstab.flox'),
               SYSTEM_IMG=str(golden_system),
               TRANSPORT_BOOT=str(ROOT / 'out/diskless-v2-transport.img'),
               ANDROID_DISK=str(golden_disk), DISK=str(golden_disk),
               DISK_MANIFEST=str(golden_disk) + '.manifest.json',
               MANIFEST=str(golden_disk) + '.manifest.json',
               LAYOUT=str(ROOT / 'diskless-v2/layout.json'),
               PHASE4_ENV=str(ROOT / 'diskless-v2/phase4-accepted.env'),
               FACT_REPORT=str(output / 'frozen-facts.txt'),
               CONTINUATION_REPORT=str(baseline / 'continuation-host-audit.txt'),
               TRACER_REPORT=str(baseline / 'tracer-host-audit.txt'),
               TRACE_MAP=str(baseline / 'partition-trace-map.json'),
               CONTINUATION_IMAGE=str(baseline / 'continuation.img'),
               IMAGE=str(output / 'diagnostic.img'), REPORT=str(output / 'panic-hold-host-gate.txt'))
    step(output, '01-original-preflight',
         ['bash', str(ROOT / 'scripts/v2/phase6_v2_panic_hold_real_preflight.sh')],
         'DISKLESS_V2_PHASE6_V2_PANIC_HOLD_REAL_PREFLIGHT=PASS', env)
    boot = output / 'diagnostic.img'
    if hashlib.sha256(boot.read_bytes()).hexdigest() != BOOT_SHA:
        raise RuntimeError('P2 boot identity mismatch')
    command = [sys.executable, str(ROOT / 'scripts/v2/phase6_v2_audit_root_fstab.py')]
    inputs = dict(source_system=golden_system, system=system, source_disk=golden_disk, disk=disk,
                  source_manifest=Path(str(golden_disk) + '.manifest.json'), manifest=manifest,
                  layout=ROOT / 'diskless-v2/layout.json',
                  fstab=ROOT / 'out/diskless-v2-android/fstab.flox', report=output / 'derivative-audit.json')
    for key, value in inputs.items():
        command.extend(['--' + key.replace('_', '-'), str(value)])
    step(output, '02-derivative-audit', command, 'PHASE6_V2_ROOT_FSTAB_HOST_AUDIT=PASS')
    audit = json.loads((output / 'derivative-audit.json').read_bytes())
    if (audit['disk']['candidate_sha256'] != DISK_SHA or audit['system']['candidate_sha256'] != SYSTEM_SHA
            or audit['manifest_sha256'] != MANIFEST_SHA or audit['hardware_authorized'] is not False):
        raise RuntimeError('derivative identity/scope mismatch')
    step(output, '03-disk-structure', [sys.executable, str(ROOT / 'scripts/v2/validate_disk.py'),
         '--disk', str(disk), '--manifest', str(manifest)], 'DISKLESS_V2_DISK_VERIFIED=1')
    maps = [output / 'partition-trace-map.json', output / 'partition-trace-map-repeat.json']
    for index, trace in enumerate(maps):
        step(output, f'04-trace-map-{index}',
             [sys.executable, str(ROOT / 'scripts/v2/prepare_phase6_v2_partition_trace.py'),
              '--disk', str(disk), '--manifest', str(manifest), '--layout', str(inputs['layout']),
              '--output', str(trace)], 'DISKLESS_V2_PHASE6_V2_PARTITION_TRACE_MAP=PASS')
    if maps[0].read_bytes() != maps[1].read_bytes():
        raise RuntimeError('derivative trace map not deterministic')
    maps[1].unlink()
    result = dict(status='HOST_PASS', evidence_class='HOST_FACT', hardware_authorized=False,
                  runtime_effect='IMPLEMENTED_UNPROVEN', original_frozen_gates='fresh/unchanged',
                  disk=str(disk), disk_sha256=DISK_SHA, manifest=str(manifest), manifest_sha256=MANIFEST_SHA,
                  system_sha256=SYSTEM_SHA, boot=str(boot), boot_sha256=BOOT_SHA,
                  trace_map=str(maps[0]), trace_map_sha256=hashlib.sha256(maps[0].read_bytes()).hexdigest(),
                  binary_question='does-root-fstab-delta-enable-both-cache-and-persist-filesystem-read-evidence')
    (output / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PHASE6_V2_ROOT_FSTAB_COMPOSED_PREFLIGHT=PASS')
    print('hardware_authorized=no')


if __name__ == '__main__':
    main()
