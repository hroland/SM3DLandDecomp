#include "al/Rail/Rail.h"

namespace al {

Rail::Rail()
    : _0(0)
    , mRailParts(nullptr)
    , mRailPartCount(0)
    , _C(0)
    , mIsClosed(false)
{
}

float Rail::getTotalLength() const
{
    const RailPart& last = mRailParts[mRailPartCount - 1];
    return last.mTotalLength;
}

} // namespace al
