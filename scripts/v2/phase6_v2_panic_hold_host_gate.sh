#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
ANDROID_BOOT="${ANDROID_BOOT:-$OUT/boot-fstab-only.img}"
TRANSPORT_BOOT="${TRANSPORT_BOOT:-$ROOT/out/diskless-v2-transport.img}"
GENERATED_FSTAB="${GENERATED_FSTAB:-$OUT/fstab.flox}"
PHASE4_ENV="${PHASE4_ENV:-$ROOT/diskless-v2/phase4-accepted.env}"
BASELINE_WRAPPER="$ROOT/initramfs/diskless-v2-android-continuation-init"
BUILDER="$ROOT/scripts/v2/build_android_first_stage_probe.py"
IMAGE_AUDITOR="$ROOT/scripts/v2/audit_phase6_v2_continuation_image.py"
OUTPUT="${OUTPUT:-$OUT/phase6-v2-panic-hold.img}"
REPORT="${REPORT:-$OUT/phase6-v2-panic-hold-host-gate.txt}"

EXPECTED_BASELINE_WRAPPER_SHA256="2799795e56c00a448a604eb967df1921ce32dd577ca1fca11b4c9bd18a61bedc"
EXPECTED_BUILDER_GIT_BLOB="bdaeebbea1a4c406e7de7d0df3fb58b07ddd74f8"
EXPECTED_AUDITOR_GIT_BLOB="c182c52da24b8eb9006ff144f5176672d9d800d1"
OLD_LINE='[ -w /proc/sys/kernel/panic ] && echo 5 > /proc/sys/kernel/panic'
NEW_LINE='[ -w /proc/sys/kernel/panic ] && echo 0 > /proc/sys/kernel/panic'

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 cmp sha256sum git grep awk; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in "$ANDROID_BOOT" "$TRANSPORT_BOOT" "$GENERATED_FSTAB" "$PHASE4_ENV" \
         "$BASELINE_WRAPPER" "$BUILDER" "$IMAGE_AUDITOR"; do
    [[ -f "$f" ]] || fail "required input missing: $f"
done

BASELINE_SHA="$(sha256sum "$BASELINE_WRAPPER" | awk '{print $1}')"
[[ "$BASELINE_SHA" == "$EXPECTED_BASELINE_WRAPPER_SHA256" ]] || \
    fail "accepted continuation wrapper changed: actual=$BASELINE_SHA expected=$EXPECTED_BASELINE_WRAPPER_SHA256"

BUILDER_BLOB="$(git hash-object "$BUILDER")"
[[ "$BUILDER_BLOB" == "$EXPECTED_BUILDER_GIT_BLOB" ]] || \
    fail "accepted Phase5 builder changed: git-blob=$BUILDER_BLOB expected=$EXPECTED_BUILDER_GIT_BLOB"

AUDITOR_BLOB="$(git hash-object "$IMAGE_AUDITOR")"
[[ "$AUDITOR_BLOB" == "$EXPECTED_AUDITOR_GIT_BLOB" ]] || \
    fail "continuation image auditor changed: git-blob=$AUDITOR_BLOB expected=$EXPECTED_AUDITOR_GIT_BLOB"

mkdir -p "$OUT"
TMPDIR="$(mktemp -d "$OUT/.phase6-v2-panic-hold.XXXXXX")"
trap 'rm -rf "$TMPDIR"' EXIT
DIAG_WRAPPER="$TMPDIR/init"
IMG_A="$TMPDIR/a.img"
IMG_B="$TMPDIR/b.img"

python3 - "$BASELINE_WRAPPER" "$DIAG_WRAPPER" "$OLD_LINE" "$NEW_LINE" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])
old = sys.argv[3]
new = sys.argv[4]
if src.count(old) != 1:
    raise SystemExit(f"ERROR: expected exactly one panic=5 runtime line, found {src.count(old)}")
if new in src:
    raise SystemExit("ERROR: baseline already contains panic=0 diagnostic line")
patched = src.replace(old, new, 1)
out.write_text(patched)

base_lines = src.splitlines()
new_lines = patched.splitlines()
if len(base_lines) != len(new_lines):
    raise SystemExit("ERROR: diagnostic wrapper changed line count")
delta = [(i + 1, a, b) for i, (a, b) in enumerate(zip(base_lines, new_lines)) if a != b]
if delta != [(next(i + 1 for i, line in enumerate(base_lines) if line == old), old, new)]:
    raise SystemExit(f"ERROR: unexpected wrapper delta: {delta!r}")
print("DISKLESS_V2_PHASE6_V2_PANIC_HOLD_WRAPPER_DELTA=PASS")
print(f"changed_line={delta[0][0]}")
print("runtime_delta=kernel.panic:5->0")
print("panic_on_oops=unchanged:1")
print("all_other_wrapper_lines=byte-equivalent")
PY

build_one() {
    target="$1"
    python3 "$BUILDER" \
        --android-boot "$ANDROID_BOOT" \
        --transport-boot "$TRANSPORT_BOOT" \
        --generated-fstab "$GENERATED_FSTAB" \
        --wrapper "$DIAG_WRAPPER" \
        --phase4-env "$PHASE4_ENV" \
        --output "$target"
}

echo "==> Building panic-hold image A"
BUILD_A="$(build_one "$IMG_A")"
printf '%s\n' "$BUILD_A"
grep -q '^DISKLESS_V2_ANDROID_FIRST_STAGE_PROBE_BUILT=1$' <<<"$BUILD_A" || \
    fail "accepted builder did not emit success marker"

echo
echo "==> Building panic-hold image B"
BUILD_B="$(build_one "$IMG_B")"
printf '%s\n' "$BUILD_B"
cmp -s "$IMG_A" "$IMG_B" || fail "panic-hold diagnostic build is not reproducible"

DIAG_SHA="$(sha256sum "$DIAG_WRAPPER" | awk '{print $1}')"
IMAGE_SHA="$(sha256sum "$IMG_A" | awk '{print $1}')"

echo
echo "==> Auditing final image with exact diagnostic wrapper"
AUDIT="$(python3 "$IMAGE_AUDITOR" \
    --android-boot "$ANDROID_BOOT" \
    --transport-boot "$TRANSPORT_BOOT" \
    --generated-fstab "$GENERATED_FSTAB" \
    --wrapper "$DIAG_WRAPPER" \
    --image "$IMG_A")"
printf '%s\n' "$AUDIT"
grep -q '^DISKLESS_V2_PHASE6_V2_CONTINUATION_IMAGE_AUDIT=PASS$' <<<"$AUDIT" || \
    fail "final panic-hold image audit did not pass"

mv "$IMG_A" "$OUTPUT"
rm -f "$IMG_B"

{
    echo "DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS"
    echo "baseline_wrapper_sha256=$BASELINE_SHA"
    echo "diagnostic_wrapper_sha256=$DIAG_SHA"
    echo "builder_git_blob=$BUILDER_BLOB"
    echo "image_auditor_git_blob=$AUDITOR_BLOB"
    echo "runtime_delta=kernel.panic:5->0"
    echo "panic_on_oops=unchanged:1"
    echo "transport_setup=unchanged"
    echo "android_init=unchanged"
    echo "android_rc_modifications=none"
    echo "selinux_policy=stock-enforcing-baseline"
    echo "diagnostic_image=$OUTPUT"
    echo "diagnostic_image_sha256=$IMAGE_SHA"
    echo "binary_question=does-the-run-stop-without-auto-reboot-when-panic-auto-reboot-is-disabled"
    echo "interpretation_if_hold=strong-evidence-for-kernel-panic-path-but-not-stack-root-cause"
    echo "interpretation_if_reboot=panic-timeout-path-not-sufficient-to-explain-reset"
} > "$REPORT"

echo
echo "DISKLESS_V2_PHASE6_V2_PANIC_HOLD_HOST_GATE=PASS"
echo "image=$OUTPUT"
echo "image_sha256=$IMAGE_SHA"
echo "report=$REPORT"
echo "NOTE: this image is diagnostic-only; it does not replace the accepted continuation image."
