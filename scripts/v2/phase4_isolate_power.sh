#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-172.16.42.1}"
HTTP_PORT="${HTTP_PORT:-2325}"
SHELL_PORT="${SHELL_PORT:-2324}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in curl nc grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

status_url="http://$HOST:$HTTP_PORT/status.txt"
report_url="http://$HOST:$HTTP_PORT/phase4-isolate.txt"

status="$(curl --noproxy '*' -fsS --max-time 3 "$status_url" 2>/dev/null || true)"
printf '%s\n' "$status"
grep -Eq '^DISKLESS_V2_TRANSPORT_STATUS=(STRESS|PASS)$' <<<"$status" || \
    fail "transport must be alive before Phase 4 isolation test"

cat <<'REMOTE' | nc -w 45 "$HOST" "$SHELL_PORT"
BB=/bin/busybox
OUT=/www/phase4-isolate.txt
TMP=/tmp/phase4-isolate-body.txt
: > "$TMP"

log() { echo "$*" >> "$TMP"; }
finish_fail() {
    log "FAIL_REASON=$*"
    {
        echo "DISKLESS_V2_PHASE4_ISOLATION=FAIL"
        $BB cat "$TMP"
    } > "$OUT"
    exit 1
}

pid_now() {
    [ -r /sys/block/nbd0/pid ] || return 1
    p="$($BB cat /sys/block/nbd0/pid 2>/dev/null || true)"
    case "$p" in ''|*[!0-9]*|0) return 1 ;; *) echo "$p" ;; esac
}

check_session() {
    stage="$1"
    p="$(pid_now 2>/dev/null || true)"
    log "${stage}_nbd_pid=${p:-absent}"
    [ -n "$p" ] || finish_fail "NBD session absent after $stage"
    [ "$p" = "$BASE_PID" ] || finish_fail "NBD session changed after $stage: $BASE_PID -> $p"
    $BB dd if=/dev/nbd0p1 of=/dev/null bs=1048576 count=4 >/tmp/phase4-isolate-read.log 2>&1 || \
        finish_fail "NBD read failed after $stage"
}

GUARD=/sys/module/msm_otg/parameters/diskless_mode
[ -r "$GUARD" ] || finish_fail "diskless guard missing"
log "diskless_guard=$($BB cat "$GUARD" 2>/dev/null)"
BASE_PID="$(pid_now 2>/dev/null || true)"
[ -n "$BASE_PID" ] || finish_fail "initial NBD session missing"
log "baseline_nbd_pid=$BASE_PID"

# Stage A: stock flo enable-low-power writes only.
MISSING=0
write_one() {
    f="$1" v="$2"
    if [ ! -w "$f" ]; then
        log "missing_or_readonly=$f"
        MISSING=$((MISSING + 1))
        return
    fi
    echo "$v" > "$f" || {
        log "write_failed=$f value=$v"
        MISSING=$((MISSING + 1))
    }
}
for name in L2_cache pxo vdd_dig vdd_mem; do
    write_one "/sys/module/rpm_resources/enable_low_power/$name" 1
done
for cpu in 0 1 2 3; do
    write_one "/sys/module/pm_8x60/modes/cpu${cpu}/retention/idle_enabled" 1
    write_one "/sys/module/pm_8x60/modes/cpu${cpu}/power_collapse/suspend_enabled" 1
    write_one "/sys/module/pm_8x60/modes/cpu${cpu}/standalone_power_collapse/suspend_enabled" 1
    write_one "/sys/module/pm_8x60/modes/cpu${cpu}/standalone_power_collapse/idle_enabled" 1
done
write_one /sys/module/pm_8x60/modes/cpu0/power_collapse/idle_enabled 1
log "low_power_missing_count=$MISSING"
[ "$MISSING" -eq 0 ] || finish_fail "stock low-power writes incomplete"
$BB sleep 5
check_session low_power

# Stage B: framebuffer state transition only.
if [ -w /sys/class/graphics/fb0/blank ]; then
    echo 4 > /sys/class/graphics/fb0/blank || finish_fail "framebuffer blank failed"
    $BB sleep 3
    check_session framebuffer_blank
    echo 0 > /sys/class/graphics/fb0/blank || finish_fail "framebuffer unblank failed"
    $BB sleep 2
    check_session framebuffer_unblank
else
    log "framebuffer_blank=unavailable"
fi

# Stage C: runtime-PM auto policy on msm_otg only. No system suspend request.
OTG_POWER=""
for d in /sys/bus/platform/drivers/msm_otg/*; do
    [ -d "$d/power" ] || continue
    OTG_POWER="$d/power"
    break
done
[ -n "$OTG_POWER" ] || finish_fail "msm_otg power directory missing"
log "otg_power_path=$OTG_POWER"
if [ -w "$OTG_POWER/control" ]; then
    echo auto > "$OTG_POWER/control" || finish_fail "could not set OTG control=auto"
fi
[ -r "$OTG_POWER/runtime_status" ] && log "otg_runtime_status_initial=$($BB cat "$OTG_POWER/runtime_status")"
$BB sleep 8
[ -r "$OTG_POWER/runtime_status" ] && log "otg_runtime_status_after_wait=$($BB cat "$OTG_POWER/runtime_status")"
check_session otg_runtime_auto

{
    echo "DISKLESS_V2_PHASE4_ISOLATION=PASS"
    $BB cat "$TMP"
} > "$OUT"
exit 0
REMOTE

report="$(curl --noproxy '*' -fsS --max-time 3 "$report_url" 2>/dev/null || true)"
printf '%s\n' "$report"
grep -q '^DISKLESS_V2_PHASE4_ISOLATION=PASS$' <<<"$report" || fail "Phase 4 isolation test failed"

echo
echo "DISKLESS_V2_PHASE4_ISOLATION_VERIFIED=1"
