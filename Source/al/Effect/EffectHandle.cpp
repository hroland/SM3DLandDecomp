#include "types.h"

namespace {
// Reviewed prefixes; identities, remaining fields and complete sizes unknown.
struct EmitterPrefix {
    u8 _0[4];
    int count;
    u8 _8[4];
    u32 generation;
};
struct EmitterReferencePrefix {
    EmitterPrefix* emitter;
    u32 generation;

};
struct EffectHandlePrefix {
    u8 _0[4];
    EmitterReferencePrefix* reference;
};
} // namespace

NON_MATCHING
extern "C" bool FUN_0023f45c(void* pointer)
{
    const EmitterReferencePrefix* reference =
        static_cast<EffectHandlePrefix*>(pointer)->reference;
    const EmitterPrefix* emitter = reference->emitter;
    if (!emitter)
        return false;
    u32 generation = reference->generation;
    if (emitter->generation != generation)
        return false;
    return emitter->count > 0;
}
