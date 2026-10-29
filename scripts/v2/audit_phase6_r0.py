#!/usr/bin/env python3
"""Host-only Phase 6 reset audit. No device interaction."""

import argparse
import hashlib
import json
from pathlib import Path

import build_android_first_stage_probe as common

EXPECTED_ANDROID_BOOT_SHA256 = "42eec568a08f53e4c0efee01549dc36a4dcea0adb984ead02a5cb4306c4a00e6"
EXPECTED_TRANSPORT_BOOT_SHA256 = "6d99a16ab431cc3b980bf7244f4b85d2127b5d8ec1d57eeb4d106e3137a6fc87"
EXPECTED_KERNEL_SHA256 = "eada4515730b55d752d651302739eeb575db74607691ecc94e2236a43bce4e05"
EXPECTED_ANDROID_INIT_SHA256 = "cca67df0618802059d1e3e27859285f5601e9c9026b6c1fab0d39624d07dcf44"
EXPECTED_FSTAB_SHA256 = "834fea2ebaead67bcbd09cfd38a9ce3fdac9543b3f1b615cda43b3b46efd05bf"
EXPECTED_SYSTEM_SHA256 = "a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880"
EXPECTED_BUSYBOX_SHA256 = "cb1e8388f3b4f2ebf23bb7bf3dafedc24e1665dcc8950ba7ba664c22342f01de"


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        die(f"{label} not found: {path}")


def expected_layout_contract(layout_path: Path) -> bytes:
    data = json.loads(layout_path.read_text())
    if data.get("partition_table") != "dos":
        die("layout is not DOS/MBR")
    if int(data.get("sector_size", 0)) != 512:
        die("layout sector size is not 512")
    if int(data.get("nbd_max_part", 0)) != 8:
        die("layout nbd_max_part is not 8")

    wanted = {1, 2, 3, 5, 6, 7}
    parts = {int(p["number"]): p for p in data["partitions"] if int(p["number"]) in wanted}
    if set(parts) != wanted:
        die(f"layout missing required partitions: {sorted(wanted - set(parts))}")

    lines = ["NBD_MAX_PART=8"]
    for number in sorted(parts):
        part = parts[number]
        size = int(part["size_bytes"])
        if size % 512:
            die(f"p{number} size is not sector aligned")
        lines.append(f"P{number}_NAME={part['name']}")
        lines.append(f"P{number}_SECTORS={size // 512}")
        lines.append(f"P{number}_FILESYSTEM={part.get('filesystem', 'raw')}")
    return ("\n".join(lines) + "\n").encode()


def main() -> None:
    ap = argparse.ArgumentParser(description="Diskless-v2 Phase 6R0 host-only artifact audit")
    ap.add_argument("--android-boot", required=True, type=Path,
                    help="accepted Phase 5B boot-fstab-only.img")
    ap.add_argument("--transport-boot", required=True, type=Path,
                    help="accepted Phase 4 diskless-v2-transport.img")
    ap.add_argument("--generated-fstab", required=True, type=Path)
    ap.add_argument("--layout", required=True, type=Path)
    ap.add_argument("--phase4-env", required=True, type=Path)
    ap.add_argument("--system", required=True, type=Path,
                    help="clean system.raw.img used for the Android-test disk")
    args = ap.parse_args()

    for path, label in (
        (args.android_boot, "accepted Phase 5B boot"),
        (args.transport_boot, "accepted Phase 4 transport boot"),
        (args.generated_fstab, "generated fstab"),
        (args.layout, "layout.json"),
        (args.phase4_env, "phase4-accepted.env"),
        (args.system, "clean system image"),
    ):
        require_file(path, label)

    android_boot_sha = sha256_file(args.android_boot)
    if android_boot_sha != EXPECTED_ANDROID_BOOT_SHA256:
        die(f"Phase 5B boot sha256={android_boot_sha} expected={EXPECTED_ANDROID_BOOT_SHA256}")

    transport_boot_sha = sha256_file(args.transport_boot)
    if transport_boot_sha != EXPECTED_TRANSPORT_BOOT_SHA256:
        die(
            f"Phase 4 transport boot sha256={transport_boot_sha} "
            f"expected={EXPECTED_TRANSPORT_BOOT_SHA256}"
        )

    generated_fstab = args.generated_fstab.read_bytes()
    generated_fstab_sha = sha256_bytes(generated_fstab)
    if generated_fstab_sha != EXPECTED_FSTAB_SHA256:
        die(f"generated fstab sha256={generated_fstab_sha} expected={EXPECTED_FSTAB_SHA256}")

    system_sha = sha256_file(args.system)
    if system_sha != EXPECTED_SYSTEM_SHA256:
        die(f"clean system sha256={system_sha} expected={EXPECTED_SYSTEM_SHA256}")

    phase4 = common.parse_env(args.phase4_env)
    if phase4.get("KERNEL_ZIMAGE_SHA256") != EXPECTED_KERNEL_SHA256:
        die("phase4-accepted.env kernel identity does not match accepted Phase 4")

    android = common.parse_boot(args.android_boot)
    transport = common.parse_boot(args.transport_boot)
    amap = common.entry_map(common.parse_newc(common.decompress_ramdisk(android["ramdisk"])))
    tmap = common.entry_map(common.parse_newc(common.decompress_ramdisk(transport["ramdisk"])))

    if "init" not in amap:
        die("accepted Phase 5B boot ramdisk has no /init")
    init_payload = bytes(amap["init"][3])
    init_sha = sha256_bytes(init_payload)
    if init_sha != EXPECTED_ANDROID_INIT_SHA256:
        die(f"Android /init sha256={init_sha} expected={EXPECTED_ANDROID_INIT_SHA256}")

    fstab = amap.get("fstab.flox")
    if fstab is None:
        die("accepted Phase 5B boot ramdisk has no /fstab.flox")
    if bytes(fstab[3]) != generated_fstab:
        die("accepted Phase 5B /fstab.flox differs from exact generated fstab")

    forbidden_android_entries = [
        name for name in ("init.android", "diskless-init", "bin/busybox", "etc/diskless-v2-layout")
        if name in amap
    ]
    if forbidden_android_entries:
        die("accepted Android boot is already contaminated by supervisor entries: "
            + ", ".join(forbidden_android_entries))

    rc_entries = sorted(name for name in amap if name.endswith(".rc"))
    if rc_entries:
        die("accepted Phase 5B boot unexpectedly contains Android rc files: " + ", ".join(rc_entries))

    kernel_sha = sha256_bytes(transport["kernel"])
    if kernel_sha != EXPECTED_KERNEL_SHA256:
        die(f"transport kernel sha256={kernel_sha} expected={EXPECTED_KERNEL_SHA256}")

    for required in ("bin/busybox", "etc/diskless-v2-layout"):
        if required not in tmap:
            die(f"accepted transport ramdisk missing {required}")

    busybox = bytes(tmap["bin/busybox"][3])
    busybox_sha = sha256_bytes(busybox)
    if busybox_sha != EXPECTED_BUSYBOX_SHA256:
        die(f"transport BusyBox sha256={busybox_sha} expected={EXPECTED_BUSYBOX_SHA256}")

    layout_contract = bytes(tmap["etc/diskless-v2-layout"][3])
    expected_contract = expected_layout_contract(args.layout)
    if layout_contract != expected_contract:
        die("accepted transport layout contract differs from layout.json")

    if "androidboot.diskless=1" not in transport["cmdline"].split():
        die("accepted transport cmdline missing androidboot.diskless=1")
    if "nbd.max_part=8" not in transport["cmdline"].split():
        die("accepted transport cmdline missing nbd.max_part=8")

    print("DISKLESS_V2_PHASE6_R0_ARTIFACT_AUDIT=PASS")
    print(f"android_boot_sha256={android_boot_sha}")
    print(f"transport_boot_sha256={transport_boot_sha}")
    print(f"kernel_sha256={kernel_sha}")
    print(f"android_init_path=/init")
    print(f"android_init_sha256={init_sha}")
    print(f"generated_fstab_sha256={generated_fstab_sha}")
    print(f"system_sha256={system_sha}")
    print(f"busybox_sha256={busybox_sha}")
    print("busybox_source=exact-accepted-transport-payload")
    print("boot_ramdisk_android_rc_entries=0")
    print("boot_ramdisk_supervisor_entries=absent")
    print("rdinit_support=pinned-kernel-source-audited")
    print("target_handoff=/diskless-init->exec-/init")
    print("nexus_boot_required=no")


if __name__ == "__main__":
    main()
