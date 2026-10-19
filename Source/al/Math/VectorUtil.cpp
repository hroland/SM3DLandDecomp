#include "al/Math/VectorUtil.h"

namespace al {

void lerpVec(sead::Vector3f* out, const sead::Vector3f& from, const sead::Vector3f& to, float amount)
{
    out->x = from.x + (to.x - from.x) * amount;
    out->y = from.y + (to.y - from.y) * amount;
    out->z = from.z + (to.z - from.z) * amount;
}

} // namespace al

// Reviewed EU in-place normalization helper (0x0027ccbc); original SDK name unknown.
extern "C" float FUN_0027ccbc(void* vector);
// Reviewed EU scale-add helper (0x0027cca0): out = base + vector * scale.
extern "C" void FUN_0027cca0(void* out, const void* vector, float scale, const void* base);

namespace {
// Tolerance-based predicate kept out of line from the constant so ARMCC emits
// the original VFP compare instead of its integer bit-pattern shortcut.
inline bool isNearZero(const sead::Vector3f& vector, float tolerance)
{
    return vector.squaredLength() < tolerance * tolerance;
}
} // namespace

// The original loads y and z separately (y hoisted above x*x); ARMCC pairs
// them into one vldmia here, so 16 bytes differ. Behavior is identical.
NON_MATCHING
extern "C" bool FUN_0027d5c4(sead::Vector3f* vector)
{
    if (isNearZero(*vector, 0.001f)) {
        vector->x = 0.0f;
        vector->y = 0.0f;
        vector->z = 0.0f;
        return true;
    }
    FUN_0027ccbc(vector);
    return false;
}

extern "C" void FUN_0027306c(sead::Vector3f* out, const sead::Vector3f* normal, const sead::Vector3f* vector)
{
    FUN_0027cca0(out, normal, -normal->dot(*vector), vector);
}
