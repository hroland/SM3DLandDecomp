#include "al/Collision/Collider.h"

extern "C" u32 FUN_00334298();
extern "C" const al::CollisionContact* FUN_001d43c0(u32);
extern "C" const sead::Vector3f* FUN_00262dd4(const al::CollisionContact*, int);
extern "C" bool FUN_0023fb04(const sead::Vector3f*, const sead::Vector3f*);
extern "C" bool FUN_0023fa8c(const sead::Vector3f*, const sead::Vector3f*);

namespace al {

NON_MATCHING
int Collider::collectContacts(CollisionContact* contacts, u32 capacity)
{
    u32 total = FUN_00334298();
    int added = 0;
    for (u32 i = 0; i < total; ++i) {
        if (capacity <= mContactCount + added) {
            u32 previous = mContactCount;
            mContactCount = capacity;
            return capacity - previous;
        }
        const CollisionContact* source = FUN_001d43c0(i);
        contacts[mContactCount + added] = *source;
        ++added;
    }
    mContactCount += added;
    return added;
}

NON_MATCHING
void Collider::finalizeContacts(CollisionContact* contacts)
{
    for (u32 i = 0; i < mContactCount; ++i) {
        const CollisionContact& contact = contacts[i];
        const sead::Vector3f* normal = FUN_00262dd4(&contact, 0);
        if (FUN_0023fb04(normal, mGravity)) {
            if (mGroundDistance < contact.distance) {
                mGroundContact = contact;
                mGroundDistance = contact.distance;
            }
        } else if (FUN_0023fa8c(normal, mGravity)) {
            if (mWallDistance < contact.distance) {
                mWallContact = contact;
                mWallDistance = contact.distance;
            }
        } else if (mCeilingDistance < contact.distance) {
            mCeilingContact = contact;
            mCeilingDistance = contact.distance;
        }
    }
}

} // namespace al
