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
#if !defined(__ETH_HPP)
#define __ETH_HPP

#if defined(_WIN32)
    #include <WinSock2.h>
    #include <Ws2tcpip.h>
    #include <Mstcpip.h>
    #include <MSWSock.h>
    #include <Windows.h>

    #include "iocp.hpp"
#else
    #include <ctype.h>
    #include <errno.h>
    #include <fcntl.h>
    #include <limits.h>
    #include <signal.h>
    #include <stdlib.h>
    #include <stdio.h>
    #include <string.h>
    #include <time.h>
    #include <stdbool.h>
    #include <unistd.h>
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netdb.h>
    #include <arpa/inet.h>
    #include <sys/wait.h>

    #include "utils.hpp"
#endif

#include "timestamp.hpp"

#endif // __ETH_HPP

