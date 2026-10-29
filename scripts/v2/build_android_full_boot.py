#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path

import build_android_first_stage_probe as common


def main():
    ap = argparse.ArgumentParser(description="Build deterministic diskless-v2 full Android boot image")
    ap.add_argument("--android-boot", required=True, type=Path,
                    help="accepted Phase 5B boot-fstab-only.img")
    ap.add_argument("--transport-boot", required=True, type=Path,
                    help="accepted Phase 4 diskless-v2-transport.img")
    ap.add_argument("--generated-fstab", required=True, type=Path)
    ap.add_argument("--wrapper", required=True, type=Path)
    ap.add_argument("--phase4-env", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    env = common.parse_env(args.phase4_env)
    expected_kernel_sha = env.get("KERNEL_ZIMAGE_SHA256")
    if not expected_kernel_sha:
        common.die("phase4 env missing KERNEL_ZIMAGE_SHA256")

    android = common.parse_boot(args.android_boot)
    transport = common.parse_boot(args.transport_boot)

    for idx, label in ((1, "kernel_addr"), (3, "ramdisk_addr"), (5, "second_addr"),
                       (6, "tags_addr"), (7, "page_size")):
        if android["fields"][idx] != transport["fields"][idx]:
            common.die(
                f"boot geometry mismatch for {label}: "
                f"android={android['fields'][idx]} transport={transport['fields'][idx]}"
            )

    kernel = transport["kernel"]
    kernel_sha = hashlib.sha256(kernel).hexdigest()
    if kernel_sha != expected_kernel_sha:
        common.die(
            f"transport kernel sha256={kernel_sha} expected accepted Phase4={expected_kernel_sha}"
        )
    if "androidboot.diskless=1" not in transport["cmdline"] or "nbd.max_part=8" not in transport["cmdline"]:
        common.die("transport boot cmdline does not carry accepted diskless policy")

    android_entries = common.parse_newc(common.decompress_ramdisk(android["ramdisk"]))
    transport_entries = common.entry_map(
        common.parse_newc(common.decompress_ramdisk(transport["ramdisk"]))
    )
    amap = common.entry_map(android_entries)

    if "init" not in amap:
        common.die("Android ramdisk missing /init")
    if "init.android" in amap or "bin/busybox" in amap or "etc/diskless-v2-layout" in amap:
        common.die("Android ramdisk already contains diskless supervisor entries")
    if "bin/busybox" not in transport_entries or "etc/diskless-v2-layout" not in transport_entries:
        common.die("accepted transport ramdisk missing BusyBox/layout contract")

    generated_fstab = args.generated_fstab.read_bytes()
    fstab_entries = [e for e in android_entries if common.norm(e[2]) == "fstab.flox"]
    if len(fstab_entries) != 1 or fstab_entries[0][3] != generated_fstab:
        common.die("Android input boot does not contain the exact accepted Phase 5 generated fstab")

    wrapper = args.wrapper.read_bytes()
    if not wrapper.startswith(b"#!/bin/busybox sh\n"):
        common.die("Phase6 wrapper must use the injected static BusyBox interpreter")
    if b"kill -STOP 1" in wrapper or b"SIGSTOP-after-first-stage-mounts" in wrapper:
        common.die("Phase6 wrapper still contains first-stage stop policy")
    if b"DISKLESS_V2_PHASE6_LIVE_KMSG_STREAM=1" not in wrapper:
        common.die("Phase6 wrapper missing live-kmsg handshake contract")

    original_init = bytes(amap["init"][3])
    original_init_sha = hashlib.sha256(original_init).hexdigest()

    patched = []
    trailer = None
    max_ino = 0
    for e in android_entries:
        max_ino = max(max_ino, int(e[1][0]))
        if common.norm(e[2]) == "TRAILER!!!":
            trailer = e
            continue
        if common.norm(e[2]) == "init":
            e = [e[0], list(e[1]), e[2], wrapper]
        patched.append(e)

    if trailer is None:
        common.die("Android ramdisk missing cpio trailer")

    next_ino = max_ino + 1
    names = {common.norm(e[2]) for e in patched}
    if "bin" not in names:
        patched.append(common.make_entry("bin", b"", 0o040755, next_ino)); next_ino += 1
    if "etc" not in names:
        patched.append(common.make_entry("etc", b"", 0o040755, next_ino)); next_ino += 1

    init_meta = list(amap["init"][1])
    init_meta[0] = next_ino; next_ino += 1
    patched.append([amap["init"][0], init_meta, "init.android", original_init])

    busy = transport_entries["bin/busybox"]
    busy_meta = list(busy[1]); busy_meta[0] = next_ino; next_ino += 1
    patched.append([busy[0], busy_meta, "bin/busybox", bytes(busy[3])])

    layout = transport_entries["etc/diskless-v2-layout"]
    layout_meta = list(layout[1]); layout_meta[0] = next_ino; next_ino += 1
    patched.append([layout[0], layout_meta, "etc/diskless-v2-layout", bytes(layout[3])])
    patched.append(trailer)

    cpio = common.build_newc(patched)
    ramdisk = common.gzip_deterministic(cpio)
    cmdline = common.clean_cmdline(android["cmdline"])
    common.repack(android, kernel, ramdisk, cmdline, args.output)

    result = common.parse_boot(args.output)
    rmap = common.entry_map(common.parse_newc(common.decompress_ramdisk(result["ramdisk"])))
    if rmap.get("init.android", [None, None, None, None])[3] != original_init:
        common.die("repacked Phase6 image lost exact original /init payload")
    if rmap.get("init", [None, None, None, None])[3] != wrapper:
        common.die("repacked Phase6 /init is not the full-boot supervisor")
    if rmap.get("fstab.flox", [None, None, None, None])[3] != generated_fstab:
        common.die("repacked Phase6 fstab differs from accepted Phase 5 fstab")
    if hashlib.sha256(result["kernel"]).hexdigest() != expected_kernel_sha:
        common.die("repacked Phase6 kernel differs from accepted Phase 4 kernel")
    if "androidboot.selinux=permissive" in result["cmdline"]:
        common.die("Phase6 baseline unexpectedly enables SELinux permissive")

    print("DISKLESS_V2_ANDROID_FULL_BOOT_BUILT=1")
    print(f"output={args.output}")
    print(f"output_sha256={hashlib.sha256(args.output.read_bytes()).hexdigest()}")
    print(f"kernel_sha256={kernel_sha}")
    print(f"android_init_sha256={original_init_sha}")
    print(f"generated_fstab_sha256={hashlib.sha256(generated_fstab).hexdigest()}")
    print(f"busybox_sha256={hashlib.sha256(bytes(busy[3])).hexdigest()}")
    print("android_init=preserved-as-/init.android")
    print("supervisor=single-nbd-full-boot")
    print("first_stage_stop=disabled")
    print("selinux_policy=stock-enforcing-baseline")
    print("android_rc_bypasses=none")
    print(f"cmdline={cmdline}")


if __name__ == "__main__":
    main()
