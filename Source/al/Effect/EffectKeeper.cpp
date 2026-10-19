#include "al/Effect/EffectKeeper.h"

// Existing unnamed EU entry; the effect-object type/name remain unreviewed.
extern "C" void FUN_001ea00c(void* effect, bool pause);
extern "C" bool FUN_001ea220(void* effect);

namespace al {

void EffectKeeper::update()
{
    if (mNeedsUpdate) {
        bool needsUpdate = false;
        for (int i = 0; i < mEffects.size(); i++) {
            if (FUN_001ea220(mEffects.unsafeAt(i)))
                needsUpdate = true;
        }
        mNeedsUpdate = needsUpdate;
    }
}

void EffectKeeper::pauseAll()
{
    for (int i = 0; i < mEffects.size(); i++)
        FUN_001ea00c(mEffects.unsafeAt(i), true);
}

void EffectKeeper::resumeAll()
{
    for (int i = 0; i < mEffects.size(); i++)
        FUN_001ea00c(mEffects.unsafeAt(i), false);
}

} // namespace al
