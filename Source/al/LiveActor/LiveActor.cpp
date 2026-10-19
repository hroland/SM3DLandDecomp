#include "al/LiveActor/ActorInitInfo.h"
#include "al/Execute/ExecuteTableHolder.h"
#include "al/Light/ActorLightCtrl.h"
#include "al/LiveActor/ActorPoseKeeper.h"
#include "al/LiveActor/LiveActor.h"
#include "al/LiveActor/LiveActorFunction.h"
#include "al/LiveActor/LiveActorKit.h"
#include "al/LiveActor/SubActorFunction.h"
#include "al/Collision/CollisionUtil.h"
#include "al/Math/MtxUtil.h"
#include "al/Nerve/NerveKeeper.h"
#include "al/Rail/RailKeeper.h"

// Unnamed EU dependencies. These declarations record reviewed call signatures;
// their implementations have not yet been recovered here.
extern "C" sead::Vector3f FUN_001eaf34(al::Collider*, const sead::Vector3f&);
extern "C" void FUN_0024c9ec(al::Collider*) __attribute__((notailcall));
extern "C" void FUN_00129414(al::ModelKeeper*);
extern "C" const char* FUN_001e78b4(const al::LiveActor*);
extern "C" const char* FUN_0018b9b8(const al::LiveActor*);
extern "C" void FUN_001bfb98(al::IUseEffectKeeper*, const char*);
extern "C" void FUN_001bf2e4(al::AudioKeeper*, const char*);
extern "C" void FUN_001d2f90(al::ActorActionKeeper*);
extern "C" void FUN_001ca998(ActorLightCtrl*, void*);

namespace alMovementNoop {
void action(al::ActorActionKeeper*);
void shadow(al::LiveActor*);
}

// Match the observed branch-and-link calls and common return path in
// updateCollider. This compiler annotation is inferred from the emitted code.
namespace nn { namespace math { namespace ARMv6 {
void VEC3AddAsm(VEC3*, const VEC3*, const VEC3*) __attribute__((notailcall));
} } }

namespace al {

LiveActor::LiveActor(const char* name)
    : mActorName(name)
    , mActorPoseKeeper(nullptr)
    , mActorExecuteInfo(nullptr)
    , mActorActionKeeper(nullptr)
    , mCollider(nullptr)
    , mCollisionParts(nullptr)
    , mModelKeeper(nullptr)
    , mNerveKeeper(nullptr)
    , mHitSensorKeeper(nullptr)
    , mEffectKeeper(nullptr)
    , mAudioKeeper(nullptr)
    , mStageSwitchKeeper(nullptr)
    , mRailKeeper(nullptr)
    , mShadowKeeper(nullptr)
    , mActorLightCtrl(nullptr)
    , _4C(nullptr)
    , mSubActorKeeper(nullptr)
{
    getLiveActorKit()->getAllActors()->registerActor(this);
}

NerveKeeper* LiveActor::getNerveKeeper() const
{
    return mNerveKeeper;
}

void LiveActor::init(const ActorInitInfo& info) { }
void LiveActor::initAfterPlacement() { }

void LiveActor::appear() { makeActorAppeared(); }
void LiveActor::kill() { makeActorDead(); }

void LiveActor::makeActorAppeared()
{
    if (mHitSensorKeeper)
        mHitSensorKeeper->validateBySystem();
    mLiveActorFlag.isDead = false;
    if (isClipped(this))
        endClipped();
    if (!isHideModel(this) && mModelKeeper)
        mModelKeeper->show();
    resetPosition(this);
    if (mCollisionParts)
        validateCollisionPartsBySystem(this);
    if (mActorLightCtrl && (mActorLightCtrl->getMode() == 1 || mActorLightCtrl->getMode() == 0))
        mActorLightCtrl->registerDraw(mActorExecuteInfo->getDrawExecutor());
    if (mHitSensorKeeper)
        mHitSensorKeeper->update();
    addToClipping(this);
    if (mActorExecuteInfo) {
        alActorSystemFunction::addToExecutorMovement(this);
        if (!isHideModel(this) && mActorExecuteInfo->hasDrawExecutor())
            alActorSystemFunction::addToExecutorDraw(this);
    }
    if (getAudioKeeper())
        getAudioKeeper()->activate();
    if (mShadowKeeper && !isHideModel(this) && !isHideShadow(this))
        showShadow(this);
    if (mSubActorKeeper)
        alSubActorFunction::trySyncAlive(mSubActorKeeper);
}

void LiveActor::makeActorDead()
{
    if (mActorPoseKeeper)
        setVelocityZero(this);
    mLiveActorFlag.isDead = true;
    if (mHitSensorKeeper)
        mHitSensorKeeper->invalidateBySystem();
    removeFromClipping(this);
    if (mCollider)
        mCollider->onInvalidate();
    if (mCollisionParts)
        invalidateCollisionPartsBySystem(this);
    if (mModelKeeper)
        mModelKeeper->hide();
    if (getEffectKeeper())
        getEffectKeeper()->deleteAndClearEffectAll();
    if (getAudioKeeper())
        getAudioKeeper()->stopAll();
    if (mShadowKeeper)
        hideShadow(this);
    if (mActorExecuteInfo) {
        alActorSystemFunction::removeFromExecutorMovement(this);
        if (mActorExecuteInfo->hasDrawExecutor())
            alActorSystemFunction::removeFromExecutorDraw(this);
    }
    if (mSubActorKeeper)
        alSubActorFunction::trySyncDead(mSubActorKeeper);
}

void LiveActor::startClipped()
{
    mLiveActorFlag.isClipped = true;
    if (mModelKeeper)
        mModelKeeper->hide();
    if (!mLiveActorFlag.isDrawClipping) {
        if (mHitSensorKeeper)
            mHitSensorKeeper->invalidateBySystem();
        if (getEffectKeeper())
            getEffectKeeper()->pauseAll();
        if (getAudioKeeper())
            getAudioKeeper()->stopAll();
    }
    if (mShadowKeeper)
        hideShadow(this);
    if (mActorExecuteInfo) {
        if (!mLiveActorFlag.isDrawClipping)
            alActorSystemFunction::removeFromExecutorMovement(this);
        if (mActorExecuteInfo->hasDrawExecutor())
            alActorSystemFunction::removeFromExecutorDraw(this);
    }
    if (mSubActorKeeper)
        alSubActorFunction::trySyncClippingStart(mSubActorKeeper);
}

void LiveActor::endClipped()
{
    mLiveActorFlag.isClipped = false;
    if (!mLiveActorFlag.isDrawClipping) {
        if (mHitSensorKeeper) {
            mHitSensorKeeper->validateBySystem();
            updateHitSensorsAll(this);
        }
        if (getEffectKeeper())
            getEffectKeeper()->resumeAll();
        if (getAudioKeeper())
            getAudioKeeper()->activate();
    }
    if (mActorExecuteInfo) {
        if (!mLiveActorFlag.isDrawClipping)
            alActorSystemFunction::addToExecutorMovement(this);
        if (mActorExecuteInfo->hasDrawExecutor() && !isHideModel(this))
            alActorSystemFunction::addToExecutorDraw(this);
    }
    if (!isHideModel(this) && mModelKeeper)
        mModelKeeper->show();
    if (mShadowKeeper && !isHideModel(this) && !isHideShadow(this))
        showShadow(this);
    if (mSubActorKeeper)
        alSubActorFunction::trySyncClippingEnd(mSubActorKeeper);
}

void LiveActor::movement()
{
    if (mLiveActorFlag.isDead || (mLiveActorFlag.isClipped && !mLiveActorFlag.isDrawClipping))
        return;

    // Descriptive helpers preserve effect-free call remnants in the original.
    if (mActorActionKeeper)
        alMovementNoop::action(mActorActionKeeper);
    if (mModelKeeper)
        FUN_00129414(mModelKeeper);
    if (mLiveActorFlag.isValidMaterialCode && isCollidedGround(this)) {
        if (mEffectKeeper)
            FUN_001bfb98(this, FUN_001e78b4(this));
        if (mAudioKeeper)
            FUN_001bf2e4(mAudioKeeper, FUN_0018b9b8(this));
    }
    if (mHitSensorKeeper) {
        mHitSensorKeeper->attackSensor();
        if (mLiveActorFlag.isDead)
            return;
    }
    if (mNerveKeeper) {
        mNerveKeeper->update();
        if (mLiveActorFlag.isDead)
            return;
    }
    control();
    if (mLiveActorFlag.isDead)
        return;
    updateCollider();
    if (!mModelKeeper) {
        if (mEffectKeeper)
            mEffectKeeper->update();
        if (mAudioKeeper)
            mAudioKeeper->update();
        if (mCollisionParts) {
            sead::Matrix34f baseMtx;
            mActorPoseKeeper->calcBaseMtx(&baseMtx);
            al::preScaleMtx(&baseMtx, mActorPoseKeeper->getScale());
            al::syncCollisionMtx(this, &baseMtx);
        }
    }
    if (mActorActionKeeper)
        FUN_001d2f90(mActorActionKeeper);
    if (mShadowKeeper)
        alMovementNoop::shadow(this);
    if (mHitSensorKeeper)
        mHitSensorKeeper->update();
    if (mModelKeeper)
        mModelKeeper->getModel()->clearAnimPlayerFlags();
    if (mActorLightCtrl && mActorLightCtrl->getMode() == 0)
        FUN_001ca998(mActorLightCtrl, mActorExecuteInfo->getDrawExecutor());
    if (mSubActorKeeper)
        alSubActorFunction::tryMovement(mSubActorKeeper);
}

void LiveActor::updateCollider()
{
    if (!mActorPoseKeeper)
        return;

    const sead::Vector3f& velocity = getVelocity(this);
    if (!mCollider) {
        sead::Vector3f* trans = getTransPtr(this);
        nn::math::ARMv6::VEC3AddAsm(trans, trans, &velocity);
    } else if (mLiveActorFlag.isOffCollide) {
        sead::Vector3f* trans = getTransPtr(this);
        nn::math::ARMv6::VEC3AddAsm(trans, trans, &velocity);
        FUN_0024c9ec(mCollider);
    } else {
        sead::Vector3f movement;
        sead::Vector3f* trans = getTransPtr(this);
        movement = FUN_001eaf34(mCollider, velocity);
        nn::math::ARMv6::VEC3AddAsm(trans, trans, &movement);
    }
}

void LiveActor::calcAnim()
{
    if (!mLiveActorFlag.isDead && (!mLiveActorFlag.isClipped || mLiveActorFlag.isDrawClipping)) {
        if (mActorPoseKeeper)
            alLiveActorFunction::calcAnimDirect(this);
        if (getAudioKeeper())
            getAudioKeeper()->update();
    }
}

void LiveActor::attackSensor(HitSensor* me, HitSensor* other) { }
bool LiveActor::receiveMsg(u32 msg, HitSensor* other, HitSensor* me) { return false; }

void LiveActor::draw() { }

EffectKeeper* LiveActor::getEffectKeeper() const { return mEffectKeeper; }
AudioKeeper* LiveActor::getAudioKeeper() const { return mAudioKeeper; }
StageSwitchKeeper* LiveActor::getStageSwitchKeeper() const { return mStageSwitchKeeper; }

const sead::Matrix34f* LiveActor::getBaseMtx() const
{
    if (mModelKeeper)
        return mModelKeeper->getModel()->getBaseMtx();
    return nullptr;
}

void LiveActor::initStageSwitchKeeper() { mStageSwitchKeeper = new StageSwitchKeeper(); }

void LiveActor::control() { }

void LiveActor::initNerveKeeper(NerveKeeper* nk) { mNerveKeeper = nk; }
void LiveActor::initPoseKeeper(ActorPoseKeeperBase* pPoseKeeper) { mActorPoseKeeper = pPoseKeeper; }
void LiveActor::initRailKeeper(const ActorInitInfo& info) { mRailKeeper = al::tryCreateRailKeeper(al::getPlacementInfo(info)); }

} // namespace al
