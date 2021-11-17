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

#include <cstdio>

#include "utils.hpp"

#if defined(_WIN32)
    #include <Windows.h>
#else

#endif

void SocketErrorExit(const char * method)
{
    fprintf(stderr, "%s failed with: %d\n", method, GET_LAST_SOCKET_ERROR());
    exit(1);
}

void OsErrorExit(const char * method)
{
    fprintf(stderr, "%s failed with: %d\n", method, GET_LAST_ERROR());
    exit(1);
}

#if !defined(_WIN32)
/*
 *
 * Window-ish Sleep function for Linux.
 *
 */
void Sleep(unsigned ms)
{
    struct timespec value = {0}, rem = {0};

    value.tv_sec = ms / 1000;
    value.tv_nsec = (ms % 1000) * 1000 * 1000;
    nanosleep(&value, &rem);
}
#endif
