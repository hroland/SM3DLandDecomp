"""Compare original and actual ARMCC actor control flow with intercepted callbacks."""

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
from actor_behavior import prepare, MOVEMENT, COLLIDER

ROOT = Path(__file__).resolve().parents[2]
ACTOR, POSE, EXECUTE = 0x900100, 0x901000, 0x901100
TRANS, VELOCITY, SCALE = 0x904000, 0x904020, 0x904040
RETURN, CONTROL, UPDATE, BASE, GET_SCALE = 0x700FF0, 0x700000, 0x700004, 0x700008, 0x70000C
FIELDS = {"action": 0x1c, "collider": 0x20, "collision": 0x24, "model": 0x28,
          "nerve": 0x2c, "sensor": 0x30, "effect": 0x34, "audio": 0x38,
          "shadow": 0x44, "light": 0x48, "sub": 0x50}
CALLS = {0x129414: "model_pre", 0x262ba4: "ground", 0x1e78b4: "effect_name",
         0x1bfb98: "effect_material", 0x18b9b8: "audio_name", 0x1bf2e4: "audio_material",
         0x1ccde8: "attack", 0x25065c: "nerve", CONTROL: "control", UPDATE: "collider_virtual",
         0x2553b4: "effect_update", 0x268e80: "audio_update", BASE: "base", GET_SCALE: "scale",
         0x2ddc68: "prescale", 0x1d2d44: "sync", 0x1d2f90: "action_update",
         0x25873c: "sensor_update", 0x128de8: "model_post", 0x1ca998: "light", 0x18bae8: "sub",
         0x272dd8: "velocity", 0x27f3c4: "trans", 0x1eaf34: "resolve", 0x27cb48: "add",
         0x24c9ec: "reset"}


class ActorMovementARMTest(unittest.TestCase):
    comparisons = 0
    comparisons_by_function = {"movement": 0, "updateCollider": 0}

    @classmethod
    def setUpClass(cls):
        cls.stock = (ROOT / "code.bin").read_bytes()
        if hashlib.sha256(cls.stock).hexdigest() != "e1d7e188ff88467df776c17cec45c44857fadf5b699944baa8cddcae7d939e64":
            raise RuntimeError("wrong EU executable")
        cls.artifact = prepare()
        with cls.artifact.open("rb") as stream:
            elf = ELFFile(stream)
            cls.segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
            cls.entries = {name: elf.get_section_by_name(".symtab").get_symbol_by_name(symbol)[0]["st_value"]
                           for name, symbol in (("movement", MOVEMENT), ("updateCollider", COLLIDER))}

    def execute(self, name, config, rebuilt):
        machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        machine.mem_map(0x100000, 0x400000)
        machine.mem_write(0x100000, self.stock)
        machine.mem_map(0x700000, 0x1000)
        machine.mem_map(0x800000, 0x20000)
        machine.mem_map(0x900000, 0x10000)
        for address, data in self.segments:
            machine.mem_write(address, data)
        machine.reg_write(UC_ARM_REG_C1_C0_2, 0xF << 20)
        machine.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        def write32(address, value): machine.mem_write(address, struct.pack("<I", value))
        def read32(address): return struct.unpack("<I", machine.mem_read(address, 4))[0]
        def floats(address, count=3): return struct.unpack("<" + "f" * count, machine.mem_read(address, 4 * count))
        write32(ACTOR, 0x905000)
        write32(ACTOR + 0x14, POSE if config.get("pose", True) else 0)
        write32(ACTOR + 0x18, EXECUTE)
        write32(EXECUTE + 0x18, 0x906000)
        write32(POSE, 0x905100)
        for offset, target in ((0x4c, CONTROL), (0x54, UPDATE)):
            write32(0x905000 + offset, target)
        write32(0x905100 + 0x40, BASE)
        write32(0x905100 + 4, GET_SCALE)
        for index, (field, offset) in enumerate(FIELDS.items()):
            pointer = 0x901200 + index * 0x100 if config.get(field, False) else 0
            write32(ACTOR + offset, pointer)
            if pointer:
                write32(pointer, 0x906100)
                if field == "light": write32(pointer + 8, config.get("mode", 0))
        flags = bytearray(9)
        for offset, key in ((0, "dead"), (1, "clipped"), (3, "draw_clipping"), (6, "off"), (8, "material")):
            flags[offset] = config.get(key, 0)
        machine.mem_write(ACTOR + 0x54, bytes(flags))
        machine.mem_write(TRANS, struct.pack("<3f", *config.get("translation", (1.5, -2.0, 4.0))))
        machine.mem_write(VELOCITY, struct.pack("<3f", *config.get("velocity", (-0.5, 3.0, 2.0))))
        machine.mem_write(SCALE, struct.pack("<3f", 2.0, 3.0, 4.0))
        machine.reg_write(UC_ARM_REG_R0, ACTOR)
        machine.reg_write(UC_ARM_REG_SP, 0x90FFF0)
        machine.reg_write(UC_ARM_REG_LR, RETURN)
        for reg in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1): machine.reg_write(reg, 0xC0000000 + reg)
        trace = []

        def callback(uc, address, _, __):
            label = CALLS.get(address)
            if label is None: return
            args = [uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
            event = [label, args[0]]
            result = None
            if label in ("effect_material", "audio_material", "light"):
                event.append(args[1])
            elif label == "base":
                machine.mem_write(args[1], struct.pack("<12f", *range(1, 13)))
            elif label == "prescale":
                values = list(floats(args[0], 12)); scale = floats(args[1])
                for row in range(3):
                    for column in range(3): values[row * 4 + column] *= scale[column]
                machine.mem_write(args[0], struct.pack("<12f", *values))
                event = [label, floats(args[0], 12)]
            elif label == "sync": event.append(floats(args[1], 12))
            elif label == "add":
                left, right = floats(args[1]), floats(args[2])
                event += [left, right]
                machine.mem_write(args[0], struct.pack("<3f", *(a + b for a, b in zip(left, right))))
            elif label == "resolve": event.append(floats(args[1]))
            elif label == "reset":
                event.append(floats(TRANS))
                write32(args[0] + 0x24, 0)
            if label == "ground": result = config.get("ground", 0)
            elif label == "effect_name": result = 0x906200
            elif label == "audio_name": result = 0x906220
            elif label == "scale": result = SCALE
            elif label == "velocity": result = VELOCITY
            elif label == "trans": result = TRANS
            if config.get("kill_at") == label: machine.mem_write(ACTOR + 0x54, b'\1')
            trace.append(tuple(event))
            for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R12):
                uc.reg_write(reg, 0xAB000000 + reg + len(trace))
            for reg in range(UC_ARM_REG_S0, UC_ARM_REG_S15 + 1): uc.reg_write(reg, 0x3F000000 + reg)
            if result is not None: uc.reg_write(UC_ARM_REG_R0, result)
            if label == "resolve":
                for reg, value in zip((UC_ARM_REG_S0, UC_ARM_REG_S1, UC_ARM_REG_S2), config.get("resolved", (0.25, -1.5, 2.75))):
                    uc.reg_write(reg, struct.unpack("<I", struct.pack("<f", value))[0])
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        machine.hook_add(UC_HOOK_CODE, callback)
        entry = self.entries[name] if rebuilt else {"movement": 0x26DF44, "updateCollider": 0x1EBCEC}[name]
        machine.emu_start(entry, RETURN, count=10000)
        self.assertEqual(machine.reg_read(UC_ARM_REG_PC), RETURN)
        self.assertEqual(machine.reg_read(UC_ARM_REG_SP), 0x90FFF0)
        for reg in range(UC_ARM_REG_R4, UC_ARM_REG_R11 + 1): self.assertEqual(machine.reg_read(reg), 0xC0000000 + reg)
        return trace, bytes(machine.mem_read(0x900000, 0x7000))

    def compare(self, name, config):
        stock = self.execute(name, config, False)
        rebuilt = self.execute(name, config, True)
        self.assertEqual(stock, rebuilt, config)
        type(self).comparisons += 1
        type(self).comparisons_by_function[name] += 1
        return stock[0]

    def test_movement_presence_flags_callback_order_and_death(self):
        all_present = {field: True for field in FIELDS}
        for kill in (None, "attack", "nerve", "control", "model_pre", "effect_material", "audio_material"):
            trace = self.compare("movement", {**all_present, "material": 1, "ground": 1, "kill_at": kill})
            labels = [event[0] for event in trace]
            if kill in ("attack", "nerve", "control"):
                self.assertEqual(labels[-1], kill)
        trace = self.compare("movement", {})
        self.assertEqual([event[0] for event in trace], ["control", "collider_virtual"])
        rng = random.Random(0x26DF44)
        for _ in range(240):
            config = {field: bool(rng.getrandbits(1)) for field in FIELDS}
            config.update({flag: rng.getrandbits(1) for flag in ("dead", "clipped", "draw_clipping", "material", "ground")})
            config.update(mode=rng.randrange(3), kill_at=rng.choice((None, "attack", "nerve", "control")))
            trace = self.compare("movement", config)
            if config["dead"] or (config["clipped"] and not config["draw_clipping"]): self.assertEqual(trace, [])

    def test_update_collider_vfp_result_and_no_collider_paths(self):
        rng = random.Random(0x1EBCEC)
        for pose in (False, True):
            for collider in (False, True):
                for off in (0, 1):
                    for _ in range(12):
                        config = {"pose": pose, "collider": collider, "off": off,
                                  "translation": tuple(rng.randrange(-1000, 1000) / 8.0 for _ in range(3)),
                                  "velocity": tuple(rng.randrange(-1000, 1000) / 8.0 for _ in range(3)),
                                  "resolved": tuple(rng.randrange(-1000, 1000) / 8.0 for _ in range(3))}
                        trace = self.compare("updateCollider", config)
                        labels = [event[0] for event in trace]
                        expected = ([] if not pose else ["velocity", "trans", "resolve", "add"] if collider and not off
                                    else ["velocity", "trans", "add", "reset"] if collider else ["velocity", "trans", "add"])
                        self.assertEqual(labels, expected)


if __name__ == "__main__":
    unittest.main()
