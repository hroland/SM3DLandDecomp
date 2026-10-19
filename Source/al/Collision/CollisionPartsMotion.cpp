#include "al/Collision/CollisionParts.h"
#include <nn/math/math_VEC3.h>

// Reviewed EU matrix-vector helper (0x0027cb9c): out = matrix * vector.
extern "C" void FUN_0027cb9c(void* out, const void* matrix, const void* vector);

namespace al {

// The original keeps pos in r4, this in r5 and delta in r6; ARMCC assigns
// r4/r5/r6 in parameter order here, so the three callee-saved copies and the
// matching call-argument moves differ. Calls and stack layout are identical.
NON_MATCHING
void CollisionParts::calcPositionDelta(sead::Vector3f* delta, const sead::Vector3f* pos) const
{
    sead::Vector3f moved;
    FUN_0027cb9c(&moved, &mPrevMtxInv, pos);
    FUN_0027cb9c(&moved, &mMtx, &moved);
    nn::math::ARMv6::VEC3SubAsm(delta, &moved, pos);
}

} // namespace al
