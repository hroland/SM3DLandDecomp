#include "al/Model/alModelCtr.h"

const sead::Matrix34f* alModelCtr::getBaseMtx() const
{
    const char* resource = static_cast<const char*>(_8);
    return reinterpret_cast<const sead::Matrix34f*>(resource + 0x4c);
}

void alModelCtr::clearAnimPlayerFlags()
{
    if (mMtpAnimPlayer)
        mMtpAnimPlayer->clearFlag8();
    if (mMtsAnimPlayer)
        mMtsAnimPlayer->clearFlag8();
    if (mMclAnimPlayer)
        mMclAnimPlayer->clearFlag8();
    if (mVisAnimPlayer)
        mVisAnimPlayer->clearFlag8();
    if (_30)
        _30->clearFlag8();
    if (_34)
        _34->clearFlag8();
}
