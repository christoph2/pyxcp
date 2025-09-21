#include "scheduler.hpp"

#if defined(_WIN32)

#include <cstdio>
#include <cstdint>

VOID CALLBACK TimerRoutine(PVOID lpParam, BOOLEAN TimerOrWaitFired) {
    if (lpParam == nullptr) {
        std::printf("TimerRoutine lpParam is NULL\n");
        return;
    }
    
    const auto* param = static_cast<const int*>(lpParam);
    std::printf("Timer routine called. Parameter is %d.\n", *param);
    
    if (TimerOrWaitFired) {
        std::printf("The wait timed out.\n");
    } else {
        std::printf("The wait event was signaled.\n");
    }
}

#endif // _WIN32

// Vectorized multiply implementation with bounds checking
namespace {
    constexpr size_t VECTOR_SIZE = 4;
}

#if defined(_M_X64) || defined(_M_IX86) || defined(__SSE__)
    #include <xmmintrin.h>
    
    void mul4_vectorized(float* ptr) {
        if (ptr == nullptr) return;
        
        __m128 f = _mm_loadu_ps(ptr);
        f = _mm_mul_ps(f, f);
        _mm_storeu_ps(ptr, f);
    }

#elif defined(_M_ARM64) || defined(__ARM_NEON)
    #include <arm_neon.h>
    
    void mul4_vectorized(float* ptr) {
        if (ptr == nullptr) return;
        
        float32x4_t f = vld1q_f32(ptr);
        f = vmulq_f32(f, f);
        vst1q_f32(ptr, f);
    }

#else
    // Scalar fallback
    void mul4_vectorized(float* ptr) {
        if (ptr == nullptr) return;
        
        for (size_t i = 0; i < VECTOR_SIZE; ++i) {
            ptr[i] *= ptr[i];
        }
    }
#endif