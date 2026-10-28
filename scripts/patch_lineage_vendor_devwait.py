#!/usr/bin/env python3
import argparse
import mmap
import os
import shutil
import tempfile
from pathlib import Path

NEEDLE = (
    b"#!/system/bin/sh\n\n"
    b"up=\"`getprop sys.qcom.devup`\"\n"
    b"while [ \"$up\" != \"1\" ]\n"
    b"do\n"
    b"    sleep 0.1\n"
    b"    up=\"`getprop sys.qcom.devup`\"\n"
    b"done\n"
)

MARKER = b"nexus7_test diskless: skip blocking Qualcomm devwait"
REPLACEMENT_HEAD = (
    b"#!/system/bin/sh\n"
    b"# nexus7_test diskless: skip blocking Qualcomm devwait\n"
    b"exit 0\n"
)


def patch_copy(source: Path, dest: Path) -> None:
    source = source.expanduser().resolve()
    dest = dest.expanduser().resolve()

    if source == dest:
        raise SystemExit("refusing to patch vendor image in place; destination must differ from source")
    if not source.is_file():
        raise SystemExit(f"source vendor image not found: {source}")
    if len(REPLACEMENT_HEAD) > len(NEEDLE):
        raise SystemExit("internal error: replacement is longer than original devwait script")

    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=dest.name + ".", suffix=".tmp", dir=dest.parent)
    os.close(fd)
    tmp = Path(tmp_name)

    try:
        shutil.copyfile(source, tmp)

        with tmp.open("r+b") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as mm:
                count = 0
                pos = 0
                hit = -1
                while True:
                    pos = mm.find(NEEDLE, pos)
                    if pos < 0:
                        break
                    hit = pos
                    count += 1
                    pos += len(NEEDLE)

                if count != 1:
                    raise SystemExit(
                        f"expected exactly one init.qcom.devwait.sh payload in {source}, found {count}"
                    )

                replacement = REPLACEMENT_HEAD + b"#" * (len(NEEDLE) - len(REPLACEMENT_HEAD))
                mm[hit:hit + len(NEEDLE)] = replacement
                mm.flush()

                if mm.find(MARKER) < 0:
                    raise SystemExit("patch verification failed: marker not found in patched vendor image")

        os.replace(tmp, dest)
        print(f"patched vendor image written: {dest}")
        print("init.qcom.devwait.sh now exits immediately; original vendor image was not modified")
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Create a diskless vendor image copy with Qualcomm init.qcom.devwait.sh bypassed"
    )
    ap.add_argument("source", help="original raw vendor ext4 image")
    ap.add_argument("destination", help="patched raw vendor ext4 image to create")
    args = ap.parse_args()
    patch_copy(Path(args.source), Path(args.destination))


if __name__ == "__main__":
    main()
