#include <stddef.h>

// Behavior-test fallback only. Normal builds use the supplied cpprt_4.l helper.
// Its library implementation is independently byte-verified; this source is not.
#if defined(REDPEPPER_USE_RUNTIME_FALLBACK)
// The ABI signature is specified by Arm CPPABI32. The original EU helper
// also skips all callbacks when constructor is null and returns user_array.
extern "C" NON_MATCHING void* __aeabi_vec_ctor_nocookie_nodtor(
    void* user_array, void* (*constructor)(void*), size_t element_size, size_t element_count)
{
    char* element = static_cast<char*>(user_array);
    if (constructor) {
        while (element_count--) {
            constructor(element);
            element += element_size;
        }
    }
    return user_array;
}
#endif
