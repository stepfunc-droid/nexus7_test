#!/usr/bin/env python3
"""Read-only audit for direct panic-timeout writers in accepted Android images.

The experiment depends on panic_timeout remaining 0 after the supervisor's
fail-closed pre-handoff read-back. This scanner binds to the accepted system
and patched-vendor identities, then scans their raw bytes for canonical direct
writer literals. It never modifies either image.

This is a conservative artifact audit: any direct literal targeting
/proc/sys/kernel/panic (other than panic_on_oops) or kernel.panic causes FAIL.
"""

from __future__ import annotations

import argparse
import hashlib
import mmap
from pathlib import Path

EXPECTED_SYSTEM_SHA256 = "a43a7c2def20e5fe3be5404624de8a9c30dea1fe3ff2d2f84a6e8240c4ae1880"
CHUNK = 8 * 1024 * 1024
TOKENS = (b"/proc/sys/kernel/panic", b"kernel.panic")
ALLOWED_SUFFIX = b"_on_oops"


def die(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def parse_fact_report(path: Path) -> dict[str, str]:
    facts: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        facts[key.strip()] = value.strip()
    return facts


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def printable_context(data: bytes) -> str:
    out = []
    for b in data:
        if 32 <= b < 127:
            out.append(chr(b))
        elif b in (9, 10, 13):
            out.append(" ")
        else:
            out.append(".")
    return "".join(out).replace("|", "!")


def scan(path: Path) -> tuple[list[dict], list[dict]]:
    allowed: list[dict] = []
    forbidden: list[dict] = []

    with path.open("rb") as fp:
        if path.stat().st_size == 0:
            return allowed, forbidden
        with mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for token in TOKENS:
                pos = mm.find(token)
                while pos >= 0:
                    end = pos + len(token)
                    suffix = mm[end:end + len(ALLOWED_SUFFIX)]
                    before = max(0, pos - 64)
                    after = min(len(mm), end + 96)
                    item = {
                        "offset": pos,
                        "token": token.decode("ascii"),
                        "context": printable_context(mm[before:after]),
                    }
                    if suffix == ALLOWED_SUFFIX:
                        allowed.append(item)
                    else:
                        forbidden.append(item)
                    pos = mm.find(token, pos + 1)

    return allowed, forbidden


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True, type=Path)
    ap.add_argument("--vendor", required=True, type=Path)
    ap.add_argument("--fact-report", required=True, type=Path)
    args = ap.parse_args()

    for p in (args.system, args.vendor, args.fact_report):
        if not p.is_file():
            die(f"required input missing: {p}")

    facts = parse_fact_report(args.fact_report)
    if facts.get("DISKLESS_V2_PHASE6_V2_FROZEN_FACTS") != "PASS":
        die("frozen-fact report is not PASS")

    system_sha = sha256_file(args.system)
    if system_sha != EXPECTED_SYSTEM_SHA256:
        die(f"system sha256={system_sha} expected={EXPECTED_SYSTEM_SHA256}")
    if facts.get("system_sha256") != EXPECTED_SYSTEM_SHA256:
        die("frozen-fact report system identity differs from accepted system")

    vendor_expected = facts.get("vendor_fstab_sha256", "")
    if len(vendor_expected) != 64:
        die("frozen-fact report lacks vendor_fstab_sha256")
    vendor_sha = sha256_file(args.vendor)
    if vendor_sha != vendor_expected:
        die(f"vendor sha256={vendor_sha} expected frozen fact={vendor_expected}")

    total_forbidden = 0
    total_allowed = 0
    for label, path, digest in (
        ("system", args.system, system_sha),
        ("vendor", args.vendor, vendor_sha),
    ):
        allowed, forbidden = scan(path)
        total_allowed += len(allowed)
        total_forbidden += len(forbidden)
        print(f"IMAGE name={label} path={path} sha256={digest}")
        print(f"IMAGE_RESULT name={label} panic_on_oops_literals={len(allowed)} direct_panic_literals={len(forbidden)}")
        for item in allowed:
            print(
                "ALLOWED_LITERAL "
                f"image={label} offset={item['offset']} token={item['token']!r} context={item['context']!r}"
            )
        for item in forbidden:
            print(
                "FORBIDDEN_LITERAL "
                f"image={label} offset={item['offset']} token={item['token']!r} context={item['context']!r}"
            )

    if total_forbidden:
        die(f"accepted Android images contain {total_forbidden} potential direct panic-timeout writer literal(s)")
    if total_allowed == 0:
        die("expected at least one panic_on_oops literal in accepted Android images; artifact/source mismatch suspected")

    print("DISKLESS_V2_PHASE6_V2_PANIC_RUNTIME_WRITER_AUDIT=PASS")
    print(f"system_sha256={system_sha}")
    print(f"vendor_sha256={vendor_sha}")
    print(f"panic_on_oops_literals={total_allowed}")
    print("direct_panic_timeout_literals=0")
    print("scope=accepted-system-and-patched-vendor-raw-image-bytes")
    print("claim=no-canonical-direct-panic-timeout-writer-literal-found")
    print("claim_limit=does-not-prove-absence-of-a-writer-using-nonliteral-programmatic-sysctl-access")


if __name__ == "__main__":
    main()
