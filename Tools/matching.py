"""Compile upstream source with ARMCC and independently compare functions at EU addresses.

This builds per-function analysis ELFs, not an installable game. Calls into routines
outside the selected function resolve to audited stock symbol addresses. Stubs are
excluded. Every match binds the source, headers, compiler, linker and ELF hashes.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

from verify_elf import EU_SHA256, read_references, read_recovered_references
from translate_armasm import translate
from relocation_targets import infer_targets
from inline_arm_leaf import collect_helpers, inline_object
from branch_nop import nop_next_instruction_branches

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Build/matching"
WIBO = ROOT / ".local/bin/wibo"
FLAGS = ["--apcs=//interwork", "--cpu=MPCore", "--fpmode=fast", "--arm",
         "--force_new_nothrow", "--signed_chars", "--multibyte-chars", "--locale=C",
         "--no_vfe", "--no_rtti_data", "--no_rtti", "--no_exceptions", "-O3", "-Otime",
         "--data-reorder", "--split_sections", "--forceinline", "-DNON_MATCHING=",
         "-IInclude", "-ILibrary/sead/Include", "-ILibrary/nnsdk/Include",
         "-ILibrary/LibMessageStudio/Include"]
# Pinned original BL targets observed in the keeper/controller constructors.
RUNTIME_ALIASES = {"_ZnwjRKSt9nothrow_t": 0x2932B0, "_Znwj": 0x2932B0,
                   "_ZnajRKSt9nothrow_t": 0x292A78, "_Znaj": 0x292A78}
# Analysis-only regions far outside the EU image: unselected code sections that
# kept data refers to, and undefined dependencies without any original address.
OTHER_CODE_BASE = 0xC00000
PLACEHOLDER_BASE = 0xE00000


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def input_digest(paths):
    value = hashlib.sha256()
    for path in sorted(paths):
        value.update(str(path.relative_to(ROOT)).encode())
        value.update(bytes.fromhex(digest(path)))
    return value.hexdigest()


def compile_source(source, headers_digest, flags=None):
    relative = str(source.relative_to(ROOT))
    key = hashlib.sha256(relative.encode()).hexdigest()[:16]
    compiler_version = "4.0/b902" if relative.startswith("Library/nnsdk/") else "4.1/b791"
    compiler = ROOT / ".local/toolchains" / compiler_version / "bin/armcc.exe"
    assembler = shutil.which("arm-none-eabi-as")
    compiler_flags = FLAGS if flags is None else flags
    prefix = [str(WIBO), str(compiler), *compiler_flags,
              "-I" + str(compiler.parent.parent / "include"),
              "--c99" if source.suffix == ".c" else "--cpp", "-c", relative]
    inputs = {"source": relative, "source_sha256": digest(source),
              "headers_digest": headers_digest, "compiler": compiler_version,
              "compiler_sha256": digest(compiler), "wibo_sha256": digest(WIBO),
              "flags": compiler_flags, "command_prefix": prefix,
              "assembly_translator_sha256": digest(ROOT / "Tools/translate_armasm.py"),
              "assembler_sha256": digest(Path(assembler)) if assembler else None}
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    # Preserve prior verified builds when flags or source change.
    folder = OUT / "units" / key / fingerprint[:16]
    folder.mkdir(parents=True, exist_ok=True)
    obj = folder / "source.o"
    command = prefix + ["-o", str(obj)]
    record_path = folder / "compile.json"
    if obj.exists() and record_path.exists():
        record = json.loads(record_path.read_text())
        if record.get("fingerprint") == fingerprint and record.get("object_sha256") == digest(obj):
            return record
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=90)
    (folder / "compile.log").write_text(result.stdout + result.stderr)
    fallback = None
    if result.returncode and not (result.stdout + result.stderr).strip() and assembler:
        arm_source, gnu_source = folder / "source.armasm.s", folder / "source.gnu.s"
        emit_command = command.copy()
        emit_command[emit_command.index("-c")] = "-S"
        emit_command[-1] = str(arm_source)
        emitted = subprocess.run(emit_command, cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=90)
        (folder / "assembly-emission.log").write_text(emitted.stdout + emitted.stderr)
        if emitted.returncode == 0 and arm_source.exists():
            fallback = {"emit_command": emit_command, "armasm_sha256": digest(arm_source)}
            try:
                gnu_source.write_text(translate(arm_source.read_text()))
                assemble_command = [assembler, "-mcpu=mpcore", "-mfpu=vfp", str(gnu_source), "-o", str(obj)]
                result = subprocess.run(assemble_command, cwd=ROOT, capture_output=True, text=True, timeout=30)
                (folder / "assembly.log").write_text(result.stdout + result.stderr)
                fallback.update({"assemble_command": assemble_command, "gnu_source_sha256": digest(gnu_source)})
            except ValueError as error:
                fallback["error"] = str(error)
    record = {**inputs, "command": command, "fingerprint": fingerprint, "returncode": result.returncode,
              "object": str(obj.relative_to(ROOT)), "source_unchanged": digest(source) == inputs["source_sha256"]}
    if fallback:
        record["embedded_assembly_fallback"] = fallback
    if result.returncode == 0 and record["source_unchanged"]:
        record["object_sha256"] = digest(obj)
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    return record


def data_references():
    references = {}
    for path in (ROOT / "DataSymbols").rglob("*.sym"):
        for row in csv.reader(path.open()):
            if len(row) >= 2:
                references[row[0]] = int(row[1], 16)
    return references


def link_and_check(record, references, data_refs, linker, discovered, helpers):
    if record.get("returncode") or not record.get("source_unchanged"):
        return [{"source": record["source"], "status": "compile-failed", "compile_record": record}]
    obj = ROOT / record["object"]
    folder = obj.parent
    compile_record_sha256 = digest(folder / "compile.json")
    context = {"input_object_sha256": record["object_sha256"], "helpers": helpers,
               "tool_sha256": digest(ROOT / "Tools/inline_arm_leaf.py"),
               "branch_nop_tool_sha256": digest(ROOT / "Tools/branch_nop.py")}
    fingerprint = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]
    folder = folder / "inline" / fingerprint
    folder.mkdir(parents=True, exist_ok=True)
    inlined = folder / "source.o"
    changes = inline_object(obj, inlined, helpers)
    context.update({"changes": changes, "output_object_sha256": digest(inlined)})
    inline_report = folder / "inline.json"
    inline_report.write_text(json.dumps(context, indent=2) + "\n")
    obj = inlined
    results = []
    with obj.open("rb") as stream:
        elf = ELFFile(stream)
        sections = list(elf.iter_sections())
        table = elf.get_section_by_name(".symtab")
        symbols = list(table.iter_symbols())
        relocation_sections = [s for s in sections if isinstance(s, RelocationSection)]
        stock_code = (ROOT / "code.bin").read_bytes()
        candidates = [s for s in symbols if s["st_info"]["type"] == "STT_FUNC"
                      and isinstance(s["st_shndx"], int) and s["st_size"] > 0
                      and s.name in references and "stub" not in sections[s["st_shndx"]].name.lower()]
        for index, symbol in enumerate(candidates):
            name = symbol.name
            expected_address, expected_size = references[name]
            base = {"symbol": name, "source": record["source"],
                    "expected_address": expected_address, "expected_size": expected_size,
                    "actual_size": symbol["st_size"], "compile_record_sha256": compile_record_sha256,
                    "link_input_sha256": digest(obj), "inline_report": str(inline_report.relative_to(ROOT)),
                    "inline_report_sha256": digest(inline_report)}
            if symbol["st_size"] != expected_size:
                results.append({**base, "status": "size-mismatch", "matched": False})
                continue
            selected = sections[symbol["st_shndx"]]
            address = expected_address - symbol["st_value"]
            all_known = {key: value[0] for key, value in references.items()}
            all_known.update(RUNTIME_ALIASES)
            all_known.update(discovered)
            relocations = []
            for relocation_section in relocation_sections:
                if relocation_section["sh_info"] != symbol["st_shndx"]:
                    continue
                for relocation in relocation_section.iter_relocations():
                    if relocation["r_info_type"] == 0:
                        continue
                    offset = relocation["r_offset"] - symbol["st_value"]
                    if not 0 <= offset < symbol["st_size"]:
                        continue
                    target = symbols[relocation["r_info_sym"]]
                    known = all_known.get(target.name)
                    if known is None and isinstance(target["st_shndx"], int):
                        target_section = sections[target["st_shndx"]]
                        if target_section.name in data_refs:
                            known = data_refs[target_section.name] + target["st_value"]
                        elif target["st_shndx"] == symbol["st_shndx"]:
                            known = address + target["st_value"]
                    relocations.append({"offset": offset, "type": relocation["r_info_type"],
                                        "symbol": target.name, "global": target["st_info"]["bind"] != "STB_LOCAL",
                                        "known_address": known})
            actual = selected.data()[symbol["st_value"]:symbol["st_value"] + symbol["st_size"]]
            original = stock_code[expected_address - 0x100000:expected_address - 0x100000 + expected_size]
            inferred, reason = infer_targets(actual, original, expected_address, relocations, 0x100000, 0x3A1784)
            script = [f'ENTRY({name})', 'SECTIONS {',
                      f' .candidate 0x{address:x} : {{ KEEP(*({json.dumps(selected.name)})) }}']
            auxiliary = 0x800000
            for section_index, section in enumerate(sections):
                if (not section["sh_flags"] & 2 or section["sh_flags"] & 4 or not section["sh_size"]
                        or section.name.startswith((".ARM.exidx", ".ARM.extab", ".init_array", ".fini_array", ".static_init"))):
                    continue
                origin = data_refs.get(section.name, auxiliary)
                script.append(f' .aux{section_index} 0x{origin:x} : {{ *({json.dumps(section.name)}) }}')
                if section.name not in data_refs:
                    auxiliary += (section["sh_size"] + 0xFFF) & ~0xFFF
            # Unselected code stays out of the comparison but must remain linkable
            # when a kept data section (for example a vtable) refers to it.
            script.append(f' .others 0x{OTHER_CODE_BASE:x} : {{ *(i.*) *(t.*) *(.text*) *(.emb_text*) }}')
            script += [' /DISCARD/ : { *(*) }', '}']
            # Never replace the selected symbol; its bytes must come from the object.
            aliases = {key: value[0] for key, value in references.items() if key != name}
            aliases.update(RUNTIME_ALIASES)
            aliases.update(discovered)
            aliases.update(inferred)
            placeholders = {}
            for other in symbols:
                if other.name == name or not other.name or other["st_info"]["bind"] == "STB_LOCAL":
                    continue
                if other.name in aliases:
                    script.append(f'{json.dumps(other.name)} = 0x{aliases[other.name]:x};')
                elif other["st_shndx"] == "SHN_UNDEF":
                    # An undefined dependency with no audited or inferred original
                    # address gets an analysis-only placeholder outside EU code so
                    # the comparison can report the real differences instead of a
                    # link failure. A placeholder can never reproduce a stock branch.
                    placeholders[other.name] = PLACEHOLDER_BASE + 16 * len(placeholders)
                    script.append(f'{json.dumps(other.name)} = 0x{placeholders[other.name]:x};')
            linker_script = folder / f"function-{index}.ld"
            linked = folder / f"function-{index}.elf"
            comparison = folder / f"function-{index}.json"
            comparison.unlink(missing_ok=True)
            linker_script.write_text("\n".join(script) + "\n")
            # armlink's documented default --branchnop turns a tail branch that
            # resolves to the next instruction into a NOP. Apply the same rule
            # with this candidate's placement and the audited alias addresses.
            placed = folder / f"function-{index}.o"
            branch_nops = nop_next_instruction_branches(obj, placed, {selected.name: address}, aliases)
            link_object = placed if branch_nops else obj
            base.update({"branch_nop_changes": branch_nops,
                         "link_object_sha256": digest(link_object),
                         "placeholder_dependencies": placeholders})
            # An erased call can leave an undefined hidden symbol in the input
            # symbol table even after its relocation is R_ARM_NONE. Resolve it
            # with the actual compiled helper object, never an invented address.
            # Unselected helper sections remain discarded by the script above.
            extra_objects = sorted({str(ROOT / change["helper"]["object"])
                                    for change in changes if change["symbol"] not in aliases
                                    and change["helper"]["object"] != record["object"]})
            command = [linker, "--no-warn-mismatch", "--gc-sections", "-T", str(linker_script),
                       str(link_object), *extra_objects, "-o", str(linked)]
            link = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
            (folder / f"function-{index}.log").write_text(link.stdout + link.stderr)
            if link.returncode:
                results.append({**base, "status": "link-failed", "matched": False,
                                "log": str((folder / f"function-{index}.log").relative_to(ROOT))})
                continue
            # The independent checker reads the emitted executable and stock bytes itself.
            checked = subprocess.run([sys.executable, str(ROOT / "Tools/verify_elf.py"),
                                      "--elf", str(linked), "--symbol", name, "--out", str(comparison),
                                      "--references-json", str(ROOT / "Data/RecoveredFunctions.json")],
                                     cwd=ROOT, capture_output=True, text=True, timeout=30)
            if comparison.exists():
                evidence = json.loads(comparison.read_text())
                matched = checked.returncode == 0 and evidence["passed"]
                if matched:
                    discovered.update(inferred)
                results.append({**base, "status": "matched" if matched else "bytes-differ", "matched": matched,
                                "comparison": str(comparison.relative_to(ROOT)),
                                "comparison_sha256": digest(comparison),
                                "linker_script_sha256": digest(linker_script), "link_command": command,
                                "inferred_call_targets": inferred, "inference_gate": reason})
            else:
                results.append({**base, "status": "checker-failed", "matched": False,
                                "error": checked.stderr.strip()})
    return results


def union_length(ranges):
    total, end = 0, -1
    for start, stop in sorted(ranges):
        if stop > end:
            total += stop - max(start, end)
            end = stop
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", help="optional source path; default compiles all upstream units")
    parser.add_argument("--out", help="report path; targeted runs otherwise write targeted-progress.json")
    args = parser.parse_args()
    if digest(ROOT / "code.bin") != EU_SHA256:
        raise ValueError("wrong EU executable")
    linker = shutil.which("arm-none-eabi-ld")
    if not linker or not WIBO.exists():
        raise RuntimeError("local wibo and GNU ARM linker are required")
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / "matching.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    roots = [ROOT / "Source", ROOT / "Library/sead/Source", ROOT / "Library/nnsdk/Source",
             ROOT / "Library/LibMessageStudio/Source"]
    sources = ([ROOT / p for p in args.source] if args.source else
               sorted(p for directory in roots for p in directory.rglob("*")
                      if p.suffix in (".c", ".cpp") and p.name != "Stubs.c"))
    headers = [p for directory in (ROOT / "Include", ROOT / "Library") for p in directory.rglob("*")
               if p.is_file() and p.suffix in (".h", ".hpp", ".inc")]
    headers += [p for version in ("4.1/b791", "4.0/b902")
                for p in (ROOT / ".local/toolchains" / version / "include").rglob("*") if p.is_file()]
    header_hash = input_digest(headers)
    records = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = {executor.submit(compile_source, source, header_hash): source for source in sources}
        for future in as_completed(pending):
            record = future.result()
            records.append(record)
            print(f'Compile {len(records)}/{len(sources)}: {record["source"]} ({record["returncode"]})', flush=True)
    references, data_refs = read_references(ROOT / "Symbols"), data_references()
    references.update(read_recovered_references(ROOT / "Data/RecoveredFunctions.json"))
    functions = []
    discovered = {}
    helpers = collect_helpers(ROOT, records)
    for index, record in enumerate(sorted(records, key=lambda r: r["source"])):
        functions.extend(link_and_check(record, references, data_refs, linker, discovered, helpers))
        print(f'Compare {index + 1}/{len(records)}: {sum(r.get("matched", False) for r in functions)} matches', flush=True)
    matched = [r for r in functions if r.get("matched")]
    coverage = union_length((r["expected_address"], r["expected_address"] + r["expected_size"]) for r in matched)
    executable_size = json.loads((ROOT / ".local/analysis/input.json").read_text())["sections"][0]["size"]
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "code_sha256": EU_SHA256,
              "matching_tool_sha256": digest(Path(__file__)), "headers_digest": header_hash,
              "relocation_target_tool_sha256": digest(ROOT / "Tools/relocation_targets.py"),
              "leaf_inlining_tool_sha256": digest(ROOT / "Tools/inline_arm_leaf.py"),
              "branch_nop_tool_sha256": digest(ROOT / "Tools/branch_nop.py"),
              "measurement_kind": "Independent exact-function coverage in .text; verification coverage, not overall source progress",
              "source_scope": "targeted" if args.source else "all existing source units",
              "upstream_code_bin_baseline": {
                  "badge": json.loads((ROOT / "Data/Code.json").read_text()),
                  "status": "Historical upstream measurement; the separately audited local partial-image metric is recorded in BACKGROUND.md",
                  "method": "Tools/progress.py compares four-byte words throughout code.bin, including data and padding"},
              "linker_sha256": digest(Path(linker)), "source_units": len(records),
              "compiled_units": sum(r.get("returncode") == 0 for r in records),
              "byte_matched_functions": len(matched), "unique_byte_matched_entries": len({r["expected_address"] for r in matched}),
              "byte_matched_text_bytes": coverage, "text_bytes": executable_size,
              "byte_verified_text_percent": coverage / executable_size * 100,
              "functions": functions, "compile_records": records,
              "discovered_call_targets": discovered,
              "full_game_decompilation_complete": False,
              "limitations": "Per-function reconstructed ELFs call stock-address dependencies; dependencies without any audited or inferred original address link to analysis-only placeholders outside the EU image and are reported per function. GNU ld plus a limited source-derived A32 leaf-inlining pass and the documented armlink branch-to-next-instruction NOP rule implement two armlink optimizations; this is not the original armlink or a complete game link. Locale C is used for the headless host; only strict byte comparisons count matches. Source inventory ranks are not changed."}
    destination = (ROOT / args.out if args.out else
                   OUT / ("targeted-progress.json" if args.source else "progress.json"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("compiled_units", "source_units", "byte_matched_functions", "byte_verified_text_percent")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
