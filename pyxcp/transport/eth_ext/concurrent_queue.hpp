/*
 * pyXCP
 *
 * (C) 2021-2026 by Christoph Schueler <github.com/Christoph2,
 *                                      cpu12.gems@googlemail.com>
 *
 * All Rights Reserved
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * s. FLOSS-EXCEPTION.txt
 */

#if !defined(__CONCURRENT_QUEUE)
#define __CONCURRENT_QUEUE

#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <thread>
#include <utility>
#include <vector>

// A bounded, lock-free queue for exactly one producer and one consumer.
template <typename _Ty, std::size_t Capacity = 1024> class SPSCQueue {
    static_assert(std::atomic<std::size_t>::is_always_lock_free,
        "SPSCQueue requires lock-free std::atomic<std::size_t>");

public:
    static constexpr std::size_t default_capacity = Capacity;

    explicit SPSCQueue(std::size_t capacity = default_capacity) :
        m_slots(capacity)
    {
        if (capacity == 0) {
            throw std::invalid_argument("SPSCQueue capacity must be greater than zero");
        }
    }

    SPSCQueue(const SPSCQueue&) = delete;
    SPSCQueue& operator=(const SPSCQueue&) = delete;
    SPSCQueue(SPSCQueue&&) = delete;
    SPSCQueue& operator=(SPSCQueue&&) = delete;

    std::size_t capacity() const noexcept {
        return m_slots.size();
    }

    bool empty() const noexcept {
        return m_read.load(std::memory_order_acquire) ==
            m_write.load(std::memory_order_acquire);
    }

    bool enqueue(const _Ty& item) {
        return emplace(item);
    }

    bool enqueue(_Ty&& item) {
        return emplace(std::move(item));
    }

    template<typename... Args>
    bool emplace(Args&&... args) {
        const auto write = m_write.load(std::memory_order_relaxed);
        const auto read = m_read.load(std::memory_order_acquire);

        if (write - read == m_slots.size()) {
            return false;
        }

        m_slots[write % m_slots.size()].emplace(std::forward<Args>(args)...);
        m_write.store(write + 1, std::memory_order_release);
        return true;
    }

    bool dequeue(_Ty& item, std::uint32_t timeout = 50) {
        const auto deadline = std::chrono::steady_clock::now() +
            std::chrono::milliseconds(timeout);

        for (;;) {
            const auto read = m_read.load(std::memory_order_relaxed);
            const auto write = m_write.load(std::memory_order_acquire);

            if (read != write) {
                auto& slot = m_slots[read % m_slots.size()];
                item = std::move(*slot);
                slot.reset();
                m_read.store(read + 1, std::memory_order_release);
                return true;
            }

            if (std::chrono::steady_clock::now() >= deadline) {
                return false;
            }
            std::this_thread::yield();
        }
    }

private:
    std::vector<std::optional<_Ty>> m_slots;
    alignas(64) std::atomic<std::size_t> m_read {0};
    alignas(64) std::atomic<std::size_t> m_write {0};
};

#endif // __CONCURRENT_QUEUE
