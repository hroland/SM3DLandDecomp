#include "al/Collision/Collider.h"
#include "al/Collision/CollisionDirector.h"
#include "al/Collision/CollisionPath.h"
#include "al/Math/MathUtil.h"
#include "al/Math/VectorUtil.h"

// Temporary EU entry names. Pointer/float arguments are reviewed from ARM call
// sites; lower-level identities and complete types remain unknown.
extern "C" al::CollisionDirector* FUN_001676e0();
extern "C" bool FUN_0033745c(const al::CollisionContact*);
extern "C" void FUN_00331f18(const al::CollisionContact*, sead::Vector3f*, const sead::Vector3f*);
extern "C" void FUN_0025c824(al::CollisionPath*, const sead::Vector3f*, const sead::Vector3f*,
                             float, float, float);
extern "C" void FUN_0025c790(const al::CollisionPath*, sead::Vector3f*, float*, sead::Vector3f*);
extern "C" void FUN_0025c7f8(al::CollisionPath*);
extern "C" void FUN_001da3ac(const al::CollisionPath*, sead::Vector3f*);
extern "C" bool FUN_0026f71c(const sead::Vector3f*, float);
extern "C" bool FUN_001ea8a0(al::Collider*, al::CollisionPath*, sead::Vector3f*, float*,
                             al::CollisionContact*, u32);
extern "C" bool FUN_002673b0(const sead::Vector3f*, u32, u32, float);
extern "C" bool FUN_0025c9f8(const sead::Vector3f*, u32, u32, float);
extern "C" int FUN_0023eda8(al::Collider*, al::CollisionContact*, u32);
extern "C" void FUN_0023e928(al::Collider*, al::CollisionContact*, sead::Vector3f*,
                             sead::Vector3f*, bool, int);
extern "C" void FUN_0027cca0(void*, const void*, float, const void*);
extern "C" void FUN_001eaa44(al::Collider*, al::CollisionContact*);

namespace {
// Both original sampling loops snapshot filters once, while reading flags on
// every sample. A contact callback may modify the collider between the loops.
inline bool sampleCollision(al::CollisionPath* path, const u8* flags, u32 filter0,
                            u32 filter1, al::Collider* collider,
                            al::CollisionContact* contacts, u32 capacity, int* count)
{
    while (!path->isFinished()) {
        sead::Vector3f center;
        float radius;
        FUN_0025c790(path, &center, &radius, nullptr);
        bool hit = (*flags & 2) ? FUN_0025c9f8(&center, filter1, filter0, radius)
                               : FUN_002673b0(&center, filter1, filter0, radius);
        if (hit) {
            int added = FUN_0023eda8(collider, contacts, capacity);
            if (count)
                *count = added;
            return true;
        }
        FUN_0025c7f8(path);
    }
    return false;
}
} // namespace

namespace al {

NON_MATCHING
sead::Vector3f Collider::resolve(const sead::Vector3f& velocity)
{
    CollisionContact* contacts;
    u32 capacity;
    if (mQueryCapacity) {
        contacts = mQueryBuffer;
        capacity = mQueryCapacity;
    } else {
        FUN_001676e0()->getDefaultContactBuffer(&contacts, &capacity);
    }

    sead::Vector3f center(0.0f, 0.0f, 0.0f);
    sead::Vector3f movement(0.0f, 0.0f, 0.0f);
    calcCenter(&center);
    sead::Vector3f previous = mPreviousCenter;
    float previousRadius = mPreviousRadius;
    float step = mRadius * 0.9f < mPreviousRadius * 0.9f
                     ? mRadius * 0.9f : mPreviousRadius * 0.9f;
    if (step > 35.0f)
        step = 35.0f;

    sead::Vector3f platformMotion(0.0f, 0.0f, 0.0f);
    if ((mFlags & 1) && mGroundDistance >= 0.0f && FUN_0033745c(&mGroundContact)) {
        FUN_00331f18(&mGroundContact, &platformMotion, &center);
        if (platformMotion.dot(mGroundContact.normals[0]) > 0.0f)
            FUN_0027306c(&platformMotion, &mGroundContact.normals[0], &platformMotion);
    }

    mContactCount = 0;
    mGroundDistance = mWallDistance = mCeilingDistance = -99999.0f;
    mCorrection.set(0.0f, 0.0f, 0.0f);

    CollisionPath path;
    path.start.set(0.0f, 0.0f, 0.0f);
    path.delta.set(0.0f, 0.0f, 0.0f);
    path.startRadius = 0.0f;
    path.endRadius = 0.0f;
    path.step = 0.0f;
    path.t = 0.0f;
    path.previousT = 0.0f;
    sead::Vector3f destination = center + platformMotion;
    FUN_0025c824(&path, &mPreviousCenter, &destination, mPreviousRadius, mRadius, step);
    int count = 0;
    sead::Vector3f transformDelta = center + platformMotion - mPreviousCenter;
    if (!FUN_0026f71c(&transformDelta, 0.001f)
        || !al::isNearZero(mPreviousRadius - mRadius, 0.001f)) {
        FUN_001ea8a0(this, &path, &previous, &previousRadius, contacts, capacity);
    }

    step = mPreviousRadius * 0.9f;
    if (step > 35.0f)
        step = 35.0f;
    destination = previous + velocity;
    FUN_0025c824(&path, &previous, &destination, mRadius, mRadius, step);

    if (!sampleCollision(&path, &mFlags, mFilter0, mFilter1, this, contacts, capacity, &count)) {
        movement = previous - center;
        movement += velocity;
    } else {
        sead::Vector3f totalCorrection(0.0f, 0.0f, 0.0f);
        bool first = true;
        int processed = 0;
        for (;;) {
            sead::Vector3f correction(0.0f, 0.0f, 0.0f);
            sead::Vector3f normal(0.0f, 0.0f, 0.0f);
            FUN_0023e928(this, contacts, &correction, &normal, first, processed);
            first = false;
            processed += count;

            sead::Vector3f remaining;
            FUN_0025c790(&path, &previous, &previousRadius, &remaining);
            previous += correction;
            totalCorrection += correction;
            sead::Vector3f slideNormal = correction;
            if (FUN_0026f71c(&slideNormal, 0.001f))
                slideNormal = normal;
            FUN_0027d5c4(&slideNormal);
            float projection = remaining.dot(slideNormal);
            if (projection < 0.0f)
                FUN_0027cca0(&remaining, &slideNormal, -projection, &remaining);

            if (velocity.dot(remaining) < 0.0f)
                break;

            destination = previous + remaining;
            FUN_0025c824(&path, &previous, &destination, previousRadius, mRadius, step);
            FUN_0025c7f8(&path);
            count = 0;
            if (!sampleCollision(&path, &mFlags, mFilter0, mFilter1, this,
                                 contacts, capacity, &count)) {
                FUN_001da3ac(&path, &previous);
                break;
            }
            if (!(path.t < 1.0f)) {
                FUN_001da3ac(&path, &previous);
                if (count > 0) {
                    FUN_0023e928(this, contacts, &correction, nullptr, false, processed);
                    previous += correction;
                }
                break;
            }
        }
        FUN_001eaa44(this, contacts);
        mCorrection = totalCorrection;
        movement = previous - center;
    }

    mPreviousCenter = center + movement;
    mPreviousRadius = mRadius;
    if (mGroundDistance < 0.0f) {
        u32 next = mFramesSinceGrounded + 1;
        if (mFramesSinceGrounded < next)
            mFramesSinceGrounded = next;
    } else {
        mFramesSinceGrounded = 0;
        mPreviousGroundNormal = mGroundContact.normals[0];
    }
    return movement;
}

} // namespace al
