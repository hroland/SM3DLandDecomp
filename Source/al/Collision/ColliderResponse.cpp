#include "al/Collision/Collider.h"

extern "C" bool FUN_0023fb04(const sead::Vector3f*, const sead::Vector3f*);
extern "C" bool FUN_0023fa8c(const sead::Vector3f*, const sead::Vector3f*);
extern "C" bool FUN_0025c780(const al::CollisionContact*);
extern "C" bool FUN_0033745c(const al::CollisionContact*);
extern "C" void FUN_0033162c(const al::CollisionContact*, sead::Vector3f*, sead::Vector3f*);
extern "C" void FUN_0026ffc8(const al::CollisionContact*, sead::Vector3f*, sead::Vector3f*);

namespace {
inline void accumulateComponent(float* positive, float* negative, float value)
{
    if (*positive < value)
        *positive = value;
    else
        *negative = value <= *negative ? value : *negative;
}

inline void accumulate(sead::Vector3f* positive, sead::Vector3f* negative,
                       const sead::Vector3f& value)
{
    accumulateComponent(&positive->x, &negative->x, value.x);
    accumulateComponent(&positive->y, &negative->y, value.y);
    accumulateComponent(&positive->z, &negative->z, value.z);
}
}

namespace al {

NON_MATCHING
void Collider::respondContacts(CollisionContact* contacts, sead::Vector3f* correction,
                               sead::Vector3f* normal, bool, u32 startIndex)
{
    // The original stores the fifth caller argument on the stack but never
    // reads it in this body. Its internal selection pass is always enabled.
    mFlags &= ~0x38;
    for (u32 i = startIndex; i < mContactCount; ++i) {
        const CollisionContact& contact = contacts[i];
        if (FUN_0023fb04(&contact.normals[0], mGravity)) {
            if (FUN_0025c780(&contact))
                mFlags |= 8;
        } else if (FUN_0023fa8c(&contact.normals[0], mGravity)) {
            if (FUN_0025c780(&contact))
                mFlags |= 0x10;
        } else if (FUN_0025c780(&contact)) {
            mFlags |= 0x20;
        }
    }
    sead::Vector3f positive(0.0f, 0.0f, 0.0f), negative(0.0f, 0.0f, 0.0f);
    sead::Vector3f normalPositive(0.0f, 0.0f, 0.0f), normalNegative(0.0f, 0.0f, 0.0f);
    for (u32 i = startIndex; i < mContactCount; ++i) {
        const CollisionContact& contact = contacts[i];
        u8 mask;
        if (FUN_0023fb04(&contact.normals[0], mGravity))
            mask = 8;
        else if (FUN_0023fa8c(&contact.normals[0], mGravity))
            mask = 0x10;
        else
            mask = 0x20;
        sead::Vector3f displacement, surfaceNormal;
        if (mFlags & mask)
            FUN_0026ffc8(&contact, &displacement, &surfaceNormal);
        else
            FUN_0033162c(&contact, &displacement, &surfaceNormal);
        accumulate(&positive, &negative, displacement);
        if (normal)
            accumulate(&normalPositive, &normalNegative, surfaceNormal);
        if ((mFlags & 2) && FUN_0033745c(&contact)) {
            const sead::Vector3f& carry = contact._78;
            if (!(displacement.dot(carry) < 0.0f)) {
                accumulate(&positive, &negative, carry);
                if (normal)
                    accumulate(&normalPositive, &normalNegative, carry);
            }
        }
    }
    *correction = positive + negative;
    if (normal)
        *normal = normalPositive + normalNegative;
}

} // namespace al
