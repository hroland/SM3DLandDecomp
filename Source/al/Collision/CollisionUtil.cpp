#include "al/Collision/CollisionUtil.h"
#include "al/Collision/CollisionParts.h"
#include "al/LiveActor/ActorPoseKeeper.h"
#include "al/LiveActor/LiveActor.h"

namespace al {

bool isCollidedGround(const LiveActor* actor)
{
    return actor->getCollider()->getGroundDistance() >= 0;
}

void syncCollisionMtx(LiveActor* actor, const sead::Matrix34f* mtx)
{
    CollisionParts* parts = actor->getCollisionParts();
    if (!parts->isValidBySystem())
        return;
    if (parts->getJointMtx()) {
        parts->syncMtxFromJoint();
    } else if (mtx) {
        parts->syncMtx(*mtx);
    } else {
        sead::Matrix34f baseMtx;
        makeMtxSRT(&baseMtx, actor);
        parts->syncMtx(baseMtx);
    }
}

} // namespace al
