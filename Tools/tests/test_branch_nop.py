import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from branch_nop import nop_next_instruction_branches, NEXT_INSTRUCTION_NOP, UNCONDITIONAL_BRANCH_TO_SYMBOL

SOURCE = """
.syntax unified
.arm
.section "i.caller","ax",%progbits
.global caller
.type caller, %function
caller:
    ldr r0, [r0]
    b callee
.size caller, .-caller
.section "i.far","ax",%progbits
.global far
.type far, %function
far:
    mov r1, r0
    b callee
.size far, .-far
.section "i.local","ax",%progbits
.global local
.type local, %function
local:
    mov r2, r0
    b helper
    b callee
    bl callee
    bne callee
.size local, .-local
.section "i.helper","ax",%progbits
.global helper
.type helper, %function
helper:
    bx lr
.size helper, .-helper
"""


def words(path, section_name):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from elftools.elf.elffile import ELFFile
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section_by_name(section_name)
        data = section.data()
        relocations = [s for s in elf.iter_sections() if s.name == ".rel" + section_name]
        types = [r["r_info_type"] for r in relocations[0].iter_relocations()] if relocations else []
        return list(struct.unpack("<%dI" % (len(data) // 4), data)), types


@unittest.skipUnless(shutil.which("arm-none-eabi-as"), "GNU ARM assembler required")
class BranchNopTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        asm = self.folder / "input.s"
        asm.write_text(SOURCE)
        self.obj = self.folder / "input.o"
        subprocess.run([shutil.which("arm-none-eabi-as"), "-mcpu=mpcore", str(asm), "-o", str(self.obj)], check=True)

    def tearDown(self):
        shutil.rmtree(self.folder)

    def test_only_branches_resolving_to_the_next_instruction_change(self):
        out = self.folder / "output.o"
        placements = {"i.caller": 0x1000, "i.far": 0x2000, "i.local": 0x3000, "i.helper": 0x3008}
        changes = nop_next_instruction_branches(self.obj, out, placements, {"callee": 0x1008})
        self.assertEqual([(c["section"], c["offset"], c["target"]) for c in changes],
                         [("i.caller", 4, 0x1008), ("i.local", 4, 0x3008)])
        caller, caller_types = words(out, "i.caller")
        self.assertEqual(caller, [0xE5900000, NEXT_INSTRUCTION_NOP])
        self.assertEqual(caller_types, [0])
        far, far_types = words(out, "i.far")
        self.assertEqual(far[1], UNCONDITIONAL_BRANCH_TO_SYMBOL)
        self.assertNotEqual(far_types, [0])
        local, local_types = words(out, "i.local")
        # The branch to the locally defined adjacent helper becomes a NOP; the
        # far branch, the BL and the conditional branch keep their relocations.
        self.assertEqual(local[1], NEXT_INSTRUCTION_NOP)
        self.assertEqual(local[2], UNCONDITIONAL_BRANCH_TO_SYMBOL)
        self.assertEqual(local[3], 0xEBFFFFFE)
        self.assertEqual(local[4], 0x1AFFFFFE)
        self.assertEqual(local_types[0], 0)
        self.assertTrue(all(t != 0 for t in local_types[1:]))

    def test_unplaced_sections_and_unknown_targets_are_untouched(self):
        out = self.folder / "output.o"
        changes = nop_next_instruction_branches(self.obj, out, {"i.caller": 0x1000}, {})
        self.assertEqual(changes, [])
        self.assertEqual(out.read_bytes(), self.obj.read_bytes())
        changes = nop_next_instruction_branches(self.obj, out, {"i.far": 0x2000}, {"callee": 0x1008})
        self.assertEqual(changes, [])


if __name__ == "__main__":
    unittest.main()
