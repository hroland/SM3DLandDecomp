"""Documented armlink branch-to-next-instruction elimination for GNU links.

armlink's default --branchnop option (ARM DUI0803E, "armlink User Guide",
sections 4.7 and 11.12) "replaces any branch with a relocation that resolves to
the next instruction with a NOP". After --tailreorder places a tail-called
section directly behind its caller, the caller's tail B therefore appears in
the image as the legacy A32 NOP, MOV r0,r0. This pass applies that rule to
compiled objects before a GNU link, using the final placements supplied by the
caller. Only an unconditional A32 B carrying the assembler's self-relative
addend is considered. No stock binary is read here; the result is a GNU-link
build aid, not a claim of using the original armlink binary.
"""

import struct

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

BRANCH_RELOCATIONS = (1, 29)  # R_ARM_PC24, R_ARM_JUMP24
UNCONDITIONAL_BRANCH_TO_SYMBOL = 0xEAFFFFFE
NEXT_INSTRUCTION_NOP = 0xE1A00000  # MOV r0,r0


def branch_target(symbol, sections, section_addresses, aliases):
    """Final address of a relocation target, or None when it is not fixed."""
    index = symbol["st_shndx"]
    if isinstance(index, int):
        base = section_addresses.get(sections[index].name)
        return None if base is None else base + symbol["st_value"]
    if index == "SHN_UNDEF" and symbol.name:
        return aliases.get(symbol.name)
    return None


def nop_next_instruction_branches(source, destination, section_addresses, aliases):
    """Rewrite B-to-next-instruction as NOP and retire its relocation.

    section_addresses maps this object's section names to their final start
    addresses; aliases maps undefined symbol names to final addresses. Branches
    whose section or target has no fixed address are left untouched.
    """
    buffer = bytearray(source.read_bytes())
    changes = []
    with source.open("rb") as stream:
        elf = ELFFile(stream)
        if elf["e_machine"] != "EM_ARM" or not elf.little_endian or elf.elfclass != 32:
            raise ValueError("only little-endian ELF32 ARM inputs are supported")
        sections = list(elf.iter_sections())
        for relocations in sections:
            if not isinstance(relocations, RelocationSection):
                continue
            if relocations["sh_type"] != "SHT_REL":
                raise ValueError("explicit-addend relocations are unsupported")
            section = sections[relocations["sh_info"]]
            symbols = sections[relocations["sh_link"]]
            base = section_addresses.get(section.name)
            if not section["sh_flags"] & 4 or base is None:
                continue
            for index, relocation in enumerate(relocations.iter_relocations()):
                if relocation["r_info_type"] not in BRANCH_RELOCATIONS:
                    continue
                if relocation["r_offset"] % 4 or relocation["r_offset"] + 4 > section["sh_size"]:
                    raise ValueError("unaligned or out-of-range branch relocation")
                at = section["sh_offset"] + relocation["r_offset"]
                before = struct.unpack_from("<I", buffer, at)[0]
                if before != UNCONDITIONAL_BRANCH_TO_SYMBOL:
                    continue
                symbol = symbols.get_symbol(relocation["r_info_sym"])
                target = branch_target(symbol, sections, section_addresses, aliases)
                place = base + relocation["r_offset"]
                if target is None or target != place + 4:
                    continue
                struct.pack_into("<I", buffer, at, NEXT_INSTRUCTION_NOP)
                info = relocations["sh_offset"] + index * relocations["sh_entsize"] + 4
                struct.pack_into("<I", buffer, info, 0)  # R_ARM_NONE
                changes.append({"section": section.name, "offset": relocation["r_offset"],
                                "address": place, "symbol": symbol.name, "target": target,
                                "before": before, "after": NEXT_INSTRUCTION_NOP,
                                "rule": "armlink --branchnop: branch to next instruction becomes NOP"})
    destination.write_bytes(buffer)
    return changes
