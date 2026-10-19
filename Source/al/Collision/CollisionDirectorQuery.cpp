#include "al/Collision/CollisionDirector.h"

namespace al {

u32 CollisionDirector::getResultCount() const
{
    return _14->count;
}

const CollisionContact* CollisionDirector::getResult(u32 index) const
{
    return _14->contacts[index];
}

void CollisionDirector::getDefaultContactBuffer(CollisionContact** contacts, u32* capacity) const
{
    *contacts = mDefaultContacts;
    *capacity = 32;
}

// The EU callers contain these stores inline where armlink replaced each
// branch-and-link with the callee's single instruction. The out-of-line bodies
// are kept so the same source-derived optimization applies; their original
// addresses are unknown.
void CollisionDirector::setQueryFilterA(u32 filter)
{
    mQueryFilterA = filter;
}

void CollisionDirector::setQueryFilterB(u32 filter)
{
    mQueryFilterB = filter;
}

bool CollisionDirector::querySphere(const sead::Vector3f* center, u32 variant, float radius)
{
    QueryPrefix* results = _14;
    for (int i = 0; i < static_cast<int>(results->count); i++) {
        // Released results reuse their first word as the free-list link.
        CollisionContact* contact = results->contacts[i];
        contact->parts = results->freeList;
        results->freeList = contact;
    }
    results->count = 0;

    CollisionQueryInfo info(center, radius);
    info.filterA = mQueryFilterA;
    info.filterB = mQueryFilterB;
    bool hit = mEngine->querySphere(_14, &info, variant);
    mQueryFilterA = 0;
    mQueryFilterB = 0;
    return hit;
}

} // namespace al
