#!/usr/bin/env python3
"""Prepare a four-byte GPS HAL deferral with independent filesystem/byte gates."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

from assemble_disk import calculate_layout, load_layout
from ext4_readonly import Ext4Image
from phase6_v2_audit_root_fstab import compare_exact

ROOT = Path(__file__).resolve().parents[2]
GPS_SHA = 'dfe33c9f397ae51ad5085411a85f333fb41c3f587e89d1ec27e20820d98f20be'
VENDOR_SHA = '50224b71e7d534583804bb16f24a0c6a186a1cce6eff012ee2b42d9a5130aac6'
BASE_SHA = '060ba738de5fa0fa8e1d18e8db54fa31e48cc4826a870a060b444f2624498d5a'
BOOT_SHA = '50377dc8b9b304b00b300fa7927e56733c841d5d2ece9a90602874bb7f99c799'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def clone(source, target):
    require(not target.exists(), 'clone target exists')
    lib = ctypes.CDLL(None, use_errno=True)
    fn = lib.clonefile
    fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    fn.restype = ctypes.c_int
    if fn(os.fsencode(source), os.fsencode(target), 0):
        raise OSError(ctypes.get_errno(), 'native clone failed; no full-copy fallback')


def patch(path, offset, data):
    with path.open('r+b') as fp:
        fp.seek(offset);require(fp.write(data) == len(data), 'short patch')
        fp.flush();os.fsync(fp.fileno())


def elf_entry(data):
    require(data[:6] == b'\x7fELF\x01\x01', 'expected little-endian ELF32')
    require(struct.unpack_from('<H', data, 18)[0] == 40, 'expected ARM')
    offset = struct.unpack_from('<I', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 46)
    sections = [struct.unpack_from('<10I', data, offset + i*size) for i in range(count)]
    found = []
    for section in sections:
        if section[1] != 11:
            continue
        strings = sections[section[6]]
        names = data[strings[4]:strings[4]+strings[5]]
        for pos in range(section[4], section[4]+section[5], section[9]):
            name, value, length, info, other, index = struct.unpack_from('<IIIBBH', data, pos)
            if names[name:].split(b'\0', 1)[0] == b'get_gps_interface':
                require(value & 1 == 1, 'GPS entry is not Thumb')
                address = value & ~1
                sec = sections[index]
                found.append((address, sec[4]+address-sec[3]))
    require(found == [(0x2484, 0x1484)], 'unexpected GPS exported entry')
    return found[0][1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    out = args.output.resolve()
    require(not out.exists(), 'fresh output directory required')
    out.mkdir(parents=True)
    old_vendor = ROOT / 'out/diskless-v2-android/vendor-fstab.raw.img'
    old_bytes = old_vendor.read_bytes()
    require(sha(old_bytes) == VENDOR_SHA, 'original vendor mismatch')
    with Ext4Image(old_vendor) as fs:
        inode = fs.resolve('/lib/hw/gps.msm8960.so', follow_final=False)
        gps = fs.read_inode(inode)
    require(sha(gps) == GPS_SHA, 'GPS HAL source mismatch')
    require(gps[0x1484:0x1488] == bytes.fromhex('70b502f0'), 'unexpected original entry bytes')
    # Producer uses unique full-file byte matching, not the filesystem auditor's offset.
    start = old_bytes.find(gps)
    require(start >= 0 and old_bytes.find(gps, start+1) < 0, 'GPS file is not unique contiguous data')
    vendor = out / 'vendor-gps-null.raw.img'
    clone(old_vendor, vendor)
    patch(vendor, start+0x1484, bytes.fromhex('00207047'))
    # Independent consumer resolves actual file/ranges and ELF symbol, proving
    # unchanged inode, extents and every byte outside the exact four-byte delta.
    with Ext4Image(old_vendor) as before, Ext4Image(vendor) as after:
        old_i = before.resolve('/lib/hw/gps.msm8960.so', follow_final=False)
        new_i = after.resolve('/lib/hw/gps.msm8960.so', follow_final=False)
        require(old_i == new_i, 'GPS inode fields changed')
        ranges = before.file_ranges(old_i)
        require(ranges == after.file_ranges(new_i), 'GPS file ranges changed')
        original, current = before.read_inode(old_i), after.read_inode(new_i)
        require(elf_entry(original) == elf_entry(current) == 0x1484, 'ELF entry changed')
        require(current == original[:0x1484]+bytes.fromhex('00207047')+original[0x1488:], 'extra GPS changes')
        matches = [r['image_offset']+0x1484-r['file_offset'] for r in ranges
                   if r['file_offset'] <= 0x1484 and 0x1488 <= r['file_offset']+r['length']]
        require(len(matches) == 1, 'entry spans unsupported ranges')
        physical = matches[0]
    vendor_audit = compare_exact(old_vendor, vendor, [(physical, bytes.fromhex('00207047'))])
    require(vendor_audit['source_sha256'] == VENDOR_SHA and vendor_audit['changed_bytes'] == 4,
            'vendor delta gate failed')
    (out / 'gps-null.so').write_bytes(current)
    tool = subprocess.check_output(['xcrun', '--find', 'llvm-objdump'], text=True).strip()
    decoded = subprocess.run([tool, '--disassemble', '--triple=thumbv7-linux-android',
                              '--start-address=9348', '--stop-address=9352', str(out/'gps-null.so')],
                             capture_output=True, check=True)
    (out / 'entry-disassembly.txt').write_bytes(decoded.stdout)
    require(re.search(rb'\bmovs\s+r0,\s*#0', decoded.stdout) and re.search(rb'\bbx\s+lr\b', decoded.stdout),
            'independent entry decoding failed')
    print('VENDOR_ELF_FOUR_BYTE_AUDIT=PASS', flush=True)
    golden = Path.home() / 'nexus7-diskless-v2/diskless-v2-android.raw.img'
    baseline, disk = out/'pristine-Q1.raw.img', out/'disk.raw.img'
    clone(golden, baseline)
    system = ROOT/'out/phase6-v2-root-fstab-I/system-root-fstab.raw.img'
    with system.open('rb') as fp:
        fp.seek(2125824);fstab = fp.read(4295)
    require(sha(fstab) == 'bf0bf1502b5caf18a6d5de927c39a2185f9d60afacb05c1618e79ecc5657e6da', 'fstab source mismatch')
    patch(baseline, 3174400, fstab)
    clone(baseline, disk)
    cfg = load_layout(ROOT/'diskless-v2/layout.json');parts, sectors = calculate_layout(cfg)
    p2 = parts[1];p2_start,p2_size = p2['start_lba']*512,p2['sectors']*512
    patch(disk, p2_start+physical, bytes.fromhex('00207047'))
    disk_audit = compare_exact(baseline, disk, [(p2_start+physical, bytes.fromhex('00207047'))],
                               (p2_start,p2_start+p2_size))
    require(disk_audit['source_sha256'] == BASE_SHA and disk_audit['changed_bytes'] == 4, 'not Q1+four bytes')
    require(disk_audit['region_sha256'] == [VENDOR_SHA,vendor_audit['candidate_sha256']], 'p2/vendor identity mismatch')
    boot = ROOT/'out/phase6-v2-root-route-O/artifacts/diagnostic.img'
    require(sha(boot.read_bytes()) == BOOT_SHA, 'Q1 boot changed')
    obj = json.loads(Path(str(golden)+'.manifest.json').read_bytes())
    obj['disk'] = str(disk);obj['partitions'][0]['source_path'] = str(system)
    obj['partitions'][1]['source_path'] = str(vendor)
    manifest = Path(str(disk)+'.manifest.json')
    manifest.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    for name, command in [('disk-structure',[sys.executable,str(ROOT/'scripts/v2/validate_disk.py'),
                          '--disk',str(disk),'--manifest',str(manifest)]),
                         ('trace-map',[sys.executable,str(ROOT/'scripts/v2/prepare_phase6_v2_partition_trace.py'),
                          '--disk',str(disk),'--manifest',str(manifest),'--layout',str(ROOT/'diskless-v2/layout.json'),
                          '--output',str(out/'partition-trace-map.json')])]:
        result = subprocess.run(command,capture_output=True)
        (out/(name+'.stdout')).write_bytes(result.stdout);(out/(name+'.stderr')).write_bytes(result.stderr)
        require(result.returncode == 0, name+' failed')
    report = dict(status='HOST_PASS',hardware_authorized=False,runtime='IMPLEMENTED_UNPROVEN',
                  boot=str(boot),boot_sha256=BOOT_SHA,original_GPS_sha256=GPS_SHA,
                  modified_GPS_sha256=sha(current),GPS_file_offset=0x1484,vendor_physical_offset=physical,
                  vendor=vendor_audit,disk=disk_audit,
                  manifest_sha256=sha(manifest.read_bytes()),trace_map_sha256=sha((out/'partition-trace-map.json').read_bytes()),
                  diagnostic='GPS interface unavailable only; no kernel/rc/firmware changes')
    (out/'result.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('PHASE6_V2_GPS_NULL_HOST_GATE=PASS')
    print(json.dumps(report,sort_keys=True))


if __name__ == '__main__':
    main()
