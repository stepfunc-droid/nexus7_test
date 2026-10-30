#!/usr/bin/env python3
"""Read-only, full-byte audit of the proposed Phase6 root-fstab derivative.

This deliberately does not import the patch builder or its padding helper.
No output from this auditor authorizes a hardware run.
"""
import argparse
import hashlib
import json
from pathlib import Path

from assemble_disk import calculate_layout, load_layout
from ext4_readonly import Ext4Image, S_IFREG

SYSTEM_SHA = "a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880"
DISK_SHA = "c13349f8b1545a75a28aa2585891a6986b8e5b9f6fc54fc77ac5554cbcf68ca9"
MANIFEST_SHA = "4c20ce1c8254ccb321302ffa7a0b83d099cff232421c6e5d2b652799ad2af85d"
STOCK_SHA = "ea4c7678742b09fac748ff0b2bd3d481f7115c8785883a9d3ea9926b95846764"
FSTAB_SHA = "834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf"
CHUNK = 8 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare_exact(source, candidate, patches, region=None):
    """Require candidate == source with only the exact supplied replacements.

    Stream every byte, including holes, metadata, partition tables and slack.
    Optionally hash a partition independently during the same pass.
    """
    require(source.resolve() != candidate.resolve(), "source/candidate alias")
    require(source.stat().st_size == candidate.stat().st_size, "size mismatch")
    size = source.stat().st_size
    previous_end = 0
    for offset, data in sorted(patches):
        require(previous_end <= offset and offset + len(data) <= size,
                "overlapping/out-of-bounds patch")
        previous_end = offset + len(data)
    hashes = [hashlib.sha256(), hashlib.sha256()]
    region_hashes = [hashlib.sha256(), hashlib.sha256()]
    changed = 0
    with source.open('rb') as left, candidate.open('rb') as right:
        for offset in range(0, size, CHUNK):
            length = min(CHUNK, size - offset)
            original, actual = left.read(length), right.read(length)
            require(len(original) == len(actual) == length, "short read")
            expected = bytearray(original)
            for start, replacement in patches:
                lo, hi = max(start, offset), min(start + len(replacement), offset + length)
                if lo < hi:
                    expected[lo-offset:hi-offset] = replacement[lo-start:hi-start]
                    changed += sum(a != b for a, b in zip(
                        original[lo-offset:hi-offset], replacement[lo-start:hi-start]))
            require(actual == expected, f"unexpected bytes in chunk at {offset}")
            for h, data in zip(hashes, (original, actual)):
                h.update(data)
            if region:
                lo, hi = max(region[0], offset), min(region[1], offset + length)
                if lo < hi:
                    for h, data in zip(region_hashes, (original, actual)):
                        h.update(data[lo-offset:hi-offset])
    return dict(source_sha256=hashes[0].hexdigest(),
                candidate_sha256=hashes[1].hexdigest(), changed_bytes=changed,
                size_bytes=size, outside_file_data="unchanged",
                region_sha256=[h.hexdigest() for h in region_hashes] if region else None)


def audit(args):
    generated = args.fstab.read_bytes()
    require(sha(generated) == FSTAB_SHA, "unaccepted generated fstab")
    with Ext4Image(args.source_system) as src, Ext4Image(args.system) as dst:
        before = src.resolve('/fstab.flox', follow_final=False)
        after = dst.resolve('/fstab.flox', follow_final=False)
        require(before.kind == S_IFREG and before.number == 26 and before.size == 4295,
                "unexpected source root-fstab inode")
        require(before == after, "root-fstab inode fields changed")
        require(sha(src.read_inode(before)) == STOCK_SHA, "source root-fstab is not pinned stock")
        ranges = src.file_ranges(before)
        require(ranges == dst.file_ranges(after), "file ranges changed")
        # This exact artifact has a single contiguous file-data span.
        require(ranges == [dict(file_offset=0, image_offset=2125824, length=4295)],
                "unexpected exact source file-data range")
        padding_size = before.size - len(generated)
        require(padding_size >= 2, "unexpected padding size")
        expected = generated + b'#' + b' ' * (padding_size - 2) + b'\n'
        require(dst.read_inode(after) == expected, "candidate root-fstab content mismatch")
    system_result = compare_exact(args.source_system, args.system, [(2125824, expected)])
    require(system_result['source_sha256'] == SYSTEM_SHA, "golden system hash mismatch")
    cfg = load_layout(args.layout)
    parts, sectors = calculate_layout(cfg)
    manifest_bytes = args.source_manifest.read_bytes()
    require(sha(manifest_bytes) == MANIFEST_SHA, "golden manifest hash mismatch")
    manifest = json.loads(manifest_bytes)
    require(manifest['disk_size_bytes'] == sectors * cfg['sector_size'], "disk size/layout mismatch")
    require(manifest['sector_size'] == cfg['sector_size'] == 512, "sector size mismatch")
    require(manifest['alignment_sectors'] == cfg['alignment_sectors'], "alignment mismatch")
    require(manifest['nbd_max_part'] == cfg['nbd_max_part'], "nbd max_part mismatch")
    require(len(manifest['partitions']) == len(parts), "partition count mismatch")
    for recorded, computed in zip(manifest['partitions'], parts):
        for key in ('number', 'name', 'kind', 'type_id', 'start_lba', 'sectors', 'ebr_lba'):
            require(recorded.get(key) == computed.get(key), f"layout mismatch: {key}")
        require(recorded['size_bytes'] == computed['sectors'] * 512, "partition size mismatch")
    p1 = parts[0]
    start, length = p1['start_lba'] * 512, p1['sectors'] * 512
    require(length == args.system.stat().st_size, "p1/system size mismatch")
    disk_result = compare_exact(args.source_disk, args.disk,
                                [(start + 2125824, expected)], (start, start + length))
    require(disk_result['source_sha256'] == DISK_SHA, "golden disk hash mismatch")
    require(disk_result['size_bytes'] == manifest['disk_size_bytes'], "disk size mismatch")
    require(disk_result['region_sha256'] == [SYSTEM_SHA, system_result['candidate_sha256']],
            "p1 does not match source/derived system")
    candidate_manifest = json.loads(args.manifest.read_bytes())
    expected_manifest = json.loads(manifest_bytes)
    expected_manifest['disk'] = str(args.disk.resolve())
    expected_manifest['partitions'][0]['source_path'] = str(args.system.resolve())
    require(candidate_manifest == expected_manifest, "derived manifest differs beyond disk/p1 source path")
    return dict(schema=1, evidence_class="HOST_FACT", runtime="IMPLEMENTED_UNPROVEN",
                hardware_authorized=False, status="PASS", root_fstab_inode=26,
                file_data_ranges=ranges, generated_fstab_sha256=FSTAB_SHA,
                padded_fstab_sha256=sha(expected), system=system_result, disk=disk_result,
                source_manifest_sha256=sha(manifest_bytes),
                manifest_sha256=sha(args.manifest.read_bytes()),
                paths={k: str(v.resolve()) for k, v in vars(args).items() if isinstance(v, Path)})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('source-system', 'system', 'source-disk', 'disk', 'source-manifest',
                 'manifest', 'layout', 'fstab', 'report'):
        ap.add_argument('--' + name, required=True, type=Path)
    args = ap.parse_args()
    # Refuse a stale PASS and never let a report path alias an input image.
    inputs = [v.resolve() for k, v in vars(args).items() if k != 'report']
    require(args.report.resolve() not in inputs, "report aliases an input")
    require(not args.report.exists(), "refusing existing report; select a fresh audit path")
    result = audit(args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PHASE6_V2_ROOT_FSTAB_HOST_AUDIT=PASS')
    print('hardware_authorized=no')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
