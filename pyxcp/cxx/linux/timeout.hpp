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

