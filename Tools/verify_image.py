"""Independently audit a linked partial image and reproduce the upstream word metric.

Checks every emitted section against the raw image and requires zero-filled
inter-section gaps. The upstream comparison includes such padding; it is not
equivalent to recovered source or function-level byte matching.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

from verify_elf import EU_SHA256

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit(elf_path, binary_path, stock):
    binary = binary_path.read_bytes()
    with elf_path.open("rb") as stream:
        elf = ELFFile(stream)
        if elf["e_type"] != "ET_EXEC" or elf["e_machine"] != "EM_ARM" or not elf.little_endian:
            raise ValueError("requires a linked little-endian ARM executable")
        for section in elf.iter_sections():
            if isinstance(section, RelocationSection) and section.num_relocations():
                if elf.get_section(section["sh_info"])["sh_flags"] & 2:
                    raise ValueError("allocated relocations remain unresolved")
        table = elf.get_section_by_name(".symtab")
        if any(s["st_shndx"] == "SHN_UNDEF" and s["st_info"]["bind"] == "STB_GLOBAL" and s.name
               for s in table.iter_symbols()):
            raise ValueError("strong undefined symbols remain")
        sections = sorted((s for s in elf.iter_sections() if s["sh_flags"] & 2
                           and s["sh_type"] != "SHT_NOBITS" and s["sh_size"]), key=lambda s: s["sh_addr"])
        base = min(s["sh_addr"] for s in sections)
        if base != 0x100000 or max(s["sh_addr"] + s["sh_size"] for s in sections) - base != len(binary):
            raise ValueError("raw image extent does not match ELF sections at the EU load address")
        mask = bytearray(len(binary))
        cursor = 0
        for section in sections:
            start = section["sh_addr"] - base
            end = start + section["sh_size"]
            if start < cursor:
                raise ValueError("overlapping allocated sections")
            if any(binary[cursor:start]) or binary[start:end] != section.data():
                raise ValueError("raw image differs from ELF section bytes or zero linker padding")
            mask[start:end] = bytes([1 if section["sh_flags"] & 4 else 2]) * (end - start)
            cursor = end
    categories = {name: {"compared_bytes": 0, "matching_bytes": 0}
                  for name in ("executable_section", "data_section", "linker_padding", "mixed_boundary", "missing_image")}
    for offset in range(0, len(stock), 4):
        kinds = set(mask[offset:offset + 4])
        kind = ("missing_image" if len(binary[offset:offset + 4]) != 4 else
                {frozenset([0]): "linker_padding", frozenset([1]): "executable_section",
                 frozenset([2]): "data_section"}.get(frozenset(kinds), "mixed_boundary"))
        categories[kind]["compared_bytes"] += 4
        if stock[offset:offset + 4] == binary[offset:offset + 4]:
            categories[kind]["matching_bytes"] += 4
    matched = sum(v["matching_bytes"] for v in categories.values())
    return {"elf_sha256": sha(elf_path.read_bytes()), "binary_sha256": sha(binary),
            "binary_size": len(binary), "stock_size": len(stock), "size_equal": len(binary) == len(stock),
            "image_matches_elf_and_zero_padding": True,
            "measurement_kind": "Upstream four-byte-word equality across stock code.bin extent; includes padding and data",
            "matching_bytes": matched, "compared_bytes": len(stock), "matching_percent": 100 * matched / len(stock),
            "by_emitted_section_kind": categories,
            "full_game_decompilation_complete": False,
            "limitations": "A raw-word diagnostic for a partial source/stub build. It does not certify function semantics, dependency destinations, original linker behavior or a working game."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    stock = (ROOT / "code.bin").read_bytes()
    if sha(stock) != EU_SHA256:
        raise ValueError("wrong EU executable")
    manifest = json.loads((ROOT / ".local/analysis/input.json").read_text())
    if manifest["title_id"] != "0004000000053F00" or manifest["code_sha256"] != EU_SHA256:
        raise ValueError("wrong EU manifest")
    report = audit(args.elf, args.binary, stock)
    report.update({"timestamp_utc": datetime.now(timezone.utc).isoformat(), "stock_sha256": EU_SHA256,
                   "checker_sha256": sha(Path(__file__).read_bytes()),
                   "inherited_baseline": json.loads((ROOT / "Data/Code.json").read_text())})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("matching_bytes", "compared_bytes", "matching_percent", "binary_size")}))


if __name__ == "__main__":
    main()
