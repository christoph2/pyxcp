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

#if !defined(__WIN_NATIVE_SOCKET_HPP)
#define __WIN_NATIVE_SOCKET_HPP

#include <WinSock2.h>
#include <Ws2tcpip.h>
#include <Windows.h>

#include <cstddef>
#include <utility>

#include "../eth.hpp"
#include "../socketaddress.hpp"
#include "../utils.hpp"

using native_handle_t = SOCKET;
constexpr native_handle_t INVALID_NATIVE_HANDLE = INVALID_SOCKET;

/*
 * Thin RAII wrapper around a native Winsock SOCKET. This is the *only*
 * place in the Windows backend that is allowed to call raw Winsock
 * functions (socket(), bind(), connect(), ...) -- everything else talks
 * to sockets exclusively through this class or through ISocket /
 * IClientSocket / IServerSocket.
 *
 * Mirrors linux/native_socket.hpp 1:1 so that upper layers (blocking and
 * overlapped/IOCP based sockets) can be written without any further
 * `#if defined(_WIN32)` branching.
 */
class NativeSocket {
public:
    explicit NativeSocket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) {
        static Eth eth;  // Ensures WSAStartup()/WSACleanup() exactly once per process.
        m_handle = ::WSASocket(family, socktype, protocol, nullptr, 0, WSA_FLAG_OVERLAPPED);
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
            ::closesocket(m_handle);
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
        u_long mode = enabled ? 0 : 1;  // 0 = blocking, 1 = non-blocking.
        if (::ioctlsocket(m_handle, FIONBIO, &mode) != 0) {
            SocketErrorExit("NativeSocket::setBlocking()");
        }
    }

    void setOption(int level, int optname, int value) {
        if (::setsockopt(m_handle, level, optname, reinterpret_cast<const char *>(&value), sizeof(value)) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::setOption()");
        }
    }

    int getOption(int level, int optname) const {
        int value = 0;
        int len = sizeof(value);
        if (::getsockopt(m_handle, level, optname, reinterpret_cast<char *>(&value), &len) == SOCKET_ERROR) {
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
        int len = peerAddress.capacity();
        const native_handle_t accepted = ::accept(m_handle, peerAddress.data(), &len);
        if (accepted == INVALID_NATIVE_HANDLE) {
            SocketErrorExit("NativeSocket::accept()");
        }
        peerAddress.setLength(len);
        return NativeSocket(accepted);
    }

    void connect(const SocketAddress & address) {
        if (::connect(m_handle, address.data(), address.length()) == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::connect()");
        }
    }

    int send(const void * data, std::size_t length) {
        const int result = ::send(m_handle, reinterpret_cast<const char *>(data), static_cast<int>(length), 0);
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::send()");
        }
        return result;
    }

    int receive(void * data, std::size_t length) {
        const int result = ::recv(m_handle, reinterpret_cast<char *>(data), static_cast<int>(length), 0);
        if (result == SOCKET_ERROR) {
            SocketErrorExit("NativeSocket::receive()");
        }
        return result;
    }

    void shutdownBoth() {
        ::shutdown(m_handle, SD_BOTH);
    }

private:
    native_handle_t m_handle {INVALID_NATIVE_HANDLE};
};

#endif  // __WIN_NATIVE_SOCKET_HPP
