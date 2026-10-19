"""The independent gate must reject changed branch targets and misplaced code."""

import sys
import json
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_elf import compare_bytes, read_recovered_references, EU_SHA256


class ByteGateTest(unittest.TestCase):
    def test_equal_bytes_at_original_address_pass(self):
        self.assertTrue(compare_bytes(b"\x1e\xff\x2f\xe1", b"\x1e\xff\x2f\xe1", 0x100000, 0x100000)["matched"])

    def test_misplaced_identical_code_fails(self):
        result = compare_bytes(b"\x00\x00\x00\xeb", b"\x00\x00\x00\xeb", 0x100000, 0x800000)
        self.assertTrue(result["byte_exact"])
        self.assertFalse(result["matched"])

    def test_changed_branch_destination_fails(self):
        result = compare_bytes(b"\x00\x00\x00\xeb", b"\x01\x00\x00\xeb", 0x100000, 0x100000)
        self.assertFalse(result["matched"])
        self.assertEqual(result["first_difference"], 0)

    def test_extra_or_missing_bytes_fail(self):
        for expected, actual in ((b"ab", b"abc"), (b"abc", b"ab")):
            result = compare_bytes(expected, actual, 0x100000, 0x100000)
            self.assertFalse(result["matched"])
            self.assertEqual(result["first_difference"], 2)

    def test_explicit_shared_tail_references_preserve_overlapping_ranges(self):
        path = Path(__file__).resolve().parents[2] / "Data/RecoveredFunctions.json"
        references = read_recovered_references(path)
        self.assertIn((0x1CACB4, 120), references.values())
        self.assertIn((0x1CAD00, 44), references.values())

    def test_recovered_references_reject_wrong_binary_and_extent(self):
        metadata = {"code_sha256": EU_SHA256, "functions": [
            {"address": "0x001cad00", "symbol": "test",
             "code_ranges": [["0x001cad00", "0x001cad2c"]]}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "references.json"
            metadata["code_sha256"] = "0" * 64
            path.write_text(json.dumps(metadata))
            with self.assertRaises(ValueError):
                read_recovered_references(path)
            metadata["code_sha256"] = EU_SHA256
            metadata["functions"][0]["code_ranges"][0][0] = "0x001cad04"
            path.write_text(json.dumps(metadata))
            with self.assertRaises(ValueError):
                read_recovered_references(path)
