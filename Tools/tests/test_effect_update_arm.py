"""Effect behavior with real math/query bodies and intercepted emitter setters."""

import hashlib
from pathlib import Path
import random
import struct
import sys
import unittest

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from effect_behavior import prepare, UPDATE, ENTRIES
from verify_elf import EU_SHA256

ROOT = Path(__file__).resolve().parents[2]
ENTRY, PARAMS, OTHER_PARAMS = 0x900100, 0x901000, 0x901100
BUFFER, OTHER_BUFFER = 0x902000, 0x902100
MATRIX, POSITION, OTHER_MATRIX = 0x903000, 0x903100, 0x903200
RETURN, STACK = 0x700FF0, 0x90FFF0
ORIGINAL = {UPDATE: 0x1EA220, "FUN_0023f45c": 0x23F45C,
            "FUN_0027cb9c": 0x27CB9C, "FUN_00291470": 0x291470}


class EffectUpdateARMTest(unittest.TestCase):
    comparisons = 0
    comparisons_by_function = {"update": 0, "validity": 0, "transform": 0, "copy": 0}

    @classmethod
    def setUpClass(cls):
        cls.stock = (ROOT / "code.bin").read_bytes()
        if hashlib.sha256(cls.stock).hexdigest() != EU_SHA256:
            raise RuntimeError("wrong EU executable")
        cls.artifact = prepare()
        with cls.artifact.open("rb") as stream:
            elf = ELFFile(stream)
            cls.segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]

    def machine(self):
        machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        machine.mem_map(0x100000, 0x400000)
        machine.mem_write(0x100000, self.stock)
        machine.mem_map(0x700000, 0x1000)
        machine.mem_map(0x800000, 0x10000)
        machine.mem_map(0x900000, 0x10000)
        for address, data in self.segments:
            machine.mem_write(address, data)
        machine.reg_write(UC_ARM_REG_C1_C0_2, 0xF << 20)
        machine.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        return machine

    def run_function(self, machine, symbol, args, rebuilt):
        for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2), args):
            machine.reg_write(register, value)
        machine.reg_write(UC_ARM_REG_SP, STACK)
        machine.reg_write(UC_ARM_REG_LR, RETURN)
        for register in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            machine.reg_write(register, 0xC0000000 + register)
        for register in range(UC_ARM_REG_D8, UC_ARM_REG_D15 + 1):
            machine.reg_write(register, 0x3FF0000000000000 + register)
        machine.emu_start((ENTRIES if rebuilt else ORIGINAL)[symbol], RETURN, count=20000)
        self.assertEqual(machine.reg_read(UC_ARM_REG_PC), RETURN)
        self.assertEqual(machine.reg_read(UC_ARM_REG_SP), STACK)
        for register in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            self.assertEqual(machine.reg_read(register), 0xC0000000 + register)
        for register in range(UC_ARM_REG_D8, UC_ARM_REG_D15 + 1):
            self.assertEqual(machine.reg_read(register), 0x3FF0000000000000 + register)
        return machine.reg_read(UC_ARM_REG_R0)

    def execute_update(self, config, rebuilt):
        machine = self.machine()
        write32 = lambda a, v: machine.mem_write(a, struct.pack("<I", v & 0xFFFFFFFF))
        read32 = lambda a: struct.unpack("<I", machine.mem_read(a, 4))[0]
        write32(ENTRY + 4, BUFFER)
        write32(ENTRY + 8, config.get("count", 3))
        write32(ENTRY + 12, PARAMS)
        write32(ENTRY + 16, POSITION)
        write32(ENTRY + 20, MATRIX)
        values = config.get("matrix", (2, 3, 4, 5, -1, 6, 2, -4, 3, -2, 1, 9))
        machine.mem_write(MATRIX, struct.pack("<12f", *values))
        machine.mem_write(OTHER_MATRIX, struct.pack("<12f", *reversed(values)))
        machine.mem_write(POSITION, struct.pack("<3f", 1.5, -2, 3.25))
        for address in (PARAMS, OTHER_PARAMS):
            machine.mem_write(address + 0x14, struct.pack("<3f", *config.get("offset", (2, -3, 0.5))))
            machine.mem_write(address + 0x3F, bytes([config.get("position", 1), config.get("matrix_flag", 1)]))
            machine.mem_write(address + 0x45, bytes([config.get("transform", 1)]))
        for index in range(6):
            handle, reference, emitter = 0x904000 + index * 0x100, 0x905000 + index * 0x40, 0x906000 + index * 0x40
            write32(BUFFER + 4 * index, handle)
            write32(OTHER_BUFFER + 4 * index, 0x904000 + (5 - index) * 0x100)
            write32(handle + 4, reference)
            state = config.get("state", "valid")
            write32(reference, 0 if state == "null" else emitter)
            write32(reference + 4, 31)
            write32(emitter + 12, 30 if state == "stale" else 31)
            write32(emitter + 4, 0 if state == "inactive" else 2)
        trace = []

        def callback(uc, address, _, __):
            if address not in (0x23F294, 0x2D37D0):
                return
            args = [uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
            if address == 0x23F294:
                trace.append(("matrix", args[0], args[1], bytes(uc.mem_read(args[2], 48))))
            else:
                trace.append(("position", args[0], args[1], bytes(uc.mem_read(args[2], 12)),
                              bytes(uc.mem_read(args[3], 48))))
            if len(trace) == 1:
                mutation = config.get("mutation")
                if mutation == "swap_params":
                    write32(ENTRY + 12, OTHER_PARAMS)
                    machine.mem_write(OTHER_PARAMS + 0x3F, b'\1\0')
                elif mutation == "shrink":
                    write32(ENTRY + 8, 0)
                elif mutation == "grow_and_swap":
                    write32(ENTRY + 8, 5)
                    write32(ENTRY + 4, OTHER_BUFFER)
                    write32(ENTRY + 20, OTHER_MATRIX)
            for register in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R12):
                uc.reg_write(register, 0xAB000000 + register + len(trace))
            for register in range(UC_ARM_REG_S0, UC_ARM_REG_S15 + 1):
                uc.reg_write(register, 0x3F000000 + register)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        machine.hook_add(UC_HOOK_CODE, callback)
        result = self.run_function(machine, UPDATE, [ENTRY], rebuilt)
        return result, trace, bytes(machine.mem_read(0x900000, 0x7000))

    def compare_update(self, config):
        original = self.execute_update(config, False)
        self.assertEqual(original, self.execute_update(config, True), config)
        type(self).comparisons += 1
        type(self).comparisons_by_function["update"] += 1
        return original

    def test_flags_transforms_and_callback_mutations(self):
        for count in (-1, 0, 1, 3):
            for flags in range(8):
                for state in ("valid", "null", "stale", "inactive"):
                    config = dict(count=count, matrix_flag=(flags >> 1) & 1,
                                  position=flags & 1, transform=(flags >> 2) & 1, state=state)
                    result, trace, _ = self.compare_update(config)
                    self.assertEqual(result, int(count > 0 and state == "valid" and flags & 3 != 0))
                    if result and flags & 3 == 3:
                        self.assertEqual([t[0] for t in trace], ["matrix", "position"] * count)
        for mutation in ("swap_params", "shrink", "grow_and_swap"):
            for flags in range(1, 8):
                self.compare_update(dict(count=2, matrix_flag=(flags >> 1) & 1,
                                         position=flags & 1, transform=(flags >> 2) & 1, mutation=mutation))
        rng = random.Random(0x1EA220)
        for _ in range(64):
            self.compare_update(dict(count=rng.randrange(1, 6), matrix_flag=1, position=rng.randrange(2),
                                     transform=1, offset=tuple(rng.randrange(-32, 32) / 8 for _ in range(3)),
                                     matrix=tuple(rng.randrange(-64, 64) / 8 for _ in range(12))))

    def test_validity_generation_and_signed_counts(self):
        for present in (False, True):
            for same in (False, True):
                for count in (-0x80000000, -1, 0, 1, 0x7FFFFFFF):
                    for generation in (0, 0xFFFFFFFF):
                        results = []
                        for rebuilt in (False, True):
                            machine = self.machine()
                            machine.mem_write(ENTRY + 4, struct.pack("<I", PARAMS))
                            machine.mem_write(PARAMS, struct.pack("<II", MATRIX if present else 0, generation))
                            machine.mem_write(MATRIX + 4, struct.pack("<i", count))
                            machine.mem_write(MATRIX + 12, struct.pack("<I", generation if same else generation ^ 1))
                            results.append(self.run_function(machine, "FUN_0023f45c", [ENTRY], rebuilt))
                        self.assertEqual(results, [int(present and same and count > 0)] * 2)
                        type(self).comparisons += 1
                        type(self).comparisons_by_function["validity"] += 1

    def test_math_helpers_input_output_aliases(self):
        rng = random.Random(0x27CB9C)
        for symbol, label in (("FUN_0027cb9c", "transform"), ("FUN_00291470", "copy")):
            for delta in (0, 4, 12, 32, 48, 52, 64):
                for _ in range(12):
                    data = struct.pack("<32f", *(rng.randrange(-64, 64) / 8 for _ in range(32)))
                    outputs = []
                    for rebuilt in (False, True):
                        machine = self.machine()
                        machine.mem_write(MATRIX, data)
                        args = [MATRIX + delta, MATRIX, MATRIX + 48]
                        self.run_function(machine, symbol, args, rebuilt)
                        outputs.append(bytes(machine.mem_read(MATRIX, 128)))
                    self.assertEqual(*outputs)
                    type(self).comparisons += 1
                    type(self).comparisons_by_function[label] += 1
