#!/usr/bin/env python3
"""Audit the Phase6 V2 panic-timeout diagnostic wrapper against the accepted continuation."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_BASELINE_SHA256 = "2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc"

BASE_BLOCK = """[ -w /proc/sys/kernel/panic_on_oops ] && echo 1 > /proc/sys/kernel/panic_on_oops
[ -w /proc/sys/kernel/panic ] && echo 5 > /proc/sys/kernel/panic
"""

DIAGNOSTIC_BLOCK = """[ -w /proc/sys/kernel/panic_on_oops ] || fail "panic_on_oops sysctl not writable"
echo 1 > /proc/sys/kernel/panic_on_oops || fail "failed to set panic_on_oops=1"
PANIC_ON_OOPS="$($BB cat /proc/sys/kernel/panic_on_oops 2>/dev/null || true)"
[ "$PANIC_ON_OOPS" = "1" ] || fail "panic_on_oops readback=$PANIC_ON_OOPS expected=1"
[ -w /proc/sys/kernel/panic ] || fail "panic sysctl not writable"
echo 0 > /proc/sys/kernel/panic || fail "failed to set panic=0"
PANIC_TIMEOUT="$($BB cat /proc/sys/kernel/panic 2>/dev/null || true)"
[ "$PANIC_TIMEOUT" = "0" ] || fail "panic readback=$PANIC_TIMEOUT expected=0"
"""


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--replacement", required=True, type=Path)
    args = ap.parse_args()

    baseline = args.baseline.read_bytes()
    replacement = args.replacement.read_bytes()

    if sha256(baseline) != EXPECTED_BASELINE_SHA256:
        die("accepted continuation wrapper SHA changed")

    try:
        base_text = baseline.decode("utf-8")
        replacement_text = replacement.decode("utf-8")
    except UnicodeDecodeError as exc:
        die(f"wrapper is not UTF-8: {exc}")

    if base_text.count(BASE_BLOCK) != 1:
        die(f"expected exactly one accepted panic block; found {base_text.count(BASE_BLOCK)}")

    expected = base_text.replace(BASE_BLOCK, DIAGNOSTIC_BLOCK, 1)
    if replacement_text != expected:
        die("diagnostic wrapper contains bytes outside the exact allowed block replacement")

    if replacement_text.count(DIAGNOSTIC_BLOCK) != 1:
        die("diagnostic precondition block must occur exactly once")

    # The runtime precondition must complete before the supervisor starts waiting
    # for usb0 and before any NBD attach can occur. A later host-observed NBD
    # connection therefore implies that this fail-closed block passed.
    precondition_end = replacement_text.index(DIAGNOSTIC_BLOCK) + len(DIAGNOSTIC_BLOCK)
    usb_wait = replacement_text.find("while [ ! -e /sys/class/net/usb0 ]")
    nbd_call = replacement_text.find("NBD_ATTEMPT=0\nLAST_RETRY=0\nstart_nbd")
    if usb_wait < 0 or nbd_call < 0:
        die("could not locate accepted usb0/NBD runtime boundaries")
    if not (precondition_end < usb_wait < nbd_call):
        die("runtime panic read-back is not ordered before usb0/NBD")

    required = (
        'echo 0 > /proc/sys/kernel/panic || fail "failed to set panic=0"',
        'PANIC_TIMEOUT="$($BB cat /proc/sys/kernel/panic 2>/dev/null || true)"',
        '[ "$PANIC_TIMEOUT" = "0" ] || fail "panic readback=$PANIC_TIMEOUT expected=0"',
        'echo 1 > /proc/sys/kernel/panic_on_oops || fail "failed to set panic_on_oops=1"',
        'PANIC_ON_OOPS="$($BB cat /proc/sys/kernel/panic_on_oops 2>/dev/null || true)"',
        '[ "$PANIC_ON_OOPS" = "1" ] || fail "panic_on_oops readback=$PANIC_ON_OOPS expected=1"',
    )
    for fragment in required:
        if replacement_text.count(fragment) != 1:
            die(f"required diagnostic fragment missing or duplicated: {fragment}")

    forbidden = (
        "echo 5 > /proc/sys/kernel/panic",
        "androidboot.selinux=permissive",
        "/diskless-busybox",
        "rdinit=/diskless-init",
    )
    for fragment in forbidden:
        if fragment in replacement_text:
            die(f"forbidden diagnostic/runtime fragment present: {fragment}")

    print("DISKLESS_V2_PHASE6_V2_PANIC_HOLD_WRAPPER_AUDIT=PASS")
    print(f"baseline_sha256={sha256(baseline)}")
    print(f"replacement_sha256={sha256(replacement)}")
    print("causal_variable=kernel.panic:5->0")
    print("panic_on_oops_target=1")
    print("runtime_readback=fail-closed")
    print("readback_order=before-usb0-and-nbd")
    print("all_bytes_outside_precondition_block=unchanged")


if __name__ == "__main__":
    main()
