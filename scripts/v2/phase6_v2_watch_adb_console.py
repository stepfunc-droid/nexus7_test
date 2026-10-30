#!/usr/bin/env python3
"""Preserve first-visible ADB boot identities and previous consoles on the host.

Never boots, flashes, writes device files, or attributes last_kmsg to a run.
An optional adb root restarts adbd only, using user-enabled rooted debugging.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid

PROBE = ("printf 'uid='; id -u; printf 'boot_id='; cat /proc/sys/kernel/random/boot_id; "
         "printf 'serial='; getprop ro.serialno; printf 'uptime='; cat /proc/uptime")
IDENTITY = ("id; cat /proc/sys/kernel/random/boot_id; cat /proc/uptime; "
            "cat /proc/cmdline; cat /proc/mounts; "
            "getprop sys.boot_completed; getprop ro.boot.bootreason; "
            "getprop ro.build.fingerprint; cat /sys/block/nbd0/pid 2>/dev/null; true")


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run_adb(adb, serial, argv, timeout=3):
    try:
        p = subprocess.run([adb, '-s', serial, *argv], capture_output=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or b'', (exc.stderr or b'') + b'\nHOST_ADB_TIMEOUT\n'


def probe(adb, serial, runner=run_adb):
    code, out, err = runner(adb, serial, ['exec-out', 'sh', '-c', PROBE])
    if code:
        return None
    values = dict(line.split('=', 1) for line in out.decode(errors='replace').splitlines() if '=' in line)
    try:
        uuid.UUID(values['boot_id'])
        int(values['uid'])
        float(values['uptime'].split()[0])
        if values['serial'] != serial:
            raise ValueError('unexpected physical serial')
    except (KeyError, ValueError, IndexError):
        return None
    return values


def save_command(directory, name, result):
    code, out, err = result
    (directory / name).write_bytes(out)
    (directory / (name + '.stderr')).write_bytes(err)
    return dict(exit_code=code, bytes=len(out), sha256=hashlib.sha256(out).hexdigest())


def capture(adb, serial, before, directory, runner=run_adb):
    directory.mkdir()
    begun = utc()
    # Save the vulnerable previous console first, before any lengthy diagnostics.
    previous = save_command(directory, 'last_kmsg.bin',
                            runner(adb, serial, ['exec-out', 'cat', '/proc/last_kmsg'], timeout=8))
    after = probe(adb, serial, runner)
    stable = bool(after and before['boot_id'] == after['boot_id'] and after['uid'] == '0')
    identity = save_command(directory, 'identity.txt',
                            runner(adb, serial, ['exec-out', 'sh', '-c', IDENTITY], timeout=8))
    current = save_command(directory, 'dmesg.txt',
                           runner(adb, serial, ['exec-out', 'dmesg'], timeout=8))
    final = probe(adb, serial, runner)
    stable = bool(stable and final and final['boot_id'] == before['boot_id'] and final['uid'] == '0')
    result = dict(start_utc=begun, end_utc=utc(), before=before, after_console=after,
                  after_diagnostics=final, same_boot_through_capture=stable,
                  previous_console=previous, identity=identity, current_dmesg=current,
                  previous_boot_attribution='UNASSESSED; requires full USB/boot sequence and console identity',
                  first_visible_adb_is_first_successor='UNKNOWN',
                  hardware_boot_authorized=False)
    (directory / 'capture.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--adb', default='adb')
    ap.add_argument('--serial', default='07a117ae')
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--duration', type=float, default=2100)
    ap.add_argument('--interval', type=float, default=0.5)
    ap.add_argument('--root-on-return', action='store_true')
    ap.add_argument('--snapshot-current', action='store_true', help='baseline capture only; no waiting/root restart')
    ap.add_argument('--start-offline', action='store_true',
                    help='arm without a live baseline; caller must record current fastboot/transition identity')
    args = ap.parse_args()
    if args.duration <= 0 or args.interval <= 0:
        ap.error('duration and interval must be positive')
    if args.output.exists():
        ap.error('output must be a fresh directory')
    if args.start_offline and args.snapshot_current:
        ap.error('offline arming and current snapshot are mutually exclusive')
    initial = probe(args.adb, args.serial)
    if args.start_offline and initial is not None:
        ap.error('offline mode requires ADB currently unavailable; use the live baseline path')
    if not args.start_offline and (not initial or initial['uid'] != '0'):
        ap.error('baseline must be online, correct serial and already root; nothing armed')
    args.output.mkdir(parents=True)
    if not args.start_offline:
        baseline = capture(args.adb, args.serial, initial, args.output / 'boot-000-baseline')
        if (not baseline['same_boot_through_capture'] or baseline['previous_console']['exit_code']
                or not baseline['previous_console']['bytes']):
            ap.error('baseline capture unstable/unreadable; nothing armed')
    seen = {initial['boot_id']} if initial else set()
    root_attempts = {}
    capture_attempts = {}
    retry_after = {}
    blocked = set()
    started = time.monotonic()
    count = 0
    with (args.output / 'timeline.jsonl').open('x') as log:
        def emit(event, **data):
            record = dict(utc=utc(), elapsed=time.monotonic()-started, event=event, **data)
            log.write(json.dumps(record, sort_keys=True) + '\n')
            log.flush()
            if event != 'heartbeat':
                print(json.dumps(record, sort_keys=True), flush=True)
        if initial:
            emit('baseline_saved', boot_id=initial['boot_id'], snapshot_only=args.snapshot_current)
        else:
            emit('baseline_unavailable', start_mode='explicit offline',
                 previous_boot_attribution='UNKNOWN until caller sequence and console reviewed')
        if not args.snapshot_current:
            emit('armed', root_on_return=args.root_on_return,
                 provenance='ADB first-visible only; independently review all intervening USB boots')
            previous_state = 'baseline'
            heartbeat = 0
            while time.monotonic() - started < args.duration:
                tick = time.monotonic()
                current = probe(args.adb, args.serial)
                state = current['boot_id'] if current else 'unavailable'
                if state != previous_state:
                    emit('adb_identity_change', probe=current)
                    previous_state = state
                if current and current['boot_id'] not in seen:
                    if current['uid'] != '0':
                        attempts = root_attempts.get(state, 0)
                        if args.root_on_return and attempts < 3:
                            root_attempts[state] = attempts + 1
                            result = run_adb(args.adb, args.serial, ['root'], timeout=5)
                            saved = save_command(args.output, f'root-{state}-{attempts+1}.txt', result)
                            emit('adbd_root_requested', boot_id=state, result=saved)
                        elif state not in blocked:
                            emit('capture_blocked_nonroot', boot_id=state, attempts=attempts)
                            blocked.add(state)
                    elif capture_attempts.get(state, 0) < 3 and tick >= retry_after.get(state, 0):
                        capture_attempts[state] = capture_attempts.get(state, 0) + 1
                        retry_after[state] = tick + 5
                        count += 1
                        result = capture(args.adb, args.serial, current,
                                         args.output / f'boot-{count:03d}-observed')
                        if (result['same_boot_through_capture']
                                and result['previous_console']['exit_code'] == 0
                                and result['previous_console']['bytes']):
                            seen.add(state)
                        emit('console_saved', capture=count, result=result)
                if tick - heartbeat >= 5:
                    emit('heartbeat', state=state, captured_boots=len(seen))
                    heartbeat = tick
                time.sleep(max(0, args.interval - (time.monotonic() - tick)))
        emit('finished', observed_captures=count, boot_success='NOT_CLASSIFIED',
             reset_cause='UNKNOWN', previous_boot_attribution='UNASSESSED')


if __name__ == '__main__':
    main()
