#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path

PATCHES = [
    (b"import init.flox.usb.rc\n", b"#mport init.flox.usb.rc\n", "flox USB init"),
    (b"import /system/etc/init/hw/init.usb.rc\n", b"#mport /system/etc/init/hw/init.usb.rc\n", "generic USB init"),
    (b"import /system/etc/init/hw/init.usb.configfs.rc\n", b"#mport /system/etc/init/hw/init.usb.configfs.rc\n", "generic configfs USB init"),
    (b"    start devstart_sh\n", b"    #tart devstart_sh\n", "Qualcomm ADSP devstart"),
    (b"    exec - root root system -- /vendor/bin/init.qcom.devwait.sh\n", b"    #xec - root root system -- /vendor/bin/init.qcom.devwait.sh\n", "Qualcomm ADSP devwait"),
    (
        b"service installd /system/bin/installd\n    class main\n\non early-boot\n",
        b"service installd /system/bin/installd\n    class main\n\non charger   \n",
        "installd sdcardfs configfs early-boot block",
    ),
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Fail-closed audit of a clean stock Lineage system raw image for Phase 5C")
    ap.add_argument("--image", required=True, type=Path)
    args = ap.parse_args()

    if not args.image.is_file():
        raise SystemExit(f"ERROR: system image not found: {args.image}")

    data = args.image.read_bytes()
    failures = []
    for original, replacement, label in PATCHES:
        original_count = data.count(original)
        replacement_count = data.count(replacement)
        print(f"{label}: original={original_count} v1_replacement={replacement_count}")
        if original_count != 1 or replacement_count != 0:
            failures.append(label)

    if failures:
        raise SystemExit(
            "ERROR: system image is not a clean stock source for Phase 5C; failed markers: "
            + ", ".join(failures)
        )

    print("DISKLESS_V2_ANDROID_SYSTEM_SOURCE_VERIFIED=1")
    print(f"system_image={args.image}")
    print(f"system_sha256={hashlib.sha256(data).hexdigest()}")
    print("v1_system_rc_bypasses=absent")


if __name__ == "__main__":
    main()
