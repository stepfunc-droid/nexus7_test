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

for tool in curl nc grep awk; do
    command -v "$tool" >/dev/null 2>&1 || fail "missing required host tool: $tool"
done

status_url="http://$HOST:$HTTP_PORT/status.txt"
phase4_url="http://$HOST:$HTTP_PORT/phase4.txt"
diag_url="http://$HOST:$HTTP_PORT/diag.txt"

get_status() {
    curl --noproxy '*' -fsS --max-time 3 "$status_url" 2>/dev/null || true
}

get_phase4() {
    curl --noproxy '*' -fsS --max-time 3 "$phase4_url" 2>/dev/null || true
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
        fail "transport failed before Phase 4 actions"
    fi
    now="$(date +%s)"
    (( now - start_epoch < WAIT_START_SECS )) || fail "transport never entered STRESS"
    sleep 2
done

echo
echo "==> Applying Lineage-equivalent low-power actions while NBD stress is active"
# The transport initramfs intentionally contains only /bin/busybox and /bin/sh;
# invoke BusyBox applets explicitly so the diagnostic shell does not depend on
# applet symlinks. Bound the raw-shell connection so a broken suspend policy
# cannot leave the host test hanging forever.
cat <<'REMOTE' | nc -w 45 "$HOST" "$SHELL_PORT"
BB=/bin/busybox
OUT=/www/phase4.txt
TMP=/tmp/phase4-body.txt
: > "$TMP"

log() {
    echo "$*" >> "$TMP"
}

fail_remote() {
    log "FAIL_REASON=$*"
    {
        echo "DISKLESS_V2_PHASE4_ACTIONS=FAIL"
        $BB cat "$TMP"
    } > "$OUT"
    exit 1
}

GUARD=/sys/module/msm_otg/parameters/diskless_mode
[ -r "$GUARD" ] || fail_remote "diskless guard sysfs parameter missing"
GUARD_VALUE="$($BB cat "$GUARD" 2>/dev/null)"
log "diskless_guard=$GUARD_VALUE"
case "$GUARD_VALUE" in
    1|Y|y|true|TRUE) ;;
    *) fail_remote "diskless guard is not active: $GUARD_VALUE" ;;
esac

[ -r /sys/block/nbd0/pid ] || fail_remote "kernel NBD pid missing before power test"
NBD_PID_BEFORE="$($BB cat /sys/block/nbd0/pid 2>/dev/null)"
[ -n "$NBD_PID_BEFORE" ] || fail_remote "kernel NBD pid empty before power test"
log "nbd_pid_before=$NBD_PID_BEFORE"

# Reproduce the power-mode writes performed by flo's stock init.flox.power.rc
# on the 'enable-low-power' trigger. Missing stock nodes are treated as a failed
# test because the exercise would otherwise be weaker than a normal Lineage boot.
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
[ "$MISSING" -eq 0 ] || fail_remote "one or more stock low-power sysfs actions could not be applied"

$BB sleep 5

if [ -w /sys/class/graphics/fb0/blank ]; then
    echo 4 > /sys/class/graphics/fb0/blank || fail_remote "framebuffer blank failed"
    log "framebuffer_blank=4"
    $BB sleep 3
    echo 0 > /sys/class/graphics/fb0/blank || fail_remote "framebuffer unblank failed"
    log "framebuffer_unblank=0"
else
    log "framebuffer_blank=unavailable"
fi

OTG_POWER=""
for d in /sys/bus/platform/drivers/msm_otg/*; do
    [ -d "$d/power" ] || continue
    OTG_POWER="$d/power"
    break
done
if [ -n "$OTG_POWER" ]; then
    log "otg_power_path=$OTG_POWER"
    if [ -w "$OTG_POWER/control" ]; then
        echo auto > "$OTG_POWER/control" || fail_remote "could not set OTG runtime PM control=auto"
        log "otg_power_control=$($BB cat "$OTG_POWER/control" 2>/dev/null)"
    fi
    [ -r "$OTG_POWER/runtime_status" ] && log "otg_runtime_status_before_suspend=$($BB cat "$OTG_POWER/runtime_status")"
else
    fail_remote "could not locate msm_otg platform power directory"
fi

SUSPEND_RC=not_attempted
if [ -w /sys/power/state ] && $BB grep -qw mem /sys/power/state; then
    echo mem > /sys/power/state
    SUSPEND_RC=$?
    log "system_suspend_write_rc=$SUSPEND_RC"
    $BB sleep 3
else
    log "system_suspend_write_rc=unsupported"
fi

[ -r /sys/block/nbd0/pid ] || fail_remote "kernel NBD pid disappeared after power actions"
NBD_PID_AFTER="$($BB cat /sys/block/nbd0/pid 2>/dev/null)"
[ -n "$NBD_PID_AFTER" ] || fail_remote "kernel NBD pid empty after power actions"
log "nbd_pid_after=$NBD_PID_AFTER"
[ "$NBD_PID_BEFORE" = "$NBD_PID_AFTER" ] || fail_remote "NBD session changed across power actions"

if [ -n "$OTG_POWER" ] && [ -r "$OTG_POWER/runtime_status" ]; then
    log "otg_runtime_status_after_suspend=$($BB cat "$OTG_POWER/runtime_status")"
fi

$BB dd if=/dev/nbd0p1 of=/dev/null bs=1048576 count=8 >/tmp/phase4-read.log 2>&1 || \
    fail_remote "system partition read failed after power actions"
$BB dd if=/dev/zero of=/mnt/data/.phase4-write.bin bs=1048576 count=8 >/tmp/phase4-write.log 2>&1 || \
    fail_remote "userdata write failed after power actions"
$BB sync
$BB dd if=/mnt/data/.phase4-write.bin of=/dev/null bs=1048576 >/tmp/phase4-readback.log 2>&1 || \
    fail_remote "userdata readback failed after power actions"
$BB rm -f /mnt/data/.phase4-write.bin
$BB sync

{
    echo "DISKLESS_V2_PHASE4_ACTIONS=PASS"
    $BB cat "$TMP"
} > "$OUT"
exit 0
REMOTE

echo
echo "==> Phase 4 action report"
phase4="$(get_phase4)"
printf '%s\n' "$phase4"
grep -q '^DISKLESS_V2_PHASE4_ACTIONS=PASS$' <<<"$phase4" || {
    echo "--- transport diagnostics ---" >&2
    curl --noproxy '*' -fsS --max-time 3 "$diag_url" >&2 || true
    fail "device-side Phase 4 actions failed"
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
        fail "transport failed after Phase 4 power actions"
    fi
    now="$(date +%s)"
    (( now - start_epoch < WAIT_PASS_SECS )) || fail "timed out waiting for transport PASS"
    sleep 10
done

phase4="$(get_phase4)"
grep -q '^DISKLESS_V2_PHASE4_ACTIONS=PASS$' <<<"$phase4" || fail "Phase 4 report no longer says PASS"

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
echo "phase4_actions=PASS"
echo "transport_stress=PASS"
echo "single_nbd_connection=PASS"
echo "usb_root_transport=protected"
