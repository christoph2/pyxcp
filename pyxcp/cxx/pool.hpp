#if !defined(__POOL_H)
#define __POOL_H

#include <algorithm>
#include <list>
#include <deque>
#include <mutex>
#include <thread>

#include "exceptions.hpp"


/*
 *
 * Fixed-size generic resource pool.
 *
 */

template <typename Obj> void dump(std::deque<Obj>& list) {

    for (auto elem: list) {
        printf("%p ", elem);
    }
    printf("\n");
}

template<typename Obj, int N> class Pool {
public:

    explicit Pool() : m_mtx(), m_high_water_mark(N), m_allocation_count(0) {
        for (size_t i = 0; i < N; ++i) {
            m_free_objs.push_back(new Obj());
        }
    }

    ~Pool() noexcept {
        for (auto elem: m_used_objs) {
            delete elem;
        }
        for (auto elem: m_free_objs) {
            delete elem;
        }
    }

    Obj * acquire() {
        const std::lock_guard<std::mutex> lock(m_mtx);
        if (m_free_objs.empty()) {
            throw CapacityExhaustedException();
        }
        auto obj = m_free_objs.front();
        m_free_objs.pop_front();
        m_used_objs.push_back(obj);
        //printf("ACQ %p\n",  obj);
        return obj;
    }

    void release(Obj * obj)
    {
        const std::lock_guard<std::mutex> lock(m_mtx);
        //printf("REL: %p\n", obj);
        auto iter = std::find(std::begin(m_used_objs), std::end(m_used_objs), obj);
        auto found = iter != std::end(m_used_objs);
        if (found) {
            obj->reset();
            m_free_objs.push_front(obj);
            m_used_objs.erase(iter);
        } else {
            throw InvalidObjectException();
        }
    }

private:

    std::mutex m_mtx;
    size_t m_high_water_mark;
    size_t m_allocation_count;
    std::deque<Obj*> m_used_objs;
    std::deque<Obj*> m_free_objs;
};

#endif // __POOL_H
