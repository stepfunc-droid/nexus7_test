#!/usr/bin/env python3
"""Independent exact P2-to-route-diagnostic image delta audit; no device I/O."""
import argparse
import hashlib
import json
from pathlib import Path

import build_android_first_stage_probe as boot

P2_SHA = '09e277d628f46efe12b516493f07f29776894972402d51ea849b15b3b3119491'
BLOCK_SHA = '08f50f97201f622389a5f276929c68722b9125d0c3713e1c2ac8c36415669e65'
ANCHOR = b'$BB ifconfig usb0 "$NEXUS_IP" netmask 255.255.255.0 up || fail "failed to configure usb0"\n'


def require(value, text):
    if not value:
        raise ValueError(text)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'image', 'block', 'report'):
        ap.add_argument('--' + name, required=True, type=Path)
    args = ap.parse_args()
    require(not args.report.exists(), 'fresh report required')
    require(args.report.resolve() not in [p.resolve() for p in (args.baseline, args.image, args.block)],
            'report aliases input')
    require(sha(args.baseline.read_bytes()) == P2_SHA, 'wrong P2 identity')
    fragment = args.block.read_bytes()
    require(sha(fragment) == BLOCK_SHA, 'unreviewed policy block')
    original, candidate = boot.parse_boot(args.baseline), boot.parse_boot(args.image)
    for key in ('kernel', 'second', 'dt', 'board', 'cmdline_raw', 'extra_raw'):
        require(original[key] == candidate[key], 'changed boot payload/header: ' + key)
    for index, (old, new) in enumerate(zip(original['fields'], candidate['fields'])):
        if index != 2:  # compressed ramdisk size is the only changed geometry field
            require(old == new, f'header field changed: {index}')
    left = boot.parse_newc(boot.decompress_ramdisk(original['ramdisk']))
    right = boot.parse_newc(boot.decompress_ramdisk(candidate['ramdisk']))
    require([boot.norm(e[2]) for e in left] == [boot.norm(e[2]) for e in right], 'entry order/set changed')
    for before, after in zip(left, right):
        name = boot.norm(before[2])
        require(before[0] == after[0] and before[2] == after[2], 'cpio entry changed')
        old_meta, new_meta = list(before[1]), list(after[1])
        if name == 'init':
            old_meta[6] = new_meta[6]  # sole file length delta
            base, result = bytes(before[3]), bytes(after[3])
            require(base.count(ANCHOR) == 1, 'unexpected baseline insertion anchor')
            require(result == base.replace(ANCHOR, ANCHOR + fragment, 1), 'extra wrapper changes')
            require(result.index(fragment) < result.index(b'start_nbd()'), 'policy occurs after NBD setup')
        else:
            require(bytes(before[3]) == bytes(after[3]), 'entry payload changed: ' + name)
        require(old_meta == new_meta, 'cpio metadata changed: ' + name)
    report = dict(evidence_class='HOST_FACT', status='PASS', hardware_authorized=False,
                  baseline_sha256=P2_SHA, block_sha256=BLOCK_SHA,
                  image_sha256=sha(args.image.read_bytes()),
                  kernel_sha256=sha(candidate['kernel']), only_cpio_delta='/init file data/length',
                  android_rc_modifications='none', transport_attach_retry_handoff='unchanged',
                  runtime_effect='IMPLEMENTED_UNPROVEN',
                  precondition='ip/iprule present; host/32 priority0 main readback before NBD attach')
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print('PHASE6_V2_ROOT_ROUTE_IMAGE_AUDIT=PASS')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
