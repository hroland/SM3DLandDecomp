#include <sead/math/seadVector.h>

extern "C" bool FUN_0026f71c(const sead::Vector3f*, float);

NON_MATCHING
extern "C" bool FUN_0023fa8c(const sead::Vector3f* normal, const sead::Vector3f* gravity)
{
    if (FUN_0026f71c(normal, 0.001f))
        return false;
    float dot = normal->dot(*gravity);
    dot = dot > 0.0f ? dot : -dot;
    return dot < 0.342020154f;
}

NON_MATCHING
extern "C" bool FUN_0023fb04(const sead::Vector3f* normal, const sead::Vector3f* gravity)
{
    if (FUN_0026f71c(normal, 0.001f))
        return false;
    float dot = normal->dot(*gravity);
    float absolute = dot > 0.0f ? dot : -dot;
    return absolute >= 0.342020154f && dot < 0.0f;
}
