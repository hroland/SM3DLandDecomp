#include "al/Placement/PlacementFunction.h"
#include "al/Util/StringUtil.h"

namespace al {

bool tryGetStringArg(const char** out, const PlacementInfo& info, const char* argName)
{
    const char* arg = "";
    if (info.tryGetStringByKey(&arg, argName)) {
        if (!isEqualString("-", arg)) {
            *out = arg;
            return true;
        }
        return false; // this is required to match
    }
    return false;
}

bool tryGetStringArg(const char** out, const ActorInitInfo& info, const char* argName)
{
    return tryGetStringArg(out, getPlacementInfo(info), argName);
}

bool tryGetArg(int* out, const PlacementInfo& info, const char* argName)
{
    if (!info.isValid())
        return false;
    int value;
    if (!info.tryGetIntByKey(&value, argName))
        return false;
    if (value == -1)
        return false;
    *out = value;
    return true;
}

// The float and bool variants are built on the int variant; the EU image
// inlines it into both (and into the ArgN int wrappers below).
bool tryGetArg(float* out, const PlacementInfo& info, const char* argName)
{
    int value;
    if (tryGetArg(&value, info, argName)) {
        *out = value;
        return true;
    }
    return false;
}

bool tryGetArg(bool* out, const PlacementInfo& info, const char* argName)
{
    int value;
    if (tryGetArg(&value, info, argName)) {
        if (value == 0)
            *out = false;
        else
            *out = true;
        return true;
    }
    return false;
}

bool tryGetArg0(int* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg0"); }
bool tryGetArg1(int* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg1"); }
bool tryGetArg2(int* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg2"); }

bool tryGetArg0(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg0"); }
bool tryGetArg1(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg1"); }
bool tryGetArg2(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg2"); }
bool tryGetArg3(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg3"); }
bool tryGetArg4(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg4"); }
bool tryGetArg5(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg5"); }
bool tryGetArg6(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg6"); }
bool tryGetArg7(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg7"); }
bool tryGetArg8(int* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg8"); }

bool isPlaced(const ActorInitInfo& info)
{
    return info.mPlacementInfo->isValid();
}

bool tryGetObjectName(const char** out, const al::ActorInitInfo& info)
{
    return tryGetObjectName(out, getPlacementInfo(info));
}

bool tryGetObjectName(const char** out, const al::PlacementInfo& info)
{
    return info.tryGetStringByKey(out, "name");
}

bool isObjectName(const ActorInitInfo& info, const char* objectName)
{
    return isObjectName(getPlacementInfo(info), objectName);
}

bool isObjectName(const PlacementInfo& info, const char* objectName)
{
    const char* name = nullptr;
    if (tryGetObjectName(&name, info))
        return isEqualString(name, objectName);
    return false;
}

int calcLinkChildNum(const ActorInitInfo& info)
{
    ByamlIter children;
    if (getPlacementInfo(info).tryGetIterByKey(&children, "GenerateChildren"))
        return children.getSize();
    return 0;
}

NON_MATCHING
// 4 bytes less on stack ?
bool tryGetTrans(sead::Vector3f* out, const ActorInitInfo& info)
{
    if (tryGetTrans(out, getPlacementInfo(info)))
        return true;
    return false;
}

bool tryGetTrans(sead::Vector3f* out, const PlacementInfo& info)
{
    sead::Vector3f trans;
    bool valid = info.isValid() && info.tryGetFloatByKey(&trans.x, "pos_x") && info.tryGetFloatByKey(&trans.y, "pos_y") && info.tryGetFloatByKey(&trans.z, "pos_z");
    if (!valid)
        return valid;

    out->x = trans.x;
    out->y = trans.y;
    out->z = trans.z;
    return true;
}

bool isExistRail(const ActorInitInfo& info)
{
    PlacementInfo rail;
    return tryGetRailIter(&rail, getPlacementInfo(info));
}

bool tryGetRailIter(PlacementInfo* out, const PlacementInfo& info)
{
    if (info.tryGetIterByKey(out, "Rail"))
        return out->isTypeContainer();
    return false;
}

bool getLinksInfoByIndex(PlacementInfo* out, const ActorInitInfo& info, int index)
{
    ByamlIter links;
    if (getPlacementInfo(info).tryGetIterByKey(&links, "GenerateChildren"))
        return links.tryGetIterByIndex(out, index);
    return false;
}

const char* getLinksActorObjectName(const ActorInitInfo& info, int index)
{
    PlacementInfo placementInfo;
    getLinksInfoByIndex(&placementInfo, info, index);
    const char* objectName = nullptr;
    tryGetObjectName(&objectName, placementInfo);
    return objectName;
}

int getLinksArg0(const ActorInitInfo& info, int index)
{
    PlacementInfo placementInfo;
    getLinksInfoByIndex(&placementInfo, info, index);
    int value = -1;
    tryGetArg0(&value, placementInfo);
    return value;
}

} // namespace al

namespace alPlacementFunction {

int getClippingViewId(const al::PlacementInfo& info)
{
    int id = -1;
    if (!info.tryGetIntByKey(&id, "ViewId"))
        return -1;
    return id;
}

} // namespace alPlacementFunction
