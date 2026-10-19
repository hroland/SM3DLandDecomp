#include "al/Resource/Resource.h"
#include "al/System/SystemKit.h"

namespace al {

Resource* findOrCreateResource(const sead::SafeString& archive)
{
    return alProjectInterface::getSystemKit()->getResourceHolder()->findOrCreateResource(archive);
}

} // namespace al
