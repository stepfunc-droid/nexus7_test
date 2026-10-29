#!/usr/bin/env bash
set -euo pipefail

KMSG_IN="${KMSG_IN:-$HOME/phase5d-live-kmsg.txt}"
NBD_LOG="${NBD_LOG:-$HOME/nexus7-v2-android-nbd.log}"
WAIT_SECS="${WAIT_SECS:-120}"

fail() {
    echo "ERROR: $*" >&2
    if [[ -f "$KMSG_IN" ]]; then
        echo "--- tail of live kmsg ---" >&2
        tail -n 120 "$KMSG_IN" >&2 || true
    fi
    exit 1
}

for tool in grep sed tail; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

[[ -f "$KMSG_IN" ]] || fail "live-kmsg capture not found: $KMSG_IN (start 'nc -lk 11000 | tee $KMSG_IN' before booting the probe)"
[[ -f "$NBD_LOG" ]] || fail "Mac-side NBD log not found: $NBD_LOG"

echo "==> Waiting for live Android first-stage evidence"
start="$(date +%s)"
while true; do
    if grep -q 'DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=PASS ' "$KMSG_IN"; then
        break
    fi
    if grep -q 'DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=FAIL ' "$KMSG_IN"; then
        fail "probe emitted first-stage FAIL marker"
    fi

    now="$(date +%s)"
    if (( now - start >= WAIT_SECS )); then
        echo "--- relevant first-stage lines ---" >&2
        grep -E 'handing off|init first stage|__mount\(source=/dev/block/nbd0p[12]|Switching root|Unable to move|InitFatalReboot|Kernel panic|Attempted to kill init|Reboot ending|Restarting system' "$KMSG_IN" >&2 || true
        fail "timed out waiting for first-stage PASS marker"
    fi
    sleep 1
done

system_line='__mount(source=/dev/block/nbd0p1,target=/system,type=ext4)=0: Success'
vendor_line='__mount(source=/dev/block/nbd0p2,target=/vendor,type=ext4)=0: Success'

grep -Fq "$system_line" "$KMSG_IN" || fail "exact /system first-stage mount success line missing"
grep -Fq "$vendor_line" "$KMSG_IN" || fail "exact /vendor first-stage mount success line missing"

marker="$(grep 'DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=PASS ' "$KMSG_IN" | tail -n 1)"
before="$(sed -n 's/.*nbd_pid_before=\([0-9][0-9]*\).*/\1/p' <<<"$marker")"
after="$(sed -n 's/.*nbd_pid_after=\([0-9][0-9]*\).*/\1/p' <<<"$marker")"

[[ -n "$before" && "$before" == "$after" ]] || fail "NBD pid changed or missing in PASS marker: before=$before after=$after"
grep -Fq 'system_source=/dev/block/nbd0p1' <<<"$marker" || fail "PASS marker has wrong system source"
grep -Fq 'vendor_source=/dev/block/nbd0p2' <<<"$marker" || fail "PASS marker has wrong vendor source"
grep -Fq 'pid1_action=SIGSTOP-after-first-stage-mounts' <<<"$marker" || fail "PID1 stop marker missing"

connections="$(grep -cE 'client [^ ]+ connected; export size=' "$NBD_LOG" || true)"
[[ "$connections" == "1" ]] || fail "expected exactly one successful NBD connection in $NBD_LOG; found $connections"
if grep -Eqi 'transport error|client error|Traceback|bad request magic|unsupported NBD command' "$NBD_LOG"; then
    grep -Ei 'transport error|client error|Traceback|bad request magic|unsupported NBD command' "$NBD_LOG" >&2 || true
    fail "Mac-side NBD log contains a server/protocol error"
fi

echo "$marker"
echo
echo "DISKLESS_V2_ANDROID_FIRST_STAGE_VERIFIED=1"
echo "system_mount=/dev/block/nbd0p1"
echo "vendor_mount=/dev/block/nbd0p2"
echo "nbd_session=unchanged:$before"
echo "android_init=original-Lineage-first-stage"
echo "pid1=SIGSTOP-at-first-stage-gate"
echo "single_nbd_connection=PASS"
echo "android_late_boot=not-tested"
echo "evidence=$KMSG_IN"
