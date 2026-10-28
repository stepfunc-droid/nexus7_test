#!/usr/bin/env python3
import argparse
import mmap
import os
import shutil
import tempfile
from pathlib import Path

PATCHES = [
    (
        b"import init.flox.usb.rc\n",
        b"#mport init.flox.usb.rc\n",
        "flox USB init",
    ),
    (
        b"import /system/etc/init/hw/init.usb.rc\n",
        b"#mport /system/etc/init/hw/init.usb.rc\n",
        "generic USB init",
    ),
    (
        b"import /system/etc/init/hw/init.usb.configfs.rc\n",
        b"#mport /system/etc/init/hw/init.usb.configfs.rc\n",
        "generic configfs USB init",
    ),
    (
        b"    start devstart_sh\n",
        b"    #tart devstart_sh\n",
        "Qualcomm ADSP devstart",
    ),
    (
        b"    exec - root root system -- /vendor/bin/init.qcom.devwait.sh\n",
        b"    #xec - root root system -- /vendor/bin/init.qcom.devwait.sh\n",
        "Qualcomm ADSP devwait",
    ),
    (
        b"service installd /system/bin/installd\n"
        b"    class main\n"
        b"\n"
        b"on early-boot\n",
        b"service installd /system/bin/installd\n"
        b"    class main\n"
        b"\n"
        b"on charger   \n",
        "installd sdcardfs configfs early-boot block",
    ),
]


def patch_copy(source: Path, dest: Path) -> None:
    source = source.expanduser().resolve()
    dest = dest.expanduser().resolve()

    if source == dest:
        raise SystemExit("refusing to patch system image in place; destination must differ from source")
    if not source.is_file():
        raise SystemExit(f"source system image not found: {source}")

    for needle, replacement, _ in PATCHES:
        if len(replacement) != len(needle):
            raise SystemExit("internal error: diskless system replacement changed byte length")

    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=dest.name + ".", suffix=".tmp", dir=dest.parent)
    os.close(fd)
    tmp = Path(tmp_name)

    try:
        shutil.copyfile(source, tmp)

        with tmp.open("r+b") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as mm:
                for needle, replacement, label in PATCHES:
                    count = 0
                    pos = 0
                    hit = -1
                    while True:
                        pos = mm.find(needle, pos)
                        if pos < 0:
                            break
                        hit = pos
                        count += 1
                        pos += len(needle)

                    if count == 0 and mm.find(replacement) >= 0:
                        print(f"{label}: already disabled")
                        continue
                    if count != 1:
                        raise SystemExit(
                            f"expected exactly one {label!r} match in {source}, found {count}"
                        )

                    mm[hit:hit + len(needle)] = replacement
                    print(f"{label}: disabled")

                mm.flush()

                for _, replacement, label in PATCHES:
                    if mm.find(replacement) < 0:
                        raise SystemExit(f"patch verification failed for {label}")

        os.replace(tmp, dest)
        print(f"patched system image written: {dest}")
        print(
            "Android USB gadget init, flox ADSP devstart/devwait, and installd "
            "sdcardfs configfs early-boot setup disabled; original system image was not modified"
        )
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Create a diskless system image copy with Android USB gadget "
            "reconfiguration, flox Qualcomm ADSP startup/wait, and installd "
            "sdcardfs configfs early-boot setup disabled"
        )
    )
    ap.add_argument("source", help="original/raw diskless system ext4 image")
    ap.add_argument("destination", help="patched raw system ext4 image to create")
    args = ap.parse_args()
    patch_copy(Path(args.source), Path(args.destination))


if __name__ == "__main__":
    main()
