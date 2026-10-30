#!/usr/bin/env python3
"""Check preflight ordering/failure propagation with isolated child-gate fixtures.

This tests host orchestration only; fixture PASS markers are not artifact or
device evidence. The real gate must still run against accepted inputs.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


FROZEN = r'''#!/usr/bin/env bash
set -euo pipefail
echo frozen >> "$FIXTURE_CALLS"
[[ "$REPORT" == "$FIXTURE_FACT" ]]
[[ "$ANDROID_DISK" == "$FIXTURE_DISK" ]]
[[ "$DISK_MANIFEST" == "$FIXTURE_MANIFEST" ]]
if [[ "$FIXTURE_MODE" == frozen-fail ]]; then
    echo 'fixture frozen validation failed' >&2
    exit 19
fi
if [[ "$FIXTURE_MODE" == frozen-no-marker ]]; then exit 0; fi
echo 'fresh=yes' > "$REPORT"
echo 'DISKLESS_V2_PHASE6_V2_FROZEN_FACTS=PASS' >> "$REPORT"
cat "$REPORT"
'''

BASE = r'''#!/usr/bin/env bash
set -euo pipefail
echo base >> "$FIXTURE_CALLS"
grep -q '^fresh=yes$' "$FIXTURE_FACT"
[[ "$DISK" == "$FIXTURE_DISK" ]]
[[ "$MANIFEST" == "$FIXTURE_MANIFEST" ]]
[[ "$IMAGE" == "$FIXTURE_CONTINUATION" ]]
if [[ "$FIXTURE_MODE" == base-fail ]]; then exit 23; fi
echo 'DISKLESS_V2_PHASE6_V2_REAL_PREFLIGHT=PASS'
'''

HOST = r'''#!/usr/bin/env bash
set -euo pipefail
echo host >> "$FIXTURE_CALLS"
[[ "$FACT_REPORT" == "$FIXTURE_FACT" ]]
[[ "$REPORT" == "$FIXTURE_DIAG_REPORT" ]]
[[ "$OUTPUT" == "$FIXTURE_DIAG_IMAGE" ]]
grep -q '^fresh=yes$' "$FACT_REPORT"
echo fixture-image > "$OUTPUT"
cat > "$REPORT" <<'REPORT'
DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS
causal_variable=kernel.panic:5->0
panic_on_oops_target=1
runtime_precondition=fail-closed-readback-before-usb0-and-nbd
accepted_image_direct_panic_timeout_literals=0
writer_audit_limit=nonliteral-programmatic-sysctl-access-not-proven-absent
transport_setup=unchanged
android_init=unchanged
android_rc_modifications=none
selinux_policy=stock-enforcing-baseline
hardware_authorized=no
REPORT
echo "diagnostic_image_sha256=$(sha256sum "$OUTPUT" | awk '{print $1}')" >> "$REPORT"
echo 'DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS'
'''


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"ERROR: {message}")


def main() -> None:
    source = Path(__file__).with_name("phase6_v2_panic_hold_real_preflight.sh")
    cases = (
        ("frozen-fail", ["frozen"], False),
        ("frozen-no-marker", ["frozen"], False),
        ("base-fail", ["frozen", "base"], False),
        ("pass", ["frozen", "base", "host"], True),
    )
    with tempfile.TemporaryDirectory(prefix="phase6-v2-preflight-selftest-") as temp:
        root = Path(temp)
        scripts = root / "scripts/v2"
        scripts.mkdir(parents=True)
        target = scripts / source.name
        shutil.copyfile(source, target)
        for name, data in (
            ("phase6_v2_frozen_fact_gate.sh", FROZEN),
            ("phase6_v2_real_preflight.sh", BASE),
            ("phase6_v2_panic_hold_host_gate.sh", HOST),
        ):
            (scripts / name).write_text(data)
        for mode, expected_calls, expect_pass in cases:
            run = root / mode
            run.mkdir()
            fact = run / "custom-facts.txt"
            fact.write_text("DISKLESS_V2_PHASE6_V2_FROZEN_FACTS=PASS\nstale=yes\n")
            calls = run / "calls.txt"
            env = dict(os.environ)
            env.update({
                "OUT": str(run),
                "FACT_REPORT": str(fact),
                "REPORT": str(run / "custom-diagnostic-report.txt"),
                "IMAGE": str(run / "custom-diagnostic.img"),
                "CONTINUATION_IMAGE": str(run / "custom-continuation.img"),
                "DISK": str(run / "custom-disk.img"),
                "MANIFEST": str(run / "custom-manifest.json"),
                "FIXTURE_CALLS": str(calls),
                "FIXTURE_FACT": str(fact),
                "FIXTURE_DISK": str(run / "custom-disk.img"),
                "FIXTURE_MANIFEST": str(run / "custom-manifest.json"),
                "FIXTURE_CONTINUATION": str(run / "custom-continuation.img"),
                "FIXTURE_DIAG_REPORT": str(run / "custom-diagnostic-report.txt"),
                "FIXTURE_DIAG_IMAGE": str(run / "custom-diagnostic.img"),
                "FIXTURE_MODE": mode,
            })
            result = subprocess.run(["bash", str(target)], env=env,
                                    capture_output=True, text=True, timeout=30)
            actual_calls = calls.read_text().splitlines() if calls.exists() else []
            check(actual_calls == expected_calls,
                  f"{mode}: calls={actual_calls}, stderr={result.stderr}")
            marker = "DISKLESS_V2_PHASE6_V2_PANIC_HOLD_REAL_PREFLIGHT=PASS"
            check((result.returncode == 0) == expect_pass,
                  f"{mode}: exit={result.returncode}, stderr={result.stderr}")
            check((marker in result.stdout) == expect_pass,
                  f"{mode}: incorrect final PASS marker")
            if expect_pass:
                check("hardware_authorized=no" in result.stdout,
                      "fixture success self-authorized hardware")
            print(f"case={mode} result=PASS order={','.join(actual_calls)}")
    print("DISKLESS_V2_PHASE6_V2_PANIC_PREFLIGHT_SELFTEST=PASS")
    print("scope=isolated-host-orchestration-fixtures-only")


if __name__ == "__main__":
    main()
