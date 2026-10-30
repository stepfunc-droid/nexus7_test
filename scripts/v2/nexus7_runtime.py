#!/usr/bin/env python3
"""Portable Mac launcher for the explicitly packaged Q2 profile (no flashing)."""
import argparse
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SERIAL = '07a117ae'
LOCATION = 336789504


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    with path.open('rb') as fp:
        return hashlib.file_digest(fp, 'sha256').hexdigest()


def verify(master=False):
    pins = json.loads((ROOT/'release.json').read_text())['files']
    for name, expected in pins.items():
        if name.endswith('.raw.img') and not master:
            continue
        require(digest(ROOT/name) == expected, 'Identity mismatch: '+name)


def clone(source, target):
    require(not target.exists(), 'Destination already exists')
    lib = ctypes.CDLL(None, use_errno=True)
    fn = lib.clonefile
    fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    fn.restype = ctypes.c_int
    if fn(os.fsencode(source), os.fsencode(target), 0):
        raise OSError(ctypes.get_errno(), 'APFS clone failed; no copy fallback')


def usb():
    raw = subprocess.check_output(['ioreg', '-a', '-p', 'IOUSB', '-l', '-w', '0'])
    found = []
    def walk(node):
        if isinstance(node, list):
            for item in node: walk(item)
        elif isinstance(node, dict):
            if node.get('locationID') == LOCATION and 'idProduct' in node:
                found.append(node)
            walk(node.get('IORegistryEntryChildren', []))
    walk(plistlib.loads(raw))
    return found


def endpoint_ready():
    if not any(d.get('idVendor') == 0x0525 and d.get('idProduct') == 0xa4a2 for d in usb()):
        return False
    hardware = subprocess.check_output(['networksetup', '-listallhardwareports'], text=True)
    candidates = []
    for block in hardware.split('\n\n'):
        if re.search(r'Hardware Port: .*?(?:RNDIS|Ethernet Gadget)', block):
            match = re.search(r'^Device: (en\d+)$', block, re.M)
            if match: candidates.append(match.group(1))
    require(len(candidates) <= 1, 'Ambiguous USB Ethernet interfaces')
    if not candidates: return False
    interface = candidates[0]
    require(interface not in {'en0', 'en1', 'en2'}, 'Refusing management interface')
    data = subprocess.check_output(['ifconfig', interface], text=True)
    return bool(re.search(r'\binet 172\.16\.42\.2 netmask 0xffffff00\b', data))


def serve(disk):
    verify()
    disk = disk.resolve()
    require(disk.is_file() and disk.stat().st_size == 6246367232, 'Wrong disk size')
    require(disk.parent == (ROOT/'disks').resolve(), 'Serve only working copies in disks/')
    require(not subprocess.run(['lsof', '-nP', '-iTCP:10810', '-sTCP:LISTEN'],
                              capture_output=True).stdout, 'Port10810 already in use; preserve existing root server')
    run = ROOT/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S-%fZ')
    run.mkdir(parents=True)
    (run/'armed.json').write_text(json.dumps({'pid':os.getpid(), 'disk':str(disk)}))
    print('Armed. In another terminal run: python3 nexus7.py boot', flush=True)
    print('Waiting up to180s for USB gadget + dedicated172.16.42.2/24. Keep this terminal open.', flush=True)
    deadline = time.monotonic()+180
    while not endpoint_ready():
        require(time.monotonic() < deadline, 'USB endpoint unavailable; no server started')
        time.sleep(.25)
    command = [sys.executable, str(ROOT/'tools/phase6_v2_nbd_observed_server.py'),
               '--stats-log', str(run/'stats.jsonl'), '--system-range', '1048576', '1573912576',
               '--bind', '172.16.42.2', '--port', '10810', '--name', 'nexus7',
               '--trace-map', str(ROOT/'partition-trace-map.json'),
               '--trace-log', str(run/'trace.jsonl'), str(disk)]
    with (run/'server.log').open('x') as log:
        server = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                  stderr=subprocess.STDOUT, start_new_session=True)
    (run/'server.pid').write_text(str(server.pid)+'\n')
    subprocess.Popen(['caffeinate','-i','-w',str(server.pid)], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    print('NBD server PID',server.pid,'log',run/'server.log',flush=True)
    time.sleep(1)
    require(server.poll() is None and 'server listening on 172.16.42.2:10810' in (run/'server.log').read_text(),
            'Server failed to start; inspect server.log')
    try:
        while server.poll() is None:
            os.kill(server.pid, signal.SIGUSR1)
            time.sleep(5)
    except KeyboardInterrupt:
        print('Monitor stopped. ROOT SERVER REMAINS RUNNING at PID',server.pid,
              '; stop it only after device shutdown/verified fastboot.',flush=True)


def boot():
    verify()
    fastboot = shutil.which('fastboot')
    require(fastboot, 'fastboot not in PATH')
    armed = []
    for path in (ROOT/'runs').glob('*/armed.json'):
        record = json.loads(path.read_text())
        ps = subprocess.run(['ps','-p',str(record['pid']),'-o','command='],capture_output=True,text=True)
        if str(ROOT/'nexus7.py') in ps.stdout and 'serve' in ps.stdout:
            armed.append(record)
    require(len(armed) == 1, 'Exactly one packaged serve process must be armed first')
    def identity(product, pid):
        devices = usb()
        require(any(d.get('idVendor') == 0x18d1 and d.get('idProduct') == pid and
                    d.get('USB Serial Number') == SERIAL for d in devices), 'Unexpected physical USB identity')
        result = subprocess.run([fastboot,'-s',SERIAL,'getvar','product'],capture_output=True,text=True,timeout=8)
        require(result.returncode == 0 and re.search(r'product:\s*'+re.escape(product)+r'(?:\s|$)',
                                                   result.stdout+result.stderr), 'Unexpected bootloader product')
    identity('flo', 0x4ee0)
    subprocess.run([fastboot,'-s',SERIAL,'boot',str(ROOT/'lk2nd.img')],check=True,timeout=30)
    deadline = time.monotonic()+15
    while True:
        try:
            identity('lk2nd-msm8960', 0xd00d)
            break
        except (RuntimeError, subprocess.TimeoutExpired):
            require(time.monotonic() < deadline, 'lk2nd identity not verified; diagnostic NOT booted')
            time.sleep(.3)
    subprocess.run([fastboot,'-s',SERIAL,'boot',str(ROOT/'boot.img')],check=True,timeout=30)
    print('Both RAM boot commands succeeded; this is not Android boot acceptance. Keep NBD/USB/Mac running.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('verify')
    new = sub.add_parser('new-disk'); new.add_argument('name')
    srv = sub.add_parser('serve'); srv.add_argument('disk',type=Path)
    sub.add_parser('boot')
    args = parser.parse_args()
    if args.command == 'verify': verify(master=True); print('Bundle identity PASS (HOST_FACT)')
    elif args.command == 'new-disk':
        require(re.fullmatch(r'[A-Za-z0-9_-]+',args.name), 'Use a simple disk name')
        verify(master=True)
        target=ROOT/'disks'/(args.name+'.raw.img')
        clone(ROOT/'masters/lineage18.1-gps-off-clean.raw.img',target)
        target.chmod(0o600); print(target)
    elif args.command == 'serve': serve(args.disk)
    else: boot()


if __name__ == '__main__':
    try: main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit('ERROR: '+str(error))
