#!/usr/bin/env python3
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

import phase6_v2_watch_adb_console as watch

BOOT_A = 'b124ede8-c0bb-490a-8697-211f41b4bb73'
BOOT_B = '4204ca11-7f6a-4e85-bf3d-5a2a9998b6f9'


class CaptureTest(unittest.TestCase):
    def test_capture_order_and_boot_change(self):
        for changed in (False, True):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                calls = []
                def runner(adb, serial, argv, timeout=3):
                    calls.append(argv)
                    if argv[-1] == watch.PROBE:
                        boot = BOOT_B if changed else BOOT_A
                        return 0, f'uid=0\nboot_id={boot}\nserial=07a117ae\nuptime=123.45 0\n'.encode(), b''
                    if argv[-1] == '/proc/last_kmsg':
                        return 0, b'previous\x00console\r\n', b''
                    return 0, b'diagnostics\n', b''
                before = dict(uid='0', boot_id=BOOT_A, serial='07a117ae', uptime='122.0 0')
                directory = Path(temporary) / 'capture'
                result = watch.capture('adb', '07a117ae', before, directory, runner)
                self.assertEqual(calls[0], ['exec-out', 'cat', '/proc/last_kmsg'])
                self.assertEqual((directory / 'last_kmsg.bin').read_bytes(), b'previous\x00console\r\n')
                self.assertEqual(result['same_boot_through_capture'], not changed)
                self.assertEqual(result['first_visible_adb_is_first_successor'], 'UNKNOWN')
                self.assertFalse(json.loads((directory / 'capture.json').read_text())['hardware_boot_authorized'])

    def test_invalid_probe_rejected(self):
        for data in (b'uid=0\n', b'uid=0\nboot_id=bad\nserial=07a117ae\nuptime=2\n',
                     f'uid=0\nboot_id={BOOT_A}\nserial=wrong\nuptime=2\n'.encode()):
            self.assertIsNone(watch.probe('adb', '07a117ae', lambda *args: (0, data, b'')))

    def test_cli_offline_root_return_and_single_capture(self):
        self.cli_scenario(False)

    def test_cli_starts_in_fastboot_without_live_baseline(self):
        self.cli_scenario(True)

    def cli_scenario(self, offline):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / 'adb'
            fake.write_text(f'''#!{sys.executable}
import json,sys
from pathlib import Path
p=Path(__file__).with_suffix('.state')
s=json.loads(p.read_text()) if p.exists() else dict(probes=0,root=False)
args=sys.argv[3:]
if args == ['root']:
 s['root']=True
 p.write_text(json.dumps(s))
 sys.exit(0)
if args[-1].startswith("printf 'uid='"):
 s['probes']+=1
 p.write_text(json.dumps(s))
 if (not {offline!r} and s['probes']==4) or ({offline!r} and s['probes']==1):
  sys.exit(1)
 initial=not {offline!r} and s['probes']<=3
 uid=0 if initial or s['root'] else 2000
 boot='{BOOT_A}' if initial else '{BOOT_B}'
 print(f'uid={{uid}}\\nboot_id={{boot}}\\nserial=07a117ae\\nuptime=123.4 0')
elif args[-1]=='/proc/last_kmsg':
 sys.stdout.buffer.write(b'previous NBD console\\x00\\n')
else:
 print('mock diagnostics')
''')
            fake.chmod(0o755)
            output = root / 'logs'
            command = [sys.executable, str(Path(watch.__file__)), '--adb', str(fake),
                       '--output', str(output), '--duration', '2', '--interval', '0.02', '--root-on-return']
            if offline:
                command.append('--start-offline')
            result = subprocess.run(command, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            records = [json.loads(line) for line in (output / 'timeline.jsonl').read_text().splitlines()]
            events = [r['event'] for r in records]
            self.assertIn('armed', events)
            self.assertIn('baseline_unavailable' if offline else 'baseline_saved', events)
            self.assertIn('adbd_root_requested', events)
            self.assertEqual(events.count('console_saved'), 1)
            saved = next(r for r in records if r['event'] == 'console_saved')
            self.assertTrue(saved['result']['same_boot_through_capture'])
            self.assertEqual(saved['result']['before']['boot_id'], BOOT_B)
            self.assertEqual(records[-1]['reset_cause'], 'UNKNOWN')
            self.assertFalse(any(c in str(records) for c in ('fastboot boot', 'adb reboot')))


if __name__ == '__main__':
    unittest.main()
