#include "al/Collision/CollisionDirector.h"
#include "al/Collision/CollisionParts.h"

// Global engine accessor behind the collision director (EU 0x001676f0);
// original name unknown. Defined with the other director getters.
extern "C" al::CollisionDirector::QueryEngine* FUN_001676f0();

namespace al {

void CollisionParts::validateBySystem()
{
    if (_140)
        return;
    _140 = true;
    _141 = true;
    FUN_001676f0()->addParts(this);
}

void CollisionParts::invalidateBySystem()
{
    if (!_140)
        return;
    _140 = false;
    _141 = false;
    FUN_001676f0()->removeParts(this);
}

} // namespace al
