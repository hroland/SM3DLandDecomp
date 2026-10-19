#include "al/Execute/ExecuteTableHolder.h"
#include "al/LiveActor/LiveActorFunction.h"
#include "al/Model/ModelKeeper.h"

// The flag queries below are separate out-of-line routines in the original
// image (armlink --inline copies their single load into these callers), so
// this unit must not share a translation unit with their definitions.

namespace al {

void showModel(LiveActor* actor)
{
    if (!isDead(actor) && !isClipped(actor)) {
        if (actor->getModelKeeper())
            actor->getModelKeeper()->show();
        if (actor->getShadowKeeper() && !isHideShadow(actor))
            showShadow(actor);
        alActorSystemFunction::addToExecutorDraw(actor);
    }
    actor->getLiveActorFlag().isHideModel = false;
}

void hideModel(LiveActor* actor)
{
    if (!isDead(actor) && !isClipped(actor)) {
        if (actor->getModelKeeper())
            actor->getModelKeeper()->hide();
        if (actor->getShadowKeeper())
            hideShadow(actor);
        alActorSystemFunction::removeFromExecutorDraw(actor);
    }
    actor->getLiveActorFlag().isHideModel = true;
}

} // namespace al
