#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-172.16.42.1}"
HTTP_PORT="${HTTP_PORT:-2325}"
NBD_LOG="${NBD_LOG:-$HOME/nexus7-v2-android-nbd.log}"
KMSG_OUT="${KMSG_OUT:-$HOME/nexus7-v2-android-first-stage-kmsg.txt}"
WAIT_SECS="${WAIT_SECS:-180}"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

for tool in curl grep awk; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

status_url="http://$HOST:$HTTP_PORT/status.txt"
first_url="http://$HOST:$HTTP_PORT/first-stage.txt"
kmsg_url="http://$HOST:$HTTP_PORT/kmsg.txt"

get() {
    curl --noproxy '*' -fsS --max-time 3 "$1" 2>/dev/null || true
}

echo "==> Waiting for Android first-stage probe supervisor"
start="$(date +%s)"
while true; do
    status="$(get "$status_url")"
    if grep -q '^DISKLESS_V2_ANDROID_PROBE_STATUS=' <<<"$status"; then
        printf '%s\n' "$status"
        break
    fi
    now="$(date +%s)"
    (( now - start < WAIT_SECS )) || fail "probe HTTP status never became reachable"
    sleep 1
done

echo
echo "==> Waiting for original Lineage first-stage init to mount system/vendor"
start="$(date +%s)"
while true; do
    report="$(get "$first_url")"
    if grep -q '^DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=PASS$' <<<"$report"; then
        printf '%s\n' "$report"
        break
    fi
    if grep -q '^DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=FAIL$' <<<"$report"; then
        printf '%s\n' "$report" >&2
        get "$kmsg_url" > "$KMSG_OUT" || true
        echo "--- tail of captured kmsg ---" >&2
        tail -n 120 "$KMSG_OUT" >&2 || true
        fail "Android first-stage mount probe reported FAIL"
    fi
    status="$(get "$status_url")"
    if grep -q '^DISKLESS_V2_ANDROID_PROBE_STATUS=FAIL$' <<<"$status"; then
        printf '%s\n' "$status" >&2
        get "$kmsg_url" > "$KMSG_OUT" || true
        fail "single-NBD supervisor failed before first-stage PASS"
    fi
    now="$(date +%s)"
    if (( now - start >= WAIT_SECS )); then
        get "$kmsg_url" > "$KMSG_OUT" || true
        echo "--- current status ---" >&2
        printf '%s\n' "$status" >&2
        echo "--- tail of captured kmsg ---" >&2
        tail -n 120 "$KMSG_OUT" >&2 || true
        fail "timed out waiting for Android first-stage mounts"
    fi
    sleep 1
done

before="$(awk -F= '$1=="nbd_pid_before" {print $2}' <<<"$report")"
after="$(awk -F= '$1=="nbd_pid_after" {print $2}' <<<"$report")"
system_src="$(awk -F= '$1=="system_source" {print $2}' <<<"$report")"
vendor_src="$(awk -F= '$1=="vendor_source" {print $2}' <<<"$report")"

[[ "$before" =~ ^[0-9]+$ && "$before" == "$after" ]] || fail "NBD pid changed or missing: before=$before after=$after"
[[ "$system_src" == "/dev/block/nbd0p1" ]] || fail "unexpected /system source: $system_src"
[[ "$vendor_src" == "/dev/block/nbd0p2" ]] || fail "unexpected /vendor source: $vendor_src"
grep -q '^pid1_action=SIGSTOP-after-first-stage-mounts$' <<<"$report" || fail "PID1 was not intentionally stopped at the gate"

status="$(get "$status_url")"
printf '\n==> Final probe status\n%s\n' "$status"
grep -q '^DISKLESS_V2_ANDROID_PROBE_STATUS=FIRST_STAGE_PASS$' <<<"$status" || \
    fail "probe status is not FIRST_STAGE_PASS"

get "$kmsg_url" > "$KMSG_OUT" || true
if [[ ! -s "$KMSG_OUT" ]]; then
    fail "captured kmsg is empty: $KMSG_OUT"
fi
grep -q 'DISKLESS_V2_ANDROID_FIRST_STAGE_MOUNTS=PASS' "$KMSG_OUT" || \
    fail "kmsg does not contain first-stage PASS marker"

[[ -f "$NBD_LOG" ]] || fail "Mac-side NBD log not found: $NBD_LOG"
connections="$(grep -cE 'client [^ ]+ connected; export size=' "$NBD_LOG" || true)"
[[ "$connections" == "1" ]] || fail "expected exactly one successful NBD connection in $NBD_LOG; found $connections"
if grep -Eqi 'transport error|client error|Traceback|bad request magic|unsupported NBD command' "$NBD_LOG"; then
    grep -Ei 'transport error|client error|Traceback|bad request magic|unsupported NBD command' "$NBD_LOG" >&2 || true
    fail "Mac-side NBD log contains a server/protocol error"
fi

echo
echo "DISKLESS_V2_ANDROID_FIRST_STAGE_VERIFIED=1"
echo "system_mount=/dev/block/nbd0p1"
echo "vendor_mount=/dev/block/nbd0p2"
echo "nbd_session=unchanged:$before"
echo "android_init=original-Lineage-first-stage"
echo "pid1=SIGSTOP-at-first-stage-gate"
echo "single_nbd_connection=PASS"
echo "android_late_boot=not-tested"
echo "kmsg=$KMSG_OUT"
