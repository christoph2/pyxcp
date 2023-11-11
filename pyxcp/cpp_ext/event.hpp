
#ifndef __EVENT_HPP
#define __EVENT_HPP

#include <atomic>
#include <condition_variable>
#include <mutex>

class Event {
   public:

    Event(const Event& other) noexcept {
        std::scoped_lock lock(other.m_mtx);
        m_flag = other.m_flag;
    }

    ~Event() = default;
    Event()  = default;

    void signal() noexcept {
        std::scoped_lock lock(m_mtx);
        m_flag = true;
        m_cond.notify_one();
    }

    void wait() noexcept {
        std::unique_lock lock(m_mtx);
        m_cond.wait(lock, [this] { return m_flag; });
        m_flag = false;
    }

    bool state() const noexcept {
        std::scoped_lock lock(m_mtx);
        return m_flag;
    }

   private:

    mutable std::mutex      m_mtx{};
    bool                    m_flag{ false };
    std::condition_variable m_cond{};
};

#if 0
class Spinlock {
   public:

    Spinlock() : m_flag(ATOMIC_FLAG_INIT) {
    }

    ~Spinlock() = default;

    void lock() {
        while (m_flag.test_and_set()) {
        }
    }

    void unlock() {
        m_flag.clear();
    }

private:
    std::atomic_flag m_flag;
};
#endif

#endif  // __EVENT_HPP
