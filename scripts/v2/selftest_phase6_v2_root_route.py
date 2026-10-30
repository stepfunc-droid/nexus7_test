#!/usr/bin/env python3
"""Exercise the actual rule precondition using a host-only command stub."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RoutePreconditionTest(unittest.TestCase):
    def execute(self, rules, add_failure=False, missing=False):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            mock = folder / 'busybox'
            mock.write_text('''#!/bin/sh
case "$1" in
 --list) [ "$ROUTE_TEST_MISSING" = 1 ] || printf 'ip\\niprule\\n';;
 awk) shift; exec /usr/bin/awk "$@";;
 ip)
  shift
  case "$*" in
   'rule add priority 0 to 172.16.42.2/32 table main')
    printf '%s\\n' "$*" >> "$ROUTE_TEST_COMMANDS"
    [ "$ROUTE_TEST_ADD_FAILURE" != 1 ];;
   'rule show') cat "$ROUTE_TEST_RULES";;
   *) exit 91;;
  esac;;
 *) exit 92;;
esac
''')
            mock.chmod(0o755)
            fixture = folder / 'rules';fixture.write_text(rules)
            fragment = (ROOT / 'initramfs/phase6-root-route-rule.inc').read_text()
            # The last line writes a device log marker, unrelated to the gate;
            # never execute that device path during a host-only test.
            core = fragment[:fragment.index('echo "diskless-v2: root-peer rule ready')]
            script = folder / 'test.sh'
            script.write_text('''#!/bin/sh
HOST=172.16.42.2
fail() { exit 42; }
require_applet() { "$BB" --list | /usr/bin/grep -qx "$1" || fail; }
''' + core + '\nprintf REACHED_ATTACH\n')
            env = dict(os.environ, BB=str(mock), ROUTE_TEST_RULES=str(fixture),
                       ROUTE_TEST_COMMANDS=str(folder / 'commands'),
                       ROUTE_TEST_MISSING=str(int(missing)), ROUTE_TEST_ADD_FAILURE=str(int(add_failure)))
            return subprocess.run(['/bin/sh', str(script)], env=env, capture_output=True, timeout=5)

    def test_exact_host_priority_and_table(self):
        for rules, expected in [
            ('0: from all lookup local\n0: from all to 172.16.42.2 lookup main\n', 0),
            ('0: from all to 172.16.42.2/32 lookup main\n', 0),
            ('100: from all to 172.16.42.2 lookup main\n', 42),
            ('0: from all to 172.16.42.3 lookup main\n', 42),
            ('0: from all to 172.16.42.0/24 lookup main\n', 42),
            ('0: from all to 172.16.42.2 lookup local\n', 42),
            ('0: from all lookup local\n32766: from all lookup main\n', 42),
            ('', 42),
        ]:
            with self.subTest(rules=rules):
                result = self.execute(rules)
                self.assertEqual(result.returncode, expected, result.stderr.decode())
                self.assertEqual(b'REACHED_ATTACH' in result.stdout, expected == 0)

    def test_add_failure_stops_even_with_valid_readback(self):
        self.assertEqual(self.execute('0: from all to 172.16.42.2 lookup main\n', add_failure=True).returncode, 42)

    def test_missing_applet_stops(self):
        self.assertEqual(self.execute('0: from all to 172.16.42.2 lookup main\n', missing=True).returncode, 42)


if __name__ == '__main__':
    unittest.main()
