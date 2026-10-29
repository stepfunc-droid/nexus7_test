#!/usr/bin/env python3
"""Independent host audit for the Phase6 Audit-V2 continuation boot image."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import build_android_first_stage_probe as common

EXPECTED_KERNEL_SHA256 = "eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05"
EXPECTED_ANDROID_INIT_SHA256 = "cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44"
EXPECTED_FSTAB_SHA256 = "834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf"
EXPECTED_BUSYBOX_SHA256 = "cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de"


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def comparable_entry(entry):
    magic, vals, name, payload = entry
    return magic, tuple(vals), common.norm(name), bytes(payload)


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit Phase6 V2 continuation boot image")
    ap.add_argument("--android-boot", required=True, type=Path)
    ap.add_argument("--transport-boot", required=True, type=Path)
    ap.add_argument("--generated-fstab", required=True, type=Path)
    ap.add_argument("--wrapper", required=True, type=Path)
    ap.add_argument("--image", required=True, type=Path)
    args = ap.parse_args()

    for path in (args.android_boot, args.transport_boot, args.generated_fstab,
                 args.wrapper, args.image):
        if not path.is_file():
            die(f"required input missing: {path}")

    android = common.parse_boot(args.android_boot)
    transport = common.parse_boot(args.transport_boot)
    result = common.parse_boot(args.image)

    if sha256(result["kernel"]) != EXPECTED_KERNEL_SHA256:
        die("continuation image kernel differs from accepted Phase4 kernel")
    if result["kernel"] != transport["kernel"]:
        die("continuation kernel differs byte-for-byte from accepted transport kernel")
    if result["second"] != android["second"] or result["dt"] != android["dt"]:
        die("continuation changed Android second/dt payload")

    amap = common.entry_map(common.parse_newc(common.decompress_ramdisk(android["ramdisk"])))
    tmap = common.entry_map(common.parse_newc(common.decompress_ramdisk(transport["ramdisk"])))
    rmap = common.entry_map(common.parse_newc(common.decompress_ramdisk(result["ramdisk"])))

    original_init = bytes(amap["init"][3])
    if sha256(original_init) != EXPECTED_ANDROID_INIT_SHA256:
        die("Phase5B input /init identity is not the accepted Lineage init")
    if bytes(rmap.get("init.android", [None, None, None, b""])[3]) != original_init:
        die("/init.android is not exact accepted original Lineage init")

    wrapper = args.wrapper.read_bytes()
    if bytes(rmap.get("init", [None, None, None, b""])[3]) != wrapper:
        die("ramdisk /init is not exact Audit-V2 continuation wrapper")
    if not wrapper.startswith(b"#!/bin/busybox sh\n"):
        die("continuation wrapper lost accepted BusyBox shebang")

    generated_fstab = args.generated_fstab.read_bytes()
    if sha256(generated_fstab) != EXPECTED_FSTAB_SHA256:
        die("generated fstab identity differs from accepted Phase5")
    if bytes(rmap.get("fstab.flox", [None, None, None, b""])[3]) != generated_fstab:
        die("continuation /fstab.flox differs from exact accepted generated fstab")

    busybox = bytes(tmap.get("bin/busybox", [None, None, None, b""])[3])
    if sha256(busybox) != EXPECTED_BUSYBOX_SHA256:
        die("accepted transport BusyBox identity mismatch")
    if bytes(rmap.get("bin/busybox", [None, None, None, b""])[3]) != busybox:
        die("continuation /bin/busybox differs from accepted transport payload")

    layout = bytes(tmap.get("etc/diskless-v2-layout", [None, None, None, b""])[3])
    if not layout:
        die("accepted transport layout payload missing")
    if bytes(rmap.get("etc/diskless-v2-layout", [None, None, None, b""])[3]) != layout:
        die("continuation layout contract differs from accepted transport payload")

    # Every original Android ramdisk entry other than /init must remain exact.
    for name, entry in amap.items():
        if name == "init":
            continue
        if name not in rmap:
            die(f"continuation removed original Android ramdisk entry: {name}")
        if comparable_entry(rmap[name]) != comparable_entry(entry):
            die(f"continuation changed original Android ramdisk entry: {name}")

    allowed_added = {"init.android", "bin/busybox", "etc/diskless-v2-layout", "bin", "etc"}
    unexpected_added = sorted(set(rmap) - set(amap) - allowed_added)
    if unexpected_added:
        die("unexpected continuation ramdisk additions: " + ", ".join(unexpected_added))

    # There must be no Android rc modification/addition in the boot ramdisk.
    original_rc = {name for name in amap if name.endswith(".rc")}
    result_rc = {name for name in rmap if name.endswith(".rc")}
    if result_rc != original_rc:
        die(f"Android rc entry set changed: original={sorted(original_rc)} result={sorted(result_rc)}")

    tokens = result["cmdline"].split()
    for exact in ("androidboot.diskless=1", "nbd.max_part=8", "panic=5", "rdinit=/init"):
        if tokens.count(exact) != 1:
            die(f"accepted Phase5D cmdline token must occur exactly once: {exact}")
    if any(t.startswith("rdinit=") and t != "rdinit=/init" for t in tokens):
        die("continuation introduced a different rdinit target")
    if "androidboot.selinux=permissive" in tokens:
        die("continuation requests SELinux permissive")

    forbidden_entries = {
        "diskless-init",
        "diskless-busybox",
        "diskless-v2-layout",
    }
    present_forbidden = sorted(forbidden_entries & set(rmap))
    if present_forbidden:
        die("continuation contains revoked R1 entries: " + ", ".join(present_forbidden))

    print("DISKLESS_V2_PHASE6_V2_CONTINUATION_IMAGE_AUDIT=PASS")
    print(f"image_sha256={hashlib.sha256(args.image.read_bytes()).hexdigest()}")
    print(f"kernel_sha256={EXPECTED_KERNEL_SHA256}")
    print(f"android_init_sha256={EXPECTED_ANDROID_INIT_SHA256}")
    print(f"generated_fstab_sha256={EXPECTED_FSTAB_SHA256}")
    print(f"busybox_sha256={EXPECTED_BUSYBOX_SHA256}")
    print("busybox_path=/bin/busybox")
    print("supervisor_path=/init")
    print("android_first_stage_path=/init.android")
    print("rdinit=/init")
    print("android_rc_modifications=none")
    print("selinux_policy=stock-enforcing-baseline")
    print("revoked_r1_entries=absent")


if __name__ == "__main__":
    main()
