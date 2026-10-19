import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from relocation_targets import infer_targets


class RelocationTargetTest(unittest.TestCase):
    def test_unknown_call_target_requires_exact_surrounding_code(self):
        emitted = struct.pack("<3I", 0xE92D4010, 0xEBFFFFFE, 0xE8BD8010)
        original = struct.pack("<3I", 0xE92D4010, 0xEB00003D, 0xE8BD8010)
        relocation = {"offset": 4, "type": 28, "symbol": "callee", "global": True}
        targets, _ = infer_targets(emitted, original, 0x100000, [relocation], 0x100000, 0x200000)
        self.assertEqual(targets, {"callee": 0x100100})
        changed = struct.pack("<I", 0xE92D4030) + original[4:]
        self.assertEqual(infer_targets(emitted, changed, 0x100000, [relocation], 0x100000, 0x200000)[0], {})

    def test_known_target_and_branch_condition_cannot_be_overridden(self):
        emitted = struct.pack("<I", 0xEBFFFFFE)
        original = struct.pack("<I", 0xEB00003E)
        relocation = {"offset": 0, "type": 28, "symbol": "callee", "global": True,
                      "known_address": 0x100200}
        self.assertEqual(infer_targets(emitted, original, 0x100000, [relocation], 0x100000, 0x200000)[0], {})
        relocation.pop("known_address")
        self.assertEqual(infer_targets(emitted, struct.pack("<I", 0x1B00003E), 0x100000,
                                      [relocation], 0x100000, 0x200000)[0], {})

    def test_unknown_absolute_data_address_is_not_inferred(self):
        relocation = {"offset": 0, "type": 2, "symbol": "data", "global": True}
        targets, reason = infer_targets(bytes(4), struct.pack("<I", 0x3A2000), 0x100000,
                                        [relocation], 0x100000, 0x200000)
        self.assertEqual(targets, {})
        self.assertIn("no confirmed", reason)
