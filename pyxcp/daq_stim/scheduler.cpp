
#include "scheduler.hpp"

#if defined(_WIN32)

VOID CALLBACK TimerRoutine(PVOID lpParam, BOOLEAN TimerOrWaitFired) {
    if (lpParam == NULL) {
        printf("TimerRoutine lpParam is NULL\n");
    } else {
        // lpParam points to the argument; in this case it is an int

        printf("Timer routine called. Parameter is %d.\n", *(int*)lpParam);
        if (TimerOrWaitFired) {
            printf("The wait timed out.\n");
        } else {
            printf("The wait event was signaled.\n");
        }
    }
}

    #include <xmmintrin.h>

void mul4_vectorized(float* ptr) {
    __m128 f = _mm_loadu_ps(ptr);
    f        = _mm_mul_ps(f, f);
    _mm_storeu_ps(ptr, f);
}
#endif
