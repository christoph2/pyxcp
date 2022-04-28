#if !defined(__MEMORYBLOCK_HPP)
#define __MEMORYBLOCK_HPP

#include "iresource.hpp"

/*
 *
 * Fixed size memory block.
 *
 */
template <typename T, int N> class MemoryBlock : IResource {

public:

    explicit MemoryBlock() : m_memory(nullptr) {
        m_memory = new T[N];
        //printf("MemBlock-ctor: %p\n", m_memory);
    }

    ~MemoryBlock() {
        //printf("MemoryBlock-dtor: %p\n", m_memory);
        if (m_memory) {
            delete[] m_memory;
        }
    }

    T * data() {
        return m_memory;
    }

    void reset() {
    #if !defined(NDEBUG)

    #endif
    }

private:
    T * m_memory;

};

#endif // __MEMORYBLOCK_HPP
