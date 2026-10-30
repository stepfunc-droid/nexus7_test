#!/usr/bin/env python3
"""Exercise exact-byte gate rejection across chunk and partition boundaries."""
import hashlib
from pathlib import Path
import tempfile
import unittest

import phase6_v2_audit_root_fstab as gate


class ExactBytesTest(unittest.TestCase):
    def test_exact_patch_partition_and_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            source, candidate = (Path(directory) / name for name in ('source', 'candidate'))
            original = bytes(range(256)) * 5
            source.write_bytes(original)
            start, replacement = 125, b'fstab-diagnostic'
            expected = original[:start] + replacement + original[start+len(replacement):]
            candidate.write_bytes(expected)
            old_chunk = gate.CHUNK
            gate.CHUNK = 128
            try:
                result = gate.compare_exact(source, candidate, [(start, replacement)], (129, 1030))
                self.assertEqual(result['region_sha256'], [hashlib.sha256(x[129:1030]).hexdigest()
                                                          for x in (original, expected)])
                for offset in (0, 124, 125, 129, 140, 1029, 1279):
                    bad = bytearray(expected)
                    bad[offset] ^= 1
                    candidate.write_bytes(bad)
                    with self.assertRaises(ValueError, msg=f'tamper {offset}'):
                        gate.compare_exact(source, candidate, [(start, replacement)])
                candidate.write_bytes(expected + b'x')
                with self.assertRaises(ValueError):
                    gate.compare_exact(source, candidate, [(start, replacement)])
                with self.assertRaises(ValueError):
                    gate.compare_exact(source, source, [(start, replacement)])
                candidate.write_bytes(expected)
                with self.assertRaises(ValueError):
                    gate.compare_exact(source, candidate, [(125, b'ab'), (126, b'cd')])
                with self.assertRaises(ValueError):
                    gate.compare_exact(source, candidate, [(1280, b'x')])
            finally:
                gate.CHUNK = old_chunk


if __name__ == '__main__':
    unittest.main()
