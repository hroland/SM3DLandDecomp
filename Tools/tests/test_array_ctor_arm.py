"""Differentially check the actual runtime source against the original EU helper."""

import hashlib
from pathlib import Path
import random
import struct
import unittest

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                               UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R11,
                               UC_ARM_REG_R12, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR)

ROOT = Path(__file__).resolve().parents[2]
ARRAY, CALLBACK, RETURN = 0x900100, 0xA00000, 0xA00004


class ArrayCtorARMTest(unittest.TestCase):
    comparisons = 0

    @classmethod
    def setUpClass(cls):
        cls.stock = (ROOT / "code.bin").read_bytes()
        if hashlib.sha256(cls.stock).hexdigest() != "e1d7e188ff88467df776c17cec45c44857fadf5b699944baa8cddcae7d939e64":
            raise RuntimeError("wrong EU executable")
        with (ROOT / "Build/headless/array_ctor_recovered.elf").open("rb") as stream:
            elf = ELFFile(stream)
            cls.segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
            cls.entry = elf.get_section_by_name(".symtab").get_symbol_by_name("__aeabi_vec_ctor_nocookie_nodtor")[0]["st_value"]

    def execute(self, size, count, ctor, offset, rebuilt):
        machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        machine.mem_map(0x100000, 0x400000)
        machine.mem_write(0x100000, self.stock)
        machine.mem_map(0x800000, 0x100000)
        for address, data in self.segments:
            machine.mem_write(address, data)
        machine.mem_map(0x900000, 0x10000)
        machine.mem_map(0xA00000, 0x1000)
        initial = bytes([0xA5]) * 0x1000
        machine.mem_write(0x900000, initial)
        args = (ARRAY + offset, CALLBACK if ctor else 0, size, count)
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
            machine.reg_write(reg, value)
        stack = 0x90FFF0
        machine.reg_write(UC_ARM_REG_SP, stack)
        machine.reg_write(UC_ARM_REG_LR, RETURN)
        for reg in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            machine.reg_write(reg, 0xC0000000 + reg)
        calls = []

        def callback(uc, address, _, __):
            if address != CALLBACK:
                return
            pointer = uc.reg_read(UC_ARM_REG_R0)
            calls.append(pointer)
            uc.mem_write(pointer, struct.pack("<I", 0xB0000000 + len(calls)))
            for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R12):
                uc.reg_write(reg, 0xDD000000 + reg + len(calls))
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        machine.hook_add(UC_HOOK_CODE, callback)
        machine.emu_start(self.entry if rebuilt else 0x28EABC, RETURN, count=3000)
        self.assertEqual(machine.reg_read(UC_ARM_REG_PC), RETURN)
        self.assertEqual(machine.reg_read(UC_ARM_REG_SP), stack)
        self.assertEqual(machine.reg_read(UC_ARM_REG_R0), args[0])
        for reg in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            self.assertEqual(machine.reg_read(reg), 0xC0000000 + reg)
        return calls, bytes(machine.mem_read(0x900000, 0x1000))

    def check(self, size, count, ctor=True, offset=0):
        stock = self.execute(size, count, ctor, offset, False)
        rebuilt = self.execute(size, count, ctor, offset, True)
        self.assertEqual(stock, rebuilt)
        expected = [ARRAY + offset + i * size for i in range(count)] if ctor else []
        self.assertEqual(stock[0], expected)
        type(self).comparisons += 1

    def test_callback_stride_order_return_and_preserved_registers(self):
        for size in (0, 1, 4, 8, 12, 96):
            for count in range(7):
                for offset in (0, 1):
                    self.check(size, count, offset=offset)
        rng = random.Random(0x28EABC)
        for _ in range(80):
            self.check(rng.randrange(0, 100), rng.randrange(0, 8), offset=rng.randrange(0, 4))

    def test_null_constructor_ignores_large_sizes_and_counts(self):
        for size in (0, 1, 0x80000000, 0xFFFFFFFF):
            for count in (0, 1, 7, 0x80000000, 0xFFFFFFFF):
                self.check(size, count, ctor=False)
