
#if !defined(__TIMEOUT_HPP)
#define __TIMEOUT_HPP

#include <Windows.h>

#include "utils.hpp"


/*
 *
 * Implements a timer queue based time-out.
 *
 * Resolution is milli-seconds.
 *
 *
 */

class IOCP;

void CALLBACK Timeout_CB(void * lpParam, unsigned char TimerOrWaitFired);


class TimeoutTimer {
public:

    explicit TimeoutTimer(uint64_t value) : m_millis(value) {
        m_timer_queue = ::CreateTimerQueue();
        if (m_timer_queue == nullptr)
            OsErrorExit("TimeoutTimer::TimeoutTimer() -- CreateTimerQueue");
        }

    TimeoutTimer(const TimeoutTimer&) = default;
    TimeoutTimer(const TimeoutTimer&&) = delete;

    ~TimeoutTimer() {
        if (!::DeleteTimerQueue(m_timer_queue)) {
            OsErrorExit("TimeoutTimer::~TimeoutTimer() -- DeleteTimerQueueEx");
        }
    }

    void arm() {
        if (m_iocp != nullptr) {
            if (!::CreateTimerQueueTimer(&m_timer, m_timer_queue, Timeout_CB, reinterpret_cast<void*>(m_iocp), m_millis, 0, 0)) {
                OsErrorExit("TimeoutTimer::arm() -- CreateTimerQueueTimer");
            }
        }
    }

    void disarm() {
        if (m_timer != INVALID_HANDLE_VALUE) {
            if (!::DeleteTimerQueueTimer(m_timer_queue, m_timer, nullptr)) {
                OsErrorExit("TimeoutTimer::disarm() -- DeleteTimerQueueTimer");
            }
            m_timer = INVALID_HANDLE_VALUE;
        }
    }

    HANDLE getHandle() const {
        return m_timer_queue;
    }

    uint64_t getValue() const {
        return m_millis;
    }

    void setValue(uint64_t new_millis) {
        m_millis = new_millis;
    }

    void setIOCP(IOCP * iocp) {
        m_iocp = iocp;
    }

private:

    uint64_t m_millis;
    HANDLE m_timer_queue {INVALID_HANDLE_VALUE};
    HANDLE m_timer {INVALID_HANDLE_VALUE};
    IOCP * m_iocp = nullptr;
};

#endif // __TIMEOUT_HPP
