"""Attempt a complete link of the current partial repository, without stock-backed symbols.

All executable/data bytes come from compiled Source/ and library files, including
the repository's explicit stubs. Placement follows upstream O/m and DataSymbols
conventions. This is a partial decompilation build, not a completed game.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from elftools.elf.elffile import ELFFile

from matching import ROOT, FLAGS, compile_source, digest, input_digest, data_references
from inline_arm_leaf import collect_helpers, inline_object
from branch_nop import nop_next_instruction_branches
from source_aliases import alias_script

CFLAGS = ["--apcs=//interwork", "--cpu=MPCore", "--fpmode=fast", "--arm",
          "--signed_chars", "--multibyte-chars", "--locale=C", "-Otime",
          "--data-reorder", "--split_sections", "-DNON_MATCHING=",
          "-IInclude", "-ILibrary/sead/Include", "-ILibrary/nnsdk/Include",
          "-ILibrary/LibMessageStudio/Include"]


def placements():
    result = {}
    for path in sorted((ROOT / "Symbols").rglob("*.sym")):
        if path.name == "Unnamed.sym":
            continue
        for row in csv.reader(path.open()):
            if len(row) >= 4 and row[3] in ("O", "m"):
                result[row[0]] = int(row[1], 16)
    recovered = json.loads((ROOT / "Data/RecoveredFunctions.json").read_text())
    for function in recovered["functions"]:
        state = function.get("verification_status", "").lower()
        if "byte-exact" in state or "exact bytes" in state:
            result[function["symbol"]] = int(function["address"], 16)
    return result


def object_sections(path):
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        sections = list(elf.iter_sections())
        table = elf.get_section_by_name(".symtab")
        functions = {}
        for symbol in table.iter_symbols():
            index = symbol["st_shndx"]
            if symbol["st_info"]["type"] == "STT_FUNC" and isinstance(index, int):
                functions[symbol.name] = {"section": sections[index].name,
                                          "offset": symbol["st_value"], "size": symbol["st_size"],
                                          "binding": symbol["st_info"]["bind"]}
        allocated = [{"name": s.name, "size": s["sh_size"], "flags": s["sh_flags"],
                      "type": s["sh_type"]} for s in sections if s["sh_flags"] & 2 and s["sh_size"]]
    return functions, allocated


def linker_script(objects):
    function_addresses, data_addresses = placements(), data_references()
    fixed = {}
    missing = set(function_addresses)
    section_addresses = {}
    inventory = []
    definitions = {}
    remaining = {name: [] for name in ("rodata", "static_init", "extab", "exidx", "data", "bss", "code", "module_id")}
    for obj in objects:
        functions, sections = object_sections(obj)
        for name, info in functions.items():
            definitions.setdefault(name, []).append({**info, "object": str(obj)})
            if name not in function_addresses:
                continue
            if "stub" in info["section"].lower():
                continue
            missing.discard(name)
            start = function_addresses[name] - info["offset"]
            key = (str(obj), info["section"])
            if key in section_addresses and section_addresses[key] != start:
                raise ValueError(f"conflicting placement of shared section {key}")
            section_addresses[key] = start
            fixed.setdefault(start, set()).add(key)
        for section in sections:
            inventory.append({"object": str(obj.relative_to(ROOT)), **section})
            if section["name"] in data_addresses:
                start = data_addresses[section["name"]]
                fixed.setdefault(start, set()).add((str(obj), section["name"]))
            if (str(obj), section["name"]) in section_addresses or section["name"] in data_addresses:
                continue
            name = section["name"]
            if name == ".module_id":
                category = "module_id"
            elif section["flags"] & 4:
                category = "code"
            elif section["type"] == "SHT_NOBITS":
                category = "bss"
            elif name.startswith((".static_init", ".init_array")):
                category = "static_init"
            elif name.startswith(".ARM.extab"):
                category = "extab"
            elif name.startswith(".ARM.exidx"):
                category = "exidx"
            elif section["flags"] & 1:
                category = "data"
            else:
                category = "rodata"
            remaining[category].append((str(obj), name))
    script = ["ENTRY(__ctr_start)", "SECTIONS {"]
    for index, (address, selectors) in enumerate(sorted(fixed.items())):
        script.append(f" .fixed_{index} 0x{address:x} : {{")
        for path, section in sorted(selectors):
            script.append(f"  {json.dumps(path)}({json.dumps(section)})")
        script.append(" }")
    # Match the upstream scatter template's unassigned data/code regions.
    # No known original addresses are assigned to undefined dependencies.
    for category, declaration in [("rodata", ".rodata 0x003a2000"), ("static_init", ".static_init"),
                                   ("extab", ".ARM.extab"), ("exidx", ".ARM.exidx"),
                                   ("data", ".data 0x003e1000"), ("bss", ".bss (NOLOAD)"),
                                   ("code", ".rest_code 0x00432000"), ("module_id", ".module_id 0x04000000")]:
        script.append(f" {declaration} : {{")
        for path, section in remaining[category]:
            script.append(f"  {json.dumps(path)}({json.dumps(section)})")
        if category == "bss":
            script.append("  *(COMMON)")
        script.append(" }")
    script += [" /DISCARD/ : { *(.comment .note*) }", "}"]
    aliases = ROOT / "Data/SourceAliases.json"
    if aliases.exists():
        script += alias_script(json.loads(aliases.read_text())["aliases"], definitions)
    return "\n".join(script) + "\n", sorted(missing), inventory, section_addresses, function_addresses


def nop_adjacent_tail_branches(objects, section_addresses, function_addresses, missing):
    """Apply armlink's documented branch-to-next-instruction NOP rule in place.

    Only sections with fixed original placements and targets that are actually
    defined by a placed, non-stub section participate; everything else is left
    for the GNU linker.
    """
    targets = {name: address for name, address in function_addresses.items() if name not in missing}
    changes = []
    for obj in objects:
        placed = {section: start for (path, section), start in section_addresses.items() if path == str(obj)}
        if not placed:
            continue
        for change in nop_next_instruction_branches(obj, obj, placed, targets):
            changes.append({"object": str(obj.relative_to(ROOT)), **change})
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    out = ROOT / "Build/whole"
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / "build.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # Share the compiler cache lock with targeted matching jobs.
    cache_lock = (ROOT / "Build/matching/matching.lock").open("w")
    fcntl.flock(cache_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    roots = [ROOT / "Source", ROOT / "Library/sead/Source", ROOT / "Library/nnsdk/Source",
             ROOT / "Library/LibMessageStudio/Source"]
    sources = sorted(p for directory in roots for p in directory.rglob("*") if p.suffix in (".c", ".cpp"))
    headers = [p for directory in (ROOT / "Include", ROOT / "Library") for p in directory.rglob("*")
               if p.is_file() and p.suffix in (".h", ".hpp", ".inc")]
    headers += [p for version in ("4.1/b791", "4.0/b902")
                for p in (ROOT / ".local/toolchains" / version / "include").rglob("*") if p.is_file()]
    header_hash = input_digest(headers)
    records = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = [executor.submit(compile_source, p, header_hash, CFLAGS if p.suffix == ".c" else FLAGS)
                   for p in sources]
        for future in as_completed(pending):
            record = future.result()
            records.append(record)
            print(f'Compile {len(records)}/{len(sources)}: {record["source"]} ({record["returncode"]})', flush=True)
    records.sort(key=lambda r: r["source"])
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "build_tool_sha256": digest(Path(__file__)), "headers_digest": header_hash,
              "compiled_units": sum(r.get("returncode") == 0 for r in records),
              "source_units": len(records), "compile_records": records,
              "original_backed_definitions": False, "full_game_decompilation_complete": False,
              "limitations": "Current partial source plus explicit stubs. ARMCC with GNU ld, source-derived leaf inlining and armlink's documented branch-to-next-instruction NOP rule. Genuine runtime archives are available; original armlink requires an unavailable license."}
    if report["compiled_units"] != report["source_units"]:
        report["status"] = "compile-failed"
        (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
        return 1
    helpers = collect_helpers(ROOT, [r for r in records if r["source"] != "Source/Stubs.c"])
    context = {"compile_fingerprints": [r["fingerprint"] for r in records], "helpers": helpers,
               "inline_tool_sha256": digest(ROOT / "Tools/inline_arm_leaf.py"),
               "branch_nop_tool_sha256": digest(ROOT / "Tools/branch_nop.py"),
               "build_tool_sha256": digest(Path(__file__)),
               "symbol_inputs_sha256": input_digest(list((ROOT / "Symbols").rglob("*.sym"))),
               "data_inputs_sha256": input_digest(list((ROOT / "DataSymbols").rglob("*.sym"))),
               "recovered_references_sha256": digest(ROOT / "Data/RecoveredFunctions.json")}
    context["source_aliases_sha256"] = digest(ROOT / "Data/SourceAliases.json") if (ROOT / "Data/SourceAliases.json").exists() else None
    context["source_alias_tool_sha256"] = digest(ROOT / "Tools/source_aliases.py")
    fingerprint = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]
    build = out / fingerprint
    build.mkdir(exist_ok=True)
    objects = []
    inlining = []
    for index, record in enumerate(records):
        obj = build / f"unit-{index}.o"
        changes = inline_object(ROOT / record["object"], obj, helpers)
        objects.append(obj)
        inlining.append({"source": record["source"], "object": str(obj.relative_to(ROOT)),
                         "inlined_sha256": digest(obj), "changes": changes})
    script, missing, inventory, section_addresses, function_addresses = linker_script(objects)
    branch_nops = nop_adjacent_tail_branches(objects, section_addresses, function_addresses, missing)
    # Record the final link-object hashes after both placement-dependent passes.
    for record in inlining:
        record["sha256"] = digest(ROOT / record["object"])
    script_path = build / "Linker.ld"
    script_path.write_text(script)
    linker = shutil.which("arm-none-eabi-ld")
    if not linker:
        raise RuntimeError("GNU ARM linker is missing")
    elf = build / "RedPepper.elf"
    command = [linker, "--no-warn-mismatch", "-T", str(script_path), "-Map", str(build / "RedPepper.map"),
               *map(str, objects), "-o", str(elf)]
    report.update({"build_directory": str(build.relative_to(ROOT)), "build_context": context, "inlining": inlining,
                   "branch_nops": branch_nops,
                   "linker_script_sha256": digest(script_path), "link_command": command,
                   "linker_sha256": digest(Path(linker)), "missing_placement_symbols": missing,
                   "allocated_input_sections": inventory})
    if args.prepare_only:
        report["status"] = "prepared"
    else:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
        (build / "link.log").write_text(result.stdout + result.stderr)
        report.update({"status": "linked" if result.returncode == 0 else "link-failed",
                       "link_returncode": result.returncode, "link_log": str((build / "link.log").relative_to(ROOT))})
        if result.returncode == 0:
            report["elf_sha256"] = digest(elf)
            objcopy = shutil.which("arm-none-eabi-objcopy")
            binary = build / "code.bin"
            conversion = subprocess.run([objcopy, "-O", "binary", str(elf), str(binary)], capture_output=True, text=True)
            report["objcopy_returncode"] = conversion.returncode
            if conversion.returncode == 0:
                report["binary_sha256"] = digest(binary)
                report["binary_size"] = binary.stat().st_size
    (build / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "compiled_units", "source_units")}), flush=True)
    return 0 if report["status"] in ("prepared", "linked") else 1


if __name__ == "__main__":
    sys.exit(main())
