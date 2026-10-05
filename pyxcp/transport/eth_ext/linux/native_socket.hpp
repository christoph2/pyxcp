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

#if !defined(__LINUX_NATIVE_SOCKET_HPP)
#define __LINUX_NATIVE_SOCKET_HPP

#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#include <cstddef>
#include <utility>

#include "../eth.hpp"
#include "../socketaddress.hpp"
#include "../utils.hpp"

using native_handle_t = int;
constexpr native_handle_t INVALID_NATIVE_HANDLE = -1;

// Generic OS handle type, mirroring Windows' HANDLE so that platform
// neutral code (IAsyncIoService, TimeoutTimer, ...) can be written
// without further #if defined(_WIN32) branching.
using HANDLE = int;

#if !defined(SOCKET_ERROR)
    #define SOCKET_ERROR (-1)
#endif

/*
 * Thin RAII wrapper around a native BSD socket file descriptor. This is
 * the *only* place in the Linux backend that is allowed to call raw
 * socket functions (socket(), bind(), connect(), ...) -- everything else
 * talks to sockets exclusively through this class or through ISocket /
 * IClientSocket / IServerSocket.
 *
 * Mirrors win/native_socket.hpp 1:1 so that upper layers (blocking and
 * epoll based sockets) can be written without any further
 * `#if defined(_WIN32)` branching.
 */
class NativeSocket {
public:
    explicit NativeSocket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) {
        static Eth eth;  // No-op on Linux, kept for symmetry with the Windows backend.
        m_handle = ::socket(family, socktype, protocol);
        if (m_handle == INVALID_NATIVE_HANDLE) {
            SocketErrorExit("NativeSocket::NativeSocket()");
        }
    }

    explicit NativeSocket(native_handle_t handle) : m_handle(handle) {
    }

    ~NativeSocket() {
        close();
    }

    NativeSocket(const NativeSocket &) = delete;
    NativeSocket & operator=(const NativeSocket &) = delete;

    NativeSocket(NativeSocket && other) noexcept : m_handle(std::exchange(other.m_handle, INVALID_NATIVE_HANDLE)) {
    }

    NativeSocket & operator=(NativeSocket && other) noexcept {
        if (this != &other) {
            close();
            m_handle = std::exchange(other.m_handle, INVALID_NATIVE_HANDLE);
        }
        return *this;
    }

    void close() {
        if (m_handle != INVALID_NATIVE_HANDLE) {
            ::close(m_handle);
            m_handle = INVALID_NATIVE_HANDLE;
        }
    }

    bool valid() const {
        return m_handle != INVALID_NATIVE_HANDLE;
    }

    native_handle_t handle() const {
        return m_handle;
    }

    void setBlocking(bool enabled) {
        int flags = ::fcntl(m_handle, F_GETFL, 0);
        if (flags == -1) {
            SocketErrorExit("NativeSocket::setBlocking()");
        }
        flags = enabled ? (flags & ~O_NONBLOCK) : (flags | O_NONBLOCK);
        if (::fcntl(m_handle, F_SETFL, flags) == -1) {
            SocketErrorExit("NativeSocket::setBlocking()");
        }
    }

    void setOption(int level, int optname, int value) {
        if (::setsockopt(m_handle, level, optname, &value, sizeof(value)) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::setOption()");
        }
    }

    int getOption(int level, int optname) const {
        int value = 0;
        socklen_t len = sizeof(value);
        if (::getsockopt(m_handle, level, optname, &value, &len) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::getOption()");
        }
        return value;
    }

    void bind(const SocketAddress & address) {
        if (::bind(m_handle, address.data(), address.length()) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::bind()");
        }
    }

    void listen(int backlog) {
        if (::listen(m_handle, backlog) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::listen()");
        }
    }

    NativeSocket accept(SocketAddress & peerAddress) {
        socklen_t len = static_cast<socklen_t>(peerAddress.capacity());
        const native_handle_t accepted = ::accept(m_handle, peerAddress.data(), &len);
        if (accepted == INVALID_NATIVE_HANDLE) {
            SocketErrorExit("NativeSocket::accept()");
        }
        peerAddress.setLength(static_cast<int>(len));
        return NativeSocket(accepted);
    }

    void connect(const SocketAddress & address) {
        if (::connect(m_handle, address.data(), address.length()) == SOCKET_ERROR) {
            if (errno != EINPROGRESS) {
                SocketErrorExit("NativeSocket::connect()");
            }
        }
    }

    int send(const void * data, std::size_t length) {
        const int result = static_cast<int>(::send(m_handle, data, length, 0));
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::send()");
        }
        return result;
    }

    int receive(void * data, std::size_t length) {
        const int result = static_cast<int>(::recv(m_handle, data, length, 0));
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::receive()");
        }
        return result;
    }

    void shutdownBoth() {
        ::shutdown(m_handle, SHUT_RDWR);
    }

private:
    native_handle_t m_handle {INVALID_NATIVE_HANDLE};
};

#endif  // __LINUX_NATIVE_SOCKET_HPP
