"""Prepare actual ARMCC actor functions at separate addresses for ARM comparisons.

This is a behavior harness with intercepted dependencies, not a whole-game link.
It intentionally accepts non-matching function sizes and never claims byte parity.
"""

import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from matching import ROOT, compile_source, input_digest, digest
from inline_arm_leaf import collect_helpers, inline_object
from verify_elf import read_references, read_recovered_references, EU_SHA256

MOVEMENT = "_ZN2al9LiveActor8movementEv"
COLLIDER = "_ZN2al9LiveActor14updateColliderEv"


def prepare():
    if digest(ROOT / "code.bin") != EU_SHA256:
        raise ValueError("wrong EU executable")
    out = ROOT / "Build/headless/actor"
    out.mkdir(parents=True, exist_ok=True)
    with (ROOT / "Build/matching/matching.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return prepare_locked(out)


def prepare_locked(out):
    headers = [p for directory in (ROOT / "Include", ROOT / "Library") for p in directory.rglob("*")
               if p.is_file() and p.suffix in (".h", ".hpp", ".inc")]
    headers += [p for version in ("4.1/b791", "4.0/b902")
                for p in (ROOT / ".local/toolchains" / version / "include").rglob("*") if p.is_file()]
    header_hash = input_digest(headers)
    records = [compile_source(ROOT / source, header_hash) for source in
               ("Source/al/LiveActor/LiveActor.cpp", "Source/al/LiveActor/LiveActorFunction.cpp",
                "Source/al/LiveActor/MovementNoop.cpp")]
    if any(r["returncode"] for r in records):
        raise RuntimeError("actor source did not compile")
    context = {"compile_records": records, "inline_tool_sha256": digest(ROOT / "Tools/inline_arm_leaf.py"),
               "tool_sha256": digest(Path(__file__)), "references_sha256": digest(ROOT / "Data/RecoveredFunctions.json"),
               "symbols_sha256": input_digest(list((ROOT / "Symbols").rglob("*.sym")))}
    fingerprint = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]
    folder = out / fingerprint
    folder.mkdir(exist_ok=True)
    source = folder / "actor.o"
    changes = inline_object(ROOT / records[0]["object"], source, collect_helpers(ROOT, records))
    script = [f"ENTRY({MOVEMENT})", "SECTIONS {",
              f' .movement 0x800000 : {{ KEEP(*(i.{MOVEMENT})) }}',
              f' .collider 0x801000 : {{ KEEP(*(i.{COLLIDER})) }}', " /DISCARD/ : { *(*) }", "}"]
    refs = read_references(ROOT / "Symbols")
    refs.update(read_recovered_references(ROOT / "Data/RecoveredFunctions.json"))
    script += [f'{json.dumps(name)} = 0x{address:x};' for name, (address, _) in refs.items()
               if name not in (MOVEMENT, COLLIDER)]
    linker_script = folder / "actor.ld"
    linker_script.write_text("\n".join(script) + "\n")
    elf = folder / "actor.elf"
    command = [shutil.which("arm-none-eabi-ld"), "--no-warn-mismatch", "--gc-sections", "-T", str(linker_script),
               str(source), *[str(ROOT / r["object"]) for r in records[1:]], "-o", str(elf)]
    linked = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    (folder / "link.log").write_text(linked.stdout + linked.stderr)
    if linked.returncode:
        raise RuntimeError("actor behavior link failed: " + linked.stderr)
    report = {"context": context, "command": command, "elf": str(elf.relative_to(ROOT)), "elf_sha256": digest(elf),
              "linker_script_sha256": digest(linker_script), "inline_changes": changes,
              "limits": "Actual ARMCC actor source with intercepted dependencies. This harness establishes behavior only; exact-byte evidence is recorded separately."}
    (folder / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    return elf
