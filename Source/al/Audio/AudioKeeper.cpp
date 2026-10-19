#include "al/Audio/AudioKeeper.h"

// Unnamed lower-level audio callbacks; only their pointer arguments are reviewed.
extern "C" void FUN_001d9dc0(void*);
extern "C" void FUN_001da074(void*);

// Existing unnamed EU entry; the control object and argument meanings are
// not fully typed. The original stop routine passes zero.
extern "C" void FUN_001d9f10(void* control, int value);

namespace al {

void AudioKeeper::update()
{
    if (mControl->mCount > 0) {
        FUN_001d9dc0(mHandle);
        FUN_001da074(mControl);
    }
}

void AudioKeeper::activate()
{
    mActive = true;
}

void AudioKeeper::stopAll()
{
    FUN_001d9f10(mControl, 0);
    mActive = false;
}

} // namespace al
