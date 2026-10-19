"""Full collider control-flow comparison, with pinned math and engine callbacks.

Only two boundaries are intercepted: the global LiveActorKit accessor and the
CollisionDirector's virtual query engine. The global director wrapper, both
query wrappers, the director query and the default-buffer accessor execute as
original code or as rebuilt source on each side.
"""

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
from collision_behavior import prepare, ENTRIES
from verify_elf import EU_SHA256

ROOT = Path(__file__).resolve().parents[2]
COLLIDER, TRANS, VELOCITY = 0x900100, 0x903000, 0x903100
PARTS, DIRECTOR, CONTACTS = 0x905000, 0x909000, 0x90A100
KIT, QUERY, POINTERS, RECORDS, GRAVITY = 0x908000, 0x909100, 0x909200, 0x90C000, 0x903200
ENGINE, ENGINE_VTABLE, ENGINE_QUERY = 0x909300, 0x909400, 0x700100
STACK, RETURN = 0x90FFF0, 0x700FF0


def install_engine(uc, w32):
    """Give the director a query engine whose virtual query lands on a hook."""
    w32(DIRECTOR + 4, ENGINE)
    w32(ENGINE, ENGINE_VTABLE)
    for slot in range(8):
        w32(ENGINE_VTABLE + slot * 4, 0x700200 + slot * 4)
    w32(ENGINE_VTABLE + 0x14, ENGINE_QUERY)
    w32(DIRECTOR + 8, 0xDEAD0001)
    w32(DIRECTOR + 0xC, 0xDEAD0002)
    w32(QUERY + 0xC, 0xFEED0000)


class CollisionResolutionARMTest(unittest.TestCase):
    comparisons = 0
    comparisons_by_function = {"resolve": 0, "path_init": 0, "path_advance": 0,
                               "path_sample": 0, "path_position": 0}

    @classmethod
    def setUpClass(cls):
        cls.stock = (ROOT / "code.bin").read_bytes()
        if hashlib.sha256(cls.stock).hexdigest() != EU_SHA256:
            raise RuntimeError("wrong EU executable")
        cls.artifact = prepare()
        with cls.artifact.open("rb") as stream:
            elf = ELFFile(stream)
            cls.segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]

    def execute(self, config, rebuilt):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x100000, 0x400000)
        uc.mem_write(0x100000, self.stock)
        uc.mem_map(0x700000, 0x1000)
        uc.mem_map(0x800000, 0x10000)
        uc.mem_map(0x900000, 0x10000)
        for address, data in self.segments:
            uc.mem_write(address, data)
        uc.reg_write(UC_ARM_REG_C1_C0_2, 0xF << 20)
        uc.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        def w32(a, value): uc.mem_write(a, struct.pack("<I", value & 0xFFFFFFFF))
        def r32(a): return struct.unpack("<I", uc.mem_read(a, 4))[0]
        def wf(a, values): uc.mem_write(a, struct.pack("<" + "f" * len(values), *values))
        def vf(a): return struct.unpack("<3f", uc.mem_read(a, 12))
        w32(COLLIDER, 0x123)
        w32(COLLIDER + 4, 0x456)
        w32(COLLIDER + 12, TRANS)
        w32(COLLIDER + 16, GRAVITY)
        wf(GRAVITY, [0, -1, 0])
        w32(KIT + 0x28, DIRECTOR)
        w32(DIRECTOR + 0x14, QUERY)
        w32(QUERY + 8, POINTERS)
        install_engine(uc, w32)
        for i in range(8):
            record = RECORDS + i * 0x88
            w32(POINTERS + i * 4, record)
            uc.mem_write(record, bytes((j + i) % 256 for j in range(0x88)))
            w32(record, PARTS)
            wf(record + 8, config.get("normal", [(1, 0, 0), (0, 1, 0), (0, -1, 0)][i % 3]))
            wf(record + 0x5C, [config.get("ground", 0.25) + i / 4])
            wf(record + 0x60, [0, 0, 0])
            wf(record + 0x6C, config.get("contact_direction", (1, 1, 0)))
            wf(record + 0x78, config.get("correction", (0, 0, 0)))
            uc.mem_write(record + 0x84, bytes([config.get("contact_flag", 1)]))
        wf(TRANS, config.get("center", (3.0, -2.0, 5.0)))
        wf(VELOCITY, config.get("velocity", (4.0, 1.0, 0.5)))
        wf(COLLIDER + 0x14, [config.get("radius", 2.0), 0.0])
        wf(COLLIDER + 0x1F0, config.get("previous", config.get("center", (3.0, -2.0, 5.0))))
        wf(COLLIDER + 0x1FC, [config.get("previous_radius", config.get("radius", 2.0))])
        w32(COLLIDER + 0x20, config.get("capacity", 4))
        w32(COLLIDER + 0x24, 99)
        w32(COLLIDER + 0x28, CONTACTS)
        w32(DIRECTOR + 0x18, CONTACTS)
        wf(COLLIDER + 0x2C, [99, 98, 97])
        w32(COLLIDER + 0x38, PARTS)
        wf(COLLIDER + 0x40, [0, 1, 0])
        wf(COLLIDER + 0xC0, [config.get("old_ground", -1.0)])
        wf(COLLIDER + 0x14C, [88])
        wf(COLLIDER + 0x1D8, [77])
        w32(COLLIDER + 0x1DC, config.get("frames", 0))
        wf(COLLIDER + 0x1E0, [0.5, 0.5, 0.5])
        uc.mem_write(COLLIDER + 0x1EC, bytes([config.get("flags", 0)]))
        identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]
        moved = identity.copy()
        for index, value in zip((3, 7, 11), config.get("platform", (0, 0, 0))):
            moved[index] = value
        wf(PARTS + 0x44, moved)
        wf(PARTS + 0xD4, identity)
        w32(PARTS + 0x134, int(config.get("platform_disabled", False)))
        trace = []
        queries = 0

        def callback(machine, address, _, __):
            nonlocal queries
            if address not in (0x277250, ENGINE_QUERY):
                return
            args = [machine.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
            result = None
            if address == 0x277250:
                trace.append(("kit",))
                result = KIT
            else:
                # engine->querySphere(results, info, variant): record the whole ABI.
                info = args[2]
                trace.append(("engine", args[0], args[1], args[3], vf(r32(info)), r32(info + 4), r32(info + 8),
                              r32(info + 12), r32(DIRECTOR + 8), r32(DIRECTOR + 0xC), r32(QUERY)))
                result = int(config.get("all_hits", False) or queries in config.get("hits", ()))
                count = config.get("contacts", 1) if result else 0
                w32(QUERY, count)
                for i in range(min(count, 8)):
                    w32(r32(POINTERS + i * 4), PARTS)
                if config.get("mutate_query") and queries == 0:
                    w32(COLLIDER, 0x789)
                    w32(COLLIDER + 4, 0xABC)
                    uc.mem_write(COLLIDER + 0x1EC, bytes([config.get("flags", 0) ^ 2]))
                    w32(COLLIDER + 0x20, 7)
                if config.get("flip_velocity") and queries == 0:
                    wf(VELOCITY, tuple(-value for value in vf(VELOCITY)))
                queries += 1
            for register in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R12):
                machine.reg_write(register, 0xAB000000 + register + len(trace))
            for register in range(UC_ARM_REG_S0, UC_ARM_REG_S15 + 1):
                machine.reg_write(register, 0x3F000000 + register)
            if result is not None:
                machine.reg_write(UC_ARM_REG_R0, result)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE, callback)
        uc.reg_write(UC_ARM_REG_R0, COLLIDER)
        uc.reg_write(UC_ARM_REG_R1, VELOCITY)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, RETURN)
        for register in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            uc.reg_write(register, 0xC0000000 + register)
        for register in range(UC_ARM_REG_D8, UC_ARM_REG_D15 + 1):
            uc.reg_write(register, 0x3FF0000000000000 + register)
        uc.emu_start(0x800000 if rebuilt else 0x1EAF34, RETURN, count=200000)
        self.assertEqual(uc.reg_read(UC_ARM_REG_PC), RETURN, config)
        self.assertEqual(uc.reg_read(UC_ARM_REG_SP), STACK)
        for register in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            self.assertEqual(uc.reg_read(register), 0xC0000000 + register)
        for register in range(UC_ARM_REG_D8, UC_ARM_REG_D15 + 1):
            self.assertEqual(uc.reg_read(register), 0x3FF0000000000000 + register)
        returned = tuple(uc.reg_read(r) for r in (UC_ARM_REG_S0, UC_ARM_REG_S1, UC_ARM_REG_S2))
        return returned, trace, bytes(uc.mem_read(0x900000, 0xE000))

    def compare(self, config):
        original = self.execute(config, False)
        self.assertEqual(original, self.execute(config, True), config)
        type(self).comparisons += 1
        type(self).comparisons_by_function["resolve"] += 1
        return original

    def test_no_contact_platform_preprocessing_and_saturation(self):
        for flags in (0, 1, 2, 3):
            for capacity in (0, 4):
                for frames in (0, 0xFFFFFFFE, 0xFFFFFFFF):
                    for platform in ((0, 0, 0), (0.5, 1, -0.25), (0, -0.5, 0)):
                        self.compare(dict(flags=flags, capacity=capacity, frames=frames,
                                          old_ground=1, platform=platform))
        self.compare(dict(previous=(2, -2, 5), previous_radius=1.5, hits=(0, 1)))
        self.compare(dict(radius=100, previous_radius=80, velocity=(1, 2, 3)))
        self.compare(dict(radius=2, previous_radius=80, velocity=(0, 0, 0)))
        self.compare(dict(flags=1, old_ground=1, platform=(1, 2, 3), platform_disabled=True))

    def test_contacts_sliding_terminal_response_and_mutations(self):
        for hits in ((0,), (1,), (0, 1), (1, 2), (2, 3)):
            for ground in (-1, 0, 0.5):
                for correction in ((-0.25, 0, 0), (0, 0, 0), (0, 0.125, 0)):
                    for variant in (0, 2):
                        self.compare(dict(hits=hits, ground=ground, correction=correction, flags=variant))
        for contacts in (0, 1, 4):
            self.compare(dict(hits=(0, 1), contacts=contacts, mutate_query=True))
        self.compare(dict(hits=(0,), flip_velocity=True))
        self.compare(dict(all_hits=True, velocity=(3, 0, 0)))

    def test_random_finite_vectors_and_filter_snapshots(self):
        rng = random.Random(0x1EAF34)
        for _ in range(80):
            velocity = tuple(rng.randrange(-32, 32) / 8 for _ in range(3))
            center = tuple(rng.randrange(-64, 64) / 8 for _ in range(3))
            self.compare(dict(velocity=velocity, center=center, radius=rng.choice((0.5, 2, 4)),
                              hits=rng.choice(((), (0,), (1,), (0, 1), (2, 3))),
                              flags=rng.randrange(4), mutate_query=bool(rng.getrandbits(1)),
                              ground=rng.choice((-1, 0)), correction=(0, 0, 0)))

    def test_sweep_helpers_radius_degeneracy_progress_and_aliases(self):
        original_entries = {"FUN_0025c824": 0x25C824, "FUN_0025c790": 0x25C790,
                            "FUN_0025c7f8": 0x25C7F8, "FUN_001da3ac": 0x1DA3AC}
        def run(symbol, path_values, start, end, scalar_args, alias, rebuilt):
            uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            uc.mem_map(0x100000, 0x400000)
            uc.mem_write(0x100000, self.stock)
            uc.mem_map(0x700000, 0x1000)
            uc.mem_map(0x800000, 0x10000)
            uc.mem_map(0x900000, 0x10000)
            for address, data in self.segments:
                uc.mem_write(address, data)
            uc.reg_write(UC_ARM_REG_C1_C0_2, 0xF << 20)
            uc.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
            uc.mem_write(COLLIDER, struct.pack("<11f", *path_values))
            uc.mem_write(TRANS, struct.pack("<3f", *start))
            uc.mem_write(VELOCITY, struct.pack("<3f", *end))
            center = COLLIDER if alias else TRANS
            remaining = COLLIDER + 12 if alias else VELOCITY
            args = [COLLIDER]
            if symbol == "FUN_0025c824":
                args += [TRANS, VELOCITY]
            elif symbol == "FUN_0025c790":
                args += [center, TRANS + 0x40, remaining]
            elif symbol == "FUN_001da3ac":
                args += [center]
            for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
                uc.reg_write(register, value)
            for register, value in zip((UC_ARM_REG_S0, UC_ARM_REG_S1, UC_ARM_REG_S2), scalar_args):
                uc.reg_write(register, struct.unpack("<I", struct.pack("<f", value))[0])
            uc.reg_write(UC_ARM_REG_SP, STACK)
            uc.reg_write(UC_ARM_REG_LR, RETURN)
            for register in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
                uc.reg_write(register, 0xC0000000 + register)
            for register in range(UC_ARM_REG_D8, UC_ARM_REG_D15 + 1):
                uc.reg_write(register, 0x3FF0000000000000 + register)
            uc.emu_start((ENTRIES if rebuilt else original_entries)[symbol], RETURN, count=20000)
            self.assertEqual(uc.reg_read(UC_ARM_REG_PC), RETURN)
            self.assertEqual(uc.reg_read(UC_ARM_REG_SP), STACK)
            for register in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
                self.assertEqual(uc.reg_read(register), 0xC0000000 + register)
            for register in range(UC_ARM_REG_D8, UC_ARM_REG_D15 + 1):
                self.assertEqual(uc.reg_read(register), 0x3FF0000000000000 + register)
            return bytes(uc.mem_read(0x900000, 0x4000))

        cases = []
        base_path = (1, 2, 3, 4, -2, 1, 2, 3, 0.25, 0, 0)
        for start_radius in (-1, 0, 2):
            for end_radius in (-1, 0, 2):
                for end in ((1, 2, 3), (1.25, 2, 3), (8, -2, 4)):
                    for distance in (0, 1, 35):
                        cases.append(("FUN_0025c824", base_path, (1, 2, 3), end,
                                      (start_radius, end_radius, distance), False))
        for t in (-0.5, 0, 0.5, 1, 1.5):
            for step in (-0.5, 0, 0.125, 0.75, 2):
                path = list(base_path); path[8:10] = [step, t]
                cases.append(("FUN_0025c7f8", path, (1, 2, 3), (4, 5, 6), (), False))
        for t in (-0.25, 0, 0.25, 1, 1.25):
            for alias in (False, True):
                path = list(base_path); path[9] = t
                for symbol in ("FUN_0025c790", "FUN_001da3ac"):
                    cases.append((symbol, path, (1, 2, 3), (4, 5, 6), (), alias))
        for case in cases:
            self.assertEqual(run(*case, False), run(*case, True), case)
            type(self).comparisons += 1
            label = {"FUN_0025c824": "path_init", "FUN_0025c7f8": "path_advance",
                     "FUN_0025c790": "path_sample", "FUN_001da3ac": "path_position"}[case[0]]
            type(self).comparisons_by_function[label] += 1
