# Super Mario 3D Land EU continuation

The active checkout is `/Users/hroland/Projects/decompilation/RedPepper`, cloned
from https://github.com/3dsdecomp/RedPepper, with all five submodules initialized.
Upstream HEAD: `6bd828b729f2442d18e7a586b6858a5fc6aeb6cd`. `../May 2026/` is reference-only;
do not modify it or replace this project's Source/ with its separate recovery.
No applicable AGENTS.md was found. Work headlessly and keep changes local.

## Progress accounting and user's correction

The inherited upstream code.bin baseline is **4.0704% (126,044/3,096,576 bytes)**,
as recorded in `Data/Code.json`. We already inherited that implementation.
`Tools/progress.py` counts equal four-byte words across the entire image,
including data and padding. It does not require whole-function matches.
An actual whole-source **partial GNU-linked image now exceeds that baseline**:
**4.6787% (144,880/3,096,576 bytes)** under the same four-byte-word comparison.
It is at `Build/whole-runtime/711d8abc001ac850/code.bin`, not `Build/code.bin`.
The inherited badge is preserved as history. The local image contains explicit
stubs and extra code beyond the stock extent; it is not a working game rebuild.
See the latest October 19 placement-args checkpoint below for current provenance.

The lower local matching percentages were incorrectly presented as overall
progress. They measured independent exact-function verification in .text.
The user explicitly objected to redundant baseline work on October 14. Report
these as diagnostic coverage, separate from upstream progress and new recovery.
Never add their percentages to the badge or describe them as a restart from zero.
Do not fabricate a sparse/zero image or copy stock instructions to raise a badge.

The full scan at 2026-10-14T19:06:37Z compiled **125/125 actual source units**.
It verified **442 symbol entries (423 unique entries), 16,636 unique .text bytes**,
**0.6031%** of the 2,758,532-byte .text section. Most are inherited source.
`Build/matching/progress.json` is that historic pinned snapshot, not a full game.
Its source/header hashes remain part of its evidence; later headers have changed.
Focus subsequent batches on missing game routines and checks of changed source.
`--source` runs now write separate targeted reports instead of overwriting it.

## Input evidence

The user's EU CIA and decrypted EU cartridge were independently extracted with
Project_CTR ctrtool; both decompressed executable buffers are identical:

- Title ID `0004000000053F00`; product code `CTR-P-AREP`.
- Size 3,096,576 bytes.
- SHA-256 `e1d7e188ff88467df776c17cec45c44857fadf5b699944baa8cddcae7d939e64`.
- .text `0x00100000..0x003a1784`; .rodata `0x003a2000`; .data `0x003e1000`.
- CIA ExeFS/RomFS hash checks passed. Extraction logs contain private material.

`code.bin` is pinned stock input. `.local/analysis/input.json` records the layout;
`.local/input/provenance.json` records original/extractor/repository hashes.
Independent extractions remain in `.local/input/eu/` and `eu-cartridge/`.
All original assets, extraction logs, .local and build artifacts are excluded
from Git. Preserve these inputs and never track or publish them.

## Original compiler and verification

ARMCC now runs headlessly on macOS through Wibo 1.2.0. Game/al/sead/LMS use
4.1 build 791; SDK source uses 4.0 build 902. `Tools/bootstrap_armcc.py` validates
hash-pinned public compiler/Wibo downloads and extracted files. Provenance is
`.local/toolchains/provenance.json`.

- Compiler archive SHA-256:
  `bda0cea5b13a9c3f08322fa76f9f9dcda59bda290f57f1a06e05cd80044fafdb`.
- Wibo SHA-256:
  `2b3000ef6a7a490c24ccd71967735ae0005e218922e51806cca1b8d77fd3cf7c`.

Use the compiler's include directory with `-I`, not a `--sys_include PATH` pair.
Locale C is required by this runtime; CP932 strings/data still need investigation.
Only exact stock-byte checks count as matches. The initial decomp.me package
lacks the separate assembler/linker tools and standard link libraries. A full
official MDK 4.22 package has since been downloaded and extracted; its tools
and libraries are under `.local/toolchains/mdk422`. Original armlink 4.1 build
791 runs through Wibo but cannot link without a license file (L9932E).
The upstream original-linker CMake/scatter build remains unestablished. Do not
repeat the license failure without new license or supported setup evidence.

`Tools/matching.py` compiles actual repository source, excludes Stubs.c and
links per-function analysis ELFs at original EU addresses with GNU ARM ld.
Strict ARMCC -S to GNU assembly translation handles the few assembler units;
unknown directives are rejected. Compile caches bind source/header/tool hashes
and preserve previous builds when inputs change.

Unknown direct calls may be resolved from stock instructions only when the
entire non-relocation body and branch form already agree. Known targets cannot
be overridden, conflicts are rejected, and unknown absolute data addresses are
not inferred. The independent `Tools/verify_elf.py` then checks emitted bytes,
original address/size, stub exclusion and outstanding allocated relocations.
External dependency bodies remain at stock addresses; per-function matching is
not a complete source rebuild. Matching reports never automatically edit ranks.

## Source recovery milestones

`NerveKeeper::update` now dispatches the active mEndNerve rather than the pending
mNerve cleared by tryChangeNerve. The transfer stores pending=null before active.
With ARMCC, constructor (76 bytes), update (160), setNerve (68) and getter (20)
are exact at the EU addresses. Update's NON_MATCHING marker was removed and its
rank changed m to O with evidence. GCC evidence is behavior-only: 930 ARM cases.

`initNerveState` was restored from its stub in Source/al/Nerve/NerveFunction.cpp.
It calls virtual init before reacquiring the host's keeper/controller and
registering the state. GCC passes 700 initialization/registration comparisons
(423 initializer, 277 shared-tail entry). The initializer remains NON_MATCHING.
Its original 0x001cacb4..0x001cad2c body overlaps the independent registration
entry 0x001cad00..0x001cad2c; never sum overlapping ranges twice.

The first recovery milestone established **340 distinct bytes** (historic snapshot):

- LiveActor::makeActorDead, 0x0027d250, 260 bytes, restored from a stub in this
  batch. It clears velocity, marks dead, disables sensors/clipping/collision/model,
  clears effects/audio, removes execution requests and synchronizes subactors.
  All original bytes and direct call destinations match. Rank U to O.
- LiveActor::getBaseMtx, 0x003375dc, 24 bytes; rank U to O.
- alModelCtr::getBaseMtx, 0x0025c754, 12 bytes; returns a matrix at offset 0x4c
  from the opaque pointer at model offset 8. Name is descriptive, not original.
- NerveStateCtrl::registerState, 0x001cad00, 44 bytes; stores state/nerve/name
  and advances the count. Name is descriptive; no invented Symbols rank.

AudioKeeper::stopAll, removeFromClipping and removeFromExecutorMovement were
descriptive call dependencies at this checkpoint. stopAll is now recovered in
the later dependency batch; the two removal bodies remain unrecovered.
ActorExecuteInfo now preserves opaque fields through the pointer at offset 0x18;
its draw-participation interpretation is provisional. New header edits are saved
in Tools/patches/RedPepper-Headers-actor-lifecycle.patch. Earlier model/state
header patches are retained alongside it. Preserve submodule changes and patches.

Source SHA-256 values at the first lifecycle checkpoint (later manifests pin later sources):
- `Source/al/LiveActor/LiveActor.cpp`: `d5cb71e0e7941be1c3e982c4ef3f3f40636a46857acaaa48e396b244aa321371`.
- `Source/al/LiveActor/LiveActorFunction.cpp`: `9216ba6443c29ed310edc7e953f1818cc6c52bb1ba51d127c4c1ff640d73f029`.
- `Source/al/Model/alModelCtr.cpp`: `781c5823a9efe728a8658b2a6922870c0637c17bc7188c4caef86b03710e12f9`.
- `Source/al/Nerve/NerveStateCtrl.cpp`: `fea9cd1a8ff9dadf11bec40f5c82afb1b7eb2d2672cd9011e8ba40ec0d79ee79`.

`Build/matching/milestones/2026-10-14-source-recovery.json` contains original
addresses, comparison/compile/link/source/header patch hashes and provenance.
Manifest SHA-256: `c37f00916cf5af135638f05b7ea2aa81bf1631423b498bfb8e1ab3ab719cfdad`.
Targeted report SHA-256: `3163ba924d48ce73d8773f73ff64cb1058fbb663234e3f6ba1988e0737820551`.
Full scan report SHA-256: `65a52dba8be7ba3334c7aa5d127d8e2ebc39135bbb573109810da6c7624332c0`.
The targeted three-unit report verifies 24 entries/900 bytes including inherited
controller routines; that is a targeted verification result, not new recovery.

The suite at that checkpoint passed 23 tests and 1,630 ARM comparisons. The
current suite passes **53 tests and 4,270 ARM comparisons**; the October 19
checkpoint records the current report and its hashes. GCC behavior evidence is
not ARMCC byte matching.

## October 14 actor lifecycle recovery

A further **912 distinct source bytes** now pass independent exact-byte checks:

- LiveActor::makeActorAppeared, 0x0027ea40, 364 bytes; restored from a stub, U to O.
- LiveActor::startClipped, 0x002795c0, **228 bytes**; restored, U to O.
- LiveActor::endClipped, 0x002797f4, 312 bytes; restored, U to O.
- al::updateHitSensorsAll, 0x0026e13c, 8 bytes; descriptive wrapper name, recorded
  in Data/RecoveredFunctions.json without inventing an upstream symbol rank.

Cumulative newly recovered exact source now totals **1,252 distinct bytes** in
eight functions, separate from inherited source certification. NerveKeeper's
160-byte update correction is tracked separately as a fix to an existing routine.
The inherited raw-word code.bin baseline remains **4.0704%**; a local full image
has not been built, so do not add these counts/percentages to that badge.

startClipped's old 256-byte Symbols record included 28 bytes of the next unrelated
function. Disassembly proves its two terminal paths at 0x0027969c (tail branch)
and 0x002796a0 (POP r4,pc), followed by the independently listed next entry
0x002796a4. The entry range is 228 bytes. Ghidra's first chunk agrees but also
includes a separate subactor tail; do not count that tail again. The boundary
review is .local/analysis/reviewed/actor-clipping-boundaries.json. Symbols size
was corrected with this evidence before exact comparison, not shortened to
hide an instruction mismatch.

The original appearance/clipping routines call small flag queries rather than
reading every flag directly. ARMCC emits the correct caller layouts when these
calls are retained. Armlink's documented --inline optimization replaces a BL
to a 4/8-byte A32 leaf with its sole non-return instruction. Tools/inline_arm_leaf.py
implements only a conservative subset for GNU-linked analysis ELFs, sourcing
instructions exclusively from compiled repository helper objects. It reads no
stock binary. PC/LR/SP-sensitive instructions, unknown/relocated bodies, Thumb,
tail B/BLX, conflicting conditions and interior-function call addends are rejected.
Five focused tests cover permitted leaves and unsafe cases. This is **ARMCC plus
GNU ld and a source-derived optimization**, not an invocation of original armlink.
The independent emitted-byte comparison still gates every matching claim.
Reference: https://documentation-service.arm.com/static/5f733e2d1b758617cd956b36?token=
(pages 77-80, sections on function inlining/conditions and branch-to-NOP).

ActorLightCtrl's reviewed prefix has a mode at offset 8; only modes 1 and 0
register the draw pointer from ActorExecuteInfo offset 0x18. Complete class size,
remaining fields and draw argument type are unknown. Header helper names are
descriptive where upstream names were absent; effect pause/resume, model show,
audio activation and draw/clipping registration dependency bodies remain to be
recovered. All callback ordering and original direct call targets in the four
new functions are byte-verified.

Latest evidence: Build/matching/milestones/2026-10-14-actor-lifecycle.json.
Manifest SHA-256: `083f81a12a0e226eba00bc28d0b05988687930cfb0fef05657e23b8d0c1e4f8b`.
Targeted report SHA-256: `4594f648d8838a5129e95ba80e44f4580e53c480c34980d725bf6f3d1000fe81`.
Build/matching/actor-lifecycle-progress.json checks the two changed units:
30 matched entries/1,900 bytes (**0.0689% of .text**, targeted verification only).
It preserves the earlier whole-source snapshot. Prior manifests remain unchanged.
The new Tools/patches/RedPepper-Headers-lifecycle-recovery.patch is cumulative
against the clean headers submodule, including the new Light header. Preserve
it and the uncommitted header edits; do not layer older partial patches on top.

A bounded official-tool search initially found no full installed toolchain in this or the
reference checkout. Keil's legacy download endpoint returned HTTP 500, and the
current evaluation page redirects to the newer MDK product. Original armlink,
armar/fromelf and runtime libraries remain absent. Do not retry the same endpoints
on every batch without new evidence. GNU single-leaf inlining resolved the current
source issue, so independent recovery can proceed. A complete source/link build
was still required at that checkpoint. The later official download and actual
partial image below supersede that missing-download state, not the requirement
for a complete independently verified game before declaring completion.

## October 14 lifecycle dependencies and real partial image

Four more routines are recovered from actual source and independently byte-exact
in the targeted original-address verification ELFs:

- AudioKeeper::activate, 0x001bf134, 12 bytes.
- AudioKeeper::stopAll, 0x0024ad94, 32 bytes.
- EffectKeeper::pauseAll, 0x0024adcc, 60 bytes.
- EffectKeeper::resumeAll, 0x001bfaa4, 60 bytes.

All four method names are descriptive; original names are unknown. AudioKeeper's
reviewed prefix has active at offset 0 and an opaque control pointer at 0xc.
EffectKeeper's reviewed prefix is a PtrArray at offset 0; its loop rereads the
count and buffer after callbacks. Complete class sizes remain unknown. Their
lower-level callbacks remain unrecovered. New source bytes: **164**, cumulative
newly recovered distinct game/source bytes: **1,416**. Keeper's 160-byte update
fix remains separate; inherited verification and supplied runtime are separate.
These targeted ELFs resolve unimplemented dependencies to stock addresses; the
whole partial image instead calls actual linked implementations or explicit
stubs. Do not assume the whole image preserves every targeted call destination.

Source hashes:
- `Source/al/Audio/AudioKeeper.cpp`: `f6f10b41b3b427705d5f1e73d05bd261612fd0ec8c242495e900a5c30872ef39`.
- `Source/al/Effect/EffectKeeper.cpp`: `7102ebf726352e8db26dd562afa8ba87743a75c6dcaf4824b6edee2a5069c642`.

The new cumulative header patch is
`Tools/patches/RedPepper-Headers-lifecycle-dependencies.patch`, SHA-256
`9492b99eb257e97f30ca8108403f8507ac057272fd85930c5676251a36ee024a`.
It includes the untracked Light header and applies cleanly to the headers
submodule HEAD. Apply it to a clean base, not over older cumulative patches.
Nine newly exposed lifecycle dependencies were added as clearly marked standard
NOP placeholders in Source/Stubs.c. They are not recovered or byte-matching code.

The user explicitly authorized downloading the full compiler package. The public
official download `https://www.keil.com/files/eval/mdk422.exe` succeeded:
423,929,584 bytes, SHA-256
`4c1a4f0448489a244fdfde32f01a07362b6ad0d8ef008b9b98ec20cee6be10c0`.
Official notes at `https://www.keil.com/update/relnotes/MDK422.htm` identify
RealView 4.1.0.791. Only ARM/BIN40, ARM/RV31 and the license document were
extracted headlessly with bsdtar; the GUI installer was not run. Provenance for
1,343 extracted files is `.local/toolchains/mdk422/provenance.json`, SHA-256
`fdd9fdab878abb4f1eb5b940a0d48ec322458151222a1b13abee8ae3e50b96a0`.

- `armlib/c_4.l` SHA-256: `643af4a35cf6b11d3cfa26fc1cf7c8fde2982fbdda0d8a32747bfabd6a383d6d`.
- `cpplib/cpprt_4.l` SHA-256: `af94582ef9f66067a1008a93907145cd73ee9f39777838db28ae719b301db01b`.
- Original armlink SHA-256: `92d505775260f4197fb7848a011ee03a746d600faa52b101f7ad02b08f2b3cef`.

Original armlink --vsn reports 4.1 build 791. A minimal link reports L9932E:
no license file for armlink/bsp_armlink, searching C:\flexlm\license.dat.
Exact attempt/log: `Build/runtime/mdk422/armlink-attempt.json` and
`armlink-license.log`. No license activation or bypass was attempted. The free
MDK-Lite edition's documented 32 KB limit is insufficient for this game. The
remaining prerequisite for original armlink is a usable license, not another
copy of the compiler or runtime archives. Do not repeat this failure or download
other versions solely to evade the limit. Continue independent source work.

The supplied cpprt_4.l array constructor at 0x0028eabc is now **64/64 byte exact**
in the actual whole-linked ELF. Its R_ARM_V4BX relocation converts BX r6 to
MOV pc,r6 under GNU --fix-v4bx, corresponding to upstream --arm_only. No stock
instruction is copied. Inherited O rank is restored for the supplied library.
The 60-byte provisional source fallback remains NON_MATCHING, guarded by
REDPEPPER_USE_RUNTIME_FALLBACK and enabled only in behavior tests; normal builds
use the genuine archive. It passes 184 original-vs-GCC ARM cases, with constructor
callbacks intercepted. This is not 64 new game-source bytes.

`Tools/whole_build.py --prepare-only` compiles/caches all **129/129** actual source
units. Initial bare GNU links failed on runtime symbols; the saved 129-object
failure is `Build/whole/a637fb0b5df3ecc5/failure-summary.json`. The newly added
`Tools/whole_runtime_build.py` checks source/header/object/runtime hashes, selects
47 genuine archive members with a relocatable GNU link, then links 128 source
objects (excluding the optional fallback) plus those separate runtime members.
It uses actual upstream/reviewed placements, source-derived leaf inlining and
GNU --fix-v4bx. Exception-table Base/Limit are derived from the emitted section.
No missing dependency receives a stock-address alias, and no stock code/data is
used to produce the image. It is ARMCC + genuine runtime + GNU ld, not armlink.

Final partial image directory: `Build/whole-runtime/8f1c775008d5245c`.
The independent `Tools/verify_image.py` checks ELF type/endian, unresolved strong
symbols/allocated relocations, every raw emitted section, zero inter-section
padding and image extent before comparing words across the pinned stock length.
Three focused tests reject modified code, modified padding and changed extent.
The current 28-test suite passes **1,814 ARM comparisons** (930 keeper, 700 state,
184 optional array fallback). These behavior cases do not establish ARMCC bytes.

The local image's upstream-style word metric is **4.4749%**:
**138,568 equal-word bytes / 3,096,576 stock bytes**, comprising 25,352 bytes in
emitted executable sections, 3,484 in emitted data and **109,732 in linker gaps**.
Equal words in executable sections are not necessarily whole matching functions.
The binary is **3,377,024 bytes**, larger than stock because unmatched code/stubs
live in the upstream garbage region. It is not installable or a working game.
The metric exceeds the inherited 4.0704%; it must not be represented as 4.4749%
of the source newly recovered, or added to earlier exact-function coverage.

Artifact hashes:
- ELF: `ba900f29a32b6eb38e87ba4b587660b26f973b2714cd072e9eca49e858d7cfe5`.
- Partial code.bin: `74fc11364c8bb4bbb84c8e159c0c4945f38f3adf6dc08d508fbf3f3f494cbfbc`.
- Build report: `306b6e7c270f46d493a2855b12433de236eff1e3f580da3ca6805a6ac5d82737`.
- Image comparison: `0e776d206d9ac89521a8835e3ccb2bdb93ee1ad9bca94a522ce9aeb031000ef8`.
- Current suite report: `924990fe08aef3abb3725b69ac26d09b5b8eb6768db26bcae68270096413fe40`.

The complete checkpoint binds source, compiler, headers, runtime archives,
test/checker/linker tools and all reports:
`Build/matching/milestones/2026-10-14-lifecycle-dependencies-and-runtime-link.json`,
SHA-256 `c09e6df732ab85203886de34508264dfe24b4090ea0f60bf698280898b8baedf`.
Earlier milestones remain unchanged. Preserve the successful baseline; do not
re-run whole inherited function scans or rebuild unchanged images for progress.

## October 15 actor movement and collision control flow

The saved movement/collider batch is implemented in the actual checkout:

- LiveActor::movement, 0x0026df44, **504 bytes**: recovered from its stub, all
  original bytes and direct destinations independently exact; rank U to O.
- nn::math::ARMv6::VEC3AddAsm, 0x0027cb48, **28 bytes**: restored in the existing
  nnsdk assembly-source file, assembled with the SDK compiler convention and
  independently exact. Its name is inferred from an existing header declaration
  and the adjacent verified subtraction routine; the name itself is not proven
  by byte equality. Recorded with an explicit 28-byte reference and rank O.
- LiveActor::updateCollider, 0x001ebcec, **168 original bytes**: restored readable
  source and behavior-verified, but ARMCC emits **176 bytes** with different
  tail-call epilogues. It remains NON_MATCHING and is rank M, not byte-exact.

New exact source: **532 bytes** (504 game C++, 28 SDK assembly), cumulative
**1,948 distinct bytes** across 14 routines. The game-source portion is 1,920
bytes; the SDK addition is separate. Keeper's 160-byte correction and the supplied
64-byte runtime helper remain separate. updateCollider receives no exact-byte
credit. Source/stub inventories are not whole-game completeness estimates.

Movement preserves callback order and reloads the dead flag after sensor attack,
nerve update and virtual control. It does not recheck death after the collision
virtual callback. The collision-only update computes a base matrix, obtains the
pose scale and synchronizes the scaled matrix. The light update checks mode 0.
The no-op remnant at 0x26e0cc guards the **shadow** keeper at actor+0x44, not rail
at +0x40. Original helper identities/addresses behind two no-op call remnants
remain unknown. MovementNoop.cpp factors them into explicitly descriptive empty
action/shadow helpers; these helpers are not counted or given original ranks.
Some lower-level argument types, such as material-name pointers, remain inferred.

The conservative source-derived inliner now accepts conditional BL instructions
that ARMCC tags R_ARM_JUMP24, while rejecting actual tail B and BLX. A compiled
return-only helper can become an unconditional legacy MOV r0,r0 NOP. This is an
effect-free instruction under any ordinary call condition. The pass still reads
no stock executable. Its new condition test covers all 15 ordinary conditions;
the actual 504-byte caller comparison independently checks the resulting code.
GNU ld also receives actual compiled helper objects when erased calls retain
undefined hidden symbol names; no arbitrary symbol address is invented.
Reference: the later Arm armlink guide, pages 78-79, documents return-only
functions inlined as NOPs. `.local/research/armlink-user-guide.pdf` is pinned in
the boundary review. This is a source-derived GNU build aid, not original armlink.

`Tools/actor_behavior.py` builds the actual ARMCC movement/collider source into
a separate-address test ELF. The new differential tests pass **248 movement**
and **96 updateCollider** original-vs-rebuilt cases, including optional keepers,
dead/clipped/draw-clipping/material flags, early death at callbacks, matrix
arguments, VFP s0-s2 vector returns, translation results, stack/callee-saved
register preservation and caller-saved clobbering. Dependency callbacks are
intercepted. These tests do not verify the bodies of the unrecovered dependencies.
The current full suite passes **31 tests and 2,158 ARM comparisons**: 930 keeper,
700 state, 184 optional array fallback and 344 actor. The first three suites use
GCC; actor tests use actual ARMCC objects. Exact-byte proofs are separate reports.

Boundary/type evidence is `.local/analysis/reviewed/actor-movement-boundaries.json`,
SHA-256 `9508b944631237f2ebbe7b99b55a7e7eb77507dc5f0b34a9b4ce63ff5d173a23`.
No prior Ghidra annotations or exports were modified or relaunched. The old
May 2026 checkout was inspected only as a read-only reference and supplied no
replacement source for these functions.

The new nnsdk source edit is preserved in `Tools/patches/nnsdk-vector-add.patch`,
SHA-256 `39e80c4bee5fe07f2fe3802b7e9149cbd9cc23f1f1ea3ad0ec236eb4ddfa2fcd`;
it applies cleanly to the SDK submodule HEAD. Header edits are unchanged from the
last cumulative header patch. Preserve both dirty submodules and their patches.
Source hashes at that checkpoint:

- `Source/al/LiveActor/LiveActor.cpp`: `0b13a69be5eab11ea7cc52e31a155234203fab65b90bb9d59ec060641acdcaaf`.
- `Library/nnsdk/Source/math/math_VEC3.cpp`: `d13384f8e026a3261028d18e10f1e105c0a284f5ee1368f4ca3d48351c9d4424`.

After these source changes, **130/130 units compile**. The partial image links
129 source objects plus 47 genuine runtime members. Fifteen newly exposed
movement/collider dependencies are explicitly marked NOP placeholders in
Source/Stubs.c; none is counted as recovered. The initial missing-dependency
link failure is saved at `Build/whole-runtime/0279ade31883beec`. The subsequent
successful build is `Build/whole-runtime/c2e724d86c2ef2e8`.

Independent raw-image audit: **4.4926% (139,116/3,096,576 equal-word bytes)**,
up from 4.4749% in the prior actual image. It comprises 25,832 equal-word bytes
in emitted executable sections, 3,552 in emitted data and **109,732 in linker
padding**. The 548-byte raw-word increase is not the source-recovery byte count.
The image size is **3,377,416 bytes**, including unmatched code/stubs beyond the
stock extent; it remains a partial build, not a working game. All raw sections
and zero linker gaps are checked against the emitted ELF. Original inputs were
not used as code/data buffers or undefined-address aliases in image production.

Artifact hashes:

- ELF: `b1ffc5ddd927530363a428fb6f8fe69c4ce232590ea174a96a919558fd56ea94`.
- Partial code.bin: `b7cd1e95a8541362036c5cdd768c6e6a2f7fe3dc6b681db53a58df9b4a5772f0`.
- Build report: `2344605a5d299b31018f64a0f094ee58c11ab34d6b61c55e293a35e6899489a5`.
- Image comparison: `a454805c059cc4693f4a9fbc2b8fdc288ef24821b80c8b421f0705ba46d592d0`.
- Targeted source report: `86c58978894dfe9a4e76c24243ce32668eefd89a9b91b0ea5d8d0f6fdb497645`.
- Suite report: `d85bac7052c36abb2dc8ad79f589eb5fc48dfc98dcd82ac04ff730eaa3d30096`.

The complete immutable checkpoint is
`Build/matching/milestones/2026-10-15-actor-movement.json`, SHA-256
`26b218aca6144fd7609ab3d029216b41e2b85ff5999fbd4c5a572ea39bb52c66`.
It binds input/source/header/compiler/library/tool/report hashes, new exact
ranges, provisional status and next tasks. Source/tool snapshots are retained
under the sibling `2026-10-15-actor-movement-sources` directory. Earlier
checkpoints and the inherited upstream badge are unchanged. All work is local.

## October 15 movement-keeper dependency completion

Five further routines now pass independent original-address exact-byte checks,
adding **480 newly exact source bytes**:

- LiveActor::updateCollider, 0x001ebcec, **168 bytes**. The prior 176-byte
  provisional implementation is now fully matching; NON_MATCHING removed,
  rank M to O. Standard `notailcall` annotations on the reset and vector-add
  callees preserve branch-and-link calls, and placing the no-collider branch
  first reproduces the original common return layout. These annotations are
  inferred matching-source choices, not proof of the original source attributes.
- alSubActorFunction::tryMovement, 0x0018bae8, **100 bytes**. Existing loop
  conventions, entry flag 4 and alive checks dispatch virtual movement at
  vtable+0x1c. Count and buffer are reread after callbacks. Name is descriptive.
- alModelCtr::clearAnimPlayerFlags, 0x00128de8, **80 bytes**. Six optional pointers
  at 0x20,0x24,0x28,0x2c,0x30,0x34 each clear target byte 8. Name is descriptive;
  the final two player roles and meaning of byte 8 remain unknown.
- EffectKeeper::update, 0x002553b4, **84 bytes**. Existing upstream declaration;
  its address was independently bound by exact movement/calcAnimDirect callers.
  It guards on byte 0x10, calls each effect and stores whether any returned true.
- AudioKeeper::update, 0x00268e80, **48 bytes**. Existing upstream declaration;
  exact calcAnim callers independently bound this address. It tests the signed
  count at control+0x28 and calls the handle/control callbacks in order. Like
  the original, it does not insert a null-control guard.

Of these 480 bytes, 312 are newly implemented dependency bodies and 168 complete
the previously provisional collider source. Cumulative newly recovered exact
source is now **2,428 distinct bytes across 19 routines**: 2,400 game C++ bytes
and the earlier 28 SDK assembly bytes. Keeper's 160-byte correction and supplied
runtime code remain separate. No no-op factoring helpers are counted separately.
No invented original ranks were assigned to the descriptive helper names.

AnimPlayerSimple's pointer placeholder at offset 8 is refined to a boolean plus
three opaque bytes, preserving later offsets. alModelCtr's reviewed prefix now
includes the two extra player slots. EffectKeeper's prefix includes opaque +0xc
and the guard/result byte at +0x10. AudioKeeper preserves active at 0, handle at
8 and control at 0xc, with a reviewed control-prefix count at 0x28. Complete
types/sizes and several field meanings remain unknown. No sizeof/allocation use
of alModelCtr exists in the current source. Prefix refinement is not a claim of
complete class recovery. Earlier movement sources now call these actual methods
instead of duplicate temporary FUN names; their byte checks remain exact.

The current clean-base cumulative header patch is
`Tools/patches/RedPepper-Headers-movement-keepers.patch`, SHA-256
`c402a3b67a930c25071ed0d5aba4cfeb1c1d2594b09b42ebde6c4aa91036e867`.
It applies to the clean headers submodule HEAD and includes the untracked Light
header. Preserve the dirty headers and nnsdk submodules and their separate
patches; do not layer older cumulative header patches. The intermediate
movement-dependencies patch and all prior evidence remain intact.

Compiler attribute reference:
`https://documentation-service.arm.com/static/5eb946b50f1c1e0dae6ee21e`, section
10.44, documents preventing tail calls to a callee. The local annotations are
matching aids, not an original armlink invocation or a binary patch. Boundary
and type reviews are `.local/analysis/reviewed/movement-dependencies.json` and
`movement-keepers.json`, with SHA-256 values
`b1ef0d11e58ff8f86129143a004ac79de5aae952d471fd87645845b943ed5f37`
and `2123f422bb5038092a360be0509b7d6c4795e65f41fcc7f7fa4f6819fca50781`.
No prior Ghidra annotations were overwritten.

The focused seven-unit report checks current actor/model/effect/audio source;
46 matched entries cover 3,560 .text bytes, including inherited routines. This
is targeted verification coverage, not the raw-image or source-completion metric.
The existing suite still passes **31 tests and 2,158 ARM comparisons**, including
248 movement and 96 collider cases using actual ARMCC code. Dependencies remain
intercepted; the new lower-level callback bodies are not behavior-tested by that
harness. Exact-byte proofs of the five recovered bodies are separate evidence.

All **130/130 source units compile**, and the refreshed partial image links
129 source objects plus 47 genuine runtime members. It is at
`Build/whole-runtime/11ca66f9e0cf55a4`. Source/Stubs.c removes the recovered
dependencies and duplicate temporary update aliases, while explicitly retaining
three newly exposed lower-level effect/audio placeholders. No placeholder body
is counted as recovered or placed at an original address to inflate matching.

The actual whole-source ELF independently matches the model flag-clear and
subactor movement functions, **180/180 bytes**, at their original addresses.
`new-source-whole-comparison.json` checks all five new functions: the other
three differ only at **five branch destinations** to still-unrecovered callees:

- updateCollider: reset 0x0024c9ec and resolution 0x001eaf34.
- EffectKeeper::update: child update 0x001ea220.
- AudioKeeper::update: callbacks 0x001d9dc0 and 0x001da074.

`remaining-call-differences.json` records every actual/original instruction at
those differences. Targeted original-address ELFs bind these dependencies to
their original locations; the whole partial build binds real source or explicit
stubs. Thus all five pass source-level function checks, while only two currently
pass the actual whole-image function check. Do not conflate these scopes.

Latest raw-word image metric: **4.5107% (139,676/3,096,576 bytes)**, up from
4.4926% at the previous checkpoint. It includes 109,732 equal bytes of linker
padding. The raw-word increase of 560 is not the new-source count of 480. The
image is **3,377,192 bytes**, still larger than stock and not a working game.
Independent audit checks all raw sections and zero gaps against the actual ELF.
No stock code/data buffers or undefined stock-address aliases produce the image.

Current evidence hashes:

- ELF: `9c2f6f8c133e10d46a4682642d23d868ea16f49222eec5064190b839269f747f`.
- Partial code.bin: `5e8f50d63ab97241c8b141a5f0d31bf3bb361e9dc1a7b6351d6a9156275e3b4a`.
- Targeted report: `20f09fe9b0f7d8c2d96249208d19028f4cc6a66d6d3ba040b8f9a0141b28471c`.
- Suite report: `021cf18cfea08e456f7b17872f9ca4615b4d58b15917647146d3c8d135b40e7a`.
- Whole build report: `a8fa2ce3f3f3b700480c21331a670c9baad98cb1f1d09d9f2cb3cddb30e331dd`.
- Image comparison: `f6e52dc511e7d3f0c0850f51401a369e555e84325f2572a3627270b6e40160ba`.
- Whole-function comparison: `a7adb5303242f911848018479b1647fbfe3bafbb50eb8ece12bdfd9d94631ce6`.
- Current LiveActor.cpp: `58bf369578ba6ce20b42c728e4f9a7bb9a730dca86e5cc5ebfb0dc1f3ecd446f`.

The complete immutable checkpoint, including original/input/source/header/tool/
compiler/library/artifact hashes and next actions, is
`Build/matching/milestones/2026-10-15-movement-keepers.json`, SHA-256
`50880661857518f1163bc6e3bd2e2f0662b7c6f51261558fce8b2d7987af419a`.
Source/tool/header snapshots are retained under the sibling
`2026-10-15-movement-keepers-sources` directory. Prior manifests, source snapshots,
input ROMs and the historical upstream badge remain unchanged. No publication.

## October 15 collider and audio callback recovery

Six further routines now pass independent exact-byte checks, adding **736 newly
recovered game C++ bytes**:

- Collider::onInvalidate, 0x0024c9ec, **88 bytes**: 80 instruction bytes and the
  two 4-byte literals, -99999.0f and 0.0f. Existing upstream method name is bound
  independently by already-exact actor callers. The next entry is 0x0024ca44;
  Ghidra's 80-byte body omits the literal pool. It clears the reviewed fields,
  calculates previous center and saves radius.
- Collider::calcCenter, 0x003370b4, **432 bytes**: descriptive name; computes
  center from translation, optional local offset, matrix flag 4 and Y offset.
  Sequential component writes and pointer reloads preserve alias behavior.
- FUN_001d9dc0, 0x001d9dc0, **56 bytes**: iterates the audio handle array with
  signed count at 0 and buffer at 8, reloading both after callbacks.
- FUN_001da074, 0x001da074, **124 bytes**: traverses the circular control list,
  saves next before virtual query at +0x24, clears owner before unlink, then
  decrements the saved owner's count. The false-query callback stays in order.
- FUN_001c21a4, 0x001c21a4, **16 bytes**: unwraps a handle entry and tail-dispatches
  its object's virtual slot +4.
- FUN_001c25d8, 0x001c25d8, **20 bytes**: loads receiver at object+0x48 and
  tail-dispatches receiver virtual slot +8 with receiver and object arguments.

Cumulative newly recovered exact source: **3,164 distinct bytes across 25
routines**, comprising 3,136 game C++ bytes and the earlier 28 SDK assembly bytes.
Keeper's 160-byte correction, supplied runtime and inherited source certification
remain separate. The existing sead::ListNode::erase_ implementation is now
independently bound to 0x0028e964 and verifies all **48 bytes**; that is inherited
source certification, not new recovery. Audio temporary FUN names are retained;
complete types and method identities remain unknown. Four Unnamed.sym placeholder
extents were corrected from 4 to 16/20/56/124 with terminal/next-entry evidence,
then promoted U to O only after independent exact checks. No invented method rank.

Collider's prefix now preserves reviewed offsets through 0x1fc, with opaque gaps
and an opaque cleared word at +0x24. Complete class size is not asserted. Chained
sentinel assignments and per-component memcpy reproduce scheduling/copy order
without embedded opcodes or aliasing violations. The original copy helper is
unknown. Audio prefixes retain the virtual slots, receiver, array and list fields;
only the sentinel's two link words are meaningful. An inline node helper and
standard noinline annotations preserve the observed caller/register boundaries.
These are matching-source choices; original attributes and source-unit boundaries
are not proven. The small wrappers' virtual callee bodies remain unrecovered.

ARMCC rejects a C alias directly naming the C++ method; those failed compile
reports are retained. The GNU partial build now uses Data/SourceAliases.json and
Tools/source_aliases.py for **symbolic aliases to actual unique compiled source
functions**, with no numeric addresses: FUN_0024c9ec -> Collider::onInvalidate,
FUN_0028e964 -> ListNode::erase_. The final ELF independently confirms both alias
addresses equal their defined targets, sizes 88 and 48. Three new tests verify
that aliases follow real bodies at two placements and reject address constants,
undefined/stub/local/ambiguous targets, duplicates and script injection. This is
a GNU build aid; original armlink integration remains unestablished.

The focused seven-unit report is
`Build/matching/collider-audio-supported-progress.json`. It verifies 43 entries /
3,476 .text bytes, including inherited routines and compiled actor leaf helpers.
This is targeted diagnostic coverage, not newly recovered bytes or overall game
progress. The earlier five-unit probe lacks some caller helpers; its link failures
do not establish regressions. The supported report supplies those actual sources.
Current suite: **34 passing tests, 2,158 ARM comparisons**. Existing behavior
harnesses intercept dependencies; the new collider/audio body proof is separate
exact-byte evidence. No unchanged inherited full scan was repeated.

All **132/132 source units compile**; the refreshed partial image links 131
source objects plus 47 genuine runtime members. It is at
`Build/whole-runtime/6400edbabc23eb4f`. All six new routines match in this actual
whole-source ELF, including their linked direct call destinations. The inherited
unlink and AudioKeeper::update also match, **8/10 functions** in the focused
whole-ELF report. The other two differ only at one branch each: updateCollider
still calls the collision-resolution placeholder (original 0x001eaf34), and
EffectKeeper::update still calls the effect-child placeholder (0x001ea220).
`remaining-call-differences.json` records both instructions and the alias audit.
Dynamic virtual dependencies and unrelated game routines remain unrecovered.

Raw-word partial-image metric: **4.5365% (140,476/3,096,576 bytes)**, up from
4.5107% at the prior checkpoint. It includes 27,120 equal-word bytes in emitted
executable sections, 3,628 in emitted data and **109,728 in linker padding**.
The 800-byte raw-word increase is separate from 736 newly recovered source bytes.
The image is **3,377,080 bytes**, includes explicit stubs and extra code beyond
stock, and is not a working game. Independent audit checks all emitted bytes and
zero inter-section gaps. No stock code/data buffer or undefined-address alias
enters image production. The historical upstream badge remains unchanged.

The new cumulative clean-base header patch is
`Tools/patches/RedPepper-Headers-collider-audio.patch`, SHA-256
`c42504aa9b45f551dfbf77099b09b3d138e40b38dd80bd9b112328b82af47c9e`.
It was applied to an archived clean header HEAD and compared to every modified /
untracked header. Preserve it, both dirty submodules, the separate SDK patch and
all earlier cumulative patches/evidence; do not layer old cumulative patches.
Reviews: `.local/analysis/reviewed/collider-audio.json` and `audio-dispatch.json`.
Ghidra exports and reviewed annotations were not overwritten or relaunched.

Exact hashes at this checkpoint:

- ELF: `4f42e1d6ed387f16f8c86ee780467b43e2bb4c43ee20121b5b3ee2dace4edbe4`.
- Partial code.bin: `68d681dd2e0350941c935b172013b8687c07db69e071e018356172c6a399892c`.
- Targeted report: `2d4429cdae38318807b5840f03f89a885b8dd84ad1ca591469579abb6d43a686`.
- Suite report: `4accc2110b641c5819293ea6d80beeac6edfe3e355be366bf4ef41c5a5a80f2a`.
- Collider.cpp: `971f35ec74eb4fc2598b722cbd160440f82cf3e51d65788f6300209ac363e9c6`.
- AudioCallbacks.cpp: `e600141b748dcf416f95f8826a301b7bb5f6b455e1229f8470d4024c899b5892`.

Immutable checkpoint: `Build/matching/milestones/2026-10-15-collider-audio.json`,
SHA-256 `b32f65712aa6908060cf5d56b063e87fb3f21cb02bb620424499cff4cd951112`. It binds exact input, source, header, compiler, tools, reports and
artifact hashes. Mutable sources/reports are copied under the sibling
`2026-10-15-collider-audio-sources` directory. Prior checkpoints and original
inputs remain intact. All work stays local; nothing committed or published.

## October 15 effect update and matrix dependencies

Two SDK-style native assembly helpers are newly recovered and byte-exact, **92
bytes** total, both also exact in the actual whole-source ELF:

- FUN_0027cb9c, 0x0027cb9c, **60 bytes**: loads a row-major 3x4 matrix and vector,
  accumulates translation then x/y/z products with the original VFP order, and
  writes the transformed vector. All input loads precede output stores.
- FUN_00291470, 0x00291470, **32 bytes**: checks self-copy, loads all 48 matrix
  bytes before output writes, and returns. Original symbol identities are unknown;
  the source follows the SDK's existing assembly-helper convention and uses its
  pinned ARMCC 4.0 compiler plus strict assembly translation. No stock buffers.

Cumulative newly byte-exact source is **3,256 distinct bytes across 27 routines**:
3,136 game C++ bytes and 120 SDK-style assembly bytes. Keeper's 160-byte fix,
inherited certification and supplied runtime remain separate. Temporary-name
extents were independently checked before promoting only these two U to O.
Duplicate original FUN_00291470 rows now consistently carry 32/O.

Two actual game C++ routines have also been restored from placeholders, but
remain **NON_MATCHING / rank M**, with **no exact-byte credit**:

- al::EffectEntry::update, 0x001ea220, **252 original bytes**, currently emits
  252 bytes. EffectEntry is a descriptive prefix name. The loop reloads count,
  handles and parameters after callbacks; flags +0x40/+0x3f choose matrix and
  position updates, and flag +0x45 applies a local offset through the matrix.
- FUN_0023f45c, 0x0023f45c, **56 original bytes**, currently emits 56 bytes.
  It checks a nonnull emitter, matching reference/emitter IDs and positive signed
  emitter count. Generation/count names and complete layouts remain inferred.

The updater's inline matrix-application helper reproduces original r6/r7/r8
allocation. Four argument-setup words still differ at +0x5c,+0x64,+0x6c,+0x70;
validity has eight instruction-word differences. Exact differences and analysis
ELF hashes are in `Build/matching/effect-nonmatching-differences.json`. No binary
rewriting or instruction-buffer substitution was used. ARMCC automatically emits
all three hint NOPs without source NOPs. Early explicit-NOP experiments were
removed. An aggregate-return experiment used the wrong vector return ABI and was
rejected; a 4.0 game-compiler probe had more differences and was rejected. Normal
4.1 game compilation is preserved. These are source probes, not license evasion.

`Tools/effect_behavior.py` and three new tests execute the actual ARMCC updater
and validity source plus the actual compiled math helpers in a separate-address
ELF. They pass **421 new original-vs-rebuilt ARM comparisons**: 213 updater,
40 validity, 84 transform and 84 matrix copy. Cases cover flags, null/stale/inactive
emitters, signed count boundaries, callback-driven parameter/count/buffer/matrix
changes, pointer reloads, overlapping input/output, stack/callee-saved registers
and caller-saved clobbering. Only the two lower-level emitter setters are
intercepted; their bodies remain unrecovered. This behavior proof does not make
the two provisional routines byte-exact or prove a working game.

Current suite: **37 tests and 2,579 ARM comparisons**, all passing. Existing
keeper/state/array/actor cases remain separate; the effect harness uses ARMCC
4.1 plus the SDK 4.0 assembly objects. The focused four-unit report is
`Build/matching/effect-supported-progress.json`, five matched entries / 296 bytes
including inherited keeper methods. That is diagnostic coverage, not new source.

The GNU source-alias list now also binds FUN_001ea220 to the actual compiled
EffectEntry::update body. The full ELF audits all three symbolic aliases; this
provisional target stays in rest_code (0x00435634), and receives no stock placement.
The two unrecovered setters at 0x0023f294 and 0x002d37d0 remain explicit stubs.
EffectKeeper now calls actual provisional source rather than a placeholder, but
its whole-image call destination is still different from the original.

All **135/135 source units compile**; the partial image links 134 source objects
and 47 genuine runtime members. New artifact directory:
`Build/whole-runtime/99b9628622d8426e`. Focused full-ELF comparison verifies both
math helpers; the updater/validity remain unplaced nonmatching source and their
keeper caller retains a destination difference. It is **not** a working game.

Raw-word metric: **4.5395% (140,568/3,096,576 bytes)**, up from 4.5365%. It includes
27,212 equal-word bytes in emitted executable sections, 3,628 in data and
**109,728 in linker padding**. Image size: **3,377,408 bytes**, including unmatched
code/stubs beyond the original extent. Independent image audit validates emitted
sections and zero gaps; no stock code/data buffer or undefined-address alias
produces the image. Historical upstream Data/Code.json remains unchanged.

The collider resolution boundary/ABI review corrects an important next-step
assumption: its complete **0x001eaf34..0x001eb664 extent is 1,840 bytes**, including
five literal words at 0x001eb284..0x001eb298. Ghidra's split instruction chunks total
1,820 bytes and omit that pool. Literals are 0, 0.9f, 35.0f, -99999.0f, 0.001f.
The final path loads the return vector into VFP s0-s2, agreeing with the exact
updateCollider caller; Ghidra's void signature is incomplete. Field +0x1dc has a
saturating unsigned increment; its existing header name/type remain inferred.
Full collision source is still missing. Reviews are
`.local/analysis/reviewed/effect-update.json` and `collision-resolution-abi.json`.
Ghidra exports and reviewed annotations were preserved.

The new cumulative clean-base SDK patch is
`Tools/patches/nnsdk-effect-math.patch`, SHA-256
`9d4d14f884e392be0d72c2e5733f90917eb9317bcd9f459c552496690a846bb4`.
It includes the earlier vector addition and the new matrix file, applies to a
clean SDK HEAD, and reproduces all modified/untracked SDK sources. Preserve both
dirty submodules, all previous evidence, this patch and the unchanged cumulative
`RedPepper-Headers-collider-audio.patch`. Do not layer cumulative SDK patches.

Exact checkpoint hashes:

- ELF: `cb822c1ac6bed0275e759eb6e9eaf57257801421e16834eb4c6aeb7f2c18aca1`.
- Partial code.bin: `3c05bb1f1692a7db20e902751a1d47a13274e501cb8cc19766cf9ff4625a9084`.
- Targeted report: `bf9ba7a8672a4da767329a993dabe50eec548e634e008486dc62036733e859ca`.
- Suite report: `1829d8312ded6115b6567876c249bdd438c873157f8a9b30d1dfb0130a5d3153`.
- EffectUpdate.cpp: `f83dd3955d0fbc4403d08cc80997b4533bac4b2f4d0acf3242944f14d64935fb`.
- EffectHandle.cpp: `e5a3f476fafb26b15827ac5c76d48f2a746318616e6f3a11d2329a7feabef667`.
- SDK math_MTX34.cpp: `4fb1053eb62b0998519b41dd68cde554259d97be16221fcfa0ab29c07e23349e`.

Immutable checkpoint: `Build/matching/milestones/2026-10-15-effect-update.json`,
SHA-256 `464aaba3e141bca662043ab9f42c4a51e603f02f2752395aabe10b4fe33ea8c9`. Input/source/header/compiler/tool/report/artifact hashes and the
next task are pinned, with mutable sources/reports under the sibling
`2026-10-15-effect-update-sources` directory. Prior checkpoints and inputs remain
intact. All changes are local; nothing committed or published.

## October 15 full collision control flow (provisional)

Actual source now implements Collider::resolve at **0x001eaf34** and its four
sweep helpers. These are **provisional NON_MATCHING / rank M**, with no new exact
C++ byte credit. The complete original ranges total **2,204 bytes including
literals**, and current ARMCC bodies total **2,212 bytes**:

- Collider::resolve, 1,840 original / 1,864 compiled bytes. Full two-stage sweep,
  platform carry motion, shape-change preparation, query filter snapshots, flag
  reloads, contact response, slide projection, backward-motion rejection, final
  contact state, native VFP vector return and unsigned saturating airborne counter.
- FUN_0025c824, sweep initialization, 192 / 180 bytes.
- FUN_0025c790, interpolated center/radius and optional remaining motion, 104 / 104.
- FUN_0025c7f8, progress advance/clamp, 44 / 40.
- FUN_001da3ac, interpolated position, 24 / 24.

Full boundaries include the original literal pools, not just Ghidra instruction
chunks. They were not shortened to fit emitted code. Optional remaining motion
is **delta * (1-t)**. Initial step is min(currentRadius*0.9, previousRadius*0.9,35);
second step is min(previousRadius*0.9,35). Pseudocode's missing scalar arguments
and void return were corrected from ARM call sites. Names/roles remain inferred.

New native vector scale-add FUN_0027cca0 at **0x0027cca0 is 28/28 byte-exact** in
both the targeted analysis and actual whole-source ELF. It loads vector/base
before output and preserves original VFP order. This is SDK-style assembly with
an unknown original symbol identity, separate from new game C++ recovery.
Cumulative exact recovery is **3,284 distinct bytes across 28 routines**: 3,136
game C++ and 148 SDK-style assembly bytes. Keeper's 160-byte correction, inherited
certification and supplied runtime remain separate. No provisional routine got
exact credit; source-shaped gameplay progress and byte certification are separate.

The collider prefix now types filters at 0/4, query capacity/count/buffer at
0x20/24/28, three 0x88-byte contact spans at 0x38/c4/150 with normal at +8,
distances c0/14c/1d8, unsigned counter1dc and previous normal1e0. Opaque contact
fields remain opaque; complete class size is not asserted. No new/sizeof(Collider)
use exists in current source. CollisionPath has eleven reviewed floats. Existing
onInvalidate and calcCenter preserve all **520 exact bytes** after the header
refinement, including in the actual whole-source ELF.

`Tools/collision_behavior.py` builds actual resolve/center/path/vector source at
separate test addresses. Four new tests pass **377 original-vs-rebuilt ARM
comparisons**: 251 full resolver, 81 path initialization, 25 advance, 10 sample,
10 position. Cases include contacts/sliding, terminal response, two sweep phases,
platform motion, callback-driven flag/filter/velocity mutations, filter snapshots,
global/default and explicit buffers, counter saturation, degenerate radius/path
conditions, helper overlap and ABI preservation. Remaining original math bodies
execute as analysis dependencies; seven engine callbacks are intercepted. Those
callback bodies, NaNs, complete collision engine and full game remain unverified.
The production image uses actual source/stubs, never these stock-address aliases.

Current suite: **41 passing tests, 2,956 ARM comparisons**. The focused seven-unit
report `Build/matching/collision-resolution-final-progress.json` verifies 38 entries
/3,200 bytes including prior routines and caller helpers; that is diagnostic
coverage, not new recovery. Provisional ranges retain mismatch/size failures.
The fourth GNU symbolic alias, FUN_001eaf34 -> Collider::resolve, targets actual
compiled rest_code at 0x00435518, size 1,864, with no fixed stock address. All four
aliases are independently inspected in `source-alias-audit.json`.

The first whole compile exposed new stubs appended after #undef STUB. The block
was moved before cleanup; failed report/logs are preserved. The corrected build
compiles **137/137 units** and links 136 source objects plus 47 genuine runtime
members. Directory: `Build/whole-runtime/ebf9548211798462`. Focused full-ELF check
passes scale-add and the existing reset/center (3/9 checked entries). Provisional
resolver/path bodies stay in rest_code; the actor caller still has a destination
difference. Thirteen new lower-level collision dependencies remain explicit
placeholders. The image is still an incomplete, non-working game build.

Raw-word metric: **4.5404% (140,596/3,096,576 bytes)**, up from 4.5395%. It includes
27,240 equal-word bytes in emitted executable sections, 3,628 in emitted data and
**109,728 in linker padding**. Image size is **3,379,808 bytes**, with unmatched
code/stubs beyond stock. Independent audit validates emitted sections and zero
gaps against the ELF. No stock buffers or undefined-address aliases produce it.
The upstream historical badge and earlier evidence remain unchanged.

New cumulative patches, each validated by application to clean submodule HEAD
and comparison to all modified/untracked files:

- `Tools/patches/RedPepper-Headers-collision-resolution.patch`:
  `6fc418ac0edce1e9fa4170d898f38799b715952a3a18280b934a293226393eed`.
- `Tools/patches/nnsdk-collision-scale-add.patch`:
  `a024900a99c5939d820612402b5508824533b1338754ca73e9ec660c9681f4d5`.

Preserve both dirty submodules and all older evidence. Apply cumulative patches
to clean bases, not over earlier cumulative patches. New review:
`.local/analysis/reviewed/collision-resolution-source.json`; previous ABI review
and disassembly are preserved. No Ghidra annotation/export or May 2026 file changed.

Current exact hashes:

- ELF: `431777f745b14b67a31dcd60285940ef79a5eaab8f62aee9444db3ed40e3415c`.
- Partial code.bin: `7f64ab913a6a2ad92836b7a2acebb07d5286b656257ad3578ba53c81e4e9e950`.
- Targeted report: `beb4f7cf64a83c62d4cb32ce9fd38624b92558ce9d07d4c39448a3d318558a0c`.
- Suite report: `09734f8129213b08ce6cdb19e04c6296076a7df44aec2b65d9f10b2872298c5c`.
- ColliderResolution.cpp: `f995b384cadafc92794c05da76c4047419b778076741eebd9bea22e839f2bcc0`.
- CollisionPath.cpp: `ea082a9eba14ecd7567cdf55ec925139dfab9297812ce411117b450e81d42e16`.

Immutable checkpoint: `Build/matching/milestones/2026-10-15-collision-resolution.json`,
SHA-256 `b96bed6ed8b25ec528c3014bcff2c9c2e8e5635b48c135a2b451092f334ce562`. Exact input/source/header/compiler/tool/report/artifact hashes and
next tasks are pinned. Mutable sources/reports are saved under the sibling
`2026-10-15-collision-resolution-sources` directory. All changes remain local;
nothing committed, pushed or published.

## October 15 contact collection, selection and query source

Four new C++ helpers are independently byte-exact, **88 distinct bytes**, in
both targeted original-address ELFs and the actual whole-source partial ELF:

- CollisionDirector::getResultCount at 0x003342ac, 12 bytes.
- CollisionDirector::getResult at 0x001d43dc, 16 bytes.
- FUN_00262dd4 at 0x00262dd4, 16 bytes, indexed normal-vector pointer.
- FUN_0026f71c at 0x0026f71c, 44 bytes, squared norm below squared epsilon.

Names and geometry field groupings are descriptive/inferred where upstream
identities are unknown. The first two entries share original tails with query
wrappers; never count these 28 bytes again if the wrappers later match. Normal
and near-zero helper ranks change M to O. The independently listed result tail
has its old 4-byte U extent corrected to 16/O; the new descriptive count entry
gets no invented upstream symbol row. Cumulative newly exact source is **3,372
bytes across 32 routines**: 3,224 game C++ and 148 SDK-style assembly bytes.
Keeper's 160-byte correction, supplied runtime and inherited certification remain
separate. No provisional routine receives exact-byte credit.

Actual new Source/ bodies also replace six placeholders/absent dependencies:

- Collider::collectContacts at 0x0023eda8: 472 original / 504 compiled bytes.
- Collider::finalizeContacts at 0x001eaa44: 1,256 / 1,264 bytes.
- Count and indexed-result wrappers at 0x00334298 and 0x001d43c0: full reachable
  original extents 32/44 bytes, currently emitted prefixes 20/28 bytes.
- Surface classifiers at 0x0023fa8c and 0x0023fb04: original 120/140 bytes,
  currently 120/136 bytes. They reject a near-zero normal, then classify the dot
  with gravity against 0x3eaf1d44 (~0.342020154), using its magnitude and sign.

All six are **NON_MATCHING / rank M**, despite behavior checks. Their full original
ranges total 2,064 bytes including 28 shared getter-tail bytes; emitted bodies
total 2,072 bytes. Ten new source entries cover 2,124 distinct original bytes,
including the 88 exact bytes. The prior five provisional collision/path routines
and two provisional effect routines remain provisional and retain their evidence.

Collection snapshots total once, clamps capacity inside its loop, reloads member
count after the entry accessor and preserves 32-bit subtraction wrap. Zero total
preserves the old count even when above capacity. Each 0x88-byte record copies
0x85 meaningful bytes; three trailing padding bytes stay unchanged. The reviewed
record uses four normal-vector and three vertex-vector slots, with exact original
meanings still inferred. Finalization classifies ground, wall, then ceiling;
strictly larger distance wins, ties retain the prior contact. Source/selected
member aliasing is tested. Gravity pointer is at Collider+0x10; query chain is
kit+0x28 -> director+0x14 -> count+0 / pointer buffer+8. Complete layouts unknown.
Reset/center remain exact across all 520 bytes after these header refinements.

The query wrappers expose a Ghidra boundary error: its exports stop at the
getLiveActorKit call. Actual code continues through MOV r0,r0 branch-to-next
instructions into shared getters. References retain the complete 32/44-byte
reachable ranges; they were not shrunk to fit compiler prefixes. No new tail
reordering transform was added, and these wrappers remain nonmatching. Near-zero
and classifiers are separate translation units because ARMCC otherwise inlines
or propagates register clobbers between them; original source grouping is unknown.

Four new tests add **385 ARM comparisons**: collection139, finalization112,
query44 and classification90. They cover padding, capacity edges, zero total,
self-copy, callback-driven count changes/total snapshots, surface/distance ties,
member aliasing, threshold-adjacent floats, near-zero vectors and preserved ABI.
The existing 377 resolver/path cases now execute actual rebuilt contact collection,
finalization, query wrappers, getters, classification and near-zero bodies. Their
old collection/finalization interceptions are gone. Six engine/global-accessor
entries remain intercepted: global director, global kit, pre-sweep, two query
variants and response. Original geometry/math dependencies still execute in this
analysis ELF. Callback bodies, nonfinite behavior and full collision/game remain
unverified. Current suite: **45 passing tests, 3,341 ARM comparisons**. Behavior
proof and exact-byte proof are separate.

All **142/142 source units compile**, linking 141 source objects and 47 genuine
runtime members. New image directory: `Build/whole-runtime/35539b92f576ca6a`.
Independent focused whole-ELF comparison passes 6/13 entries: four new helpers
plus the preserved reset/center. Seven provisional entries, including the earlier
resolver, remain unplaced rest_code. Six GNU symbolic source aliases now include
collection/finalization, audited against their actual compiled bodies. No stock
buffers or undefined stock-address dependencies produce this image.

Raw-word metric is **4.5432% (140,684/3,096,576 bytes)**, up from 4.5404%:
27,328 matching bytes in emitted executable sections, 3,628 in data and **109,728
in linker padding**. Image size is **3,381,832 bytes**; it contains stubs and extra
code beyond stock and is not a working game. Data/Code.json's historical upstream
4.0704% remains unchanged. These raw-image percentages are not source completeness.

The new cumulative headers patch applies cleanly to submodule HEAD and reproduces
all versioned and nonignored untracked files:
`Tools/patches/RedPepper-Headers-collision-contacts.patch`, SHA-256
`6f5081c1404e5eb96068ac11b52ff4223079a21e6c6c7dc229b6ee38e6e71342`.
SDK source/patch is unchanged; preserve `nnsdk-collision-scale-add.patch` and both
dirty submodules. Apply cumulative patches to clean bases only. New local reviews
are collision-contacts-source.json and collision-contacts-original.disasm.txt.
No Ghidra annotation/export, original asset or May 2026 file was modified.

Exact current hashes:

- ELF: `30645f81421afa0747714ba260ee5b09d6cfa04a40e830c7cebf3bd9ed265870`.
- Partial code.bin: `1dbaa0cd7db5088e013951b5133a1cecb9c0cf4ed13fa497f983d3cf27f36622`.
- Targeted report: `08d3901938bd7485ab0e7da2c1a6736de1299ceef5e2c94a39f2557ec0c6e51d`.

Immutable checkpoint: `Build/matching/milestones/2026-10-15-collision-contacts-final.json`,
SHA-256 `042a63135d9b9f21aac99c7082e6547b99567b792c72d785bb1f529e972a49c1`.
It binds input/source/header/compiler/tool/report/artifact hashes and 306 source/
report snapshots in the sibling `2026-10-15-collision-contacts-final-sources`.
The earlier contact draft remains preserved; final evidence corrects its prose
callback count from five to six, with test outcomes and byte proofs unchanged.
All earlier checkpoints remain intact. Nothing committed, pushed or published.

## October 15 pre-sweep and collision response source

Actual source now implements the two remaining intercepted control-flow bodies,
plus their contact response helpers. Four larger routines remain **NON_MATCHING /
rank M**: 1,820 original bytes including literals, 1,780 compiled bytes:

- Collider::sweepShapeChange at 0x001ea8a0: **404 original / 404 compiled bytes**.
  Snapshots filters once, reloads flags per sample, applies accumulated correction
  only to the shifted query variant, collects/resolves hits, samples the final
  center/radius, finalizes contacts and clears the count when any hit occurred.
- Collider::respondContacts at 0x0023e928: **1,152 / 1,112 bytes**. First classifies
  contacts and marks surface bits, then selects full-normal or projected response,
  accumulates signed component extrema and optional platform carry, and produces
  correction plus an optional normal. Its fifth stack argument is never read in
  the original body; the internal selection condition is initialized to1. Source
  preserves that unused argument and observed behavior, without inventing its role.
- FUN_0026ffc8 at 0x0026ffc8: **48 / 48 bytes**. Scales a contact normal by distance
  and optionally copies its SDK vector base. Register argument setup still differs.
- FUN_0033162c at 0x0033162c: **216 / 216 bytes**. Normalizes contact6c-contact60,
  projects displacement and original normal onto that direction. The original
  normal is cached before correction output, preserving input/output alias behavior.

Two additional C++ predicates are byte-exact in targeted and whole-source ELFs,
**40 distinct bytes**: FUN_0025c780 (16 bytes, contact flag equals1), and
FUN_0033745c (24 bytes, parts prefix field+0x134 equals0). Their temporary names
and complete parts semantics remain unknown. Only those two ranks change M to O.
Cumulative newly exact source: **3,412 bytes across 34 routines**, comprising
3,264 game C++ and148 SDK-style assembly bytes. Keeper160, supplied runtime64,
inherited certification and earlier provisional source stay separate.

Boundary review prevents two misleading extents. Pre-sweep ends after its zero
literal at0x1eaa30, giving0x1ea8a0..0x1eaa34 (400 instruction bytes plus4 literal).
The next16 bytes are a separate entry/shared setter, not extra pool words. The
response body0x23e928..0x23eda8 contains a zero literal at0x23ed74 followed by its
own reachable tail0x23ed78..0x23eda8, which branches back into the earlier body.
Its full1,152-byte range is retained; it was not shortened to fit emitted code.
Reviews and disassembly are in .local/analysis/reviewed/collision-response-*.

Three new tests add **638 ARM comparisons**: pre-sweep99, response441 and helpers98.
Cases cover sample completion/t>=1, filter snapshots/flag mutation, capacity,
selection bits across surface types, start index, the unused fifth argument,
positive maxima/negative minima, carry dot sign and disabled parts, null optional
outputs, normalization degeneracy and helper input/output aliases. The existing
385 contact cases and377 resolver/path cases remain; the resolver fixtures now
provide valid contact parts/motion fields and use actual response/pre-sweep code.
Earlier mock-based fixtures/evidence remain preserved in prior snapshots. Velocity
mutation now occurs in the query callback, since response is no longer intercepted.
Current suite: **48 passing tests, 3,979 ARM comparisons**.

Only four collision engine/global-accessor addresses remain intercepted: global
collision director0x1676e0, global kit0x277250 and query variants0x2673b0/0x25c9f8.
The normalization helper and remaining geometry/math dependencies still execute
original code in the analysis ELF. Those dependencies are source/stubs in production.
Finite behavior checks are not exact-byte proof, complete physics or a working game.
The new sweep/response C caller aliases target their actual provisional source;
all eight symbolic aliases are independently audited in the whole ELF.

All **145/145 units compile**, linking144 source objects plus47 genuine runtime
members. Artifact directory: `Build/whole-runtime/10140227f77e88a0`.
Focused whole-ELF comparison passes4/8 entries: two new predicates plus520 preserved
reset/center bytes. All four new larger bodies remain unplaced rest_code.
Raw-word metric: **4.5445% (140,724/3,096,576 bytes)**, up from4.5432%; executable
matching27,368, data3,628 and **padding109,728 bytes**. Image size3,383,568 bytes;
explicit stubs and extra code remain, so this is an incomplete non-working game
image. Historical Data/Code.json4.0704% is unchanged. No stock instruction/data
buffers or stock-address aliases for undefined dependencies produce the image.

The new cumulative headers patch is clean-base validated, including every
versioned/nonignored untracked file:
`Tools/patches/RedPepper-Headers-collision-response.patch`, SHA-256
`4cd60c9385e808d1b5e6c6b898eaacb4c386c050ffc36091ab47bfa4691c7a19`.
SDK source and nnsdk-collision-scale-add.patch are unchanged. Preserve both dirty
submodules and all previous patches/evidence; apply cumulative patches to clean
heads only. No Ghidra annotation/export, original asset or May2026 file changed.

Exact hashes:

- ELF: `79ef26d4f15dc0b9c09ebe38cf9bb998fdad2b3cab2a456b1b5dbb11775ae8df`.
- Partial image: `1b79c32e6dfeadb3479ffc25af652ab3bb1a10d0109003c833f6703448f037c6`.
- Targeted report: `7efd91dbc9b6d5dfc99716f99c2c9cfe1d1cf23b9df6c4a86a59fc768cf597e3`.
- Suite report: `6571cee7f022f103a0fab8663fe32e9708a454c45f0e170bc18cb0541b0b2382`.

Immutable checkpoint: `Build/matching/milestones/2026-10-15-collision-response.json`,
SHA-256 `6af293f547d3568fbfd148183360aa4610a701a668ee9e18c77932fc87ec94b2`.
It binds input/source/header/compiler/tool/report/artifact hashes and312 snapshots
in the sibling collision-response-sources directory. All previous checkpoints
are preserved. Nothing committed, pushed or published.

## October 19 query wrappers, director query and armlink branch-NOP rule

Actual source replaces the last four collision engine/global-accessor
interceptions except the global kit accessor. Ten routines are byte-exact at
their original addresses in targeted and whole-source ELFs, **520 distinct new
bytes** (448 game C++ plus 72 SDK-style assembly); none overlaps a previously
counted range (checked against every exact range in Data/RecoveredFunctions.json):

- FUN_002673b0 / FUN_0025c9f8 (84 + 84): sphere query wrappers, variants 0 and 1.
  Both save the s0 radius in s16 across getLiveActorKit, store filters A/B at
  director+8/+0xc and tail-call the director query. The stores are armlink
  `--inline` copies of two 8-byte setters, reproduced by the existing leaf pass.
- CollisionDirector::querySphere at 0x0025ca4c (148): recycles previous results
  onto a free list with a signed count reloaded per iteration, zeroes the count,
  builds {center, filterA, filterB, radius} on the stack, calls engine vtable
  slot +0x14 with (results, info, variant) and clears both filters.
- FUN_001676e0 (16) global director accessor and
  CollisionDirector::getDefaultContactBuffer at 0x001d44cc (20).
- FUN_00334298 (20) and FUN_001d43c0 (28): the global result-count/result
  wrappers, now exact as 20/28-byte extents ending in the NOP before their shared
  getter tails (12/16 bytes, already counted earlier; never double-counted).
- FUN_0027306c (40): removes the normal component through the scale-add helper.
- FUN_0027ccbc (72, SDK-style asm): in-place normalize returning length in s0.
- FUN_00331f18 (8): platform-motion wrapper (contact->parts, then 0x331f20).

Two bodies stay **NON_MATCHING / rank M** with finite behavior proof only:
FUN_0027d5c4 normalize-or-zero (88/88; the original loads y and z separately,
ARMCC pairs them into one vldmia: 4 words) and
CollisionParts::calcPositionDelta at 0x00331f20 (72/72; only callee-saved
register assignment differs: original pos r4, this r5, delta r6). The normalize
threshold is the VFP compare against (0.001f)^2 = 0x358637be; the ARMCC integer
compare shortcut was avoided so unordered inputs take the original path.
Cumulative newly exact source: **3,932 bytes across 44 routines**, 3,712 game C++
and 220 SDK-style assembly. Keeper 160, supplied runtime 64, inherited
certification and provisional source stay separate.

A documented linker rule now explains the shared tails: armlink's default
`--branchnop` (DUI0803E 4.7/11.12) replaces a branch whose relocation resolves to
the next instruction with a NOP after `--tailreorder`. `Tools/branch_nop.py`
applies exactly that rule (unconditional A32 B with a branch relocation to P+4
becomes MOV r0,r0, relocation R_ARM_NONE) to targeted links and, after the leaf
pass, to whole-image placements; two tests cover kept far/local branches. In the
whole image it fires at 21 sites, including 18 inherited upstream tail calls, and
every one of those words reads MOV r0,r0 in the original image. Reviews and both
disassemblies are in .local/analysis/reviewed/collision-query-*.

Behavior: the analysis ELF now executes the wrappers, director query, accessors,
normalization, projection and platform motion as source; only the global kit
accessor 0x277250 and the director's virtual engine slot are intercepted, through a
fake engine object whose hook records results pointer, query info and director
filters. Three new tests add **291 ARM comparisons** (director/query 170, accessors
3, normalization 62, platform motion 56): signed recycling incl. 0x80000000 and
0xFFFFFFFF counts, filter reset, threshold bit patterns around 0.001f, length
return/degenerate vectors, projection and matrix aliases. Filter setters have no
separate original body. Current suite: **53 passing tests, 4,270 ARM comparisons**.

All **146/146 units compile**, linking 145 source objects plus 47 genuine runtime
members. Artifact directory: `Build/whole-runtime/af7e912c6cda9a7d`.
Focused whole-ELF comparison passes 13/20 entries: the nine placed game routines
plus the SDK normalize and the earlier predicates; FUN_00331f18 is placed but its
tail stays a real B because the NON_MATCHING delta body is unplaced rest_code.
Raw-word metric: **4.5634% (141,308/3,096,576 bytes)**, up from 4.5445%;
executable matching 27,956 (+588), data 3,628 and **padding 109,724 bytes**. Image
size 3,383,584 bytes; stubs and extra code remain, so this is an incomplete
non-working game image. Historical Data/Code.json 4.0704% is unchanged. No stock
buffers or stock-address aliases for undefined dependencies produce the image.
The CollisionContact free-list overlay uses the existing void* member: a union
made ARMCC copy that word twice in collect/finalize record copies (+4/+24 bytes).

Cumulative clean-base patches, validated by applying to clean heads and diffing
against the dirty submodules (identical): `Tools/patches/RedPepper-Headers-
collision-query.patch` SHA-256
`0e2651f2195f855e2e4700d57b2cded5799f12cdf0e386ae8465a1c4f996022e` and
`Tools/patches/nnsdk-collision-normalize.patch` SHA-256
`89d48ab34899a5baa5ff47cb87730e60d32803ed2d5c7159e65b6f45a83976b9`. Preserve both
dirty submodules and all previous patches; apply cumulative patches to clean heads
only. No Ghidra annotation/export, original asset or May 2026 file changed.

Exact hashes:

- ELF: `0c75e5575ee6bd7cbe44766cf2fdac12120193dd149acc3881cae7ab6c9d3be3`.
- Partial image: `984385ccb4ad4558c3bc06fa800230dfb43ace65fc5b68eb714903423f81ac93`.
- Targeted report: `19432a97fb168d81ca18f39b425280cb3d8b59e1e2a39f56bdb643669294835b`.
- Suite report: `13c3861b1b41f855ed3dfe3005ff780944bb51184156536a277f5e8ddeebbab7`.

Immutable checkpoint: `Build/matching/milestones/2026-10-19-collision-query.json`,
SHA-256 `742e3e5ec2bf63ea20cbc5caa3b38691e52db3bb5db8b03760930d446c635b8b`.
It binds input/source/header/compiler/tool/report/artifact hashes and 369 snapshots
in the sibling collision-query-sources directory. All previous checkpoints are
preserved. Nothing committed, pushed or published.

## October 19 sensor messages, actor utilities and the placement ArgN family

Three focused batches toward the user's 10% partial-image target added **85
byte-exact routines / 3,452 distinct new bytes**, all compiled from actual source
at their original EU addresses (reports `Build/matching/sensor-msg-progress.json`,
`utilities-batch1-progress.json`, `placement-args-progress.json`; 647 matches in
the full run `progress-full-2026-10-19.json`):

- sendMsg family (28 routines, 784 bytes): the remaining 28-byte `al::sendMsgN`
  wrappers; SensorMsg.h gained the missing enumerators/macros (1,3,6,7,10,11,15,
  21,31,33,35,38,42-44,48,54,56,57,59-62, ItemGet, PlayerStatueTouch).
- Actor utilities (17 routines, 760 bytes): showModel 0x26a9fc (100) / hideModel
  0x27ae84 (84) in the new unit `Source/al/LiveActor/ActorModelFunction.cpp`;
  addToClipping / removeFromClipping 0x1dbefc / 0x1dc038 (32 each);
  validate/invalidateCollisionPartsBySystem (84 / 8); CollisionParts::
  validateBySystem 0x1c983c / invalidateBySystem 0x1c96c0 (60 each, new unit
  `Source/al/Collision/CollisionParts.cpp`); syncCollisionMtx 0x1d2d44 (108);
  alActorSystemFunction::addToExecutorDraw / removeFromExecutorDraw /
  removeFromExecutorMovement (24 each); al::isExistArchive (32);
  findOrCreateResource 0x243260 (28, new `Source/al/Resource/Resource.cpp`);
  SensorHitGroup::add (24); getFront (16); FUN_001676f0 (20, engine accessor,
  recorded in Data/RecoveredFunctions.json). LiveActor.cpp now calls
  `al::preScaleMtx` / `al::syncCollisionMtx` instead of the FUN_ externs;
  movement (504) and updateCollider (168) stay byte-exact.
- Placement ArgN family (40 routines, 1,908 bytes): tryGetArg(int*/float*/bool*,
  const PlacementInfo&, const char*) at 0x249b00 / 0x250dc4 / 0x250e20 (80 / 92 /
  100); nine int ActorInitInfo wrappers tryGetArg0..8 (92 each, inline "ArgN"
  literal), tryGetArg0/2(int*, PlacementInfo) 0x26ee58 / 0x2670d8, nine float and
  eight bool ActorInitInfo tail-call wrappers (20 each), two float and five bool
  PlacementInfo tail-call wrappers (16 each), getLinksArg0 0x1de7cc (152,
  descriptive name) and Rail::getTotalLength 0x260fa8 (28, RailPart record).
  Tail-call wrappers live in the new unit `Source/al/Placement/
  PlacementArgFunction.cpp`; bodies and int wrappers stay in PlacementFunction.cpp.

Eight upstream rows that already compiled byte-exact were promoted separately
(LMS_SetMemFuncs/LMSi_Free/LMSi_Malloc/LMS_CloseMessage/LMS_GetTextNum/
LMS_InitMessage, nn::dbg::Break, __ctr_start; 300 bytes, not new source).

Compiler/linker rules established (each reproduced by the pinned ARMCC):

- armlink `--inline` copies of standalone `bool` accessors appear as `ldrsb` in
  callers; the accessor definitions and such callers must be in different
  translation units (ActorModelFunction.cpp vs LiveActorFunction.cpp).
- A tail-call wrapper must not share a unit with the body it branches to (the
  float/bool ArgN wrappers); a wrapper that inlines a body must share its unit
  (the int ArgN wrappers, getLinksArg0). The float and bool bodies are built on
  the int body: `if (tryGetArg(&value, info, key)) { *out = value; ... }` and
  `if (value == 0) *out = false; else *out = true;` reproduce 0x250dc4 / 0x250e20
  exactly (register order r6 = iter, r5 = key follows from the inlined call).
- String literal form: a literal occurrence duplicated by inlining becomes a
  shared `.constdata` pointer (`ldr rX,[pc]`); a single occurrence stays an
  inline `add rX, pc` literal. 0x26ee58 ("Arg0") is pointer-form because
  getLinksArg0 inlines it; 0x267134 ("Arg1") implies a dead-stripped inliner and
  stays rank U (84 bytes) with the inline-literal compile differing.
- `e320f000` NOPs after `cmp` following some bool-returning calls are compiler
  output (HitSensorKeeper::getSensor, getLinksArg0), not linker NOPs.
- Symbols sizes follow st_size: trailing pointer literal pools are excluded,
  inline string literals included. Ghidra sizes stay unreliable; never run
  Tools/progress.py.

Image order is not grouped by translation unit (ByamlIter methods span
0x24c85c..0x2910f8); unit membership is inferred only from inlining evidence.

Open: FileLoader::isExistArchive 0x32f3e8 (44, prologue order `cmp/movne/push/
ldreq` not reproduced; stays U), tryGetArg1(int*, PlacementInfo) 0x267134, and
the seadVector static initializer 0x383870 (1,424 vs 312): the original
initializes Vector2/3/4 statics for s32, u32, f32 and f64 (60 objects, order
zero/ex/ey/ones, zero/ex/ey/ez/ones, zero/ex/ey/ez/ew/ones per type); the 60 .bss
addresses are the `ldr r0,[pc]` literals from 0x383cf0 (first 0x3f3664,
0x3f364c, 0x3f3654, 0x3f365c, 0x430634, ...) and belong in
DataSymbols/sead/math/seadVector.sym before extending seadVector.cpp.

Whole-source partial image: prepare `Build/whole/build.json` (151 units),
runtime link `Build/whole-runtime/711d8abc001ac850`, independent
`verify_image.py`: **4.6787%** (144,880 / 3,096,576 raw words; previous
4.5634%, inherited baseline 4.0704%; Data/Code.json unchanged). ELF SHA-256
`af0009d0f70b1c9ba59a5ddff57585656da6bc95894df47dceedf7f5890b8be0`, partial
image `0388b9f6822be654c19f758585e19d1a5bb9812cc6428d7711fff2fad1639c75`
(the pre-promotion build e1171540cbcedbe0 measured 4.6715%). Tools/headless.py
verify (run before the final promotions): 53 tests, 4,270 ARM
comparisons, passed. Stubs.c: 18 stubs removed (recovered), FUN_002ddc68 folded
into the existing preScaleMtx stub, 8 new dependency stubs inserted before
`#undef STUB` (ClippingActorHolder::addToClipping/removeFromClipping,
CollisionParts::resetMtxFromJoint/resetMtx/syncMtxFromJoint/syncMtx,
ResourceHolder::findOrCreateResource, sead::FileDevice::tryIsExistFile).

Cumulative clean-base header patch `Tools/patches/RedPepper-Headers-placement-
args.patch` SHA-256
`fedc0c658a5f4d6378038916f95cfad8e2627ddddb97e8e8b79f222cab03f4f6` (base
835050ad, applied to a clean clone and diffed identical; includes the new
ResourceHolder.h, CollisionContact.h, CollisionPath.h, Light/). nnsdk patch
unchanged. Immutable checkpoint `Build/matching/milestones/2026-10-19-placement-
args.json` SHA-256
`ffa2d2b2b7e539e34dbf1758d11a312ae4a6897aeeba5ebaa535629205e8a871` with 335
source/report snapshots in the sibling placement-args-sources directory. All
previous checkpoints preserved. Nothing committed, pushed or published; no
Ghidra annotation/export, original asset or May 2026 file changed.

## Headless analysis state

The EU Ghidra export finished with 12,181 automatically discovered functions,
12,180 pseudocode files and one timeout at 0x001a9574 (about 45 KB; review the
boundary first). No Ghidra or matcher process is active at this checkpoint.
These counts are machine analysis, not source progress. Do not repeat the export
without a specific reason or overwrite reviewed annotations.

Tools/ReviewNerveRegistration.java verified stock memory and pinned prior
source/test/ELF hashes, then created reviewed structures and a USER_DEFINED
initializer signature preserving the shared tail. Evidence and typed output
are under .local/analysis/reviewed/. Its verification snapshot is historic:
later NerveKeeper changes must not be claimed as part of that review. Do not
rerun the script blindly over the reviewed signature. State vtable slots after
init still need review.

## Commands and next bounded batch

All Python commands use .local/venv/bin/python. Start by inspecting status and
active processes; do not duplicate running imports/builds:

```sh
.local/venv/bin/python Tools/headless.py status
```

1. Preserve partial image **4.6787%** at `Build/whole-runtime/711d8abc001ac850`.
   Read the latest placement-args checkpoint and retain all 4,270 comparisons,
   the 3,452 + 520 exact bytes and prior source/byte proofs. Keep metrics
   separate. Next byte sources, largest first: the Collider family (resolve
   1,840, finalizeContacts 1,256, respondContacts 1,152, collectContacts 472,
   sweepShapeChange 404; all M), the seadVector static initializer (needs the
   60 DataSymbols rows above and a decision on touching the clean sead
   submodule), ClippingActorHolder add/remove bodies, CollisionParts
   reset/sync matrix helpers, ExecuteRequestKeeper::request (220), preScaleMtx
   (116), and the 19 KB of M/m near-misses in progress-full-2026-10-19.json.
2. Recover the collision engine behind director+4 (virtual slot +0x14 sphere
   query), the CollisionParts/engine structures it fills, and the remaining
   geometry/math dependencies still executed as original analysis inputs.
   Review full ARM extents, shared tails and scalar VFP arguments first; apply
   the branch-NOP rule only where the resolved target is the next instruction.
   Remove the global kit interception 0x277250 only with its actual body and
   fixtures. Keep FUN_0027d5c4 and calcPositionDelta M unless a natural source
   form reproduces the original load pairing/register assignment; both are
   recorded in .local/analysis/reviewed/collision-query-source.json.
3. Keep the full resolver and four sweep helpers NON_MATCHING until true source
   byte matches. Full original resolver range is 1,840 bytes, native s0-s2 return;
   do not shrink it to Ghidra's 1,820 instruction bytes. Original/compiled sizes
   and register/scheduling differences are recorded. Source/ABI choices and full
   class layouts remain partly inferred. Pursue source/compiler matches when
   useful without opcode rewriting, padded sparse images or rank inflation.
4. Preserve provisional effect update/validity and its 421 behavior comparisons;
   lower-level effect setters at 0x23f294/0x2d37d0 are still missing. Continue real
   game routines and focused checks. Include LiveActorFunction.cpp/MovementNoop.cpp
   with LiveActor.cpp for compiled leaf helpers. Only promote ranks after exact
   size/address/bytes and encoded destination checks.
5. After meaningful changes, run Tools/headless.py verify, focused matching.py,
   whole_build.py --prepare-only, whole_runtime_build.py and independent image /
   function checks. Whole images use only actual source/stubs and genuine runtime
   members. Stock-address dependency aliases are analysis-only, never production.
   Insert new stubs before #undef STUB. Original armlink's known license prerequisite
   is unchanged; do not repeat its probe or download versions to evade licensing.

Background continuation remains ACTIVE every four hours in the app. The user's
persistent goal is the full independently verified EU decompilation and rebuild.
Make concrete bounded batches; keep reporting meaningful progress with metric
names, the inherited baseline and newly recovered routines/bytes. Stay quiet
when unchanged, and notify only on milestones, completion, failure or required
user action. Do not stop the schedule until actual completion or cancellation.
Keep the app/machine available for local runs. Do not push or publish.

Research reference: https://github.com/yibie/awesome-rea for independent
verification gates and relevant headless reverse-engineering tools.
