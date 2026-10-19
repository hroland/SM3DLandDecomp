import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inline_arm_leaf import conditional_inline, leaf_instruction, NOP, EMPTY_CALL_NOP


class LeafInliningTest(unittest.TestCase):
    def body(self, *words):
        return struct.pack("<" + "I" * len(words), *words)

    def test_load_and_return_only(self):
        self.assertEqual(leaf_instruction(self.body(0xE1D005D5, 0xE12FFF1E)), 0xE1D005D5)
        self.assertEqual(leaf_instruction(self.body(0xE12FFF1E)), NOP)

    def test_location_sensitive_and_control_instructions_rejected(self):
        for word in (0xE59F0000, 0xE59D0000, 0xE1A0000E, 0xE1A0F000, 0xEBFFFFFE):
            self.assertIsNone(leaf_instruction(self.body(word, 0xE12FFF1E)))

    def test_requires_exact_return_and_size(self):
        self.assertIsNone(leaf_instruction(self.body(0xE1D005D5, 0xE1A00000)))
        self.assertIsNone(leaf_instruction(self.body(0xE1D005D5, 0xE1A00000, 0xE12FFF1E)))

    def test_conditions_preserved_and_conflicts_rejected(self):
        self.assertEqual(conditional_inline(0x1BFFFFFE, 0xE1D005D5), 0x11D005D5)
        self.assertEqual(conditional_inline(0xEBFFFFFE, 0x01D005D5), 0x01D005D5)
        self.assertIsNone(conditional_inline(0x1BFFFFFE, 0x01D005D5))

    def test_tail_branches_and_blx_not_inlined(self):
        self.assertIsNone(conditional_inline(0xEAFFFFFE, 0xE1D005D5))
        self.assertIsNone(conditional_inline(0xFAFFFFFE, 0xE1D005D5))

    def test_empty_call_is_effect_free_under_every_ordinary_condition(self):
        for condition in range(15):
            self.assertEqual(conditional_inline((condition << 28) | 0x0BFFFFFE, NOP), EMPTY_CALL_NOP)
        self.assertIsNone(conditional_inline(0xEAFFFFFE, NOP))
        self.assertIsNone(conditional_inline(0xFAFFFFFE, NOP))
