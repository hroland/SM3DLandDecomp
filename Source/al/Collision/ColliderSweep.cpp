#include "al/Collision/Collider.h"
#include "al/Collision/CollisionPath.h"

extern "C" void FUN_0025c790(const al::CollisionPath*, sead::Vector3f*, float*, sead::Vector3f*);
extern "C" void FUN_0025c7f8(al::CollisionPath*);
extern "C" bool FUN_002673b0(const sead::Vector3f*, u32, u32, float);
extern "C" bool FUN_0025c9f8(const sead::Vector3f*, u32, u32, float);

namespace al {

NON_MATCHING
bool Collider::sweepShapeChange(CollisionPath* path, sead::Vector3f* center, float* radius,
                                CollisionContact* contacts, u32 capacity)
{
    bool hitAny = false;
    sead::Vector3f totalCorrection(0.0f, 0.0f, 0.0f);
    u32 filter0 = mFilter0;
    u32 filter1 = mFilter1;
    while (!path->isFinished()) {
        sead::Vector3f sample;
        float sampleRadius;
        FUN_0025c790(path, &sample, &sampleRadius, nullptr);
        bool hit;
        if (mFlags & 2) {
            sead::Vector3f shifted = sample + totalCorrection;
            hit = FUN_0025c9f8(&shifted, filter1, filter0, sampleRadius);
        } else {
            hit = FUN_002673b0(&sample, filter1, filter0, sampleRadius);
        }
        if (hit) {
            hitAny = true;
            collectContacts(contacts, capacity);
            sead::Vector3f correction(0.0f, 0.0f, 0.0f);
            respondContacts(contacts, &correction, nullptr, false, 0);
            totalCorrection += correction;
            if (path->t >= 1.0f)
                break;
        }
        FUN_0025c7f8(path);
    }
    FUN_0025c790(path, center, radius, nullptr);
    *center += totalCorrection;
    if (hitAny) {
        finalizeContacts(contacts);
        mContactCount = 0;
    }
    return hitAny;
}

} // namespace al
