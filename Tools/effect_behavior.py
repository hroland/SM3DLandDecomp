"""Build actual effect sources for behavior checks with two intercepted setters.

Separate-address test ELF only. This is not a production build or a byte match.
"""

import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from matching import ROOT, compile_source, input_digest, digest
from verify_elf import EU_SHA256

UPDATE = "_ZN2al11EffectEntry6updateEv"
ENTRIES = {UPDATE: 0x800000, "FUN_0023f45c": 0x801000,
           "FUN_0027cb9c": 0x802000, "FUN_00291470": 0x803000}


def prepare():
    if digest(ROOT / "code.bin") != EU_SHA256:
        raise ValueError("wrong EU executable")
    out = ROOT / "Build/headless/effect"
    out.mkdir(parents=True, exist_ok=True)
    with (ROOT / "Build/matching/matching.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        headers = [p for directory in (ROOT / "Include", ROOT / "Library")
                   for p in directory.rglob("*")
                   if p.is_file() and p.suffix in (".h", ".hpp", ".inc")]
        headers += [p for version in ("4.1/b791", "4.0/b902")
                    for p in (ROOT / ".local/toolchains" / version / "include").rglob("*") if p.is_file()]
        records = [compile_source(ROOT / name, input_digest(headers)) for name in
                   ("Source/al/Effect/EffectUpdate.cpp", "Source/al/Effect/EffectHandle.cpp",
                    "Library/nnsdk/Source/math/math_MTX34.cpp")]
        if any(r["returncode"] for r in records):
            raise RuntimeError("effect source did not compile")
        context = {"compile_records": records, "tool_sha256": digest(Path(__file__)),
                   "limits": "Actual ARMCC code at separate test addresses. Two setters are intercepted."}
        folder = out / hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]
        folder.mkdir(exist_ok=True)
        script = [f"ENTRY({UPDATE})", "SECTIONS {"]
        script += [f' .function_{i} 0x{address:x} : {{ KEEP(*(i.{name})) }}'
                   for i, (name, address) in enumerate(ENTRIES.items())]
        script += [" /DISCARD/ : { *(*) }", "}",
                   'FUN_0023f294 = 0x23f294;', 'FUN_002d37d0 = 0x2d37d0;']
        path = folder / "effect.ld"
        path.write_text("\n".join(script) + "\n")
        elf = folder / "effect.elf"
        command = [shutil.which("arm-none-eabi-ld"), "--no-warn-mismatch", "--gc-sections", "-T", str(path),
                   *[str(ROOT / r["object"]) for r in records], "-o", str(elf)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
        (folder / "link.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("effect behavior link failed: " + result.stderr)
        report = {"context": context, "command": command, "elf": str(elf.relative_to(ROOT)),
                  "elf_sha256": digest(elf), "script_sha256": digest(path),
                  "limits": "Behavior only; setter dependency bodies and original byte matching are not established."}
        text = json.dumps(report, indent=2) + "\n"
        (folder / "build.json").write_text(text)
        (out / "build.json").write_text(text)
        return elf
