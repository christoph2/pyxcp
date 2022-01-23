/*
 * pyXCP
 *
 * (C) 2021 by Christoph Schueler <github.com/Christoph2,
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

#include <chrono>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <queue>

template <typename _Ty> class ConcurrentQueue {
public:

    explicit ConcurrentQueue<_Ty>() = default;

    ConcurrentQueue<_Ty>(const ConcurrentQueue<_Ty>& other) noexcept :
        m_elements(other.m_elements), m_mtx(),  m_cond()
    {}

    bool empty() const {
        std::unique_lock<std::mutex> lock(m_mtx);

        return m_elements.empty();
    }

    void enqueue(const _Ty& item) {
        std::lock_guard<std::mutex> lock(m_mtx);
        bool const empty = m_elements.empty();

        m_elements.emplace_back(std::move(item));
        m_mtx.unlock();

        if (empty) {
            m_cond.notify_one();
        }

    }

    bool dequeue(_Ty& item, uint32_t timeout = 50) {
        std::unique_lock<std::mutex> lock(m_mtx);

        while (m_elements.empty()) {
            if (m_cond.wait_for(lock, std::chrono::milliseconds(timeout)) == std::cv_status::timeout) {
                return false; // Wait timed out.
            }
        }

        item = std::move(m_elements.front());
        m_elements.pop_front();
        return true;
    }

private:
    //std::queue<_Ty> m_elements {};
    std::deque<_Ty> m_elements {};
    mutable std::mutex m_mtx {};
    std::condition_variable m_cond {};
};

#endif // __CONCURRENT_QUEUE
