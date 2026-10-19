"""Strict EU function comparison, independent of asm-differ's similarity grades.

Only fully linked, correctly placed, non-stub functions can pass. Identical bytes
at identical addresses also preserve encoded PC-relative branch/literal targets.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

ROOT = Path(__file__).resolve().parents[1]
EU_SHA256 = "e1d7e188ff88467df776c17cec45c44857fadf5b699944baa8cddcae7d939e64"


def compare_bytes(expected, actual, expected_address, actual_address):
    first_difference = next((i for i, (a, b) in enumerate(zip(expected, actual)) if a != b), None)
    if first_difference is None and len(expected) != len(actual):
        first_difference = min(len(expected), len(actual))
    return {"byte_exact": expected == actual,
            "correct_address": expected_address == actual_address,
            "matched": expected == actual and expected_address == actual_address,
            "expected_size": len(expected), "actual_size": len(actual),
            "first_difference": first_difference}


def read_references(directory):
    references = {}
    for path in sorted(directory.rglob("*.sym")):
        with path.open(newline="") as stream:
            for row in csv.reader(stream):
                if len(row) < 4 or not row[0]:
                    continue
                value = (int(row[1], 16), int(row[2]))
                if row[0] in references and references[row[0]] != value:
                    raise ValueError(f"conflicting upstream references: {row[0]}")
                references[row[0]] = value
    return references


def read_recovered_references(path):
    metadata = json.loads(path.read_text())
    if metadata["code_sha256"] != EU_SHA256:
        raise ValueError("recovered references belong to a different executable")
    references = {}
    for function in metadata["functions"]:
        ranges = function["code_ranges"]
        if len(ranges) != 1:
            raise ValueError("strict comparison currently requires a contiguous function range")
        start, end = (int(value, 0) for value in ranges[0])
        if start != int(function["address"], 0) or end <= start:
            raise ValueError("invalid recovered function range")
        name = function["symbol"]
        if name in references:
            raise ValueError(f"duplicate recovered reference: {name}")
        references[name] = (start, end - start)
    return references


def read_function(elf, name):
    table = elf.get_section_by_name(".symtab")
    candidates = [] if table is None else table.get_symbol_by_name(name) or []
    functions = [s for s in candidates if s["st_info"]["type"] == "STT_FUNC"
                 and isinstance(s["st_shndx"], int)]
    if len(functions) != 1:
        raise ValueError(f"expected one defined function: {name}")
    symbol = functions[0]
    section = elf.get_section(symbol["st_shndx"])
    if not section["sh_flags"] & 4 or "stub" in section.name.lower():
        raise ValueError(f"function is not in a non-stub executable section: {name}")
    address, size = symbol["st_value"], symbol["st_size"]
    offset = address - section["sh_addr"]
    if size <= 0 or offset < 0 or offset + size > section["sh_size"]:
        raise ValueError(f"invalid function extent: {name}")
    return address, section.data()[offset:offset + size]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--symbol", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--references-json", type=Path,
                        help="explicit reviewed references for newly recovered functions")
    args = parser.parse_args()
    code = (ROOT / "code.bin").read_bytes()
    if hashlib.sha256(code).hexdigest() != EU_SHA256:
        raise ValueError("wrong EU code.bin")
    manifest = json.loads((ROOT / ".local/analysis/input.json").read_text())
    if manifest["title_id"] != "0004000000053F00" or manifest["code_sha256"] != EU_SHA256:
        raise ValueError("wrong EU input manifest")
    references = read_references(ROOT / "Symbols")
    if args.references_json:
        for name, value in read_recovered_references(args.references_json).items():
            if name in references and references[name] != value:
                raise ValueError(f"recovered reference conflicts with upstream: {name}")
            references[name] = value
    results = []
    with args.elf.open("rb") as stream:
        elf = ELFFile(stream)
        if elf["e_type"] != "ET_EXEC" or elf["e_machine"] != "EM_ARM" or not elf.little_endian:
            raise ValueError("comparison requires a fully linked little-endian ARM executable")
        for section in elf.iter_sections():
            if isinstance(section, RelocationSection) and section.num_relocations():
                target = elf.get_section(section["sh_info"])
                if target["sh_flags"] & 2:
                    raise ValueError("unresolved runtime relocations must be applied before comparison")
        for name in args.symbol:
            if name not in references:
                raise ValueError(f"unknown EU reference symbol: {name}")
            expected_address, expected_size = references[name]
            segment = next((s for s in manifest["sections"] if s["flags"] & 1
                            and s["address"] <= expected_address
                            and expected_address + expected_size <= s["address"] + s["size"]), None)
            if segment is None or expected_size <= 0:
                raise ValueError(f"reference function is outside EU executable section: {name}")
            offset = segment["offset"] + expected_address - segment["address"]
            address, actual = read_function(elf, name)
            expected = code[offset:offset + expected_size]
            results.append({"symbol": name, "expected_address": expected_address,
                            "actual_address": address,
                            "expected_sha256": hashlib.sha256(expected).hexdigest(),
                            "actual_sha256": hashlib.sha256(actual).hexdigest(),
                            **compare_bytes(expected, actual, expected_address, address)})
    report = {"passed": all(r["matched"] for r in results), "functions": results,
              "stock_code_sha256": EU_SHA256,
              "elf_sha256": hashlib.sha256(args.elf.read_bytes()).hexdigest(),
              "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "symbols_promoted": False}
    if args.references_json:
        report["references_sha256"] = hashlib.sha256(args.references_json.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "matched": sum(r["matched"] for r in results),
                      "compared": len(results), "report": str(args.out)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
