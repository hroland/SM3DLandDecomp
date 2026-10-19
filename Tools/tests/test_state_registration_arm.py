"""Check the recovered EU state initializer and its shared registration tail."""

import hashlib
import itertools
from pathlib import Path
import random
import struct
import unittest

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                               UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R11,
                               UC_ARM_REG_R12, UC_ARM_REG_PC, UC_ARM_REG_SP,
                               UC_ARM_REG_LR)

ROOT = Path(__file__).resolve().parents[2]
HOST, HOST_VT, K1, K2 = 0x900000, 0x900100, 0x900200, 0x900300
C1, C2, A1, A2 = 0x900400, 0x900500, 0x901000, 0x902000
S1, S2, STATE_VT = 0x903000, 0x903100, 0x903200
GET, INIT, RETURN = 0xA00000, 0xA00004, 0xA00008
ORIGINAL = {"init": 0x1CACB4, "register": 0x1CAD00}
SYMBOLS = {
    "init": "_ZN2al14initNerveStateEPNS_9IUseNerveEPNS_14NerveStateBaseEPKNS_5NerveEPKc",
    "register": "_ZN2al14NerveStateCtrl13registerStateEPNS_14NerveStateBaseEPKNS_5NerveEPKc",
}


class StateRegistrationARMTest(unittest.TestCase):
    comparisons = 0
    comparisons_by_function = {"init": 0, "register": 0}

    @classmethod
    def setUpClass(cls):
        cls.stock = (ROOT / "code.bin").read_bytes()
        if hashlib.sha256(cls.stock).hexdigest() != (
                "e1d7e188ff88467df776c17cec45c44857fadf5b699944baa8cddcae7d939e64"):
            raise RuntimeError("wrong EU binary")
        with (ROOT / "Build/headless/state_registration_recovered.elf").open("rb") as stream:
            elf = ELFFile(stream)
            cls.segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments()
                            if s["p_type"] == "PT_LOAD"]
            table = elf.get_section_by_name(".symtab")
            cls.addresses = {kind: table.get_symbol_by_name(name)[0]["st_value"]
                             for kind, name in SYMBOLS.items()}

    def run_arm(self, kind, count=0, capacity=8, state=S1, nerve=0x11112222,
                name=0x33334444, mode=0, scratch=0, rebuilt=False):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x100000, 0x400000)
        uc.mem_write(0x100000, self.stock)
        uc.mem_map(0x810000, 0x10000)
        for address, data in self.segments:
            uc.mem_write(address, data)
        uc.mem_map(0x900000, 0x10000)
        uc.mem_write(0x900000, b"\xA5" * 0x4000)
        uc.mem_map(0xA00000, 0x1000)
        uc.mem_write(HOST, struct.pack("<2I", HOST_VT, K1))
        uc.mem_write(HOST_VT, struct.pack("<I", GET))
        for keeper, ctrl in ((K1, C1), (K2, C2)):
            uc.mem_write(keeper, struct.pack("<6I", HOST, 0x55, 0x66, 7, ctrl, 0x77))
        uc.mem_write(C1, struct.pack("<4I", capacity, count, A1, A1 + 12))
        uc.mem_write(C2, struct.pack("<4I", 8, 2, A2, 0))
        for address in (S1, S2):
            uc.mem_write(address, struct.pack("<2IB3x", STATE_VT, K1, 0))
        uc.mem_write(STATE_VT, struct.pack("<8I", 0, 0, 0, INIT, 0, 0, 0, 0))
        for reg, value in ((UC_ARM_REG_R0, HOST if kind == "init" else C1),
                           (UC_ARM_REG_R1, state), (UC_ARM_REG_R2, nerve),
                           (UC_ARM_REG_R3, name), (UC_ARM_REG_R12, scratch),
                           (UC_ARM_REG_SP, 0x90FFF0), (UC_ARM_REG_LR, RETURN)):
            uc.reg_write(reg, value)
        for reg in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            uc.reg_write(reg, 0xAA000000 + reg)
        events = []

        def snapshot():
            return bytes(uc.mem_read(0x900000, 0x4000))

        def hook(machine, address, size, _):
            if address not in (INIT, GET):
                return
            receiver = machine.reg_read(UC_ARM_REG_R0)
            events.append((address, receiver, snapshot()))
            if address == INIT:
                self.assertEqual(receiver, state)
                if mode == 1:
                    machine.mem_write(HOST + 4, struct.pack("<I", K2))
                elif mode == 2:
                    machine.mem_write(K1 + 16, struct.pack("<I", C2))
                elif mode == 3:
                    machine.mem_write(C1 + 4, struct.pack("<I", count + 1))
                elif mode == 5:
                    machine.mem_write(state + 8, b"\x01")
                elif mode == 7:
                    machine.mem_write(C1 + 8, struct.pack("<I", A2))
                value = scratch
            else:
                self.assertEqual(receiver, HOST)
                if mode == 4:
                    machine.mem_write(C1 + 4, struct.pack("<I", count + 2))
                value = (K2 if mode == 6 else
                         struct.unpack("<I", machine.mem_read(HOST + 4, 4))[0])
            machine.reg_write(UC_ARM_REG_R0, value)
            for reg, mask in ((UC_ARM_REG_R1, 0x11111111), (UC_ARM_REG_R2, 0x22222222),
                              (UC_ARM_REG_R3, 0x33333333), (UC_ARM_REG_R12, 0x44444444)):
                machine.reg_write(reg, scratch ^ mask)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE, hook)
        uc.emu_start(self.addresses[kind] if rebuilt else ORIGINAL[kind], RETURN, count=3000)
        self.assertEqual(uc.reg_read(UC_ARM_REG_PC), RETURN)
        self.assertEqual(uc.reg_read(UC_ARM_REG_SP), 0x90FFF0)
        for reg in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            self.assertEqual(uc.reg_read(reg), 0xAA000000 + reg)
        return snapshot(), events

    def check_case(self, kind, **kwargs):
        self.assertEqual(self.run_arm(kind, **kwargs),
                         self.run_arm(kind, rebuilt=True, **kwargs), (kind, kwargs))
        type(self).comparisons += 1
        type(self).comparisons_by_function[kind] += 1

    def test_registration_preserves_neighbors_and_ignores_capacity(self):
        for count, capacity, state, nerve, name in itertools.product(
                range(5), (0, 2, 8), (0, S1, S2),
                (0, 0x11112222), (0, 0x33334444)):
            self.check_case("register", count=count, capacity=capacity,
                            state=state, nerve=nerve, name=name)

    def test_state_init_precedes_lookup_and_registration(self):
        for count, state, mode, nerve, name in itertools.product(
                range(5), (S1, S2), range(8), (0, 0x11112222), (0, 0x33334444)):
            self.check_case("init", count=count, state=state, mode=mode,
                            nerve=nerve, name=name)

    def test_random_arguments_and_caller_saved_registers(self):
        rng = random.Random(0x1CACB4)
        for _ in range(200):
            kind = rng.choice(("init", "register"))
            self.check_case(kind, count=rng.randrange(5), capacity=rng.randrange(9),
                            state=rng.choice((S1, S2)), nerve=rng.getrandbits(32),
                            name=rng.getrandbits(32), mode=rng.randrange(8),
                            scratch=rng.getrandbits(32))
