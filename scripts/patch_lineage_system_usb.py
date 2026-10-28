#!/usr/bin/env python3
import argparse
import mmap
import os
import shutil
import tempfile
from pathlib import Path

NEEDLE = b"import init.flox.usb.rc\n"
REPLACEMENT = b"#mport init.flox.usb.rc\n"
MARKER = REPLACEMENT


def patch_copy(source: Path, dest: Path) -> None:
    source = source.expanduser().resolve()
    dest = dest.expanduser().resolve()

    if source == dest:
        raise SystemExit("refusing to patch system image in place; destination must differ from source")
    if not source.is_file():
        raise SystemExit(f"source system image not found: {source}")
    if len(REPLACEMENT) != len(NEEDLE):
        raise SystemExit("internal error: USB import replacement changed byte length")

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

                if count == 0 and mm.find(MARKER) >= 0:
                    print(f"{source}: init.flox.usb.rc import already disabled")
                elif count != 1:
                    raise SystemExit(
                        f"expected exactly one 'import init.flox.usb.rc' in {source}, found {count}"
                    )
                else:
                    mm[hit:hit + len(NEEDLE)] = REPLACEMENT
                    mm.flush()

                if mm.find(MARKER) < 0:
                    raise SystemExit("patch verification failed: disabled USB import marker not found")

        os.replace(tmp, dest)
        print(f"patched system image written: {dest}")
        print("init.flox.usb.rc import disabled; original system image was not modified")
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Create a diskless system image copy with flox Android USB reconfiguration disabled"
    )
    ap.add_argument("source", help="original/raw diskless system ext4 image")
    ap.add_argument("destination", help="patched raw system ext4 image to create")
    args = ap.parse_args()
    patch_copy(Path(args.source), Path(args.destination))


if __name__ == "__main__":
    main()
