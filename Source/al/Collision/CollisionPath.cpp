#include "al/Collision/CollisionPath.h"
#include <math.h>

extern "C" void FUN_0027cca0(void*, const void*, float, const void*);

NON_MATCHING
extern "C" void FUN_0025c824(al::CollisionPath* path, const sead::Vector3f* start,
                             const sead::Vector3f* end, float startRadius,
                             float endRadius, float stepDistance)
{
    path->t = 0.0f;
    path->previousT = 0.0f;
    path->start = *start;
    path->delta = *end - *start;
    path->startRadius = startRadius;
    path->endRadius = endRadius;
    float distance = (sqrtf(path->delta.squaredLength()) + endRadius) - startRadius;
    path->step = distance <= 0.0f ? 1.0f : stepDistance / distance;
}

NON_MATCHING
extern "C" void FUN_0025c790(const al::CollisionPath* path, sead::Vector3f* center,
                             float* radius, sead::Vector3f* remaining)
{
    FUN_0027cca0(center, &path->delta, path->t, &path->start);
    *radius = path->startRadius + (path->endRadius - path->startRadius) * path->t;
    if (remaining)
        nn::math::ARMv6::VEC3MulAsm(remaining, &path->delta, 1.0f - path->t);
}

NON_MATCHING
extern "C" void FUN_0025c7f8(al::CollisionPath* path)
{
    path->previousT = path->t;
    path->t = sead::Mathf::min(1.0f, path->t + path->step);
}

NON_MATCHING
extern "C" void FUN_001da3ac(const al::CollisionPath* path, sead::Vector3f* center)
{
    FUN_0027cca0(center, &path->delta, path->t, &path->start);
}
