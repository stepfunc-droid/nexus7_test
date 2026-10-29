#!/usr/bin/env python3
"""Build the Phase 6R1 clean full-boot image from accepted Phase 4/5 artifacts."""

import argparse
import hashlib
from pathlib import Path

import build_android_first_stage_probe as common

EXPECTED_ANDROID_INIT_SHA256 = "cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44"
EXPECTED_FSTAB_SHA256 = "834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf"
EXPECTED_BUSYBOX_SHA256 = "cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de"


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean_cmdline(stock: str) -> str:
    remove_prefixes = ("androidboot.diskless=", "nbd.max_part=", "panic=", "rdinit=")
    tokens = [token for token in stock.split() if not token.startswith(remove_prefixes)]
    if any(token.startswith("androidboot.selinux=") for token in tokens):
        die("accepted Android boot must not contain an explicit SELinux mode override")
    tokens += [
        "androidboot.diskless=1",
        "nbd.max_part=8",
        "panic=5",
        "rdinit=/diskless-init",
    ]
    result = " ".join(tokens)
    if len(result.encode()) > 1536:
        die("Phase6 R1 cmdline exceeds legacy boot header capacity")
    return result


def clone_entry(entry):
    return [entry[0], list(entry[1]), entry[2], bytes(entry[3])]


def main() -> None:
    ap = argparse.ArgumentParser(description="Build deterministic Phase6 6R1 clean full-boot image")
    ap.add_argument("--android-boot", required=True, type=Path,
                    help="accepted Phase5B boot-fstab-only.img")
    ap.add_argument("--transport-boot", required=True, type=Path,
                    help="accepted Phase4 transport boot image")
    ap.add_argument("--generated-fstab", required=True, type=Path)
    ap.add_argument("--wrapper", required=True, type=Path)
    ap.add_argument("--phase4-env", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    for path in (args.android_boot, args.transport_boot, args.generated_fstab,
                 args.wrapper, args.phase4_env):
        if not path.is_file():
            die(f"required input not found: {path}")

    env = common.parse_env(args.phase4_env)
    expected_kernel_sha = env.get("KERNEL_ZIMAGE_SHA256")
    if not expected_kernel_sha:
        die("phase4 env missing KERNEL_ZIMAGE_SHA256")

    android = common.parse_boot(args.android_boot)
    transport = common.parse_boot(args.transport_boot)

    for idx, label in ((1, "kernel_addr"), (3, "ramdisk_addr"), (5, "second_addr"),
                       (6, "tags_addr"), (7, "page_size")):
        if android["fields"][idx] != transport["fields"][idx]:
            die(
                f"boot geometry mismatch for {label}: "
                f"android={android['fields'][idx]} transport={transport['fields'][idx]}"
            )

    kernel = bytes(transport["kernel"])
    kernel_sha = sha256(kernel)
    if kernel_sha != expected_kernel_sha:
        die(f"transport kernel sha256={kernel_sha} expected={expected_kernel_sha}")

    android_entries = common.parse_newc(common.decompress_ramdisk(android["ramdisk"]))
    transport_entries = common.entry_map(
        common.parse_newc(common.decompress_ramdisk(transport["ramdisk"]))
    )
    amap = common.entry_map(android_entries)

    if "init" not in amap:
        die("accepted Android ramdisk missing /init")
    original_init = bytes(amap["init"][3])
    original_init_sha = sha256(original_init)
    if original_init_sha != EXPECTED_ANDROID_INIT_SHA256:
        die(f"Android /init sha256={original_init_sha} expected={EXPECTED_ANDROID_INIT_SHA256}")

    generated_fstab = args.generated_fstab.read_bytes()
    if sha256(generated_fstab) != EXPECTED_FSTAB_SHA256:
        die("generated fstab identity differs from accepted Phase5 value")
    fstab = amap.get("fstab.flox")
    if fstab is None or bytes(fstab[3]) != generated_fstab:
        die("accepted Android boot does not contain exact Phase5 /fstab.flox")

    forbidden_existing = {
        "init.android", "diskless-init", "diskless-busybox", "diskless-v2-layout",
        "bin/busybox", "etc/diskless-v2-layout",
    }
    present_forbidden = sorted(forbidden_existing.intersection(amap))
    if present_forbidden:
        die("accepted Android ramdisk already contains supervisor artifacts: "
            + ", ".join(present_forbidden))

    if "bin/busybox" not in transport_entries or "etc/diskless-v2-layout" not in transport_entries:
        die("accepted transport ramdisk missing BusyBox/layout payload")
    busybox = bytes(transport_entries["bin/busybox"][3])
    layout = bytes(transport_entries["etc/diskless-v2-layout"][3])
    if sha256(busybox) != EXPECTED_BUSYBOX_SHA256:
        die("accepted transport BusyBox identity changed")

    wrapper = args.wrapper.read_bytes()
    if not wrapper.startswith(b"#!/diskless-busybox sh\n"):
        die("6R1 wrapper must use /diskless-busybox as its interpreter")
    wrapper_text = wrapper.decode("utf-8")
    required_wrapper_fragments = (
        "BB=/diskless-busybox",
        "LAYOUT=/diskless-v2-layout",
        "nbd-client",
        "umount /sys",
        "umount /proc",
        "exec /init",
    )
    for fragment in required_wrapper_fragments:
        if fragment not in wrapper_text:
            die(f"6R1 wrapper missing required contract fragment: {fragment}")
    forbidden_wrapper_fragments = (
        "/init.android", "httpd", "/proc/kmsg", "/dev/kmsg", "last_kmsg",
        "SIGSTOP", "11000", "11001", "2324", "2325",
        "androidboot.selinux=permissive",
    )
    for fragment in forbidden_wrapper_fragments:
        if fragment in wrapper_text:
            die(f"6R1 wrapper contains forbidden diagnostic/runtime fragment: {fragment}")

    trailer = None
    patched = []
    max_ino = 0
    original_names = []
    for entry in android_entries:
        max_ino = max(max_ino, int(entry[1][0]))
        name = common.norm(entry[2])
        if name == "TRAILER!!!":
            trailer = clone_entry(entry)
            continue
        original_names.append(name)
        patched.append(clone_entry(entry))
    if trailer is None:
        die("accepted Android ramdisk missing cpio trailer")

    next_ino = max_ino + 1
    patched.append(common.make_entry("diskless-init", wrapper, 0o100755, next_ino)); next_ino += 1
    patched.append(common.make_entry("diskless-busybox", busybox, 0o100755, next_ino)); next_ino += 1
    patched.append(common.make_entry("diskless-v2-layout", layout, 0o100644, next_ino)); next_ino += 1
    patched.append(trailer)

    cpio = common.build_newc(patched)
    ramdisk = common.gzip_deterministic(cpio)
    cmdline = clean_cmdline(android["cmdline"])
    common.repack(android, kernel, ramdisk, cmdline, args.output)

    # Parse and independently verify the constructed output before reporting success.
    result = common.parse_boot(args.output)
    result_entries = common.parse_newc(common.decompress_ramdisk(result["ramdisk"]))
    rmap = common.entry_map(result_entries)

    if bytes(rmap["init"][3]) != original_init:
        die("output changed stock /init payload")
    if sha256(bytes(rmap["init"][3])) != EXPECTED_ANDROID_INIT_SHA256:
        die("output /init identity mismatch")
    if bytes(rmap["fstab.flox"][3]) != generated_fstab:
        die("output changed accepted /fstab.flox")
    if bytes(rmap.get("diskless-init", [None, None, None, b""])[3]) != wrapper:
        die("output /diskless-init does not match wrapper source")
    if bytes(rmap.get("diskless-busybox", [None, None, None, b""])[3]) != busybox:
        die("output /diskless-busybox does not match accepted transport BusyBox")
    if bytes(rmap.get("diskless-v2-layout", [None, None, None, b""])[3]) != layout:
        die("output /diskless-v2-layout does not match accepted transport layout")
    if "init.android" in rmap:
        die("output unexpectedly contains /init.android")

    output_original_names = [
        common.norm(entry[2]) for entry in result_entries
        if common.norm(entry[2]) not in {
            "diskless-init", "diskless-busybox", "diskless-v2-layout", "TRAILER!!!"
        }
    ]
    if output_original_names != original_names:
        die("output changed original ramdisk entry order/names")

    for name in original_names:
        before = amap[name]
        after = rmap[name]
        if tuple(before[1]) != tuple(after[1]) or bytes(before[3]) != bytes(after[3]):
            die(f"output changed original ramdisk entry metadata/payload: {name}")

    if sha256(bytes(result["kernel"])) != expected_kernel_sha:
        die("output kernel differs from accepted Phase4 kernel")

    tokens = result["cmdline"].split()
    for token in ("androidboot.diskless=1", "nbd.max_part=8", "panic=5", "rdinit=/diskless-init"):
        if tokens.count(token) != 1:
            die(f"output cmdline must contain exactly one {token}")
    if any(token.startswith("androidboot.selinux=") for token in tokens):
        die("output cmdline contains forbidden explicit SELinux override")
    if any(token == "rdinit=/init" for token in tokens):
        die("output cmdline still points rdinit at stock /init")

    print("DISKLESS_V2_PHASE6_R1_IMAGE_BUILT=1")
    print(f"output={args.output}")
    print(f"output_sha256={hashlib.sha256(args.output.read_bytes()).hexdigest()}")
    print(f"kernel_sha256={kernel_sha}")
    print(f"android_init_path=/init")
    print(f"android_init_sha256={original_init_sha}")
    print(f"generated_fstab_sha256={sha256(generated_fstab)}")
    print(f"busybox_sha256={sha256(busybox)}")
    print(f"wrapper_sha256={sha256(wrapper)}")
    print("rdinit=/diskless-init")
    print("android_init=unchanged-path-and-bytes")
    print("ramdisk_original_entries=unchanged")
    print("ramdisk_added_entries=/diskless-init,/diskless-busybox,/diskless-v2-layout")
    print("diagnostic_children=none")
    print("selinux_policy=stock-enforcing-baseline")
    print("android_rc_bypasses=none")
    print(f"cmdline={result['cmdline']}")


if __name__ == "__main__":
    main()
