#include "al/Collision/CollisionContact.h"
#include "al/Collision/CollisionParts.h"
#include "al/Math/VectorUtil.h"

namespace {
// Only the accessed original prefix is described, not the complete parts type.
struct PartsPrefix {
    u8 opaque[0x134];
    u32 disabled;
};
}

extern "C" bool FUN_0025c780(const al::CollisionContact* contact)
{
    return contact->flags == 1;
}

extern "C" bool FUN_0033745c(const al::CollisionContact* contact)
{
    return static_cast<const PartsPrefix*>(contact->parts)->disabled == 0;
}

// Platform motion carried by the contact's parts (0x00331f18). The original
// tail branch reaches the adjacent method body and was emitted as armlink's NOP.
extern "C" void FUN_00331f18(const al::CollisionContact* contact, sead::Vector3f* delta,
                             const sead::Vector3f* pos)
{
    static_cast<const al::CollisionParts*>(contact->parts)->calcPositionDelta(delta, pos);
}

NON_MATCHING
extern "C" void FUN_0026ffc8(const al::CollisionContact* contact,
                              sead::Vector3f* correction, sead::Vector3f* normal)
{
    const sead::Vector3f* contactNormal = &contact->normals[0];
    nn::math::ARMv6::VEC3MulAsm(correction, contactNormal, contact->distance);
    if (normal)
        *static_cast<nn::math::VEC3*>(normal) = *contactNormal;
}

NON_MATCHING
extern "C" void FUN_0033162c(const al::CollisionContact* contact,
                              sead::Vector3f* correction, sead::Vector3f* normal)
{
    const sead::Vector3f* contactNormal = &contact->normals[0];
    if (contact->flags == 1) {
        nn::math::ARMv6::VEC3MulAsm(correction, contactNormal, contact->distance);
        if (normal)
            *static_cast<nn::math::VEC3*>(normal) = *contactNormal;
        return;
    }
    sead::Vector3f direction;
    nn::math::ARMv6::VEC3SubAsm(&direction, &contact->_6C, &contact->_60);
    FUN_0027d5c4(&direction);
    sead::Vector3f displacement;
    nn::math::ARMv6::VEC3MulAsm(&displacement, contactNormal, contact->distance);
    sead::Vector3f originalNormal = *contactNormal;
    nn::math::ARMv6::VEC3MulAsm(correction, &direction, displacement.dot(direction));
    nn::math::ARMv6::VEC3MulAsm(normal, &direction, originalNormal.dot(direction));
}
