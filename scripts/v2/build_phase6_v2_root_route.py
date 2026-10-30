#!/usr/bin/env python3
"""Build a separate route diagnostic and APFS-cloned pristine R1-equivalent disk."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import build_android_first_stage_probe as boot

ROOT = Path(__file__).resolve().parents[2]


def run(out, name, command):
    with (out / (name + '.stdout')).open('xb') as stdout, (out / (name + '.stderr')).open('xb') as stderr:
        p = subprocess.run(command, stdout=stdout, stderr=stderr, cwd=ROOT)
    (out / (name + '.status')).write_text(str(p.returncode) + '\n')
    if p.returncode:
        raise RuntimeError(name + ' failed; inspect captured output')
    print(name + '=PASS', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists():
        ap.error('fresh output directory required')
    out.mkdir(parents=True)
    baseline = ROOT / 'out/phase6-v2-root-fstab-K-preflight/diagnostic.img'
    if hashlib.sha256(baseline.read_bytes()).hexdigest() != '09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491':
        raise ValueError('P2 baseline mismatch')
    entries = boot.entry_map(boot.parse_newc(boot.decompress_ramdisk(boot.parse_boot(baseline)['ramdisk'])))
    fragment = (ROOT / 'initramfs/phase6-root-route-rule.inc').read_bytes()
    if hashlib.sha256(fragment).hexdigest() != '08f50f97201f622389a5f276929c68722b9125d0c3713e1c2ac8c36415669e65':
        raise ValueError('unreviewed route block')
    anchor = b'$BB ifconfig usb0 "$NEXUS_IP" netmask 255.255.255.0 up || fail "failed to configure usb0"\n'
    original = bytes(entries['init'][3])
    if original.count(anchor) != 1:
        raise ValueError('unexpected P2 anchor')
    wrapper = out / 'init'
    wrapper.write_bytes(original.replace(anchor, anchor + fragment, 1))
    run(out, '00-shell-syntax', ['/bin/sh', '-n', str(wrapper)])
    images = [out / 'diagnostic.img', out / 'repeat.img']
    common = ['--android-boot', str(ROOT / 'out/diskless-v2-android/boot-fstab-only.img'),
              '--transport-boot', str(ROOT / 'out/diskless-v2-transport.img'),
              '--generated-fstab', str(ROOT / 'out/diskless-v2-android/fstab.flox'), '--wrapper', str(wrapper)]
    for index, image in enumerate(images):
        run(out, f'01-build-{index}', [sys.executable, str(ROOT / 'scripts/v2/build_android_first_stage_probe.py'),
            *common, '--phase4-env', str(ROOT / 'diskless-v2/phase4-accepted.env'), '--output', str(image)])
    if images[0].read_bytes() != images[1].read_bytes():
        raise ValueError('non-reproducible route diagnostic')
    images[1].unlink()
    run(out, '02-accepted-image-audit', [sys.executable, str(ROOT / 'scripts/v2/audit_phase6_v2_continuation_image.py'),
        *common, '--image', str(images[0])])
    run(out, '03-independent-route-audit', [sys.executable, str(ROOT / 'scripts/v2/audit_phase6_v2_root_route.py'),
        '--baseline', str(baseline), '--image', str(images[0]), '--block', str(ROOT / 'initramfs/phase6-root-route-rule.inc'),
        '--report', str(out / 'image-audit.json')])
    # Native APFS copy-on-write keeps the original and runtime-written R1 image
    # while avoiding a second full physical 6.2GB allocation. Never fall back to
    # an unbounded full copy on a nearly full host volume.
    golden = Path.home() / 'nexus7-diskless-v2/diskless-v2-android.raw.img'
    disk = out / 'disk.raw.img'
    libc = ctypes.CDLL(None, use_errno=True)
    clone = libc.clonefile
    clone.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    clone.restype = ctypes.c_int
    if clone(os.fsencode(golden), os.fsencode(disk), 0):
        raise OSError(ctypes.get_errno(), 'APFS clonefile failed; no full-copy fallback')
    system = ROOT / 'out/phase6-v2-root-fstab-I/system-root-fstab.raw.img'
    with disk.open('r+b') as target, system.open('rb') as source:
        source.seek(2125824);data = source.read(4295)
        if len(data) != 4295:
            raise ValueError('short system fstab read')
        target.seek(3174400);target.write(data);target.flush();os.fsync(target.fileno())
    source_manifest = Path(str(golden) + '.manifest.json')
    manifest = Path(str(disk) + '.manifest.json')
    obj = json.loads(source_manifest.read_bytes());obj['disk'] = str(disk)
    obj['partitions'][0]['source_path'] = str(system)
    manifest.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    run(out, '04-fresh-disk-audit', [sys.executable, str(ROOT / 'scripts/v2/phase6_v2_audit_root_fstab.py'),
        '--source-system', str(Path.home() / 'system.raw.img'), '--system', str(system),
        '--source-disk', str(golden), '--disk', str(disk), '--source-manifest', str(source_manifest),
        '--manifest', str(manifest), '--layout', str(ROOT / 'diskless-v2/layout.json'),
        '--fstab', str(ROOT / 'out/diskless-v2-android/fstab.flox'), '--report', str(out / 'disk-audit.json')])
    audit = json.loads((out / 'disk-audit.json').read_text())
    if audit['disk']['candidate_sha256'] != '060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a':
        raise ValueError('fresh disk not identical to R1 pre-run')
    run(out, '05-trace-map', [sys.executable, str(ROOT / 'scripts/v2/prepare_phase6_v2_partition_trace.py'),
        '--disk', str(disk), '--manifest', str(manifest), '--layout', str(ROOT / 'diskless-v2/layout.json'),
        '--output', str(out / 'partition-trace-map.json')])
    result = dict(status='HOST_PASS', hardware_authorized=False, runtime_effect='IMPLEMENTED_UNPROVEN',
                  image_sha256=hashlib.sha256(images[0].read_bytes()).hexdigest(),
                  wrapper_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),
                  block_sha256=hashlib.sha256(fragment).hexdigest(), disk_sha256=audit['disk']['candidate_sha256'],
                  manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                  trace_map_sha256=hashlib.sha256((out / 'partition-trace-map.json').read_bytes()).hexdigest(),
                  disk_copy='native APFS clonefile, independently audited', disk=str(disk), image=str(images[0]))
    (out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PHASE6_V2_ROOT_ROUTE_ARTIFACTS=HOST_PASS')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
