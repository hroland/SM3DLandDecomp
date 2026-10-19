"""Verify real upstream source or run/resume the local EU Ghidra export."""

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
BUILD = ROOT / "Build/headless"
EU_SHA256 = "e1d7e188ff88467df776c17cec45c44857fadf5b699944baa8cddcae7d939e64"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_input():
    manifest = json.loads((LOCAL / "analysis/input.json").read_text())
    if manifest["title_id"] != "0004000000053F00":
        raise ValueError("analysis target is not the EU title")
    if manifest["code_sha256"] != EU_SHA256 or digest(ROOT / "code.bin") != EU_SHA256:
        raise ValueError("EU code differs from the pinned extraction")
    if digest(LOCAL / "analysis/code.elf") != manifest["elf_sha256"]:
        raise ValueError("analysis ELF changed; prepare and validate it again")
    return manifest


def verify():
    manifest = check_input()
    compiler = shutil.which("arm-none-eabi-g++")
    if not compiler:
        raise RuntimeError("arm-none-eabi-g++ is required for behavior verification")
    BUILD.mkdir(parents=True, exist_ok=True)
    command = [compiler, "-mcpu=mpcore", "-marm", "-mfloat-abi=soft", "-std=c++11",
               "-O2", "-fwrapv", "-ffreestanding", "-fno-exceptions", "-fno-rtti",
               "-fno-unwind-tables", "-fno-asynchronous-unwind-tables", "-DNON_MATCHING=",
               "-IInclude", "-ILibrary/RedPepper-Headers/Include", "-nostdlib",
               "-Wl,-T,Tools/tests/nerve_link.ld", "Source/al/Nerve/NerveKeeper.cpp",
               "-o", "Build/headless/nerve_recovered.elf"]
    # Invalidate previous evidence before attempting a new build or test run.
    (BUILD / "verification.json").write_text(json.dumps({"passed": False, "status": "running"}) + "\n")
    registration_command = command[:command.index("-Wl,-T,Tools/tests/nerve_link.ld")] + [
        "-ILibrary/sead/Include", "-ILibrary/nnsdk/Include", "-ffunction-sections", "-fdata-sections",
        "-Wl,--gc-sections,-T,Tools/tests/state_registration_link.ld",
        "-Wl,--undefined=_ZN2al14NerveStateCtrl13registerStateEPNS_14NerveStateBaseEPKNS_5NerveEPKc",
        "Source/al/Nerve/NerveFunction.cpp", "Source/al/Nerve/NerveStateCtrl.cpp",
        "-o", "Build/headless/state_registration_recovered.elf"]
    array_command = command[:command.index("-Wl,-T,Tools/tests/nerve_link.ld")] + [
        "-DREDPEPPER_USE_RUNTIME_FALLBACK",
        "-Wl,-T,Tools/tests/array_ctor_link.ld", "Source/Runtime/ArrayCtor.cpp",
        "-o", "Build/headless/array_ctor_recovered.elf"]
    commands = [command, registration_command, array_command]
    for index, build_command in enumerate(commands):
        build = subprocess.run(build_command, cwd=ROOT, capture_output=True, text=True)
        (BUILD / f"compile-{index}.log").write_text(build.stdout + build.stderr)
        if build.returncode:
            print(build.stdout + build.stderr)
            return build.returncode
    suite = unittest.defaultTestLoader.discover(str(ROOT / "Tools/tests"))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(stream.getvalue(), end="")
    classes = {"keeper": sys.modules["test_nerve_arm"].NerveARMTest,
               "state_registration": sys.modules["test_state_registration_arm"].StateRegistrationARMTest,
               "array_ctor": sys.modules["test_array_ctor_arm"].ArrayCtorARMTest,
               "actor": sys.modules["test_actor_movement_arm"].ActorMovementARMTest,
               "effect": sys.modules["test_effect_update_arm"].EffectUpdateARMTest,
               "collision": sys.modules["test_collision_resolution_arm"].CollisionResolutionARMTest,
               "collision_contacts": sys.modules["test_collision_contacts_arm"].CollisionContactsARMTest}
    comparisons = {name: cls.comparisons for name, cls in classes.items()}
    paths = [ROOT / "Source/al/Nerve/NerveKeeper.cpp", ROOT / "Include/types.h",
             ROOT / "Tools/tests/test_nerve_arm.py", ROOT / "Tools/tests/nerve_link.ld",
             ROOT / "Tools/headless.py", BUILD / "nerve_recovered.elf"]
    paths += sorted((ROOT / "Library/RedPepper-Headers/Include/al/Nerve").glob("*.h"))
    paths += sorted((ROOT / "Tools/tests").glob("*.py"))
    paths += [ROOT / "Tools/verify_elf.py", ROOT / "Tools/source_aliases.py",
              ROOT / "Tools/whole_build.py", ROOT / "Data/SourceAliases.json"]
    paths += [ROOT / "Data/RecoveredFunctions.json",
              ROOT / "Tools/patches/RedPepper-Headers-nerve-state-registration.patch"]
    paths += [ROOT / "Source/al/Nerve/NerveFunction.cpp", ROOT / "Source/al/Nerve/NerveStateCtrl.cpp",
              ROOT / "Source/Stubs.c", ROOT / "Tools/tests/state_registration_link.ld",
              BUILD / "state_registration_recovered.elf"]
    paths += [ROOT / "Source/Runtime/ArrayCtor.cpp", ROOT / "Tools/tests/array_ctor_link.ld",
              BUILD / "array_ctor_recovered.elf"]
    paths += [ROOT / "Tools/actor_behavior.py", ROOT / "Tools/inline_arm_leaf.py",
              ROOT / "Tools/matching.py", ROOT / "Source/al/LiveActor/LiveActor.cpp",
              ROOT / "Source/al/LiveActor/LiveActorFunction.cpp", ROOT / "Source/al/LiveActor/MovementNoop.cpp",
              classes["actor"].artifact, BUILD / "actor/build.json"]
    paths += [ROOT / "Tools/effect_behavior.py", ROOT / "Source/al/Effect/EffectUpdate.cpp",
              ROOT / "Source/al/Effect/EffectHandle.cpp",
              ROOT / "Library/nnsdk/Source/math/math_MTX34.cpp",
              classes["effect"].artifact, BUILD / "effect/build.json"]
    paths += [ROOT / "Tools/collision_behavior.py", ROOT / "Source/al/Collision/Collider.cpp",
              ROOT / "Source/al/Collision/ColliderResolution.cpp", ROOT / "Source/al/Collision/CollisionPath.cpp",
              ROOT / "Library/nnsdk/Source/math/math_VEC3.cpp",
              ROOT / "Library/RedPepper-Headers/Include/al/Collision/Collider.h",
              ROOT / "Library/RedPepper-Headers/Include/al/Collision/CollisionPath.h",
              ROOT / "Library/RedPepper-Headers/Include/al/Collision/CollisionContact.h",
              classes["collision"].artifact, BUILD / "collision/build.json"]
    paths += [ROOT / ("Source/al/Collision/" + name + ".cpp") for name in
              ("ColliderContacts", "CollisionQuery", "CollisionDirectorQuery",
               "ContactClassification", "ContactVectorMath", "ColliderSweep",
               "ColliderResponse", "CollisionContactResponse")]
    paths += [ROOT / "Library/RedPepper-Headers/Include/al/Collision/CollisionDirector.h",
              ROOT / "Library/RedPepper-Headers/Include/al/LiveActor/LiveActorKit.h",
              ROOT / "Library/RedPepper-Headers/Include/al/Collision/CollisionParts.h",
              ROOT / "Library/RedPepper-Headers/Include/al/Math/VectorUtil.h",
              ROOT / "Source/al/Collision/CollisionPartsMotion.cpp", ROOT / "Source/al/Math/VectorUtil.cpp",
              ROOT / "Tools/branch_nop.py"]
    report = {
        "passed": result.wasSuccessful(), "tests": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "successful_arm_comparisons": sum(comparisons.values()),
        "successful_arm_comparisons_by_suite": comparisons,
        "state_registration_comparisons_by_function": classes["state_registration"].comparisons_by_function,
        "actor_comparisons_by_function": classes["actor"].comparisons_by_function,
        "effect_comparisons_by_function": classes["effect"].comparisons_by_function,
        "collision_comparisons_by_function": classes["collision"].comparisons_by_function,
        "collision_contact_comparisons_by_function": classes["collision_contacts"].comparisons_by_function,
        "behavior_compilers": {"keeper/state/array_fallback": "GCC", "actor": "ARMCC 4.1 build 791 with GNU ld",
                               "effect/collision": "ARMCC 4.1 build 791, SDK 4.0 build 902, GNU ld"},
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target": "Super Mario 3D Land EU", "title_id": manifest["title_id"],
        "code_sha256": EU_SHA256, "compiler_command": command, "compiler_commands": commands,
        "compiler_version": subprocess.check_output([compiler, "--version"], text=True).splitlines()[0],
        "artifacts_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths},
        "byte_matching_build": False, "full_game_decompilation_complete": False,
        "limitations": "Keeper/state/array, actual ARMCC actor, effect and collision source are tested. Actor callbacks and two effect setters are intercepted. Collision executes actual rebuilt resolve/center/path/vector/contact/query/classification/sweep/response source, the global director wrapper, both query wrappers, the director query, the default-buffer accessor, normalize-or-zero, projection and platform-motion source plus remaining pinned original math dependencies; only the global kit accessor and the director's virtual query engine are intercepted (engine hook records results pointer, query info and director filters). Query filter setters have no separate original body and are exercised only through the wrappers. Contact tests cover member-copy padding, capacity, count reloads, shared tails, classification thresholds, pre-sweep filter snapshots/completion, response extrema/carry, optional outputs, helper aliasing, signed result recycling, filter reset, threshold bit patterns, normalization length return and platform matrix aliasing. Pre-sweep and response bodies execute without interceptions. New collision cases cover finite inputs only; the engine body itself is not verified. GCC -fwrapv preserves ARM integer wrap. Behavior is not exact-byte or whole-game evidence; exact-byte checks are separate."
    }
    (BUILD / "tests.log").write_text(stream.getvalue())
    (BUILD / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("passed", "tests", "successful_arm_comparisons", "byte_matching_build")}))
    return 0 if result.wasSuccessful() else 1


def active_job():
    path = LOCAL / "analysis/job.json"
    if not path.exists():
        return None
    job = json.loads(path.read_text())
    process = subprocess.run(["ps", "-p", str(job["pid"]), "-o", "command="],
                             capture_output=True, text=True)
    if process.returncode == 0 and "ghidra" in process.stdout.lower():
        return job
    return None


def analyze():
    check_input()
    job = active_job()
    if job:
        print(json.dumps({"status": "already-running", **job}))
        return 0
    launcher = LOCAL / "ghidra_12.1.3_PUBLIC/support/analyzeHeadless"
    java_home = Path("/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home")
    if not launcher.is_file() or not java_home.is_dir():
        raise RuntimeError("local Ghidra 12.1.3 and JDK 25 are required")
    # Ghidra project URLs reject path components beginning with a dot.
    project = BUILD / "ghidra-projects"
    project.mkdir(parents=True, exist_ok=True)
    export = LOCAL / "analysis/ghidra"
    command = [str(launcher), str(project), "RedPepperEU"]
    if (project / "RedPepperEU.gpr").exists():
        command += ["-process", "code.elf", "-noanalysis"]
    else:
        command += ["-import", str(LOCAL / "analysis/code.elf"),
                    "-processor", "ARM:LE:32:v6", "-cspec", "default"]
    command += ["-scriptPath", str(ROOT / "Tools"),
                "-postScript", "ImportSymbols.java", str(ROOT / "Symbols"),
                "-postScript", "ExportAnalysis.java", str(export),
                "-max-cpu", "4", "-log", str(LOCAL / "analysis/ghidra.log")]
    log_path = LOCAL / "analysis/headless.log"
    env = dict(os.environ, JAVA_HOME=str(java_home))
    with log_path.open("a") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    job = {"pid": process.pid, "command": command, "log": str(log_path),
           "started_utc": datetime.now(timezone.utc).isoformat(), "code_sha256": EU_SHA256}
    (LOCAL / "analysis/job.json").write_text(json.dumps(job, indent=2) + "\n")
    print(json.dumps({"status": "started", **job}))
    return 0


def status():
    job = active_job()
    summary_path = LOCAL / "analysis/ghidra/summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else None
    print(json.dumps({"active_job": job, "export_summary": summary,
                      "log": str(LOCAL / "analysis/headless.log")}, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "analyze", "status"))
    args = parser.parse_args()
    LOCAL.mkdir(exist_ok=True)
    with (LOCAL / "headless.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return {"verify": verify, "analyze": analyze, "status": status}[args.action]()


if __name__ == "__main__":
    sys.exit(main())
