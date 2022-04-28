
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
