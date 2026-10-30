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
import shlex
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SERIAL = '07a117ae'
LOCATION = 336789504


def bound_location():
    path=ROOT/'device-location.json'
    if not path.exists():return LOCATION
    record=json.loads(path.read_text())
    require(record.get('serial')==SERIAL and isinstance(record.get('location'),int),
            'Invalid saved USB device identity')
    return record['location']


def remember_location(device):
    record={'serial':SERIAL,'location':device['locationID'],
            'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    tmp=ROOT/('device-location-'+str(os.getpid())+'.tmp')
    tmp.write_text(json.dumps(record)+'\n');tmp.replace(ROOT/'device-location.json')


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
            if 'idProduct' in node and (node.get('locationID')==bound_location() or
                                       node.get('USB Serial Number')==SERIAL):
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
    observer=ROOT/'tools/phase6_v2_observe_usb.py'
    require(observer.is_file(),'Packaged USB observer missing')
    with (run/'usb-observer.log').open('x') as log:
        watcher=subprocess.Popen([sys.executable,str(observer),'--output',str(run/'usb.jsonl'),
                                  '--duration','900'],stdin=subprocess.DEVNULL,stdout=log,
                                 stderr=subprocess.STDOUT,start_new_session=True)
    (run/'usb-observer.pid').write_text(str(watcher.pid)+'\n')
    for tick in range(30):
        if watcher.poll() is not None:raise RuntimeError('USB observer exited before arming')
        if (run/'usb.jsonl').exists() and (run/'usb.jsonl').stat().st_size>0:break
        time.sleep(.1)
    else:raise RuntimeError('USB observer did not produce initial state')
    (run/'armed.json').write_text(json.dumps({'pid':os.getpid(), 'disk':str(disk)}))
    print('NBD已准备。在另一终端运行 ./start-nexus7.sh 启动平板。', flush=True)
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
    monitor_server(server)


def monitor_server(server):
    while server.poll() is None:
        try:
            os.kill(server.pid, signal.SIGUSR1)
            time.sleep(5)
        except KeyboardInterrupt:
            server.terminate()
            server.wait(timeout=5)
            print('NBD服务已停止。',flush=True)
            break


def boot():
    verify()
    fastboot = shutil.which('fastboot')
    require(fastboot, 'fastboot not in PATH')
    armed = []
    for path in (ROOT/'runs').glob('*/armed.json'):
        record = json.loads(path.read_text())
        ps = subprocess.run(['ps','-p',str(record['pid']),'-o','command='],capture_output=True,text=True)
        if str(ROOT/'nexus7.py') in ps.stdout and 'serve' in ps.stdout:
            record['_run']=str(path.parent)
            armed.append(record)
    require(len(armed) == 1, 'Exactly one packaged serve process must be armed first')
    journal=Path(armed[0]['_run'])/'boot-commands.jsonl'
    def command(argv,timeout):
        def emit(event,**fields):
            with journal.open('a') as fp:
                fp.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                     'event':event,'argv':argv,**fields})+'\n')
        emit('command_attempt')
        result=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
        emit('command_result',exit=result.returncode,stdout=result.stdout,stderr=result.stderr)
        print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr)
        return result
    boot_location=None
    def identity(product, pid):
        nonlocal boot_location
        devices = usb()
        matches=[d for d in devices if d.get('idVendor')==0x18d1 and d.get('idProduct')==pid and
                 d.get('USB Serial Number')==SERIAL]
        require(len(matches)==1,'Unexpected physical USB identity')
        require(boot_location is None or matches[0]['locationID']==boot_location,
                'USB port changed during this boot sequence')
        result = command([fastboot,'-s',SERIAL,'getvar','product'],8)
        require(result.returncode == 0 and re.search(r'product:\s*'+re.escape(product)+r'(?:\s|$)',
                                                   result.stdout+result.stderr), 'Unexpected bootloader product')
        boot_location=matches[0]['locationID'];remember_location(matches[0])
    identity('flo', 0x4ee0)
    result=command([fastboot,'-s',SERIAL,'boot',str(ROOT/'lk2nd.img')],30);result.check_returncode()
    deadline = time.monotonic()+15
    while True:
        try:
            identity('lk2nd-msm8960', 0xd00d)
            break
        except (RuntimeError, subprocess.TimeoutExpired):
            require(time.monotonic() < deadline, 'lk2nd identity not verified; diagnostic NOT booted')
            time.sleep(.3)
    result=command([fastboot,'-s',SERIAL,'boot',str(ROOT/'boot.img')],30);result.check_returncode()
    print('Both RAM boot commands succeeded; this is not Android boot acceptance. Keep NBD/USB/Mac running.')


def stop_nbd():
    listeners=subprocess.run(['lsof','-t','-iTCP:10810','-sTCP:LISTEN'],capture_output=True,text=True)
    pids=set(listeners.stdout.split())
    if not pids:print('NBD服务未运行。');return
    require(len(pids)==1,'Ambiguous10810 listeners; stopped nothing')
    pid=int(next(iter(pids)))
    command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True)
    argv=shlex.split(command)
    allowed={str(ROOT/'tools/phase6_v2_nbd_observed_server.py'),
             str(Path.home()/'nexus7/releases/20261030-Q2-gps-off/tools/phase6_v2_nbd_observed_server.py'),
             str(Path.home()/'nexus7/releases/20261030-gapps-pico/tools/phase6_v2_nbd_observed_server.py'),
             '/Users/zhangjw/nexus7_test/scripts/v2/phase6_v2_nbd_observed_server.py'}
    require(any(script in argv for script in allowed),'Unrecognized NBD process; stopped nothing')
    require('--bind' in argv and argv[argv.index('--bind')+1]=='172.16.42.2' and
            '--port' in argv and argv[argv.index('--port')+1]=='10810','Unrecognized listener scope')
    os.kill(pid,signal.SIGTERM)
    for tick in range(50):
        active=subprocess.run(['lsof','-t','-iTCP:10810','-sTCP:LISTEN'],capture_output=True,text=True)
        if str(pid) not in active.stdout.split():break
        time.sleep(.1)
    else:raise RuntimeError('NBD服务尚未退出，请保留终端输出')
    print('NBD服务已停止，PID',pid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('verify')
    new = sub.add_parser('new-disk'); new.add_argument('name')
    srv = sub.add_parser('serve'); srv.add_argument('disk',type=Path)
    sub.add_parser('boot')
    sub.add_parser('stop-nbd')
    args = parser.parse_args()
    if args.command == 'verify': verify(master=True); print('Bundle identity PASS (HOST_FACT)')
    elif args.command == 'new-disk':
        require(re.fullmatch(r'[A-Za-z0-9_-]+',args.name), 'Use a simple disk name')
        verify(master=True)
        target=ROOT/'disks'/(args.name+'.raw.img')
        master=json.loads((ROOT/'release.json').read_text()).get('master_file','masters/lineage18.1-gps-off-clean.raw.img')
        require(master.startswith('masters/') and '..' not in Path(master).parts,'Invalid master path')
        clone(ROOT/master,target)
        target.chmod(0o600); print(target)
    elif args.command == 'serve': serve(args.disk)
    elif args.command == 'stop-nbd': stop_nbd()
    else: boot()


if __name__ == '__main__':
    try: main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit('ERROR: '+str(error))
