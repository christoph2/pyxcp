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

#if !defined(__KQUEUE_NATIVE_SOCKET_HPP)
#define __KQUEUE_NATIVE_SOCKET_HPP

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
using HANDLE = int;

#if !defined(SOCKET_ERROR)
    #define SOCKET_ERROR (-1)
#endif

class NativeSocket {
   public:
    explicit NativeSocket(int family, int socktype, int protocol) {
        static Eth eth;
        m_handle = ::socket(family, socktype, protocol);
        if (m_handle == INVALID_NATIVE_HANDLE) {
            SocketErrorExit("NativeSocket::NativeSocket()");
        }
        suppressSigpipe();
    }

    explicit NativeSocket(native_handle_t handle) : m_handle(handle) {
        suppressSigpipe();
    }

    ~NativeSocket() {
        close();
    }

    NativeSocket(const NativeSocket&) = delete;
    NativeSocket& operator=(const NativeSocket&) = delete;

    NativeSocket(NativeSocket&& other) noexcept : m_handle(std::exchange(other.m_handle, INVALID_NATIVE_HANDLE)) {}

    NativeSocket& operator=(NativeSocket&& other) noexcept {
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

    bool valid() const { return m_handle != INVALID_NATIVE_HANDLE; }
    native_handle_t handle() const { return m_handle; }

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
        socklen_t length = sizeof(value);
        if (::getsockopt(m_handle, level, optname, &value, &length) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::getOption()");
        }
        return value;
    }

    void bind(const SocketAddress& address) {
        if (::bind(m_handle, address.data(), address.length()) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::bind()");
        }
    }

    void listen(int backlog) {
        if (::listen(m_handle, backlog) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::listen()");
        }
    }

    NativeSocket accept(SocketAddress& peerAddress) {
        socklen_t length = static_cast<socklen_t>(peerAddress.capacity());
        const native_handle_t accepted = ::accept(m_handle, peerAddress.data(), &length);
        if (accepted == INVALID_NATIVE_HANDLE) {
            SocketErrorExit("NativeSocket::accept()");
        }
        peerAddress.setLength(static_cast<int>(length));
        return NativeSocket(accepted);
    }

    void connect(const SocketAddress& address) {
        if (::connect(m_handle, address.data(), address.length()) == SOCKET_ERROR && errno != EINPROGRESS) {
            SocketErrorExit("NativeSocket::connect()");
        }
    }

    int send(const void* data, std::size_t length) {
#if defined(MSG_NOSIGNAL)
        constexpr int flags = MSG_NOSIGNAL;
#else
        constexpr int flags = 0;
#endif
        const int result = static_cast<int>(::send(m_handle, data, length, flags));
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::send()");
        }
        return result;
    }

    int receive(void* data, std::size_t length) {
        const int result = static_cast<int>(::recv(m_handle, data, length, 0));
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::receive()");
        }
        return result;
    }

    int receiveFrom(void* data, std::size_t length, sockaddr* peer, socklen_t* peerLength) {
        const int result = static_cast<int>(::recvfrom(m_handle, data, length, 0, peer, peerLength));
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::receiveFrom()");
        }
        return result;
    }

    void shutdownBoth() {
        ::shutdown(m_handle, SHUT_RDWR);
    }

   private:
    void suppressSigpipe() {
#if defined(SO_NOSIGPIPE)
        const int enabled = 1;
        if (::setsockopt(m_handle, SOL_SOCKET, SO_NOSIGPIPE, &enabled, sizeof(enabled)) == SOCKET_ERROR) {
            const int error = errno;
            close();
            errno = error;
            SocketErrorExit("NativeSocket::suppressSigpipe()");
        }
#endif
    }

    native_handle_t m_handle{INVALID_NATIVE_HANDLE};
};

#endif  // __KQUEUE_NATIVE_SOCKET_HPP
