#include "al/LiveActor/LiveActorKit.h"

// armlink placed the director getters directly behind these wrappers
// (--tailreorder) and turned each tail branch into a NOP (--branchnop); the
// 20/28-byte wrapper extents end at those NOPs, before the shared getter tails.
extern "C" u32 FUN_00334298()
{
    return al::getLiveActorKit()->getCollisionDirector()->getResultCount();
}

extern "C" const al::CollisionContact* FUN_001d43c0(u32 index)
{
    return al::getLiveActorKit()->getCollisionDirector()->getResult(index);
}

extern "C" const sead::Vector3f* FUN_00262dd4(const al::CollisionContact* contact, int index)
{
    return &contact->normals[index];
}

// Global director accessor used by the collider resolution; original name unknown.
extern "C" al::CollisionDirector* FUN_001676e0()
{
    return al::getLiveActorKit()->getCollisionDirector();
}

// Global engine accessor behind the director (EU 0x001676f0); original name unknown.
extern "C" al::CollisionDirector::QueryEngine* FUN_001676f0()
{
    return al::getLiveActorKit()->getCollisionDirector()->getEngine();
}

// Sphere query wrappers. Both store the filters through the director's
// out-of-line setters (armlink --inline copies in the original) before the
// shared query; the second variant's tail branch lands on the adjacent query
// body in the original image and is therefore a --branchnop NOP there.
extern "C" bool FUN_002673b0(const sead::Vector3f* center, u32 filterA, u32 filterB, float radius)
{
    al::CollisionDirector* director = al::getLiveActorKit()->getCollisionDirector();
    director->setQueryFilterA(filterA);
    director->setQueryFilterB(filterB);
    return director->querySphere(center, 0, radius);
}

extern "C" bool FUN_0025c9f8(const sead::Vector3f* center, u32 filterA, u32 filterB, float radius)
{
    al::CollisionDirector* director = al::getLiveActorKit()->getCollisionDirector();
    director->setQueryFilterA(filterA);
    director->setQueryFilterB(filterB);
    return director->querySphere(center, 1, radius);
}
