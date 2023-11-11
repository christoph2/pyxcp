
#ifndef __TSQUEUE_HPP
#define __TSQUEUE_HPP

#include <condition_variable>
#include <mutex>
#include <queue>

template<typename T>
class TsQueue {
   public:

    TsQueue() = default;

    TsQueue(const TsQueue& other) noexcept {
        std::scoped_lock lock(other.m_mtx);
        m_queue = other.m_queue;
    }

    void put(T value) noexcept {
        std::scoped_lock lock(m_mtx);
        m_queue.push(value);
        m_cond.notify_one();
    }

    std::shared_ptr<T> get() noexcept {
        std::unique_lock lock(m_mtx);
        m_cond.wait(lock, [this] { return !m_queue.empty(); });
        std::shared_ptr<T> result(std::make_shared<T>(m_queue.front()));
        m_queue.pop();
        return result;
    }

    bool empty() const noexcept {
        std::scoped_lock lock(m_mtx);
        return m_queue.empty();
    }

   private:

    mutable std::mutex      m_mtx;
    std::queue<T>           m_queue;
    std::condition_variable m_cond;
};

#endif  // __TSQUEUE_HPP
