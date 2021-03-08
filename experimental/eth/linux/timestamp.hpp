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

#include <time.h>
#include <cstdint>
#include "itimestamp.hpp"

class Timestamp : public ITimestamp {
public:

    Timestamp();
    double get() const;

private:

    struct timespec get_raw_value() const;
    struct timespec diff(const struct timespec& start, const struct timespec& end) const;
    struct timespec m_starting_time;
};

#endif // __TIMESTAMP_HPP

