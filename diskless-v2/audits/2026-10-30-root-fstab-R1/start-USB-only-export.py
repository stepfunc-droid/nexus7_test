
from pathlib import Path
import datetime, json, os, plistlib, signal, subprocess, sys, time
root=Path('/Users/zhangjw/nexus7_test')
run=root/'out/phase6-root-fstab-R1'
sys.path.insert(0,str(root/'scripts/v2'))
from phase6_v2_observe_usb import usb_devices

def note(event, **values):
    with (run/'journal.jsonl').open('a') as fp:
        fp.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':event,**values},sort_keys=True)+'\n')

ready_interface=None
for tick in range(720):
    p=subprocess.run(['ifconfig','-a'],capture_output=True,text=True,timeout=3)
    interface=None
    for line in p.stdout.splitlines():
        if line and not line[0].isspace(): interface=line.split(':',1)[0]
        fields=line.split()
        if len(fields)>1 and fields[:2]==['inet','172.16.42.2']:
            if interface not in {'en0','en1','en2','bridge0','lo0'}:
                ready_interface=interface
    if ready_interface:
        p=subprocess.run(['ioreg','-a','-p','IOUSB','-l','-w','0'],capture_output=True,timeout=3,check=True)
        target=[d for d in usb_devices(plistlib.loads(p.stdout)) if d['locationID']==336789504]
        if target and any('gadget' in (d.get('USB Product Name') or '').lower() or 'ethernet' in (d.get('USB Product Name') or '').lower() for d in target):
            note('USB_endpoint_ready',interface=ready_interface,address='172.16.42.2',target=target)
            break
        ready_interface=None
    time.sleep(0.25)
else:
    note('USB_endpoint_wait_timeout',classification='INCONCLUSIVE')
    raise SystemExit(2)
cmd=[sys.executable,str(root/'scripts/v2/phase6_v2_nbd_observed_server.py'),'--stats-log',str(run/'nbd-stats.jsonl'),'--system-range','1048576','1573912576','--bind','172.16.42.2','--port','10810','--name','phase6-root-fstab-R1','--trace-map',str(root/'out/phase6-v2-root-fstab-K-preflight/partition-trace-map.json'),'--trace-log',str(run/'nbd-trace.jsonl'),str(root/'out/phase6-v2-root-fstab-I/disk-root-fstab.raw.img')]
with (run/'server.txt').open('x') as fp:
    server=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=fp,stderr=subprocess.STDOUT,start_new_session=True)
(run/'server.pid').write_text(str(server.pid)+'\n')
note('USB_only_server_start',pid=server.pid,argv=cmd)
for tick in range(100):
    if server.poll() is not None: raise SystemExit('server exited before readiness')
    if 'server listening on 172.16.42.2:10810' in (run/'server.txt').read_text(): break
    time.sleep(0.05)
else:
    raise SystemExit('USB-only server not ready')
note('USB_only_server_ready',pid=server.pid)
for tick in range(4200):
    if server.poll() is not None:
        note('server_exit',exit=server.returncode)
        break
    os.kill(server.pid,signal.SIGUSR1)
    time.sleep(0.5)
note('stats_sampler_end',server_still_running=server.poll() is None)
