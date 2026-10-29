#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path

import build_android_first_stage_probe as common

MARKER = b"DISKLESS_V2_PHASE6_SECOND_STAGE_EARLY_INIT=1"
MARKER_BLOCK = b'''\n# diskless-v2 Phase6 diagnostic only: prove enforcing second-stage early-init.\n# Observation only; no mount, property, SELinux, service, or wait bypass.\non early-init\n    exec_background -- /system/bin/sh -c "echo DISKLESS_V2_PHASE6_SECOND_STAGE_EARLY_INIT=1 | /system/bin/toybox nc -w 5 -q 1 172.16.42.2 11001"\n'''


def main():
    ap = argparse.ArgumentParser(description="Build enforcing Phase6 second-stage early-init marker image")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    boot = common.parse_boot(args.input)
    tokens = boot["cmdline"].split()
    if "androidboot.selinux=permissive" in tokens:
        common.die("input is permissive; enforcing baseline required")
    if "androidboot.diskless=1" not in tokens or "nbd.max_part=8" not in tokens:
        common.die("input is not the accepted diskless-v2 Phase6 baseline")

    entries = common.parse_newc(common.decompress_ramdisk(boot["ramdisk"]))
    amap = common.entry_map(entries)
    for name in ("init", "init.android", "init.rc", "fstab.flox"):
        if name not in amap:
            common.die(f"input ramdisk missing /{name}")

    wrapper = bytes(amap["init"][3])
    if b"kernel_log_stream=disabled-linux-3.4" not in wrapper:
        common.die("input predates Linux 3.4 observer correction")
    if b"cat /dev/kmsg" in wrapper or b"cat /proc/kmsg" in wrapper:
        common.die("input still contains a kernel-log reader")

    init_rc = bytes(amap["init.rc"][3])
    if MARKER in init_rc:
        common.die("input /init.rc already contains marker")

    patched = []
    for e in entries:
        if common.norm(e[2]) == "init.rc":
            e = [e[0], list(e[1]), e[2], init_rc + MARKER_BLOCK]
        patched.append(e)

    ramdisk = common.gzip_deterministic(common.build_newc(patched))
    common.repack(boot, boot["kernel"], ramdisk, boot["cmdline"], args.output)

    result = common.parse_boot(args.output)
    rmap = common.entry_map(common.parse_newc(common.decompress_ramdisk(result["ramdisk"])))
    if result["kernel"] != boot["kernel"]:
        common.die("marker image changed kernel")
    if result["cmdline"] != boot["cmdline"]:
        common.die("marker image changed cmdline")
    if MARKER not in bytes(rmap["init.rc"][3]):
        common.die("marker missing after repack")
    if bytes(rmap["fstab.flox"][3]) != bytes(amap["fstab.flox"][3]):
        common.die("marker image changed fstab")
    if bytes(rmap["init.android"][3]) != bytes(amap["init.android"][3]):
        common.die("marker image changed original Android init")

    print("DISKLESS_V2_PHASE6_SECOND_STAGE_MARKER_IMAGE_BUILT=1")
    print(f"input={args.input}")
    print(f"input_sha256={hashlib.sha256(args.input.read_bytes()).hexdigest()}")
    print(f"output={args.output}")
    print(f"output_sha256={hashlib.sha256(args.output.read_bytes()).hexdigest()}")
    print("selinux_policy=stock-enforcing-baseline")
    print("marker_trigger=early-init")
    print("marker_port=11001")
    print("android_rc_bypasses=none")


if __name__ == "__main__":
    main()
