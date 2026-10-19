#include "al/LiveActor/ActorActionKeeper.h"
#include "al/LiveActor/LiveActor.h"

// Source factoring of two effect-free call remnants in EU LiveActor::movement.
// Original helper names and out-of-line addresses are unknown. These names are
// descriptive and must not be ranked or counted as additional recovered routines.
namespace alMovementNoop {
void action(al::ActorActionKeeper*) { }
void shadow(al::LiveActor*) { }
}
