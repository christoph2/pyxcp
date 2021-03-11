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
#if !defined(__POOL_H)
#define __POOL_H

#include <algorithm>
#include <list>
#include <mutex>
#include <thread>

#include "exceptions.hpp"


/*
 *
 * Fixed-size generic resource pool.
 *
 */
template<typename Obj, int N> class Pool {
public:

    explicit Pool() : m_mtx() {
        for (size_t i = 0; i < N; ++i) {
            m_free_list.push_front(std::make_unique<Obj>());
        }
   
    }
    
    Pool(const Pool&) = delete;
    Pool(const Pool&&) = delete;

    std::shared_ptr<Obj> acquire() {
        const std::lock_guard<std::mutex> lock(m_mtx);
        if (m_free_list.empty()) {
            throw CapacityExhaustedException();
        }
        auto it = m_free_list.begin();
        std::shared_ptr<Obj> obj_ptr(it->get(), [=](Obj* ptr){ptr->reset(); this->release(ptr); });
        m_used_list.push_front(std::move(*it));
        m_free_list.erase(it);
        //printf("A: %p\n", obj_ptr);
        return obj_ptr;

    }

private:

    void release(Obj *obj)
    {
        const std::lock_guard<std::mutex> lock(m_mtx);
        //printf("R: %p\n", obj);
        auto it = std::find_if(m_used_list.begin(), m_used_list.end(), [&](std::unique_ptr<Obj> &p){ return p.get() == obj; });
        if (it != m_used_list.end()) {
          m_free_list.push_back(std::move(*it));
          m_used_list.erase(it);
        } else {
            throw std::runtime_error("Tried to free an invalid object.");
        }
    }

    std::mutex m_mtx;
    std::list<std::unique_ptr<Obj>> m_free_list;
    std::list<std::unique_ptr<Obj>> m_used_list;
};

#endif // __POOL_H

