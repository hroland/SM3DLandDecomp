"""Original-vs-source contact copying, selection, query, director and math checks.

The global LiveActorKit accessor and the director's virtual query engine are
the only intercepted boundaries; query wrappers, the director query, the
accessors, normalization, projection and platform motion run as original code
or rebuilt source on each side.
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
from collision_behavior import (prepare, ENTRIES, COLLECT, FINALIZE, COUNT, RESULT, SWEEP, RESPONSE,
                                QUERY_SPHERE, DEFAULT_BUFFER, PARTS_DELTA)
from verify_elf import EU_SHA256

ROOT = Path(__file__).resolve().parents[2]
COLLIDER, CONTACTS, RECORDS = 0x900100, 0x904000, 0x906000
GRAVITY, KIT, DIRECTOR, QUERY, POINTERS = 0x903000, 0x908000, 0x909000, 0x909100, 0x909200
PATH, OUTPUT, NORMAL, RADIUS, PARTS = 0x903100, 0x903200, 0x903240, 0x903260, 0x90A000
VECTOR, SECOND, DELTA, BUFFER = 0x903300, 0x903310, 0x903320, 0x903330
ENGINE, ENGINE_VTABLE, ENGINE_QUERY = 0x909300, 0x909400, 0x700100
STACK, RETURN = 0x90FFF0, 0x700FF0
ORIGINAL = {COLLECT: 0x23EDA8, FINALIZE: 0x1EAA44, COUNT: 0x3342AC, RESULT: 0x1D43DC,
            "FUN_00334298": 0x334298, "FUN_001d43c0": 0x1D43C0,
            "FUN_00262dd4": 0x262DD4, "FUN_0023fa8c": 0x23FA8C,
            "FUN_0023fb04": 0x23FB04, "FUN_0026f71c": 0x26F71C}
ORIGINAL.update({SWEEP: 0x1EA8A0, RESPONSE: 0x23E928, "FUN_0025c780": 0x25C780,
                 "FUN_0033745c": 0x33745C, "FUN_0026ffc8": 0x26FFC8, "FUN_0033162c": 0x33162C})
ORIGINAL.update({"FUN_001676e0": 0x1676E0, "FUN_002673b0": 0x2673B0, "FUN_0025c9f8": 0x25C9F8,
                 QUERY_SPHERE: 0x25CA4C, DEFAULT_BUFFER: 0x1D44CC,
                 "FUN_0027d5c4": 0x27D5C4, "FUN_0027ccbc": 0x27CCBC, "FUN_0027306c": 0x27306C,
                 "FUN_00331f18": 0x331F18, PARTS_DELTA: 0x331F20})
QUERY_ENTRIES = ("FUN_002673b0", "FUN_0025c9f8", QUERY_SPHERE)
MATH_ENTRIES = ("FUN_0027d5c4", "FUN_0027ccbc", "FUN_0027306c")
MOTION_ENTRIES = ("FUN_00331f18", PARTS_DELTA)
RETURNS_NOTHING = (FINALIZE, RESPONSE, "FUN_0026ffc8", "FUN_0033162c", DEFAULT_BUFFER,
                   "FUN_0027306c", "FUN_00331f18", PARTS_DELTA)


def packf(*values):
    return struct.pack("<" + "f" * len(values), *values)


def bitsf(value):
    return struct.unpack("<I", packf(value))[0]


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


class CollisionContactsARMTest(unittest.TestCase):
    comparisons = 0
    comparisons_by_function = {"collect": 0, "finalize": 0, "query": 0, "classification": 0,
                               "sweep": 0, "response": 0, "response_helpers": 0,
                               "director_query": 0, "accessors": 0, "normalization": 0,
                               "platform_motion": 0}

    @classmethod
    def setUpClass(cls):
        cls.stock = (ROOT / "code.bin").read_bytes()
        if hashlib.sha256(cls.stock).hexdigest() != EU_SHA256:
            raise RuntimeError("wrong EU executable")
        cls.artifact = prepare()
        with cls.artifact.open("rb") as stream:
            elf = ELFFile(stream)
            cls.segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]

    def execute(self, symbol, config, rebuilt):
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
        # Different source/destination padding catches erroneous 0x88-byte memcpy.
        uc.mem_write(0x900000, bytes((i * 13 + 91) & 255 for i in range(0xB000)))
        def w32(a, value): uc.mem_write(a, struct.pack("<I", value & 0xFFFFFFFF))
        def r32(a): return struct.unpack("<I", uc.mem_read(a, 4))[0]
        w32(COLLIDER + 0x10, GRAVITY)
        w32(COLLIDER, 0x123)
        w32(COLLIDER + 4, 0x456)
        w32(COLLIDER + 0x24, config.get("count", 0))
        uc.mem_write(COLLIDER + 0x1EC, bytes([config.get("flags", 0)]))
        w32(PARTS + 0x134, config.get("disabled", 0))
        path = config.get("path", (1, 2, 3, 2, 0, 0, 1, 2, 0.25, 0, 0))
        uc.mem_write(PATH, packf(*path))
        uc.mem_write(GRAVITY, packf(*config.get("gravity", (0, -1, 0))))
        w32(KIT + 0x28, DIRECTOR)
        w32(DIRECTOR + 0x14, QUERY)
        w32(DIRECTOR + 0x18, CONTACTS)
        w32(QUERY, config.get("total", 0))
        w32(QUERY + 8, POINTERS)
        install_engine(uc, w32)
        for offset, value in zip((8, 0xC), config.get("filters", ())):
            w32(DIRECTOR + offset, value)
        identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]
        moved = identity.copy()
        for index, value in zip((3, 7, 11), config.get("platform", (0, 0, 0))):
            moved[index] = value
        uc.mem_write(PARTS + 0x44, packf(*moved))
        uc.mem_write(PARTS + 0xD4, packf(*config.get("previous_inverse", identity)))
        uc.mem_write(VECTOR, packf(*config.get("vector", (1, 2, 3))))
        uc.mem_write(SECOND, packf(*config.get("second", (0, 1, 0))))
        uc.mem_write(DELTA, packf(*config.get("delta", (7, 8, 9))))
        normals = config.get("normals", [(0, 1, 0), (1, 0, 0), (0, -1, 0)])
        distances = config.get("distances", [0, 1, 2, 3])
        for i in range(16):
            record = RECORDS + i * 0x88
            for base in (record, CONTACTS + i * 0x88):
                w32(base, PARTS)
                uc.mem_write(base + 8, packf(*normals[i % len(normals)]))
                uc.mem_write(base + 0x5C, packf(distances[i % len(distances)]))
                uc.mem_write(base + 0x60, packf(0, 0, 0))
                uc.mem_write(base + 0x6C, packf(*config.get("direction", (1, 1, 0))))
                uc.mem_write(base + 0x78, packf(*config.get("carry", (0, 0, 0))))
                flags = config.get("contact_flags", [1])
                uc.mem_write(base + 0x84, bytes([flags[i % len(flags)]]))
            w32(POINTERS + i * 4, CONTACTS + i * 0x88 if config.get("self_copy") else record)
        for offset, value in zip((0xC0, 0x14C, 0x1D8), config.get("previous", [-99999] * 3)):
            uc.mem_write(COLLIDER + offset, packf(value))
        if config.get("source_alias"):
            # One contact is itself the selected ground member.
            uc.mem_write(COLLIDER + 0x40, packf(0, 1, 0))
            uc.mem_write(COLLIDER + 0x94, packf(3.0))
        trace = []
        kit_calls = 0
        queries = 0
        def hook(machine, address, _, __):
            nonlocal kit_calls, queries
            if address not in (0x277250, ENGINE_QUERY):
                return
            if address == 0x277250:
                trace.append(("kit",))
                if kit_calls in config.get("mutate_count_at", {}):
                    w32(COLLIDER + 0x24, config["mutate_count_at"][kit_calls])
                if kit_calls == 1 and config.get("mutate_total"):
                    w32(QUERY, config["mutate_total"])
                kit_calls += 1
                result = KIT
            else:
                # engine->querySphere(results, info, variant): record the whole ABI
                # plus the director state the query must have prepared.
                engine, results, info, variant = (machine.reg_read(r) for r in
                                                  (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
                trace.append(("engine", engine, results, variant, bytes(machine.mem_read(r32(info), 12)),
                              r32(info + 4), r32(info + 8), r32(info + 12),
                              r32(DIRECTOR + 8), r32(DIRECTOR + 0xC), r32(QUERY), r32(QUERY + 0xC)))
                result = int(queries in config.get("hits", ()))
                count = config.get("total", 1) if result else 0
                w32(QUERY, count)
                for i in range(min(count, 16)):
                    w32(r32(POINTERS + i * 4), PARTS)
                if config.get("mutate_query") and queries == 0:
                    w32(COLLIDER, 0x789)
                    w32(COLLIDER + 4, 0xABC)
                    uc.mem_write(COLLIDER + 0x1EC, bytes([config.get("flags", 0) ^ 2]))
                queries += 1
            for register in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R12):
                machine.reg_write(register, 0xAB000000 + register)
            for register in range(UC_ARM_REG_S0, UC_ARM_REG_S15 + 1):
                machine.reg_write(register, 0x3F000000 + register)
            machine.reg_write(UC_ARM_REG_R0, result)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
        uc.hook_add(UC_HOOK_CODE, hook)
        args = {
            COLLECT: [COLLIDER, CONTACTS, config.get("capacity", 8)],
            FINALIZE: [COLLIDER, COLLIDER + 0x38 if config.get("source_alias") else CONTACTS],
            COUNT: [DIRECTOR], RESULT: [DIRECTOR, config.get("index", 0)],
            "FUN_00334298": [], "FUN_001d43c0": [config.get("index", 0)],
            "FUN_00262dd4": [CONTACTS, config.get("index", 0)],
            "FUN_0023fa8c": [CONTACTS + 8, GRAVITY], "FUN_0023fb04": [CONTACTS + 8, GRAVITY],
            "FUN_0026f71c": [CONTACTS + 8],
            SWEEP: [COLLIDER, PATH, OUTPUT, RADIUS],
            RESPONSE: [COLLIDER, CONTACTS, OUTPUT, NORMAL if config.get("with_normal", True) else 0],
            "FUN_0025c780": [CONTACTS], "FUN_0033745c": [CONTACTS],
            "FUN_0026ffc8": [CONTACTS, OUTPUT, NORMAL if config.get("with_normal", True) else 0],
            "FUN_0033162c": [CONTACTS, OUTPUT, NORMAL if config.get("with_normal", True) else 0],
            "FUN_001676e0": [],
            "FUN_002673b0": [VECTOR, config.get("filter_a", 0x11), config.get("filter_b", 0x22)],
            "FUN_0025c9f8": [VECTOR, config.get("filter_a", 0x11), config.get("filter_b", 0x22)],
            QUERY_SPHERE: [DIRECTOR, VECTOR, config.get("variant", 0)],
            DEFAULT_BUFFER: [DIRECTOR, BUFFER, BUFFER + 4],
            "FUN_0027d5c4": [VECTOR], "FUN_0027ccbc": [VECTOR],
            "FUN_0027306c": [DELTA, SECOND, VECTOR],
            "FUN_00331f18": [CONTACTS, DELTA, VECTOR], PARTS_DELTA: [PARTS, DELTA, VECTOR],
        }[symbol]
        if symbol in ("FUN_0026ffc8", "FUN_0033162c"):
            if config.get("alias_correction"):
                args[1] = CONTACTS + 8
            if config.get("alias_normal"):
                args[2] = CONTACTS + 8
        for index, alias in enumerate(config.get("alias_args", ())):
            if alias is not None:
                args[index] = args[alias]
        for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
            uc.reg_write(register, value)
        uc.reg_write(UC_ARM_REG_S0, bitsf(config.get("radius", config.get("epsilon", 0.001))))
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, RETURN)
        if symbol == SWEEP:
            w32(STACK, CONTACTS)
            w32(STACK + 4, config.get("capacity", 8))
        elif symbol == RESPONSE:
            w32(STACK, int(config.get("first", False)))
            w32(STACK + 4, config.get("start", 0))
        for register in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            uc.reg_write(register, 0xC0000000 + register)
        for register in range(UC_ARM_REG_D8, UC_ARM_REG_D15 + 1):
            uc.reg_write(register, 0x3FF0000000000000 + register)
        uc.emu_start((ENTRIES if rebuilt else ORIGINAL)[symbol], RETURN, count=50000)
        self.assertEqual(uc.reg_read(UC_ARM_REG_PC), RETURN, (symbol, config))
        self.assertEqual(uc.reg_read(UC_ARM_REG_SP), STACK)
        for register in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1):
            self.assertEqual(uc.reg_read(register), 0xC0000000 + register)
        for register in range(UC_ARM_REG_D8, UC_ARM_REG_D15 + 1):
            self.assertEqual(uc.reg_read(register), 0x3FF0000000000000 + register)
        returned = None if symbol in RETURNS_NOTHING else uc.reg_read(UC_ARM_REG_R0)
        if symbol == "FUN_0027ccbc":
            returned = uc.reg_read(UC_ARM_REG_S0)
        return returned, trace, bytes(uc.mem_read(0x900000, 0xB000))

    def compare(self, symbol, config):
        original = self.execute(symbol, config, False)
        self.assertEqual(original, self.execute(symbol, config, True), (symbol, config))
        label = "sweep" if symbol == SWEEP else "response" if symbol == RESPONSE else (
            "response_helpers" if symbol in ("FUN_0025c780", "FUN_0033745c", "FUN_0026ffc8", "FUN_0033162c") else (
            "collect" if symbol == COLLECT else "finalize" if symbol == FINALIZE else (
            "classification" if symbol in ("FUN_0023fa8c", "FUN_0023fb04", "FUN_0026f71c") else (
            "director_query" if symbol in QUERY_ENTRIES else (
            "accessors" if symbol in ("FUN_001676e0", DEFAULT_BUFFER) else (
            "normalization" if symbol in MATH_ENTRIES else (
            "platform_motion" if symbol in MOTION_ENTRIES else "query")))))))
        type(self).comparisons += 1
        type(self).comparisons_by_function[label] += 1
        return original

    def test_collection_capacity_snapshot_reload_and_padding(self):
        for count in (0, 1, 4, 9):
            for capacity in (0, 1, 4, 8):
                for total in (0, 1, 4, 8):
                    for self_copy in (False, True):
                        self.compare(COLLECT, dict(count=count, capacity=capacity, total=total, self_copy=self_copy))
        for count in (0, 2, 4):
            for mutation in (0, 1, 3):
                self.compare(COLLECT, dict(count=count, total=3, capacity=8, mutate_count_at={1: mutation}))
        self.compare(COLLECT, dict(total=3, capacity=8, mutate_total=12))
        # Clamp returns signed-width subtraction, including unsigned underflow.
        self.compare(COLLECT, dict(count=0xFFFFFFFF, capacity=1, total=1))

    def test_finalization_classification_ties_distance_and_alias(self):
        for count in (0, 1, 3, 8, 12):
            for previous in ((-99999,) * 3, (0, 0, 0), (1, 2, 3), (99,) * 3):
                for distances in ((-1, 0, 1, 2), (1,) * 4, (3, 2, 1, 0)):
                    self.compare(FINALIZE, dict(count=count, previous=previous, distances=distances))
        self.compare(FINALIZE, dict(count=1, source_alias=True))
        self.compare(FINALIZE, dict(count=4, normals=[(0, 0, 0)], distances=[1, 2, 3, 4]))
        rng = random.Random(0x1EAA44)
        for _ in range(50):
            self.compare(FINALIZE, dict(count=rng.randrange(1, 12),
                normals=[tuple(rng.randrange(-16, 17) / 16 for _ in range(3)) for _ in range(4)],
                distances=[rng.randrange(-16, 17) / 8 for _ in range(4)]))

    def test_query_shared_tails_and_normal_index(self):
        for total in (0, 1, 16, 0xFFFFFFFF):
            for symbol in (COUNT, "FUN_00334298"):
                self.compare(symbol, dict(total=total))
        for index in range(16):
            for symbol in (RESULT, "FUN_001d43c0"):
                self.compare(symbol, dict(index=index))
        for index in range(4):
            self.compare("FUN_00262dd4", dict(index=index))

    def test_classification_threshold_and_near_zero(self):
        threshold = struct.unpack("<f", struct.pack("<I", 0x3EAF1D44))[0]
        values = [0, 0.0005, 0.001, 0.002, -0.0005, -0.001, -0.002, -1, 1]
        for bits in (0x3EAF1D43, 0x3EAF1D44, 0x3EAF1D45):
            value = struct.unpack("<f", struct.pack("<I", bits))[0]
            values += [value, -value]
        for value in values:
            for symbol in ("FUN_0023fa8c", "FUN_0023fb04", "FUN_0026f71c"):
                for normal in ((1, value, 0), (0, value, 0)):
                    self.compare(symbol, dict(normals=[normal]))

    def test_response_extrema_surface_policy_and_carry(self):
        for count in (0, 1, 4, 8):
            for start in (0, 2, 8):
                for with_normal in (False, True):
                    for first in (False, True):
                        for flags in (0, 2, 0x3B):
                            for contact_flags in ([1], [0], [0, 1, 2]):
                                self.compare(RESPONSE, dict(count=count, start=start,
                                    with_normal=with_normal, first=first, flags=flags,
                                    contact_flags=contact_flags, distances=[-0.5, 1, -2, 0.25],
                                    normals=[(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)],
                                    carry=(0.25, -0.5, 1)))
        for carry in ((0, 0, 0), (-1, -1, 0), (1, 1, 0)):
            for disabled in (0, 1, 0xFFFFFFFF):
                self.compare(RESPONSE, dict(count=4, flags=2, carry=carry, disabled=disabled))

    def test_shape_sweep_query_mutation_capacity_and_completion(self):
        for t, previous in ((0, 0), (0.5, 0.25), (1, 0.75), (1, 1)):
            for step in (0.25, 1, 2):
                for flags in (0, 2):
                    for hits in ((), (0,), (1,), (0, 1, 2)):
                        self.compare(SWEEP, dict(path=(1, 2, 3, 2, -1, 0, 1, 2, step, t, previous),
                            flags=flags, hits=hits, total=3, count=0, capacity=4,
                            mutate_query=True, carry=(0.25, 0.5, 0), contact_flags=[0, 1, 2]))
        for capacity in (0, 1, 4):
            self.compare(SWEEP, dict(hits=(0, 1), capacity=capacity, total=4))

    def test_response_helper_flags_projection_and_null_normal(self):
        for flag in (0, 1, 2, 127, 255):
            self.compare("FUN_0025c780", dict(contact_flags=[flag]))
            for disabled in (0, 1, 0xFFFFFFFF):
                self.compare("FUN_0033745c", dict(contact_flags=[flag], disabled=disabled))
            for normal in ((1, 0, 0), (0, 1, 0), (0, 0, 0), (-1, 2, -3)):
                for direction in ((1, 1, 0), (0, 0, 0), (-2, 1, 3)):
                    self.compare("FUN_0033162c", dict(contact_flags=[flag], normals=[normal], direction=direction))
            for with_normal in (False, True):
                self.compare("FUN_0026ffc8", dict(contact_flags=[flag], with_normal=with_normal, distances=[2]))
        for flag in (0, 1):
            for symbol in ("FUN_0026ffc8", "FUN_0033162c"):
                for alias in ("alias_correction", "alias_normal"):
                    self.compare(symbol, dict(contact_flags=[flag], normals=[(1, -2, 3)],
                        distances=[2], direction=(1, 1, 1), **{alias: True}))

    def test_query_wrappers_director_query_and_global_accessors(self):
        # Wrappers hand filters through the director and the radius through the
        # query info; the director recycles previous results with a signed count,
        # calls the engine once and clears both filters afterwards.
        for symbol in ("FUN_002673b0", "FUN_0025c9f8"):
            for hits in ((), (0,)):
                for total in (0, 1, 3, 16, 0x80000000, 0xFFFFFFFF):
                    for radius in (0.0, 1.5, -2.25):
                        self.compare(symbol, dict(hits=hits, total=total, radius=radius, vector=(1.5, -2, 3),
                                                  filter_a=0x11 + len(hits), filter_b=0xABCD))
            self.compare(symbol, dict(hits=(0,), total=4, self_copy=True, filter_a=0, filter_b=0))
        for variant in (0, 1, 2, 0xFFFFFFFF):
            for filters in ((), (0, 0), (0x55, 0xAA)):
                for total in (0, 2, 16, 0xFFFFFFFF):
                    for hits in ((), (0,)):
                        self.compare(QUERY_SPHERE, dict(variant=variant, filters=filters, total=total,
                                                        hits=hits, radius=0.75, vector=(-1, 0.5, 2)))
        self.compare("FUN_001676e0", {})
        self.compare(DEFAULT_BUFFER, {})
        self.compare(DEFAULT_BUFFER, dict(alias_args=(None, None, 1)))

    def test_normalization_threshold_zeroing_projection_and_aliases(self):
        bits = bitsf(0.001)
        vectors = [(0, 0, 0), (0.0005, 0, 0), (0, 0.0007, 0.0007), (0.001, 0, 0), (3, 4, 0), (1, 2, 2),
                   (-5, 0, 0), (-1, -1, -1), (1e-20, 0, 0), (1e20, 0, 0), (0.25, -0.5, 0.125)]
        for near in (bits - 1, bits, bits + 1):
            value = struct.unpack("<f", struct.pack("<I", near))[0]
            vectors += [(value, 0, 0), (0, -value, 0), (0, 0, value)]
        for vector in vectors:
            for symbol in ("FUN_0027d5c4", "FUN_0027ccbc"):
                self.compare(symbol, dict(vector=vector))
        for normal in ((0, 1, 0), (1, 0, 0), (0, 0, 0), (1, 1, 1), (0.6, 0.8, 0), (-1, 2, -3)):
            for vector in ((1, 2, 3), (0, 0, 0), (-4, 0.5, 2)):
                self.compare("FUN_0027306c", dict(second=normal, vector=vector))
        for alias_args in ((None, 0, None), (None, None, 0), (None, 0, 0), (None, None, 1)):
            self.compare("FUN_0027306c", dict(second=(0.6, 0.8, 0), vector=(1, 2, 3), alias_args=alias_args))

    def test_platform_motion_matrices_and_aliases(self):
        identity = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)
        scaled = (2, 0, 0, 1, 0, 0.5, 0, -1, 0, 0, -1, 0.25)
        rotated = (0, -1, 0, 3, 1, 0, 0, -2, 0, 0, 1, 1)
        for platform in ((0, 0, 0), (0.5, 1, -0.25), (-3, 2, 1)):
            for previous_inverse in (identity, scaled, rotated):
                for vector in ((1, 2, 3), (0, 0, 0), (-1.5, 0.25, 4)):
                    for symbol in MOTION_ENTRIES:
                        self.compare(symbol, dict(platform=platform, previous_inverse=previous_inverse,
                                                  vector=vector))
        for symbol in MOTION_ENTRIES:
            self.compare(symbol, dict(platform=(1, 2, 3), previous_inverse=scaled, alias_args=(None, None, 1)))
