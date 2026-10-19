"""Limited A32 single-instruction leaf inlining from compiled objects only.

Implements the documented armlink --inline case: replace BL with the sole
non-return instruction of a 4/8-byte leaf. No stock binary is read here.
Only scalar loads, stores and integer operations without PC/LR/SP are accepted.
This is a GNU-link build aid, not a claim of using the original armlink binary.
"""

import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from capstone.arm import ARM_REG_PC, ARM_REG_LR, ARM_REG_SP
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

SAFE = {"mov", "mvn", "add", "sub", "and", "orr", "eor", "bic",
        "ldr", "ldrb", "ldrh", "ldrsb", "ldrsh", "str", "strb", "strh"}
RETURNS = {0xE12FFF1E, 0xE1A0F00E}  # BX lr / MOV pc, lr
NOP = 0xE320F000
EMPTY_CALL_NOP = 0xE1A00000  # Legacy A32 MOV r0,r0, armlink's empty-call form.


def leaf_instruction(body):
    if len(body) not in (4, 8) or struct.unpack("<I", body[-4:])[0] not in RETURNS:
        return None
    if len(body) == 4:
        return NOP
    decoder = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    decoder.detail = True
    instructions = list(decoder.disasm(body[:4], 0))
    if len(instructions) != 1:
        return None
    ins = instructions[0]
    # Instruction ID retains the base name independently of condition suffixes.
    if decoder.insn_name(ins.id) not in SAFE:
        return None
    read, write = ins.regs_access()
    if {ARM_REG_PC, ARM_REG_LR, ARM_REG_SP}.intersection(read + write):
        return None
    word = struct.unpack("<I", body[:4])[0]
    return word if word >> 28 != 15 else None


def conditional_inline(branch, instruction):
    # BL only: a tail B still needs its callee's return sequence.
    if branch & 0x0F000000 != 0x0B000000 or branch >> 28 == 15:
        return None
    if instruction == NOP:
        # An unconditional return-only body has no register/flag effects under
        # any call condition. The branch may therefore become an unconditional
        # legacy NOP. The helper body is still derived from compiled source.
        return EMPTY_CALL_NOP
    call_cond, leaf_cond = branch >> 28, instruction >> 28
    if call_cond != 14 and leaf_cond not in (14, call_cond):
        return None
    condition = leaf_cond if call_cond == 14 else call_cond
    return (instruction & 0x0FFFFFFF) | (condition << 28)


def collect_helpers(root, records):
    helpers, conflicts = {}, set()
    for record in records:
        if record.get("returncode") or not record.get("source_unchanged"):
            continue
        path = root / record["object"]
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            if elf["e_machine"] != "EM_ARM" or not elf.little_endian or elf.elfclass != 32:
                continue
            symbols = list(elf.get_section_by_name(".symtab").iter_symbols())
            relocs = [r for r in elf.iter_sections() if isinstance(r, RelocationSection)]
            for symbol in symbols:
                section_index = symbol["st_shndx"]
                if (symbol["st_info"]["type"] != "STT_FUNC" or symbol["st_info"]["bind"] == "STB_LOCAL"
                        or not isinstance(section_index, int) or symbol["st_size"] not in (4, 8)
                        or symbol["st_value"] % 4):
                    continue
                start, end = symbol["st_value"], symbol["st_value"] + symbol["st_size"]
                mapping = [s for s in symbols if s["st_shndx"] == section_index
                           and s.name.startswith(("$a", "$t", "$d")) and s["st_value"] <= start]
                if not mapping or not max(mapping, key=lambda s: s["st_value"]).name.startswith("$a"):
                    continue
                if any(r["r_info_type"] != 40 for rs in relocs if rs["sh_info"] == section_index
                       for r in rs.iter_relocations() if start <= r["r_offset"] < end):
                    continue
                section = elf.get_section(section_index)
                if not section["sh_flags"] & 4 or "stub" in section.name.lower():
                    continue
                instruction = leaf_instruction(section.data()[start:end])
                if instruction is None:
                    continue
                name = symbol.name
                candidate = {"instruction": instruction, "source": record["source"],
                             "source_sha256": record["source_sha256"],
                             "object": record["object"], "object_sha256": record["object_sha256"]}
                if name in helpers and helpers[name]["instruction"] != instruction:
                    conflicts.add(name)
                else:
                    helpers[name] = candidate
    return {name: value for name, value in helpers.items() if name not in conflicts}


def inline_object(source, destination, helpers):
    buffer = bytearray(source.read_bytes())
    changes = []
    with source.open("rb") as stream:
        elf = ELFFile(stream)
        if elf["e_machine"] != "EM_ARM" or not elf.little_endian or elf.elfclass != 32:
            raise ValueError("only little-endian ELF32 ARM inputs are supported")
        for relocations in elf.iter_sections():
            if not isinstance(relocations, RelocationSection):
                continue
            if relocations["sh_type"] != "SHT_REL":
                raise ValueError("explicit-addend relocations are unsupported")
            section = elf.get_section(relocations["sh_info"])
            symbols = elf.get_section(relocations["sh_link"])
            if not section["sh_flags"] & 4:
                continue
            for index, relocation in enumerate(relocations.iter_relocations()):
                # ARMCC also uses JUMP24 for conditional BL instructions. The
                # instruction check below still rejects actual tail B/BLX.
                if relocation["r_info_type"] not in (1, 28, 29):
                    continue
                symbol = symbols.get_symbol(relocation["r_info_sym"])
                if symbol["st_info"]["bind"] == "STB_LOCAL":
                    continue
                helper = helpers.get(symbol.name)
                if not helper:
                    continue
                at = section["sh_offset"] + relocation["r_offset"]
                if relocation["r_offset"] % 4 or relocation["r_offset"] + 4 > section["sh_size"]:
                    raise ValueError("unaligned or out-of-range call relocation")
                before = struct.unpack_from("<I", buffer, at)[0]
                # A BL relocation encodes -8 for a call to the symbol itself.
                # Reject interior-function/addend calls rather than inlining them.
                if before & 0xFFFFFF != 0xFFFFFE:
                    continue
                after = conditional_inline(before, helper["instruction"])
                if after is None:
                    continue
                struct.pack_into("<I", buffer, at, after)
                info = relocations["sh_offset"] + index * relocations["sh_entsize"] + 4
                struct.pack_into("<I", buffer, info, 0)  # R_ARM_NONE
                changes.append({"section": section.name, "offset": relocation["r_offset"],
                                "symbol": symbol.name, "before": before, "after": after,
                                "helper": helper})
    destination.write_bytes(buffer)
    return changes
