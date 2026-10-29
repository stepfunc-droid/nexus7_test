#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-172.16.42.1}"
HTTP_PORT="${HTTP_PORT:-2325}"
SHELL_PORT="${SHELL_PORT:-2324}"
NBD_LOG="${NBD_LOG:-$HOME/nexus7-v2-nbd.log}"
WAIT_START_SECS="${WAIT_START_SECS:-120}"
WAIT_PASS_SECS="${WAIT_PASS_SECS:-720}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in curl nc grep; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

status_url="http://$HOST:$HTTP_PORT/status.txt"
isolation_url="http://$HOST:$HTTP_PORT/phase4-isolate.txt"
report_url="http://$HOST:$HTTP_PORT/phase4-suspend.txt"
diag_url="http://$HOST:$HTTP_PORT/diag.txt"

get_status() {
    curl --noproxy '*' -fsS --max-time 3 "$status_url" 2>/dev/null || true
}

get_report() {
    curl --noproxy '*' -fsS --max-time 3 "$report_url" 2>/dev/null || true
}

echo "==> Waiting for transport stress state"
start_epoch="$(date +%s)"
while true; do
    status="$(get_status)"
    if grep -q '^DISKLESS_V2_TRANSPORT_STATUS=STRESS$' <<<"$status"; then
        printf '%s\n' "$status"
        break
    fi
    if grep -q '^DISKLESS_V2_TRANSPORT_STATUS=FAIL$' <<<"$status"; then
        printf '%s\n' "$status" >&2
        fail "transport failed before system-suspend gate"
    fi
    now="$(date +%s)"
    (( now - start_epoch < WAIT_START_SECS )) || fail "transport never entered STRESS"
    sleep 2
done

# Final Phase 4 acceptance requires the normal-power isolation test on this
# exact boot/kernel before the system-suspend policy is exercised.
isolation="$(curl --noproxy '*' -fsS --max-time 3 "$isolation_url" 2>/dev/null || true)"
grep -q '^DISKLESS_V2_PHASE4_ISOLATION=PASS$' <<<"$isolation" || \
    fail "same-boot isolation PASS missing; run scripts/v2/phase4_isolate_power.sh first"

echo
echo "==> Requesting system suspend; diskless PM notifier must reject it before device PM"
cat <<'REMOTE' | nc -w 20 "$HOST" "$SHELL_PORT"
BB=/bin/busybox
OUT=/www/phase4-suspend.txt
TMP=/tmp/phase4-suspend-body.txt
: > "$TMP"

log() { echo "$*" >> "$TMP"; }
finish_fail() {
    log "FAIL_REASON=$*"
    {
        echo "DISKLESS_V2_PHASE4_SUSPEND=FAIL"
        $BB cat "$TMP"
    } > "$OUT"
    exit 1
}

pid_now() {
    [ -r /sys/block/nbd0/pid ] || return 1
    p="$($BB cat /sys/block/nbd0/pid 2>/dev/null || true)"
    case "$p" in ''|*[!0-9]*|0) return 1 ;; *) echo "$p" ;; esac
}

GUARD=/sys/module/msm_otg/parameters/diskless_mode
[ -r "$GUARD" ] || finish_fail "diskless guard missing"
GUARD_VALUE="$($BB cat "$GUARD" 2>/dev/null || true)"
log "diskless_guard=$GUARD_VALUE"
case "$GUARD_VALUE" in 1|Y|y|true|TRUE) ;; *) finish_fail "diskless guard inactive" ;; esac

BASE_PID="$(pid_now 2>/dev/null || true)"
[ -n "$BASE_PID" ] || finish_fail "initial kernel NBD pid missing"
log "nbd_pid_before=$BASE_PID"

[ -w /sys/power/state ] || finish_fail "/sys/power/state is not writable"
$BB grep -qw mem /sys/power/state || finish_fail "mem suspend is not supported"

echo mem > /sys/power/state
SUSPEND_RC=$?
log "system_suspend_write_rc=$SUSPEND_RC"
[ "$SUSPEND_RC" -ne 0 ] || finish_fail "system suspend unexpectedly completed instead of being rejected"

# PM_SUSPEND_PREPARE rejection is synchronous. Give network/block workers a
# moment to expose any unintended disruption before checking the session.
$BB sleep 3
AFTER_PID="$(pid_now 2>/dev/null || true)"
log "nbd_pid_after=$AFTER_PID"
[ -n "$AFTER_PID" ] || finish_fail "kernel NBD pid disappeared after rejected suspend"
[ "$AFTER_PID" = "$BASE_PID" ] || finish_fail "NBD session changed across rejected suspend: $BASE_PID -> $AFTER_PID"

$BB dd if=/dev/nbd0p1 of=/dev/null bs=1048576 count=8 >/tmp/phase4-suspend-read.log 2>&1 || \
    finish_fail "system partition read failed after rejected suspend"
$BB dd if=/dev/zero of=/mnt/data/.phase4-suspend.bin bs=1048576 count=8 >/tmp/phase4-suspend-write.log 2>&1 || \
    finish_fail "userdata write failed after rejected suspend"
$BB sync
$BB dd if=/mnt/data/.phase4-suspend.bin of=/dev/null bs=1048576 >/tmp/phase4-suspend-readback.log 2>&1 || \
    finish_fail "userdata readback failed after rejected suspend"
$BB rm -f /mnt/data/.phase4-suspend.bin
$BB sync

{
    echo "DISKLESS_V2_PHASE4_SUSPEND=PASS"
    $BB cat "$TMP"
} > "$OUT"
exit 0
REMOTE

echo
echo "==> System-suspend gate report"
report="$(get_report)"
printf '%s\n' "$report"
grep -q '^DISKLESS_V2_PHASE4_SUSPEND=PASS$' <<<"$report" || {
    echo "--- transport diagnostics ---" >&2
    curl --noproxy '*' -fsS --max-time 3 "$diag_url" >&2 || true
    fail "early system-suspend gate failed"
}

echo
echo "==> Waiting for the existing 10-minute transport stress gate to finish"
start_epoch="$(date +%s)"
while true; do
    status="$(get_status)"
    if grep -q '^DISKLESS_V2_TRANSPORT_STATUS=PASS$' <<<"$status"; then
        printf '%s\n' "$status"
        break
    fi
    if grep -q '^DISKLESS_V2_TRANSPORT_STATUS=FAIL$' <<<"$status"; then
        printf '%s\n' "$status" >&2
        curl --noproxy '*' -fsS --max-time 3 "$diag_url" >&2 || true
        fail "transport failed after rejected system suspend"
    fi
    now="$(date +%s)"
    (( now - start_epoch < WAIT_PASS_SECS )) || fail "timed out waiting for transport PASS"
    sleep 10
done

report="$(get_report)"
grep -q '^DISKLESS_V2_PHASE4_SUSPEND=PASS$' <<<"$report" || fail "system-suspend report no longer says PASS"
isolation="$(curl --noproxy '*' -fsS --max-time 3 "$isolation_url" 2>/dev/null || true)"
grep -q '^DISKLESS_V2_PHASE4_ISOLATION=PASS$' <<<"$isolation" || fail "same-boot isolation report no longer says PASS"

if [[ -f "$NBD_LOG" ]]; then
    connections="$(grep -cE 'client [^ ]+ connected' "$NBD_LOG" || true)"
    [[ "$connections" == "1" ]] || fail "expected exactly one successful NBD connection in $NBD_LOG; found $connections"
    if grep -Eqi 'transport error|client error|Receive control failed|Send control failed' "$NBD_LOG"; then
        grep -Ei 'transport error|client error|Receive control failed|Send control failed' "$NBD_LOG" >&2 || true
        fail "Mac-side NBD log contains a transport/server error"
    fi
else
    fail "Mac-side NBD log not found: $NBD_LOG"
fi

echo
echo "DISKLESS_V2_PHASE4_VERIFIED=1"
echo "isolation_gate=PASS"
echo "system_suspend_guard=PASS"
echo "transport_stress=PASS"
echo "single_nbd_connection=PASS"
echo "usb_root_transport=protected"
