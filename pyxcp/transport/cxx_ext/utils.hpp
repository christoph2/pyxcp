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

#if !defined(__UTILS_HPP)
#define __UTILS_HPP

#if defined(_WIN32)
    #define ZeroOut(p, s)               ::SecureZeroMemory((p), (s))
    #define GET_LAST_SOCKET_ERROR()     WSAGetLastError()
    #define GET_LAST_ERROR()            GetLastError()
#else
    #include <stdlib.h>
    #include <errno.h>
    #include <time.h>

    #define ZeroOut(p, s)               ::memset((p), 0, (s))
    #define CopyMemory(d, s, l)         ::memcpy((d), (s), (l))
    #define GET_LAST_SOCKET_ERROR()     errno
    #define GET_LAST_ERROR()            errno
    void Sleep(unsigned ms);
#endif

#if defined(NDEBUG)
    #define DBG_PRINT(...)
#else
    #define DBG_PRINT(...)              printf(VA_ARGS)
#endif

void SocketErrorExit(const char * method);
void OsErrorExit(const char * method);

#endif // __UTILS_HPP
