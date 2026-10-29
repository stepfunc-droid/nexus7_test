#!/usr/bin/env python3
import argparse
import difflib
import hashlib
from pathlib import Path

from patch_boot_fstab import parse_boot, decompress_ramdisk, parse_newc

HEADER = b"# Android fstab file.\n"
ZRAM = b"/dev/block/zram0"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_boot_fstab(path: Path) -> bytes:
    meta = parse_boot(path)
    entries = parse_newc(decompress_ramdisk(meta["ramdisk"]))
    found = []
    for _magic, _vals, name, payload in entries:
        normalized = name[2:] if name.startswith("./") else name
        if normalized == "fstab.flox":
            found.append(payload)
    if len(found) != 1:
        raise SystemExit(f"ERROR: expected exactly one fstab.flox in boot ramdisk, found {len(found)}")
    return found[0]


def extract_vendor_fstab(path: Path) -> bytes:
    data = path.read_bytes()
    candidates = []
    start = 0
    while True:
        start = data.find(HEADER, start)
        if start < 0:
            break
        zpos = data.find(ZRAM, start, min(len(data), start + 65536))
        if zpos >= 0:
            end = data.find(b"\n", zpos, min(len(data), start + 65536))
            if end >= 0:
                candidates.append(data[start:end + 1])
        start += len(HEADER)
    if len(candidates) != 1:
        raise SystemExit(
            f"ERROR: expected exactly one embedded flox fstab candidate in vendor raw image, found {len(candidates)}"
        )
    return candidates[0]


def classify(data: bytes) -> str:
    if b"/dev/block/nbd" in data or b"/dev/nbd0p" in data:
        return "modified-nbd"
    if b"msm_sdcc.1/by-name/system" in data:
        return "stock-emmc-style"
    return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit the original flox fstab embedded in boot and vendor artifacts")
    ap.add_argument("--boot", required=True, type=Path)
    ap.add_argument("--vendor", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--repo-stock", type=Path)
    args = ap.parse_args()

    boot_fstab = extract_boot_fstab(args.boot)
    vendor_fstab = extract_vendor_fstab(args.vendor)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    boot_out = args.out_dir / "fstab.boot.original"
    vendor_out = args.out_dir / "fstab.vendor.original"
    artifact_out = args.out_dir / "fstab.artifact.stock"
    boot_out.write_bytes(boot_fstab)
    vendor_out.write_bytes(vendor_fstab)

    boot_state = classify(boot_fstab)
    vendor_state = classify(vendor_fstab)
    print("DISKLESS_V2_ANDROID_FSTAB_SOURCE_AUDIT=1")
    print(f"boot_fstab_sha256={sha(boot_fstab)}")
    print(f"vendor_fstab_sha256={sha(vendor_fstab)}")
    print(f"boot_fstab_state={boot_state}")
    print(f"vendor_fstab_state={vendor_state}")

    if args.repo_stock:
        repo = args.repo_stock.read_bytes()
        print(f"repo_stock_fstab_sha256={sha(repo)}")
        print(f"boot_matches_repo_stock={'yes' if boot_fstab == repo else 'no'}")
        print(f"vendor_matches_repo_stock={'yes' if vendor_fstab == repo else 'no'}")

    if boot_fstab != vendor_fstab:
        print("--- boot/vendor fstab diff ---")
        a = boot_fstab.decode("utf-8", "replace").splitlines()
        b = vendor_fstab.decode("utf-8", "replace").splitlines()
        for line in difflib.unified_diff(a, b, fromfile="boot:flox", tofile="vendor:flox", lineterm=""):
            print(line)
        raise SystemExit("ERROR: original boot and vendor fstab copies are not byte-identical")

    if boot_state != "stock-emmc-style":
        raise SystemExit(
            f"ERROR: actual ROM artifact fstab is not a clean stock eMMC-style baseline: state={boot_state}"
        )

    artifact_out.write_bytes(boot_fstab)
    print("boot_vendor_fstab_identical=yes")
    print(f"artifact_stock_fstab={artifact_out}")
    print(f"artifact_stock_fstab_sha256={sha(boot_fstab)}")
    print("DISKLESS_V2_ANDROID_FSTAB_ARTIFACT_BASELINE_VERIFIED=1")


if __name__ == "__main__":
    main()
