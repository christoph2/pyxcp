
#ifndef __BLOCKMEM_HPP
#define __BLOCKMEM_HPP

#include <array>
#include <cstdint>
#include <mutex>

/*
 *
 * Super simplicistic block memory manager.
 *
 */
template<typename T, int _IS, int _NB>
class BlockMemory {
   public:

    using mem_block_t = std::array<T, _IS>;

    constexpr explicit BlockMemory() noexcept : m_memory{ nullptr }, m_allocation_count{ 0 } {
        m_memory = new T[_IS * _NB];
    }

    ~BlockMemory() noexcept {
        if (m_memory) {
            delete[] m_memory;
        }
    }

    BlockMemory(const BlockMemory&) = delete;

    constexpr T* acquire() noexcept {
        const std::scoped_lock lock(m_mtx);

        if (m_allocation_count >= _NB) {
            return nullptr;
        }
        T* ptr = reinterpret_cast<T*>(m_memory + (m_allocation_count * _IS));
        m_allocation_count++;
        return ptr;
    }

    constexpr void release() noexcept {
        const std::scoped_lock lock(m_mtx);
        if (m_allocation_count == 0) {
            return;
        }
        m_allocation_count--;
    }

   private:

    T*            m_memory;
    std::uint32_t m_allocation_count;
    std::mutex    m_mtx;
};

#endif  // __BLOCKMEM_HPP
