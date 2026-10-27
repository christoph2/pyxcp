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
#include <cstdint>
#include <cstring>
#include <ctime>
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
    explicit NativeSocket(int family, int socktype, int protocol) {
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
        const int result = static_cast<int>(::send(m_handle, data, length, MSG_NOSIGNAL));
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

    int receiveFrom(void * data, std::size_t length, sockaddr * peer, socklen_t * peer_length) {
        const int result = static_cast<int>(::recvfrom(m_handle, data, length, 0, peer, peer_length));
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::receiveFrom()");
        }
        return result;
    }

    // Like receiveFrom(), but also extracts the SO_TIMESTAMPING receive timestamp
    // (hardware if available, otherwise software) in ns; 0 if none was delivered.
    int receiveFromTimestamped(void * data, std::size_t length, sockaddr * peer, socklen_t * peer_length, std::uint64_t & timestamp_ns) {
        iovec iov{data, length};
        alignas(cmsghdr) char control[256];
        msghdr msg{};
        msg.msg_name = peer;
        msg.msg_namelen = *peer_length;
        msg.msg_iov = &iov;
        msg.msg_iovlen = 1;
        msg.msg_control = control;
        msg.msg_controllen = sizeof(control);
        const int result = static_cast<int>(::recvmsg(m_handle, &msg, 0));
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::receiveFromTimestamped()");
        }
        *peer_length = msg.msg_namelen;
        timestamp_ns = 0;
        for (cmsghdr * cmsg = CMSG_FIRSTHDR(&msg); cmsg != nullptr; cmsg = CMSG_NXTHDR(&msg, cmsg)) {
            if (cmsg->cmsg_level == SOL_SOCKET && cmsg->cmsg_type == SCM_TIMESTAMPING && cmsg->cmsg_len >= CMSG_LEN(3 * sizeof(timespec))) {
                timespec ts[3];
                std::memcpy(ts, CMSG_DATA(cmsg), sizeof(ts));
                // ts[0]: software, ts[2]: raw hardware
                const timespec & chosen = (ts[2].tv_sec != 0 || ts[2].tv_nsec != 0) ? ts[2] : ts[0];
                timestamp_ns = static_cast<std::uint64_t>(chosen.tv_sec) * 1000000000ULL + static_cast<std::uint64_t>(chosen.tv_nsec);
                break;
            }
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
