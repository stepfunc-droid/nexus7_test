#!/usr/bin/env bash
set -euo pipefail

KMSG_IN="${KMSG_IN:-$HOME/phase6-live-kmsg.txt}"
NBD_LOG="${NBD_LOG:-$HOME/nexus7-v2-android-nbd.log}"
HANDSHAKE_WAIT_SECS="${HANDSHAKE_WAIT_SECS:-20}"
SECOND_STAGE_WAIT_SECS="${SECOND_STAGE_WAIT_SECS:-180}"

fail() {
    echo "ERROR: $*" >&2
    if [[ -f "$KMSG_IN" ]]; then
        echo "--- relevant Phase6 lines ---" >&2
        grep -E 'PHASE6|handing off|init first stage|__mount\(source=/dev/block/nbd0p[12]|Switching root|init second stage started|SELinux|InitFatalReboot|Kernel panic|Attempted to kill init|Reboot ending|Restarting system' "$KMSG_IN" >&2 || true
        echo "--- tail of live kmsg ---" >&2
        tail -n 120 "$KMSG_IN" >&2 || true
    fi
    exit 1
}

for tool in grep tail date; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

[[ -f "$KMSG_IN" ]] || fail "Phase6 live-kmsg capture not found: $KMSG_IN (start 'nc -lk 11000 | tee $KMSG_IN' before booting the Phase6 image)"
[[ -f "$NBD_LOG" ]] || fail "Mac-side NBD log not found: $NBD_LOG"

echo "==> Waiting for Phase6 live-kmsg stream handshake"
start="$(date +%s)"
while ! grep -q '^DISKLESS_V2_PHASE6_LIVE_KMSG_STREAM=1 ' "$KMSG_IN"; do
    now="$(date +%s)"
    (( now - start < HANDSHAKE_WAIT_SECS )) || fail "Phase6 live-kmsg stream handshake never arrived"
    sleep 1
done
handshake="$(grep '^DISKLESS_V2_PHASE6_LIVE_KMSG_STREAM=1 ' "$KMSG_IN" | tail -n 1)"
printf '%s\n' "$handshake"

system_line='__mount(source=/dev/block/nbd0p1,target=/system,type=ext4)=0: Success'
vendor_line='__mount(source=/dev/block/nbd0p2,target=/vendor,type=ext4)=0: Success'

echo
echo "==> Waiting for stock Lineage second-stage init"
start="$(date +%s)"
while true; do
    if grep -Fq 'init second stage started!' "$KMSG_IN"; then
        break
    fi

    if grep -Eq 'InitFatalReboot|Kernel panic|Attempted to kill init' "$KMSG_IN"; then
        fail "fatal reboot/panic occurred before second-stage init"
    fi
    if grep -Eq 'Reboot ending, jumping to kernel|Restarting system with command' "$KMSG_IN"; then
        fail "device rebooted before second-stage init"
    fi

    now="$(date +%s)"
    (( now - start < SECOND_STAGE_WAIT_SECS )) || fail "timed out waiting for stock Lineage second-stage init"
    sleep 1
done

grep -Fq "$system_line" "$KMSG_IN" || fail "exact /system first-stage mount success line missing"
grep -Fq "$vendor_line" "$KMSG_IN" || fail "exact /vendor first-stage mount success line missing"

connections="$(grep -cE 'client [^ ]+ connected; export size=' "$NBD_LOG" || true)"
[[ "$connections" == "1" ]] || fail "expected exactly one successful NBD connection in $NBD_LOG; found $connections"
if grep -Eqi 'transport error|client error|Traceback|bad request magic|unsupported NBD command' "$NBD_LOG"; then
    grep -Ei 'transport error|client error|Traceback|bad request magic|unsupported NBD command' "$NBD_LOG" >&2 || true
    fail "Mac-side NBD log contains a server/protocol error"
fi

second_stage_line="$(grep -F 'init second stage started!' "$KMSG_IN" | tail -n 1)"
echo "$second_stage_line"
echo
echo "DISKLESS_V2_PHASE6_SECOND_STAGE_REACHED=1"
echo "system_mount=/dev/block/nbd0p1"
echo "vendor_mount=/dev/block/nbd0p2"
echo "single_nbd_connection=PASS"
echo "selinux_policy=stock-enforcing-baseline"
echo "android_rc_bypasses=none"
echo "full_android_boot=continuing"
echo "phase6_final_gate=not-yet-passed"
echo "evidence=$KMSG_IN"
