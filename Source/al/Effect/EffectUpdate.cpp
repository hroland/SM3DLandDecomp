#include "types.h"
#include <sead/math/seadMatrix.h>
#include <sead/math/seadVector.h>

// Reviewed prefixes only; original class/method names and complete types are
// unknown. These field names describe observed update behavior.
namespace {
struct EffectParamsPrefix {
    u8 _0[0x14];
    sead::Vector3f localOffset;
    float scale;
    u8 _24[0x3f - 0x24];
    bool updatePosition;
    bool updateMatrix;
    u8 _41[4];
    bool transformOffset;
};
} // namespace

extern "C" bool FUN_0023f45c(void*);
extern "C" void FUN_0023f294(void*, const void*, const void*);
extern "C" void FUN_0027cb9c(void*, const void*, const void*);
extern "C" void FUN_00291470(void*, const void*);
extern "C" void FUN_002d37d0(void*, const void*, const void*, const void*);

namespace {
inline void applyEffectMatrix(void* handle, const EffectParamsPrefix* params,
                              const sead::Matrix34f* matrix)
{
    if (params->transformOffset) {
        sead::Vector3f position;
        FUN_0027cb9c(&position, matrix, &params->localOffset);
        sead::Matrix34f transformed;
        FUN_00291470(&transformed, matrix);
        transformed.setTranslation(position);
        FUN_0023f294(handle, params, &transformed);
    } else {
        FUN_0023f294(handle, params, matrix);
    }
}
} // namespace

namespace al {
// Descriptive class name for this reviewed prefix, not an original name.
class EffectEntry {
    u8 _0[4];
    void** mHandles;
    int mCount;
    EffectParamsPrefix* mParams;
    const sead::Vector3f* mPosition;
    const sead::Matrix34f* mMatrix;

public:
    bool update();
};

NON_MATCHING
bool EffectEntry::update()
{
    bool updated = false;
    for (int i = 0; i < mCount; ++i) {
        void* handle = mHandles[i];
        if (FUN_0023f45c(handle)) {
            EffectParamsPrefix* params = mParams;
            if (params->updateMatrix) {
                applyEffectMatrix(handle, params, mMatrix);
                updated = true;
            }
            if (mParams->updatePosition) {
                FUN_002d37d0(handle, mParams, mPosition, mMatrix);
                updated = true;
            }
        }
    }
    return updated;
}
} // namespace al
