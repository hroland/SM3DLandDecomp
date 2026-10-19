"""Exercise image provenance checks with an independently assembled tiny ELF."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from verify_image import audit


class ImageGateTest(unittest.TestCase):
    def setUp(self):
        if not all(shutil.which(tool) for tool in ("arm-none-eabi-as", "arm-none-eabi-ld", "arm-none-eabi-objcopy")):
            self.skipTest("GNU ARM binutils required")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        source, obj = directory / "tiny.s", directory / "tiny.o"
        script = directory / "tiny.ld"
        self.elf, self.binary = directory / "tiny.elf", directory / "tiny.bin"
        source.write_text('.arm\n.text\n.global _start\n.type _start,%function\n_start: bx lr\n.size _start,.-_start\n.data\n.word 0x12345678\n')
        script.write_text('ENTRY(_start) SECTIONS { .text 0x100000 : { *(.text) } .data 0x100010 : { *(.data) } }\n')
        subprocess.run(["arm-none-eabi-as", str(source), "-o", str(obj)], check=True, capture_output=True)
        subprocess.run(["arm-none-eabi-ld", "-T", str(script), str(obj), "-o", str(self.elf)], check=True, capture_output=True)
        subprocess.run(["arm-none-eabi-objcopy", "-O", "binary", str(self.elf), str(self.binary)], check=True)
        self.original = self.binary.read_bytes()

    def test_word_counts_distinguish_emitted_code_data_and_padding(self):
        report = audit(self.elf, self.binary, self.original)
        self.assertEqual(report["matching_bytes"], 20)
        self.assertEqual(report["by_emitted_section_kind"]["executable_section"]["matching_bytes"], 4)
        self.assertEqual(report["by_emitted_section_kind"]["data_section"]["matching_bytes"], 4)
        self.assertEqual(report["by_emitted_section_kind"]["linker_padding"]["matching_bytes"], 12)
        changed_stock = bytes([self.original[0] ^ 1]) + self.original[1:]
        self.assertEqual(audit(self.elf, self.binary, changed_stock)["matching_bytes"], 16)
        self.assertFalse(report["full_game_decompilation_complete"])

    def test_modified_code_or_padding_cannot_be_counted(self):
        for offset in (0, 4, 15, 16):
            with self.subTest(offset=offset):
                modified = bytearray(self.original)
                modified[offset] ^= 1
                self.binary.write_bytes(modified)
                with self.assertRaises(ValueError):
                    audit(self.elf, self.binary, self.original)

    def test_truncated_or_extended_image_rejected(self):
        for modified in (self.original[:-1], self.original + b'\0'):
            self.binary.write_bytes(modified)
            with self.assertRaises(ValueError):
                audit(self.elf, self.binary, self.original)


if __name__ == "__main__":
    unittest.main()
