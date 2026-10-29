#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def parse_rows(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 5:
            die(f"generated fstab row does not have 5 fields: {raw}")
        rows.append(fields)
    return rows


def one(rows: list[list[str]], mount_point: str) -> list[str]:
    found = [r for r in rows if r[1] == mount_point]
    if len(found) != 1:
        die(f"expected exactly one row for {mount_point}; found {len(found)}")
    return found[0]


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, default=root / "diskless-v2/layout.json")
    parser.add_argument("--fstab", type=Path, default=root / "out/diskless-v2-android/fstab.flox")
    args = parser.parse_args()

    layout = json.loads(args.layout.read_text())
    parts = {p["name"]: p for p in layout.get("partitions", []) if "name" in p}
    required = {"system", "vendor", "cache", "userdata", "persist", "metadata"}
    missing = sorted(required - parts.keys())
    if missing:
        die(f"layout missing required partitions: {', '.join(missing)}")

    expected_dev = {name: f"/dev/block/nbd0p{parts[name]['number']}" for name in required}
    rows = parse_rows(args.fstab)

    if any("msm_sdcc.1" in field or "/by-name/" in field for row in rows for field in row):
        die("generated fstab still contains eMMC/by-name references")
    if any(row[2] == "f2fs" for row in rows):
        die("generated fstab must not contain f2fs fallback rows")
    if any(row[0].startswith("/dev/nbd0") for row in rows):
        die("generated fstab uses transport-wrapper /dev/nbd* namespace instead of Android /dev/block")

    expected = {
        "/system": (expected_dev["system"], "ext4", "ro,barrier=1", "wait,first_stage_mount"),
        "/vendor": (expected_dev["vendor"], "ext4", "ro,barrier=1", "wait,first_stage_mount"),
        "/cache": (
            expected_dev["cache"],
            "ext4",
            "noatime,nosuid,nodev,barrier=1,data=ordered,noauto_da_alloc,errors=panic",
            "wait,check,formattable",
        ),
        "/data": (
            expected_dev["userdata"],
            "ext4",
            "noatime,nosuid,nodev,barrier=1,data=ordered,noauto_da_alloc,errors=panic",
            f"latemount,wait,check,formattable,encryptable={expected_dev['metadata']}",
        ),
        "/persist": (
            expected_dev["persist"],
            "ext4",
            "noatime,nosuid,nodev,barrier=1,data=ordered,nodelalloc",
            "wait",
        ),
    }

    for mount_point, exp in expected.items():
        row = one(rows, mount_point)
        actual = (row[0], row[2], row[3], row[4])
        if actual != exp:
            die(f"{mount_point} row mismatch: actual={actual!r} expected={exp!r}")

    usb_rows = [r for r in rows if r[0] == "/devices/platform/msm_hsusb_host/usb*"]
    if usb_rows != [[
        "/devices/platform/msm_hsusb_host/usb*",
        "auto",
        "auto",
        "defaults",
        "voldmanaged=usb:auto",
    ]]:
        die("stock USB-host vold row was not preserved exactly")

    zram_rows = [r for r in rows if r[0] == "/dev/block/zram0"]
    if zram_rows != [[
        "/dev/block/zram0",
        "none",
        "swap",
        "defaults",
        "zramsize=1610612736,notrim",
    ]]:
        die("stock zram row was not preserved exactly")

    allowed_sources = {
        expected_dev["system"],
        expected_dev["vendor"],
        expected_dev["cache"],
        expected_dev["userdata"],
        expected_dev["persist"],
        "/devices/platform/msm_hsusb_host/usb*",
        "/dev/block/zram0",
    }
    unexpected = sorted({r[0] for r in rows if r[0] not in allowed_sources})
    if unexpected:
        die(f"unexpected fstab source rows: {', '.join(unexpected)}")

    if len(rows) != 7:
        die(f"generated fstab must contain exactly 7 active rows; found {len(rows)}")

    digest = hashlib.sha256(args.fstab.read_bytes()).hexdigest()
    print("DISKLESS_V2_ANDROID_FSTAB_VERIFIED=1")
    print(f"fstab={args.fstab}")
    print(f"fstab_sha256={digest}")
    print("android_block_namespace=/dev/block")
    print(f"system={expected_dev['system']}")
    print(f"vendor={expected_dev['vendor']}")
    print(f"cache={expected_dev['cache']}")
    print(f"userdata={expected_dev['userdata']}")
    print(f"persist={expected_dev['persist']}")
    print(f"metadata={expected_dev['metadata']}")
    print("emmc_references=absent")
    print("f2fs_fallbacks=absent")
    print("vendor_formattable=disabled")
    print("usb_vold=preserved")
    print("zram=preserved")


if __name__ == "__main__":
    main()
