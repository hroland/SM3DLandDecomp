"""Build the actual collider source for comparison with the pinned EU program.

This separate-address analysis ELF executes recovered path/vector helpers,
query wrappers, the director query, remaining pinned original dependencies and
selected intercepted engine callbacks (the global kit accessor and the
director's virtual query engine). It is never used to produce game images.
"""

import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from matching import ROOT, compile_source, input_digest, digest
from verify_elf import read_references, read_recovered_references, EU_SHA256

RESOLVE = "_ZN2al8Collider7resolveERKN4sead7Vector3IfEE"
CENTER = "_ZNK2al8Collider10calcCenterEPN4sead7Vector3IfEE"
COLLECT = "_ZN2al8Collider15collectContactsEPNS_16CollisionContactEj"
FINALIZE = "_ZN2al8Collider16finalizeContactsEPNS_16CollisionContactE"
COUNT = "_ZNK2al17CollisionDirector14getResultCountEv"
RESULT = "_ZNK2al17CollisionDirector9getResultEj"
SWEEP = "_ZN2al8Collider16sweepShapeChangeEPNS_13CollisionPathEPN4sead7Vector3IfEEPfPNS_16CollisionContactEj"
RESPONSE = "_ZN2al8Collider15respondContactsEPNS_16CollisionContactEPN4sead7Vector3IfEES6_bj"
QUERY_SPHERE = "_ZN2al17CollisionDirector11querySphereEPKN4sead7Vector3IfEEjf"
DEFAULT_BUFFER = "_ZNK2al17CollisionDirector23getDefaultContactBufferEPPNS_16CollisionContactEPj"
SET_FILTER_A = "_ZN2al17CollisionDirector15setQueryFilterAEj"
SET_FILTER_B = "_ZN2al17CollisionDirector15setQueryFilterBEj"
PARTS_DELTA = "_ZNK2al14CollisionParts17calcPositionDeltaEPN4sead7Vector3IfEEPKS3_"
ENTRIES = {RESOLVE: 0x800000, CENTER: 0x803000,
           "FUN_0025c824": 0x804000, "FUN_0025c790": 0x805000,
           "FUN_0025c7f8": 0x806000, "FUN_001da3ac": 0x806100,
           "_ZN2nn4math5ARMv610VEC3AddAsmEPNS0_4VEC3EPKS2_S5_": 0x807000,
           "_ZN2nn4math5ARMv610VEC3SubAsmEPNS0_4VEC3EPKS2_S5_": 0x807100,
           "_ZN2nn4math5ARMv610VEC3MulAsmEPNS0_4VEC3EPKS2_f": 0x807200,
           "FUN_0027cca0": 0x807300,
           COLLECT: 0x808000, FINALIZE: 0x809000,
           "FUN_00334298": 0x80A000, "FUN_001d43c0": 0x80A100,
           "FUN_00262dd4": 0x80A200, COUNT: 0x80A300, RESULT: 0x80A400,
           "FUN_0023fa8c": 0x80B000, "FUN_0023fb04": 0x80B100,
           "FUN_0026f71c": 0x80B200,
           SWEEP: 0x80C000, RESPONSE: 0x80D000,
           "FUN_0025c780": 0x80E000, "FUN_0033745c": 0x80E100,
           "FUN_0026ffc8": 0x80E200, "FUN_0033162c": 0x80E300,
           "FUN_001676e0": 0x80F000, "FUN_002673b0": 0x80F100, "FUN_0025c9f8": 0x80F200,
           QUERY_SPHERE: 0x80F300, DEFAULT_BUFFER: 0x80F400,
           SET_FILTER_A: 0x80F500, SET_FILTER_B: 0x80F600,
           "FUN_0027d5c4": 0x80F700, "FUN_0027ccbc": 0x80F800, "FUN_0027306c": 0x80F900,
           "FUN_00331f18": 0x80FA00, PARTS_DELTA: 0x80FB00, "FUN_0027cb9c": 0x80FC00}


def prepare():
    if digest(ROOT / "code.bin") != EU_SHA256:
        raise ValueError("wrong EU executable")
    out = ROOT / "Build/headless/collision"
    out.mkdir(parents=True, exist_ok=True)
    with (ROOT / "Build/matching/matching.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        headers = [p for directory in (ROOT / "Include", ROOT / "Library")
                   for p in directory.rglob("*")
                   if p.is_file() and p.suffix in (".h", ".hpp", ".inc")]
        headers += [p for version in ("4.1/b791", "4.0/b902")
                    for p in (ROOT / ".local/toolchains" / version / "include").rglob("*") if p.is_file()]
        records = [compile_source(ROOT / name, input_digest(headers)) for name in
                   ("Source/al/Collision/ColliderResolution.cpp", "Source/al/Collision/Collider.cpp",
                    "Source/al/Collision/CollisionPath.cpp", "Library/nnsdk/Source/math/math_VEC3.cpp",
                    "Source/al/Collision/ColliderContacts.cpp", "Source/al/Collision/CollisionQuery.cpp",
                    "Source/al/Collision/CollisionDirectorQuery.cpp",
                    "Source/al/Collision/ContactClassification.cpp",
                    "Source/al/Collision/ContactVectorMath.cpp",
                    "Source/al/Collision/ColliderSweep.cpp", "Source/al/Collision/ColliderResponse.cpp",
                    "Source/al/Collision/CollisionContactResponse.cpp",
                    "Source/al/Collision/CollisionPartsMotion.cpp", "Source/al/Math/VectorUtil.cpp",
                    "Library/nnsdk/Source/math/math_MTX34.cpp")]
        if any(r["returncode"] for r in records):
            raise RuntimeError("collider source did not compile")
        context = {"compile_records": records, "tool_sha256": digest(Path(__file__)),
                   "references_sha256": digest(ROOT / "Data/RecoveredFunctions.json"),
                   "symbols_sha256": input_digest(list((ROOT / "Symbols").rglob("*.sym"))),
                   "limits": "Behavior analysis only; recovered resolve/center/path/vector/contact/query/director/accessor/normalization/platform-motion source, remaining pinned original dependencies and intercepted engine callbacks."}
        folder = out / hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]
        folder.mkdir(exist_ok=True)
        script = [f"ENTRY({RESOLVE})", "SECTIONS {"]
        script += [f' .function_{i} 0x{address:x} : {{ KEEP(*(i.{name})) }}'
                   for i, (name, address) in enumerate(ENTRIES.items())]
        script += [" /DISCARD/ : { *(*) }", "}"]
        refs = read_references(ROOT / "Symbols")
        refs.update(read_recovered_references(ROOT / "Data/RecoveredFunctions.json"))
        aliases = {"FUN_0023eda8": COLLECT, "FUN_001eaa44": FINALIZE,
                   "FUN_001ea8a0": SWEEP, "FUN_0023e928": RESPONSE}
        script += [f'{json.dumps(name)} = 0x{address:x};' for name, (address, _) in refs.items()
                   if name not in ENTRIES and name not in aliases]
        script += [f'{json.dumps(name)} = {json.dumps(target)};' for name, target in aliases.items()]
        path = folder / "collision.ld"
        path.write_text("\n".join(script) + "\n")
        elf = folder / "collision.elf"
        command = [shutil.which("arm-none-eabi-ld"), "--no-warn-mismatch", "--gc-sections", "-T", str(path),
                   *[str(ROOT / r["object"]) for r in records], "-o", str(elf)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
        (folder / "link.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("collider behavior link failed: " + result.stderr)
        report = {"context": context, "command": command, "elf": str(elf.relative_to(ROOT)),
                  "elf_sha256": digest(elf), "script_sha256": digest(path),
                  "limits": "Original dependency bodies are analysis inputs only; no whole-game or byte-match claim."}
        text = json.dumps(report, indent=2) + "\n"
        (folder / "build.json").write_text(text)
        (out / "build.json").write_text(text)
        return elf
