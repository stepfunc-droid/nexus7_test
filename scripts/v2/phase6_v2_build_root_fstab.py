#!/usr/bin/env python3
"""Build separate Phase6 one-file system/disk derivatives, never flash or boot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from ext4_readonly import Ext4Image

HERE = Path(__file__).resolve().parent
PINS = {
    'source_system': 'a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880',
    'source_disk': 'c13349f8b1545a75a28aa2585891a6986b8e5b9f6fc54fc77ac5554cbcf68ca9',
    'source_manifest': '4c20ce1c8254ccb321302ffa7a0b83d099cff232421c6e5d2b652799ad2af85d',
    'stock_fstab': 'ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764',
    'fstab': '834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf',
}


def digest(path):
    with path.open('rb') as fp:
        return hashlib.file_digest(fp, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in (*[key.replace('_', '-') for key in PINS], 'layout', 'output-dir'):
        ap.add_argument('--' + name, type=Path, required=True)
    args = ap.parse_args()
    if args.output_dir.exists():
        raise SystemExit('refusing existing output directory')
    for key, expected in PINS.items():
        if digest(getattr(args, key)) != expected:
            raise SystemExit(f'pinned source mismatch: {key}')
    args.output_dir.mkdir(parents=True)
    system = args.output_dir / 'system-root-fstab.raw.img'
    repeat = args.output_dir / 'system-root-fstab-repeat.raw.img'
    disk = args.output_dir / 'disk-root-fstab.raw.img'
    manifest = Path(str(disk) + '.manifest.json')
    for output in (system, repeat):
        # Reuse the accepted unique-stock-span replacement unchanged. Its vendor
        # marker is historical; only the separate root-filesystem audit is a gate.
        command = [sys.executable, str(HERE / 'patch_vendor_fstab.py'),
                   '--input', str(args.source_system), '--stock-fstab', str(args.stock_fstab),
                   '--fstab', str(args.fstab), '--output', str(output)]
        subprocess.run(command, check=True)
    first_sha, second_sha = digest(system), digest(repeat)
    if first_sha != second_sha:
        raise SystemExit('nondeterministic system derivative')
    repeat.unlink()
    with Ext4Image(system) as fs:
        inode = fs.resolve('/fstab.flox', follow_final=False)
        content, ranges = fs.read_inode(inode), fs.file_ranges(inode)
    if ranges != [dict(file_offset=0, image_offset=2125824, length=4295)]:
        raise SystemExit('unexpected candidate file ranges')
    shutil.copyfile(args.source_disk, disk)
    original_manifest = json.loads(args.source_manifest.read_bytes())
    p1_start = original_manifest['partitions'][0]['start_lba'] * original_manifest['sector_size']
    with disk.open('r+b') as fp:
        fp.seek(p1_start + ranges[0]['image_offset'])
        fp.write(content)
        fp.flush()
        os.fsync(fp.fileno())
    original_manifest['disk'] = str(disk.resolve())
    original_manifest['partitions'][0]['source_path'] = str(system.resolve())
    manifest.write_text(json.dumps(original_manifest, indent=2, sort_keys=True) + '\n')
    report = args.output_dir / 'independent-audit.json'
    command = [sys.executable, str(HERE / 'phase6_v2_audit_root_fstab.py')]
    inputs = dict(source_system=args.source_system, system=system,
                  source_disk=args.source_disk, disk=disk, source_manifest=args.source_manifest,
                  manifest=manifest, layout=args.layout, fstab=args.fstab, report=report)
    for key, value in inputs.items():
        command.extend(['--' + key.replace('_', '-'), str(value)])
    subprocess.run(command, check=True)
    (args.output_dir / 'determinism.json').write_text(json.dumps(dict(
        evidence_class='HOST_FACT', system_A_sha256=first_sha, system_B_sha256=second_sha,
        equal=True, repeat_removed=True, disk_construction='source copy + exact p1 file data',
        hardware_authorized=False), indent=2, sort_keys=True) + '\n')
    print('PHASE6_V2_ROOT_FSTAB_DERIVATIVE=HOST_PASS / IMPLEMENTED_UNPROVEN')


if __name__ == '__main__':
    main()
