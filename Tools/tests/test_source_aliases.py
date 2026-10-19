"""Source aliases must resolve to real function bodies, without address fallbacks."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from elftools.elf.elffile import ELFFile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_aliases import alias_script
from whole_build import object_sections


class SourceAliasTest(unittest.TestCase):
    def test_linked_alias_uses_actual_source_body_and_placement(self):
        if not all(shutil.which(t) for t in ("arm-none-eabi-as", "arm-none-eabi-ld")):
            self.skipTest("GNU ARM binutils required")
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source, obj = folder / "test.s", folder / "test.o"
            script, linked = folder / "test.ld", folder / "test.elf"
            source.write_text('.arm\n.text\n.global body, caller\n'
                              '.type body,%function\nbody: mov r0,#7\nbx lr\n.size body,.-body\n'
                              '.type caller,%function\ncaller: b legacy\n.size caller,.-caller\n')
            subprocess.run(["arm-none-eabi-as", str(source), "-o", str(obj)],
                           check=True, capture_output=True)
            functions, _ = object_sections(obj)
            aliases = alias_script([{"alias": "legacy", "target": "body"}],
                                   {name: [info] for name, info in functions.items()})
            for address in (0x100000, 0x800000):
                script.write_text(f'SECTIONS {{ .text 0x{address:x} : {{ *(.text) }} }}\n'
                                  + '\n'.join(aliases))
                subprocess.run(["arm-none-eabi-ld", "-T", str(script), str(obj), "-o", str(linked)],
                               check=True, capture_output=True)
                with linked.open("rb") as stream:
                    elf = ELFFile(stream)
                    table = elf.get_section_by_name(".symtab")
                    self.assertEqual(table.get_symbol_by_name("legacy")[0]["st_value"], address)
                    self.assertEqual(table.get_symbol_by_name("body")[0]["st_value"], address)
                    # Caller branches back from address+8 to the real source body.
                    self.assertEqual(elf.get_section_by_name(".text").data()[-4:], b'\xfc\xff\xff\xea')

    def test_missing_ambiguous_local_and_stub_targets_rejected(self):
        row = {"alias": "legacy", "target": "body"}
        valid = {"section": "i.body", "size": 8, "binding": "STB_GLOBAL"}
        for candidates in ([], [valid, valid], [{**valid, "section": "i.stub.body"}],
                           [{**valid, "size": 0}], [{**valid, "binding": "STB_LOCAL"}]):
            with self.subTest(candidates=candidates), self.assertRaises(ValueError):
                alias_script([row], {"body": candidates})
        with self.assertRaises(ValueError):
            alias_script([row], {"body": [valid], "legacy": [valid]})
        with self.assertRaises(ValueError):
            alias_script([row, row], {"body": [valid]})

    def test_address_constants_and_script_injection_rejected(self):
        valid = {"body": [{"section": "i.body", "size": 8, "binding": "STB_GLOBAL"}]}
        for row in ({"alias": "legacy", "target": "body", "address": "0x100000"},
                    {"alias": "legacy", "target": "0x100000"},
                    {"alias": "legacy", "target": 0x100000},
                    {"alias": 'bad"; extra = 3;', "target": "body"},
                    {"alias": "body", "target": "body"}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                alias_script([row], valid)
