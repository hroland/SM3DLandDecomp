#include "al/File/FileLoader.h"

namespace al {

bool FileLoader::isExistArchive(const sead::SafeString& archive, sead::FileDevice* device)
{
    if (!device)
        device = mDefaultDevice;
    bool exists = false;
    device->tryIsExistFile(&exists, archive);
    return exists;
}

} // namespace al
