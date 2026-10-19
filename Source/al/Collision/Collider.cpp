#include "al/Collision/Collider.h"
#include <string.h>

namespace al {

void Collider::onInvalidate()
{
    mContactCount = 0;
    mCeilingDistance = mWallDistance = mGroundDistance = -99999.0f;
    mCorrection.set(0.0f, 0.0f, 0.0f);
    mFramesSinceGrounded = 0xffffffff;
    calcCenter(&mPreviousCenter);
    mPreviousRadius = mRadius;
}

void Collider::calcCenter(sead::Vector3f* out) const
{
    // Preserve component copy order and float bits. This spelling is a matching
    // source choice; the original copy helper is unknown.
    const sead::Vector3f* trans = mTrans;
    memcpy(&out->x, &trans->x, sizeof(float));
    memcpy(&out->y, &trans->y, sizeof(float));
    out->z = trans->z;
    if (mLocalOffset) {
        if ((mFlags & 4) && mBasis) {
            out->x += mBasis->m[0][0] * mLocalOffset->x;
            out->x += mBasis->m[0][1] * mLocalOffset->y;
            out->x += mBasis->m[0][2] * mLocalOffset->z;
            out->y += mBasis->m[1][0] * mLocalOffset->x;
            out->y += mBasis->m[1][1] * mLocalOffset->y;
            out->y += mBasis->m[1][2] * mLocalOffset->z;
            out->z += mBasis->m[2][0] * mLocalOffset->x;
            out->z += mBasis->m[2][1] * mLocalOffset->y;
            out->z += mBasis->m[2][2] * mLocalOffset->z;
        } else {
            out->x += mLocalOffset->x;
            out->y += mLocalOffset->y;
            out->z += mLocalOffset->z;
        }
    } else if (mBasis) {
        out->x += mBasis->m[0][1] * mYOffset;
        out->y += mBasis->m[1][1] * mYOffset;
        out->z += mBasis->m[2][1] * mYOffset;
    } else {
        out->y += mYOffset;
    }
}

} // namespace al

