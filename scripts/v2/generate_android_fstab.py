#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            die(f"invalid env line in {path}: {raw}")
        key, value = line.split("=", 1)
        out[key] = value
    return out


def parse_fstab_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 5:
            die(f"stock fstab row does not have 5 fields: {raw}")
        rows.append(fields)
    return rows


def require_partition(parts: dict[str, dict], name: str, fs: str, readonly: bool) -> dict:
    if name not in parts:
        die(f"layout missing partition: {name}")
    p = parts[name]
    if p.get("filesystem") != fs:
        die(f"layout {name} filesystem={p.get('filesystem')} expected={fs}")
    if bool(p.get("readonly")) != readonly:
        die(f"layout {name} readonly={p.get('readonly')} expected={readonly}")
    number = p.get("number")
    if not isinstance(number, int) or number <= 0:
        die(f"layout {name} has invalid partition number: {number}")
    return p


def find_unique(rows: list[list[str]], mount_point: str, fs_type: str) -> list[str]:
    matches = [r for r in rows if r[1] == mount_point and r[2] == fs_type]
    if len(matches) != 1:
        die(f"expected exactly one stock {fs_type} row for {mount_point}; found {len(matches)}")
    return matches[0]


def fmt(row: list[str]) -> str:
    return f"{row[0]:<34} {row[1]:<10} {row[2]:<6} {row[3]:<78} {row[4]}"


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    default_stock = root / "diskless-v2/fstab.flox.stock"
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, default=root / "diskless-v2/layout.json")
    parser.add_argument("--stock", type=Path, default=default_stock)
    parser.add_argument("--env", type=Path, default=root / "diskless-v2/android.env")
    parser.add_argument("--expected-stock-sha256")
    parser.add_argument("--stock-label")
    parser.add_argument("--output", type=Path, default=root / "out/diskless-v2-android/fstab.flox")
    args = parser.parse_args()

    env = parse_env(args.env)
    required_env = {
        "ANDROID_DEVICE_BASE_COMMIT",
        "ANDROID_FSTAB_PATH",
        "ANDROID_FSTAB_SHA256",
    }
    missing = sorted(required_env - env.keys())
    if missing:
        die(f"android.env missing keys: {', '.join(missing)}")

    stock_bytes = args.stock.read_bytes()
    stock_sha = hashlib.sha256(stock_bytes).hexdigest()
    expected_sha = args.expected_stock_sha256
    if expected_sha is None and args.stock.resolve() == default_stock.resolve():
        expected_sha = env["ANDROID_FSTAB_SHA256"]
    if expected_sha is not None and stock_sha != expected_sha:
        die(f"stock fstab sha256={stock_sha} does not match expected {expected_sha}")
    stock_rows = parse_fstab_rows(stock_bytes.decode())

    layout = json.loads(args.layout.read_text())
    if layout.get("schema") != 1:
        die(f"unsupported layout schema: {layout.get('schema')}")
    if layout.get("partition_table") != "dos":
        die("Android fstab generator expects DOS/MBR v2 layout")

    parts = {p["name"]: p for p in layout.get("partitions", []) if "name" in p}
    system = require_partition(parts, "system", "ext4", True)
    vendor = require_partition(parts, "vendor", "ext4", True)
    cache = require_partition(parts, "cache", "ext4", False)
    userdata = require_partition(parts, "userdata", "ext4", False)
    persist = require_partition(parts, "persist", "ext4", False)
    metadata = require_partition(parts, "metadata", "raw", False)

    # Android first-stage init mounts tmpfs on /dev and DeviceHandler creates
    # SUBSYSTEM=block nodes under /dev/block/<basename>. The transport wrapper's
    # temporary /dev/nbd0pN nodes disappear at this handoff, so Android fstab
    # must use the canonical Android block-device namespace.
    pdev = {
        "system": f"/dev/block/nbd0p{system['number']}",
        "vendor": f"/dev/block/nbd0p{vendor['number']}",
        "cache": f"/dev/block/nbd0p{cache['number']}",
        "userdata": f"/dev/block/nbd0p{userdata['number']}",
        "persist": f"/dev/block/nbd0p{persist['number']}",
        "metadata": f"/dev/block/nbd0p{metadata['number']}",
    }

    system_row = find_unique(stock_rows, "/system", "ext4").copy()
    vendor_row = find_unique(stock_rows, "/vendor", "ext4").copy()
    cache_row = find_unique(stock_rows, "/cache", "ext4").copy()
    data_row = find_unique(stock_rows, "/data", "ext4").copy()
    persist_row = find_unique(stock_rows, "/persist", "ext4").copy()

    system_row[0] = pdev["system"]
    vendor_row[0] = pdev["vendor"]
    cache_row[0] = pdev["cache"]
    data_row[0] = pdev["userdata"]
    persist_row[0] = pdev["persist"]

    vendor_flags = [f for f in vendor_row[4].split(",") if f not in {"check", "formattable"}]
    vendor_row[4] = ",".join(vendor_flags)

    data_flags = []
    replaced_metadata = False
    for flag in data_row[4].split(","):
        if flag.startswith("encryptable="):
            data_flags.append(f"encryptable={pdev['metadata']}")
            replaced_metadata = True
        else:
            data_flags.append(flag)
    if not replaced_metadata:
        die("stock userdata ext4 row has no encryptable= metadata policy")
    data_row[4] = ",".join(data_flags)

    passthrough: list[list[str]] = []
    for row in stock_rows:
        if row[1] in {"/system", "/vendor", "/cache", "/data", "/persist"}:
            continue
        if row[0].startswith("/dev/block/platform/msm_sdcc.1/"):
            continue
        passthrough.append(row)

    generated = [system_row, vendor_row, cache_row, data_row, persist_row, *passthrough]

    if args.stock_label:
        stock_source = args.stock_label
    else:
        stock_source = f"{env['ANDROID_FSTAB_PATH']} @ {env['ANDROID_DEVICE_BASE_COMMIT']}"

    header = [
        "# Generated by scripts/v2/generate_android_fstab.py; DO NOT EDIT.",
        f"# Stock source: {stock_source}",
        f"# Stock sha256: {stock_sha}",
        "# Partition source of truth: diskless-v2/layout.json",
        "# Android block namespace: /dev/block/nbd0pN (first-stage DeviceHandler).",
        "# system/vendor are immutable; vendor check/formattable is intentionally removed.",
        "",
    ]
    output = "\n".join(header + [fmt(r) for r in generated]) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output)

    print("DISKLESS_V2_ANDROID_FSTAB_GENERATED=1")
    print(f"output={args.output}")
    print(f"stock_source={stock_source}")
    print(f"stock_fstab_sha256={stock_sha}")
    print("android_block_namespace=/dev/block")
    for name in ("system", "vendor", "cache", "userdata", "persist", "metadata"):
        print(f"{name}={pdev[name]}")


if __name__ == "__main__":
    main()
