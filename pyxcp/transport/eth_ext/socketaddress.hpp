/*
 * pyXCP
 *
 * (C) 2021-2026 by Christoph Schueler <github.com/Christoph2,
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

#if !defined(__SOCKETADDRESS_HPP)
#define __SOCKETADDRESS_HPP

#if defined(_WIN32)
    #include <WinSock2.h>
    #include <Ws2tcpip.h>
#else
    #include <sys/socket.h>
    #include <sys/types.h>
    #include <netdb.h>
#endif

#include <cstdio>
#include <cstring>

#include "eth.hpp"
#include "utils.hpp"

/*
 * Platform-neutral representation of a socket address (IPv4, IPv6, ...).
 *
 * Wraps `sockaddr_storage` so that callers never have to touch raw
 * `sockaddr` structures, address-family specific types or getaddrinfo()
 * directly -- that is entirely encapsulated here.
 */
class SocketAddress {
public:
    SocketAddress() {
        ZeroOut(&m_storage, sizeof(m_storage));
        m_length = static_cast<int>(sizeof(m_storage));
    }

    sockaddr * data() {
        return reinterpret_cast<sockaddr *>(&m_storage);
    }

    const sockaddr * data() const {
        return reinterpret_cast<const sockaddr *>(&m_storage);
    }

    int length() const {
        return m_length;
    }

    void setLength(int len) {
        m_length = len;
    }

    int capacity() const {
        return static_cast<int>(sizeof(m_storage));
    }

    /*
     * Resolves a hostname/port pair into a SocketAddress, mirroring
     * getaddrinfo() semantics while hiding the Winsock vs. BSD sockets
     * differences (error reporting, string conversion, ...) from callers.
     */
    static bool resolve(
        const char * hostname, int port, SocketAddress & address,
        int family = AF_UNSPEC, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP, int flags = AI_PASSIVE
    ) {
        // Ensures Winsock is initialized on Windows, no matter whether a
        // socket object has already been created at this point (resolve()
        // is a static, free-standing helper and must work on its own).
        static Eth eth;

        addrinfo hints;
        addrinfo * result = nullptr;
        char port_str[16] = {0};

        ZeroOut(&hints, sizeof(hints));
        hints.ai_family = family;
        hints.ai_socktype = socktype;
        hints.ai_protocol = protocol;
        hints.ai_flags = flags;

        ::snprintf(port_str, sizeof(port_str), "%d", port);
        const int err = ::getaddrinfo(hostname, port_str, &hints, &result);
        if (err != 0) {
            fprintf(stderr, "getaddrinfo() failed: %s\n", gai_strerror(err));
            if (result != nullptr) {
                ::freeaddrinfo(result);
            }
            return false;
        }

        address.m_length = static_cast<int>(result->ai_addrlen);
        std::memcpy(&address.m_storage, result->ai_addr, result->ai_addrlen);
        ::freeaddrinfo(result);
        return true;
    }

private:
    sockaddr_storage m_storage;
    int m_length;
};

#endif  // __SOCKETADDRESS_HPP
