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
#if !defined(__TIMESTAMP_HPP)
#define __TIMESTAMP_HPP

#include <cstdint>

#if defined(_WIN32)
    #include <Windows.h>
#else
    #include <time.h>
#endif

class Timestamp {
public:

#if defined(_WIN32)
    Timestamp() {
        LARGE_INTEGER tps;

        ::QueryPerformanceFrequency(&tps);
        m_ticks_per_second = tps.QuadPart;
        m_starting_time = static_cast<double>(get_raw_value());
    }

    double get() const {
        return get_raw_value() - m_starting_time;
    }
#else
    Timestamp() {
        struct timespec resolution = {0};

        if (::clock_getres(CLOCK_MONOTONIC_RAW, &resolution) == -1) {
        }
        m_starting_time = get_raw_value();
    }

    double get() const {
        struct timespec dt = {0};

        dt = diff(m_starting_time, get_raw_value());
        return static_cast<double>(dt.tv_sec) + (static_cast<double>(dt.tv_nsec) / (1000.0 * 1000.0 * 1000.0));
    }
#endif

private:

#if defined(_WIN32)
    double get_raw_value() const {
        LARGE_INTEGER now;

        ::QueryPerformanceCounter(&now);

        return static_cast<double>(now.QuadPart) / static_cast<double>(m_ticks_per_second);
    }

    double m_starting_time;
    uint64_t m_ticks_per_second;
#else
    struct timespec get_raw_value() const {
        struct timespec now;

        if (::clock_gettime(CLOCK_MONOTONIC_RAW, &now) == -1) {
        }
        return now;
    }

    struct timespec diff(const struct timespec& start, const struct timespec& end) const {
        struct timespec temp;

        if ((end.tv_nsec-start.tv_nsec) < 0) {
            temp.tv_sec = end.tv_sec-start.tv_sec - 1;
            temp.tv_nsec = 1000000000L + end.tv_nsec - start.tv_nsec;
        } else {
            temp.tv_sec = end.tv_sec-start.tv_sec;
            temp.tv_nsec = end.tv_nsec-start.tv_nsec;
        }
        return temp;
    }

    struct timespec m_starting_time;

#endif
};

#endif // __TIMESTAMP_HPP

