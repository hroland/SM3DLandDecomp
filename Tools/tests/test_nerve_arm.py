"""Differentially execute stock ARM and rebuilt C++; no game/emulator modification."""

import hashlib
import itertools
import struct
from pathlib import Path
import random
import unittest

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R4,
                               UC_ARM_REG_R11, UC_ARM_REG_PC, UC_ARM_REG_SP,
                               UC_ARM_REG_LR)


ROOT = Path(__file__).resolve().parents[2]
STOCK = ROOT / "code.bin"
REBUILT = ROOT / "Build/headless/nerve_recovered.elf"
KEEPER, VT, N1, N2, CTRL = 0x900000, 0x901000, 0x902000, 0x902010, 0x903000
EXECUTE, END, RETURN = 0xA00000, 0xA00004, 0xA00008
START_CTRL, END_CTRL = 0x1CABD8, 0x1CAC3C
STOCK_ADDRESSES = {"update": 0x25065C, "set": 0x1BEE64, "get": 0x32FD54}
SYMBOLS = {"update": "_ZN2al11NerveKeeper6updateEv",
           "set": "_ZN2al11NerveKeeper8setNerveEPKNS_5NerveE",
           "get": "_ZNK2al11NerveKeeper15getCurrentNerveEv"}


class NerveARMTest(unittest.TestCase):
    comparisons = 0
    @classmethod
    def setUpClass(cls):
        cls.stock = STOCK.read_bytes()
        if hashlib.sha256(cls.stock).hexdigest() != (
                "e1d7e188ff88467df776c17cec45c44857fadf5b699944baa8cddcae7d939e64"):
            raise RuntimeError("wrong stock binary")
        with REBUILT.open("rb") as stream:
            elf = ELFFile(stream)
            cls.segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments()
                            if s["p_type"] == "PT_LOAD"]
            symtab = elf.get_section_by_name(".symtab")
            cls.addresses = {k: symtab.get_symbol_by_name(v)[0]["st_value"]
                             for k, v in SYMBOLS.items()}

    def run_arm(self, kind, initial, rebuilt=False, callback_mode=0, next_nerve=N2):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x100000, 0x400000)
        uc.mem_write(0x100000, self.stock)
        uc.mem_map(0x800000, 0x10000)
        for address, data in self.segments:
            uc.mem_write(address, data)
        uc.mem_map(0x900000, 0x10000)
        uc.mem_map(0xA00000, 0x1000)
        uc.mem_write(KEEPER, struct.pack("<6I", *initial))
        uc.mem_write(VT, struct.pack("<2I", EXECUTE, END))
        for nerve in (N1, N2):
            uc.mem_write(nerve, struct.pack("<I", VT))
        uc.reg_write(UC_ARM_REG_R0, KEEPER)
        uc.reg_write(UC_ARM_REG_R1, next_nerve)
        uc.reg_write(UC_ARM_REG_SP, 0x90FFF0)
        uc.reg_write(UC_ARM_REG_LR, RETURN)
        for reg in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            uc.reg_write(reg, 0xAA000000 + reg)
        events = []

        def words():
            return struct.unpack("<6I", uc.mem_read(KEEPER, 24))

        def hook(machine, address, size, _):
            if address not in (EXECUTE, END, START_CTRL, END_CTRL):
                return
            r0 = machine.reg_read(UC_ARM_REG_R0)
            r1 = machine.reg_read(UC_ARM_REG_R1)
            events.append((address, r0, r1 if address != END_CTRL else None, words()))
            if address == EXECUTE and callback_mode == 1:
                # Emulate the observable effects of a state requesting a transition.
                if words()[3] < 0x80000000 and words()[1]:
                    events.append((END, words()[1], KEEPER, words()))
                machine.mem_write(KEEPER + 8, struct.pack("<2I", N2, 0xFFFFFFFF))
            elif address == EXECUTE and callback_mode == 2:
                machine.mem_write(KEEPER + 12, struct.pack("<I", 0x7FFFFFFF))
            elif address == END_CTRL and callback_mode == 3:
                machine.mem_write(KEEPER + 8, struct.pack("<I", N2))
            elif address == START_CTRL and callback_mode == 4:
                machine.mem_write(KEEPER + 8, struct.pack("<I", N1))
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE, hook)
        entry = self.addresses[kind] if rebuilt else STOCK_ADDRESSES[kind]
        uc.emu_start(entry, RETURN, count=3000)
        self.assertEqual(uc.reg_read(UC_ARM_REG_PC), RETURN)
        self.assertEqual(uc.reg_read(UC_ARM_REG_SP), 0x90FFF0)
        for reg in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            self.assertEqual(uc.reg_read(reg), 0xAA000000 + reg)
        result = uc.reg_read(UC_ARM_REG_R0) if kind == "get" else None
        return words(), events, result

    def check_case(self, kind, initial, mode=0, next_nerve=N2):
        stock = self.run_arm(kind, initial, callback_mode=mode, next_nerve=next_nerve)
        rebuilt = self.run_arm(kind, initial, rebuilt=True,
                               callback_mode=mode, next_nerve=next_nerve)
        self.assertEqual(stock, rebuilt, (kind, initial, mode, next_nerve))
        type(self).comparisons += 1

    def test_update_transitions_and_callbacks(self):
        steps = (0x80000000, 0xFFFFFFFE, 0xFFFFFFFF, 0, 1, 7, 0x7FFFFFFF)
        for active, pending, step, ctrl, mode in itertools.product(
                (0, N1, N2), (0, N1, N2), steps, (0, CTRL), range(5)):
            if not active and not pending:
                continue  # Not a valid update receiver in either implementation.
            self.check_case("update", (0x55, active, pending, step, ctrl, 0x66), mode)

    def test_set_and_get(self):
        for active, pending, step, next_nerve in itertools.product(
                (0, N1, N2), (0, N1, N2),
                (0x80000000, 0xFFFFFFFF, 0, 1, 0x7FFFFFFF), (0, N1, N2)):
            initial = (0x55, active, pending, step, CTRL, 0x66)
            self.check_case("set", initial, next_nerve=next_nerve)
            self.check_case("get", initial)

    def test_random_step_values(self):
        rng = random.Random(0x3D1A)
        for _ in range(100):
            initial = (rng.getrandbits(32), N1, rng.choice((0, N1, N2)),
                       rng.getrandbits(32), rng.choice((0, CTRL)), rng.getrandbits(32))
            self.check_case("update", initial, rng.randrange(5))


if __name__ == "__main__":
    unittest.main()
