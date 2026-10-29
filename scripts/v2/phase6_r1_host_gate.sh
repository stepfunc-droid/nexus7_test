#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/out/diskless-v2-android}"
ANDROID_BOOT="${ANDROID_BOOT:-$OUT/boot-fstab-only.img}"
TRANSPORT_BOOT="${TRANSPORT_BOOT:-$ROOT/out/diskless-v2-transport.img}"
GENERATED_FSTAB="${GENERATED_FSTAB:-$OUT/fstab.flox}"
WRAPPER="${WRAPPER:-$ROOT/initramfs/diskless-v2-android-r1-init}"
PHASE4_ENV="${PHASE4_ENV:-$ROOT/diskless-v2/phase4-accepted.env}"
R0_REPORT="${R0_REPORT:-$OUT/phase6-r0-host-audit.txt}"
OUTPUT="${OUTPUT:-$OUT/phase6-r1-full-boot.img}"
REPORT="${REPORT:-$OUT/phase6-r1-host-audit.txt}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in python3 cmp sha256sum grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

for f in "$ANDROID_BOOT" "$TRANSPORT_BOOT" "$GENERATED_FSTAB" "$WRAPPER" "$PHASE4_ENV" "$R0_REPORT"; do
    [[ -f "$f" ]] || fail "required Phase6 R1 input not found: $f"
done

grep -q '^DISKLESS_V2_PHASE6_R0_HOST_AUDIT=PASS$' "$R0_REPORT" || \
    fail "Phase6 R0 report does not contain PASS marker: $R0_REPORT"

mkdir -p "$OUT"
TMP1="$OUT/.phase6-r1-build-a.img"
TMP2="$OUT/.phase6-r1-build-b.img"
rm -f "$TMP1" "$TMP2"
trap 'rm -f "$TMP1" "$TMP2"' EXIT

build_one() {
    target="$1"
    python3 "$ROOT/scripts/v2/build_phase6_r1.py" \
        --android-boot "$ANDROID_BOOT" \
        --transport-boot "$TRANSPORT_BOOT" \
        --generated-fstab "$GENERATED_FSTAB" \
        --wrapper "$WRAPPER" \
        --phase4-env "$PHASE4_ENV" \
        --output "$target"
}

echo "==> Phase6 R1: deterministic build A"
build_one "$TMP1"

echo
echo "==> Phase6 R1: deterministic build B"
build_one "$TMP2"

cmp -s "$TMP1" "$TMP2" || fail "two Phase6 R1 builds are not byte-identical"
BUILD_SHA="$(sha256sum "$TMP1" | awk '{print $1}')"

echo
echo "DISKLESS_V2_PHASE6_R1_REPRODUCIBLE=PASS"
echo "reproducible_sha256=$BUILD_SHA"

mv "$TMP1" "$OUTPUT"
rm -f "$TMP2"
trap - EXIT

echo
echo "==> Phase6 R1: independent image audit"
AUDIT_OUTPUT="$(python3 "$ROOT/scripts/v2/audit_phase6_r1.py" \
    --android-boot "$ANDROID_BOOT" \
    --transport-boot "$TRANSPORT_BOOT" \
    --generated-fstab "$GENERATED_FSTAB" \
    --wrapper "$WRAPPER" \
    --phase4-env "$PHASE4_ENV" \
    --image "$OUTPUT")"
printf '%s\n' "$AUDIT_OUTPUT"

grep -q '^DISKLESS_V2_PHASE6_R1_IMAGE_AUDIT=PASS$' <<<"$AUDIT_OUTPUT" || \
    fail "Phase6 R1 independent image audit marker missing"

{
    echo "$AUDIT_OUTPUT"
    echo "DISKLESS_V2_PHASE6_R1_REPRODUCIBLE=PASS"
    echo "reproducible_sha256=$BUILD_SHA"
    echo "DISKLESS_V2_PHASE6_R1_HOST_GATE=PASS"
    echo "handoff=/diskless-init->exec-/init"
    echo "stock_init_path_preserved=yes"
    echo "stock_init_bytes_preserved=yes"
    echo "intended_surviving_userspace=stock-init-plus-one-nbd-handler-after-handoff"
    echo "diagnostic_children_at_handoff=0"
    echo "android_rc_modifications=none"
    echo "selinux_policy=stock-enforcing-baseline"
    echo "real_device_boot=not-performed"
} > "$REPORT"

echo
echo "DISKLESS_V2_PHASE6_R1_HOST_GATE=PASS"
echo "image=$OUTPUT"
echo "image_sha256=$BUILD_SHA"
echo "report=$REPORT"
echo "No Nexus boot was performed. Hardware remains paused until Phase6 R2 evidence design is complete."
