#!/usr/bin/env python3
"""Audit the Phase6 Audit-V2 continuation wrapper against accepted Phase5D.

This is intentionally a subtraction audit: executable lines in the continuation
wrapper must be exactly the accepted Phase5D executable lines minus explicitly
retired diagnostic/stop behavior.  New executable lines are not accepted.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_PHASE5D_WRAPPER_GIT_BLOB = "4863e82cbaf4cca4ae0544e2fd667c2f9d95317a"


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def executable_lines(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(stripped)
    return out


def expected_continuation_exec_lines(baseline_text: str) -> list[str]:
    """Return accepted Phase5D executable lines after allowed deletions only."""
    kept: list[str] = []
    in_observer = False
    skip_printf_continuation = False

    for raw in baseline_text.splitlines():
        s = raw.strip()

        if skip_printf_continuation:
            skip_printf_continuation = raw.rstrip().endswith("\\")
            continue

        if in_observer:
            if s == 'kill -0 "$KMSG_PIPE_PID" 2>/dev/null || fail "live-kmsg TCP stream could not connect to $HOST:$KMSG_PORT"':
                in_observer = False
            continue

        if s == 'exec 6</sys/block/nbd0/pid || fail "could not pin NBD pid sysfs descriptor"':
            in_observer = True
            continue

        if s == '$BB httpd -p 2325 -h /www':
            continue

        if s.startswith('set_status HANDOFF "single NBD verified; live-kmsg pipeline active;'):
            continue

        if s.startswith("printf 'diskless-v2: handing off to original Lineage first-stage init"):
            skip_printf_continuation = raw.rstrip().endswith("\\")
            continue

        if not s or s.startswith("#"):
            continue
        kept.append(s)

    if in_observer:
        die("baseline observer removal boundary did not terminate")
    if skip_printf_continuation:
        die("baseline handoff printf continuation did not terminate")
    return kept


def require_once(lines: list[str], exact: str, label: str) -> None:
    count = sum(1 for line in lines if line == exact)
    if count != 1:
        die(f"{label}: expected exactly once, found {count}: {exact}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit Phase6 V2 continuation wrapper semantic delta")
    ap.add_argument("--baseline", required=True, type=Path,
                    help="accepted Phase5D diskless-v2-android-first-stage-init")
    ap.add_argument("--replacement", required=True, type=Path,
                    help="Phase6 V2 continuation wrapper")
    args = ap.parse_args()

    baseline = args.baseline.read_bytes()
    replacement = args.replacement.read_bytes()

    baseline_blob = git_blob_sha1(baseline)
    if baseline_blob != EXPECTED_PHASE5D_WRAPPER_GIT_BLOB:
        die(
            f"Phase5D baseline git-blob={baseline_blob} "
            f"expected={EXPECTED_PHASE5D_WRAPPER_GIT_BLOB}"
        )

    if not replacement.startswith(b"#!/bin/busybox sh\n"):
        die("replacement changed accepted BusyBox shebang contract")

    baseline_exec = executable_lines(baseline.decode())
    replacement_exec = executable_lines(replacement.decode())
    expected_exec = expected_continuation_exec_lines(baseline.decode())

    if replacement_exec != expected_exec:
        # Find the first semantic difference to keep failures actionable.
        common = min(len(replacement_exec), len(expected_exec))
        idx = next((i for i in range(common) if replacement_exec[i] != expected_exec[i]), common)
        got = replacement_exec[idx] if idx < len(replacement_exec) else "<EOF>"
        want = expected_exec[idx] if idx < len(expected_exec) else "<EOF>"
        die(
            "UNJUSTIFIED_RUNTIME_DELTA at executable-line "
            f"{idx + 1}: got={got!r} expected={want!r}"
        )

    required_exact = [
        "BB=/bin/busybox",
        "export PATH=/bin:/sbin",
        "HOST=172.16.42.2",
        "PORT=10810",
        "NEXUS_IP=172.16.42.1",
        "LAYOUT=/etc/diskless-v2-layout",
        '$BB ifconfig usb0 "$NEXUS_IP" netmask 255.255.255.0 up || fail "failed to configure usb0"',
        '($BB nbd-client "$HOST" "$PORT" /dev/nbd0) >> "$NBD_LOG" 2>&1 &',
        'nbd_alive || fail "nbd0 never established kernel session/capacity after $NBD_ATTEMPT attempts"',
        'validate_partition nbd0p1 "$P1_SECTORS"',
        'validate_partition nbd0p2 "$P2_SECTORS"',
        'validate_partition nbd0p3 "$P3_SECTORS"',
        'validate_partition nbd0p5 "$P5_SECTORS"',
        'validate_partition nbd0p6 "$P6_SECTORS"',
        'validate_partition nbd0p7 "$P7_SECTORS"',
        '$BB umount /dev/pts || fail "umount /dev/pts failed before Android handoff"',
        '$BB umount -l /sys || fail "lazy umount /sys failed before Android handoff"',
        '$BB umount -l /proc || fail "lazy umount /proc failed before Android handoff"',
        "exec /init.android",
    ]
    for exact in required_exact:
        require_once(replacement_exec, exact, "accepted-runtime-contract")

    forbidden_fragments = [
        "$BB httpd ",
        "$BB nc ",
        "cat /proc/kmsg",
        "kill -STOP",
        "exec 6<",
        "exec 7>",
        "/diskless-busybox",
        "rdinit=/diskless-init",
        "androidboot.selinux=permissive",
    ]
    for frag in forbidden_fragments:
        if any(frag in line for line in replacement_exec):
            die(f"forbidden retired/runtime-redesign fragment remains: {frag}")

    # Exactly one intentional background launch is inherited: BusyBox nbd-client.
    background = [line for line in replacement_exec if line.endswith(" &")]
    if background != [
        '($BB nbd-client "$HOST" "$PORT" /dev/nbd0) >> "$NBD_LOG" 2>&1 &'
    ]:
        die(f"unexpected background-process contract: {background}")

    # The continuation supervisor may inspect geometry for p3/p5/p6, but it must
    # not perform filesystem-content I/O there.  This preserves the later-stage
    # partition-I/O evidence boundary for Audit V2.
    forbidden_partition_content_io = (
        "dd if=/dev/nbd0p3",
        "dd if=/dev/nbd0p5",
        "dd if=/dev/nbd0p6",
        "mount /dev/nbd0p3",
        "mount /dev/nbd0p5",
        "mount /dev/nbd0p6",
    )
    for frag in forbidden_partition_content_io:
        if any(frag in line for line in replacement_exec):
            die(f"replacement violates later-stage partition-I/O boundary: {frag}")

    removed_count = len(baseline_exec) - len(replacement_exec)
    print("DISKLESS_V2_PHASE6_V2_WRAPPER_SEMANTIC_DIFF=PASS")
    print(f"phase5d_baseline_git_blob={baseline_blob}")
    print(f"replacement_sha256={hashlib.sha256(replacement).hexdigest()}")
    print(f"baseline_executable_lines={len(baseline_exec)}")
    print(f"replacement_executable_lines={len(replacement_exec)}")
    print(f"removed_executable_lines={removed_count}")
    print("unchanged_transport_runtime=PASS")
    print("removed_http_runtime=PASS")
    print("removed_live_kmsg_observer=PASS")
    print("removed_sigstop_gate=PASS")
    print("busybox_invocation_contract=/bin/busybox")
    print("handoff=exec-/init.android")
    print("p3_p5_p6_content_io_by_supervisor=absent")
    print("new_executable_lines=0")


if __name__ == "__main__":
    main()
