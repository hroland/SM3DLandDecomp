#include "al/Placement/PlacementFunction.h"

// Tail-call ArgN wrappers. In the EU image every one of these is a branch to
// the tryGetArg body (never an inlined copy), so this unit must not share a
// translation unit with the bodies in PlacementFunction.cpp.

namespace al {

bool tryGetArg0(float* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg0"); }
bool tryGetArg6(float* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg6"); }

bool tryGetArg0(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg0"); }
bool tryGetArg1(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg1"); }
bool tryGetArg2(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg2"); }
bool tryGetArg3(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg3"); }
bool tryGetArg4(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg4"); }
bool tryGetArg5(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg5"); }
bool tryGetArg6(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg6"); }
bool tryGetArg7(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg7"); }
bool tryGetArg8(float* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg8"); }

bool tryGetArg0(bool* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg0"); }
bool tryGetArg3(bool* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg3"); }
bool tryGetArg4(bool* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg4"); }
bool tryGetArg5(bool* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg5"); }
bool tryGetArg7(bool* out, const PlacementInfo& info) { return tryGetArg(out, info, "Arg7"); }

bool tryGetArg0(bool* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg0"); }
bool tryGetArg1(bool* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg1"); }
bool tryGetArg2(bool* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg2"); }
bool tryGetArg3(bool* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg3"); }
bool tryGetArg4(bool* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg4"); }
bool tryGetArg5(bool* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg5"); }
bool tryGetArg6(bool* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg6"); }
bool tryGetArg7(bool* out, const ActorInitInfo& info) { return tryGetArg(out, getPlacementInfo(info), "Arg7"); }

} // namespace al
