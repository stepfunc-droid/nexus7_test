#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

CHUNK = 8 * 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_region(path: Path, offset: int, size: int) -> str:
    h = hashlib.sha256()
    remaining = size
    with path.open("rb") as fp:
        fp.seek(offset)
        while remaining:
            chunk = fp.read(min(CHUNK, remaining))
            if not chunk:
                raise SystemExit("ERROR: assembled disk ended early while hashing partition source region")
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify Phase 5C Android disk contains the exact clean system and fstab-only vendor sources")
    ap.add_argument("--disk", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--system", required=True, type=Path)
    ap.add_argument("--vendor", required=True, type=Path)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())
    sector_size = int(manifest["sector_size"])
    parts = {p["name"]: p for p in manifest["partitions"]}

    for name, source in (("system", args.system), ("vendor", args.vendor)):
        if name not in parts:
            raise SystemExit(f"ERROR: manifest missing {name} partition")
        p = parts[name]
        source_size = source.stat().st_size
        if int(p.get("source_size_bytes", -1)) != source_size:
            raise SystemExit(f"ERROR: manifest {name} source size mismatch")
        manifest_source = Path(p.get("source_path", "")).resolve()
        if manifest_source != source.resolve():
            raise SystemExit(
                f"ERROR: manifest {name} source path mismatch: {manifest_source} != {source.resolve()}"
            )

        source_sha = sha256_file(source)
        region_sha = sha256_region(args.disk, int(p["start_lba"]) * sector_size, source_size)
        if source_sha != region_sha:
            raise SystemExit(f"ERROR: assembled {name} bytes do not match source image")
        print(f"{name}_source_sha256={source_sha}")
        print(f"{name}_assembled_prefix_sha256={region_sha}")

    print("DISKLESS_V2_ANDROID_DISK_SOURCES_VERIFIED=1")
    print(f"disk={args.disk}")
    print("system_source=exact-clean-copy")
    print("vendor_source=exact-fstab-only-copy")


if __name__ == "__main__":
    main()
