#!/usr/bin/env python3
"""Independent host-only audit for the Phase 6R1 clean full-boot image."""

import argparse
import hashlib
from pathlib import Path

import build_android_first_stage_probe as common

EXPECTED_ANDROID_INIT_SHA256 = "cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44"
EXPECTED_FSTAB_SHA256 = "834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf"
EXPECTED_BUSYBOX_SHA256 = "cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de"
ADDED = {"diskless-init", "diskless-busybox", "diskless-v2-layout"}


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit Phase6 6R1 image without booting Nexus")
    ap.add_argument("--android-boot", required=True, type=Path)
    ap.add_argument("--transport-boot", required=True, type=Path)
    ap.add_argument("--generated-fstab", required=True, type=Path)
    ap.add_argument("--wrapper", required=True, type=Path)
    ap.add_argument("--phase4-env", required=True, type=Path)
    ap.add_argument("--image", required=True, type=Path)
    args = ap.parse_args()

    for path in (args.android_boot, args.transport_boot, args.generated_fstab,
                 args.wrapper, args.phase4_env, args.image):
        if not path.is_file():
            die(f"required audit input not found: {path}")

    phase4 = common.parse_env(args.phase4_env)
    expected_kernel_sha = phase4.get("KERNEL_ZIMAGE_SHA256")
    if not expected_kernel_sha:
        die("phase4 env missing KERNEL_ZIMAGE_SHA256")

    source = common.parse_boot(args.android_boot)
    transport = common.parse_boot(args.transport_boot)
    image = common.parse_boot(args.image)

    smap = common.entry_map(common.parse_newc(common.decompress_ramdisk(source["ramdisk"])))
    tmap = common.entry_map(common.parse_newc(common.decompress_ramdisk(transport["ramdisk"])))
    ientries = common.parse_newc(common.decompress_ramdisk(image["ramdisk"]))
    imap = common.entry_map(ientries)

    source_names = {name for name in smap if name != "TRAILER!!!"}
    image_names = {name for name in imap if name != "TRAILER!!!"}
    if image_names - source_names != ADDED:
        die(f"unexpected added ramdisk entries: {sorted(image_names - source_names)}")
    if source_names - image_names:
        die(f"source ramdisk entries disappeared: {sorted(source_names - image_names)}")

    for name in sorted(source_names):
        before = smap[name]
        after = imap[name]
        if tuple(before[1]) != tuple(after[1]):
            die(f"original cpio metadata changed: {name}")
        if bytes(before[3]) != bytes(after[3]):
            die(f"original cpio payload changed: {name}")

    init_payload = bytes(imap["init"][3])
    if sha256(init_payload) != EXPECTED_ANDROID_INIT_SHA256:
        die("output stock /init identity mismatch")
    if "init.android" in imap:
        die("output contains forbidden /init.android")

    generated_fstab = args.generated_fstab.read_bytes()
    if sha256(generated_fstab) != EXPECTED_FSTAB_SHA256:
        die("generated fstab identity differs from accepted Phase5")
    if bytes(imap["fstab.flox"][3]) != generated_fstab:
        die("output /fstab.flox differs from accepted generated fstab")

    wrapper = args.wrapper.read_bytes()
    if bytes(imap["diskless-init"][3]) != wrapper:
        die("output /diskless-init differs from audited wrapper source")
    if not wrapper.startswith(b"#!/diskless-busybox sh\n"):
        die("wrapper interpreter is not /diskless-busybox")
    wrapper_text = wrapper.decode("utf-8")

    if bytes(imap["diskless-busybox"][3]) != bytes(tmap["bin/busybox"][3]):
        die("output BusyBox payload differs from accepted transport payload")
    if sha256(bytes(imap["diskless-busybox"][3])) != EXPECTED_BUSYBOX_SHA256:
        die("output BusyBox identity mismatch")
    if bytes(imap["diskless-v2-layout"][3]) != bytes(tmap["etc/diskless-v2-layout"][3]):
        die("output layout payload differs from accepted transport payload")

    required_wrapper = (
        "$BB nbd-client", "$BB umount /sys", "$BB umount /proc", "exec /init",
    )
    for fragment in required_wrapper:
        if fragment not in wrapper_text:
            die(f"wrapper missing required fragment: {fragment}")

    forbidden_wrapper = (
        "/init.android", "httpd", " nc ", "/proc/kmsg", "/dev/kmsg", "last_kmsg",
        "SIGSTOP", "11000", "11001", "2324", "2325", "androidboot.selinux=permissive",
        "exec 6", "exec 7", "&\nKMSG", "| $BB nc",
    )
    for fragment in forbidden_wrapper:
        if fragment in wrapper_text:
            die(f"wrapper contains forbidden diagnostic fragment: {fragment!r}")

    if sha256(bytes(image["kernel"])) != expected_kernel_sha:
        die("output kernel differs from accepted Phase4 zImage")

    for idx, label in ((1, "kernel_addr"), (3, "ramdisk_addr"), (5, "second_addr"),
                       (6, "tags_addr"), (7, "page_size")):
        if image["fields"][idx] != source["fields"][idx]:
            die(f"output changed Android boot geometry: {label}")

    if image["board"] != source["board"]:
        die("output changed Android boot board field")
    if bytes(image["second"]) != bytes(source["second"]):
        die("output changed Android boot second component")
    if bytes(image["dt"]) != bytes(source["dt"]):
        die("output changed Android boot dt component")

    tokens = image["cmdline"].split()
    required_tokens = (
        "androidboot.diskless=1", "nbd.max_part=8", "panic=5", "rdinit=/diskless-init",
    )
    for token in required_tokens:
        if tokens.count(token) != 1:
            die(f"cmdline does not contain exactly one {token}")
    if any(token.startswith("androidboot.selinux=") for token in tokens):
        die("cmdline contains explicit SELinux override")
    if any(token == "rdinit=/init" for token in tokens):
        die("cmdline still selects stock /init as rdinit")

    rc_added = sorted(name for name in ADDED if name.endswith(".rc"))
    if rc_added:
        die(f"6R1 unexpectedly added rc files: {rc_added}")

    print("DISKLESS_V2_PHASE6_R1_IMAGE_AUDIT=PASS")
    print(f"image={args.image}")
    print(f"image_sha256={hashlib.sha256(args.image.read_bytes()).hexdigest()}")
    print(f"kernel_sha256={expected_kernel_sha}")
    print(f"android_init_path=/init")
    print(f"android_init_sha256={sha256(init_payload)}")
    print(f"generated_fstab_sha256={sha256(generated_fstab)}")
    print(f"busybox_sha256={sha256(bytes(imap['diskless-busybox'][3]))}")
    print(f"wrapper_sha256={sha256(wrapper)}")
    print("rdinit=/diskless-init")
    print("original_ramdisk_entries=byte-and-metadata-identical")
    print("added_entries=/diskless-init,/diskless-busybox,/diskless-v2-layout")
    print("android_rc_modifications=none")
    print("diagnostic_logger=none")
    print("diagnostic_network_services=none")
    print("inherited_diagnostic_fds=none-by-wrapper-contract")
    print("selinux_policy=stock-enforcing-baseline")
    print("real_device_boot=not-performed")


if __name__ == "__main__":
    main()
