"""Link the partial repository with genuine ARMCC runtime objects using GNU ld.

Consumes the hash-checked objects prepared by whole_build.py. The preliminary
relocatable link selects archive members; the final link keeps those members
separate so original function placements remain possible. No stock bytes or
stock-address definitions for missing dependencies enter either link.
"""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from matching import ROOT, digest, input_digest
from whole_build import linker_script

RUNTIME = ROOT / ".local/toolchains/mdk422/ARM/RV31/LIB"
ARCHIVES = {
    "armlib/c_4.l": "643af4a35cf6b11d3cfa26fc1cf7c8fde2982fbdda0d8a32747bfabd6a383d6d",
    "cpplib/cpprt_4.l": "af94582ef9f66067a1008a93907145cd73ee9f39777838db28ae719b301db01b",
}


def run(command, log):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
    log.write_text(result.stdout + result.stderr)
    return {"command": command, "returncode": result.returncode,
            "log": str(log.relative_to(ROOT)), "log_sha256": digest(log)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-report", type=Path, default=ROOT / "Build/whole/build.json")
    args = parser.parse_args()
    out = ROOT / "Build/whole-runtime"
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / "build.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    prepared = json.loads(args.prepared_report.read_text())
    if prepared["compiled_units"] != prepared["source_units"]:
        raise ValueError("prepare a successful whole-source compile first")
    headers = [p for directory in (ROOT / "Include", ROOT / "Library")
               for p in directory.rglob("*") if p.is_file() and p.suffix in (".h", ".hpp", ".inc")]
    headers += [p for version in ("4.1/b791", "4.0/b902")
                for p in (ROOT / ".local/toolchains" / version / "include").rglob("*") if p.is_file()]
    if input_digest(headers) != prepared["headers_digest"]:
        raise ValueError("headers changed; refresh the prepared source objects")
    for record in prepared["compile_records"]:
        if digest(ROOT / record["source"]) != record["source_sha256"]:
            raise ValueError("source changed: " + record["source"])
        if digest(ROOT / record["object"]) != record["object_sha256"]:
            raise ValueError("compiler object changed: " + record["object"])
    for name, expected in ARCHIVES.items():
        if digest(RUNTIME / name) != expected:
            raise ValueError("unexpected official runtime archive: " + name)
    objects = []
    for record in prepared["inlining"]:
        obj = ROOT / record["object"]
        if digest(obj) != record["sha256"]:
            raise ValueError("prepared link object changed: " + str(obj))
        # Normal source builds leave this optional behavior-test fallback empty.
        if record["source"] != "Source/Runtime/ArrayCtor.cpp":
            objects.append(obj)
    commands = {name: shutil.which(name) for name in
                ("arm-none-eabi-ld", "arm-none-eabi-ar", "arm-none-eabi-objcopy")}
    if not all(commands.values()):
        raise RuntimeError("GNU ARM linker, archiver and objcopy are required")
    context = {"prepared_report_sha256": digest(args.prepared_report),
               "runtime_archives": ARCHIVES,
               "tool_sha256": digest(Path(__file__)),
               "placement_tool_sha256": digest(ROOT / "Tools/whole_build.py"),
               "symbol_inputs_sha256": input_digest(list((ROOT / "Symbols").rglob("*.sym"))),
               "data_inputs_sha256": input_digest(list((ROOT / "DataSymbols").rglob("*.sym"))),
               "recovered_references_sha256": digest(ROOT / "Data/RecoveredFunctions.json"),
               "source_aliases_sha256": digest(ROOT / "Data/SourceAliases.json") if (ROOT / "Data/SourceAliases.json").exists() else None,
               "source_alias_tool_sha256": digest(ROOT / "Tools/source_aliases.py"),
               "executables_sha256": {name: digest(Path(path)) for name, path in commands.items()}}
    fingerprint = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]
    build = out / fingerprint
    build.mkdir(exist_ok=True)
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "build_context": context,
              "prepared_report": str(args.prepared_report.resolve().relative_to(ROOT)),
              "build_directory": str(build.relative_to(ROOT)), "source_objects": len(objects),
              "original_backed_definitions": False, "original_armlink_used": False,
              "full_game_decompilation_complete": False,
              "limitations": "Partial source with explicit stubs, ARMCC objects, supplied ARMCC runtime archives, GNU ld, limited source-derived leaf inlining and armlink's documented branch-to-next-instruction NOP rule applied to the prepared objects. Not a working game or original armlink build. Raw image includes linker padding and code beyond the stock extent."}
    archives = [RUNTIME / name for name in ARCHIVES]
    command = [commands["arm-none-eabi-ld"], "-r", "--no-warn-mismatch", "-Map", str(build / "partial.map"),
               *map(str, objects), "--start-group", *map(str, archives), "--end-group",
               "-o", str(build / "partial.o")]
    report["archive_selection"] = run(command, build / "partial-link.log")
    if report["archive_selection"]["returncode"]:
        report["status"] = "archive-selection-failed"
    else:
        members = []
        for archive, member in re.findall(r"([^\s]+\.l)\(([^)]+)\)", (build / "partial.map").read_text()):
            if (archive, member) in members:
                continue
            if Path(archive).resolve() not in archives or Path(member).name != member:
                raise ValueError("unexpected archive member in linker map")
            members.append((archive, member))
        report["library_members"] = []
        for index, (archive, member) in enumerate(members):
            obj = build / f"library-{index}-{member}"
            obj.write_bytes(subprocess.check_output([commands["arm-none-eabi-ar"], "p", archive, member]))
            objects.append(obj)
            report["library_members"].append({"archive": str(Path(archive).relative_to(ROOT)), "member": member,
                                               "object": str(obj.relative_to(ROOT)), "sha256": digest(obj)})
        script, missing, inventory, _, _ = linker_script(objects)
        script = script.replace(" /DISCARD/", " PROVIDE(SHT$$ARM_EXIDX$$Base = ADDR(.ARM.exidx));\n"
                                " PROVIDE(SHT$$ARM_EXIDX$$Limit = ADDR(.ARM.exidx) + SIZEOF(.ARM.exidx));\n /DISCARD/")
        script_path = build / "Linker.ld"
        script_path.write_text(script)
        report.update({"linker_script_sha256": digest(script_path), "missing_placement_symbols": missing,
                       "allocated_input_sections": inventory})
        elf = build / "RedPepper.elf"
        command = [commands["arm-none-eabi-ld"], "--no-warn-mismatch", "--fix-v4bx", "-T", str(script_path),
                   "-Map", str(build / "RedPepper.map"), *map(str, objects), "-o", str(elf)]
        report["link"] = run(command, build / "link.log")
        report["status"] = "link-failed"
        if not report["link"]["returncode"]:
            binary = build / "code.bin"
            report["elf_sha256"] = digest(elf)
            report["conversion"] = run([commands["arm-none-eabi-objcopy"], "-O", "binary", str(elf), str(binary)],
                                       build / "objcopy.log")
            report["status"] = "conversion-failed"
            if not report["conversion"]["returncode"]:
                report.update({"status": "linked", "binary_sha256": digest(binary), "binary_size": binary.stat().st_size})
    encoded = json.dumps(report, indent=2) + "\n"
    (build / "build.json").write_text(encoded)
    (out / "build.json").write_text(encoded)
    print(json.dumps({k: report[k] for k in ("status", "source_objects", "build_directory")}))
    return 0 if report["status"] == "linked" else 1


if __name__ == "__main__":
    sys.exit(main())
