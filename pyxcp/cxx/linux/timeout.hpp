
#if !defined(__TIMEOUT_HPP)
#define __TIMEOUT_HPP

#include <sys/timerfd.h>
#include <time.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>

#include "utils.hpp"

#include <chrono>

using namespace std::literals;

/*
 *
 * Implements a file descriptor based time-out.
 *
 * Resolution is milli-seconds.
 *
 * Could be used together with poll(), epoll(), or select().
 *
 */

class TimeoutTimer {
public:

    explicit TimeoutTimer(uint64_t value) : m_millis(value), m_timer_fd(-1) {
        m_timer_fd = ::timerfd_create(CLOCK_MONOTONIC, 0);
        if (m_timer_fd == -1)
            OsErrorExit("TimeoutTimer::TimeoutTimer() -- timerfd_create");
        }

    ~TimeoutTimer() {
        ::close(m_timer_fd);
    }

    void arm() {
        struct itimerspec new_value {0};

        new_value.it_interval = {0};
        new_value.it_value.tv_sec = m_millis / 1000;
        new_value.it_value.tv_nsec = (m_millis % 1000) * (1000 * 1000);

        settime(new_value);
    }

    void disarm() {
        struct itimerspec new_value {0};

        settime(new_value);
    }

    int getHandle() const {
        return m_timer_fd;
    }

    uint64_t getValue() const {
        return m_millis;
    }

    void setValue(uint64_t new_millis) {
        m_millis = new_millis;
    }

private:

    void settime(const itimerspec& new_value) {
        if (::timerfd_settime(m_timer_fd, 0, &new_value, nullptr) == -1) {
            OsErrorExit("TimeoutTimer::disarm() -- timerfd_settime");
        }
    }

    uint64_t m_millis;
    int m_timer_fd;
};

#endif // __TIMEOUT_HPP
