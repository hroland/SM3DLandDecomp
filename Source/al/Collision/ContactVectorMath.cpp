#include <sead/math/seadVector.h>

extern "C" bool FUN_0026f71c(const sead::Vector3f* vector, float epsilon)
{
    return vector->squaredLength() < epsilon * epsilon;
}
