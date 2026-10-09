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

#if !defined(__SOCKET_HPP)
#define __SOCKET_HPP

#include <array>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>

#include "../isocket.hpp"
#include "native_socket.hpp"
#include "timeout.hpp"

/*
 * epoll based connection oriented socket, used both for outgoing
 * connections (connect()) and for connections accepted by an
 * AsyncServerSocket. Every raw socket call goes through NativeSocket --
 * this class only adds the bits epoll needs on top of it (the timeout
 * timer that gets registered alongside the socket's file descriptor).
 */
class AsyncClientSocket : public IClientSocket {
public:
    explicit AsyncClientSocket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) :
        m_native(family, socktype, protocol), m_socktype(socktype), m_family(family) {
        m_native.setBlocking(false);
    }

    explicit AsyncClientSocket(NativeSocket && native, int socktype) :
        m_native(std::move(native)), m_socktype(socktype), m_family(AF_UNSPEC) {
        m_native.setBlocking(false);
    }

    native_handle_t getHandle() const override {
        return m_native.handle();
    }

    void setOption(int level, int optname, int value) override {
        m_native.setOption(level, optname, value);
    }

    int getOption(int level, int optname) const override {
        return m_native.getOption(level, optname);
    }

    void setBlocking(bool enabled) override {
        m_native.setBlocking(enabled);
    }

    void close() override {
        m_native.close();
    }

    void connect(const SocketAddress & address) override {
        m_native.setBlocking(true);
        m_native.connect(address);
        m_native.setBlocking(false);
    }

    int send(const void * data, std::size_t length) override {
        return m_native.send(data, length);
    }

    int receive(void * data, std::size_t length) override {
        return m_native.receive(data, length);
    }

    int receiveFrom(void * data, std::size_t length, sockaddr * peer, socklen_t * peer_length) {
        return m_native.receiveFrom(data, length, peer, peer_length);
    }

    int getSocketType() const {
        return m_socktype;
    }

    void bind(const std::string& address, std::uint16_t port) {
        SocketAddress local_address;
        if (!SocketAddress::resolve(address.c_str(), port, local_address, m_family, m_socktype, 0, 0)) {
            throw std::runtime_error("AsyncClientSocket::bind(): could not resolve address");
        }
        m_native.bind(local_address);
    }

    template <typename T, size_t N>
    void write(std::array<T, N> & arr) {
        m_timeout.arm();
        send(arr.data(), arr.size());
    }

    void triggerRead(unsigned int len);

    const TimeoutTimer & getTimeout() const {
        return m_timeout;
    }

private:
    NativeSocket m_native;
    int m_socktype;
    int m_family;
    TimeoutTimer m_timeout {150};
};

/*
 * Listening socket counterpart of AsyncClientSocket: bind()/listen()/
 * accept() only, hands every accepted connection off as an
 * AsyncClientSocket (which can then be registered with epoll).
 */
class AsyncServerSocket : public IServerSocket {
public:
    explicit AsyncServerSocket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) :
        m_native(family, socktype, protocol), m_socktype(socktype) {
        m_native.setBlocking(false);
    }

    native_handle_t getHandle() const override {
        return m_native.handle();
    }

    void setOption(int level, int optname, int value) override {
        m_native.setOption(level, optname, value);
    }

    int getOption(int level, int optname) const override {
        return m_native.getOption(level, optname);
    }

    void setBlocking(bool enabled) override {
        m_native.setBlocking(enabled);
    }

    void close() override {
        m_native.close();
    }

    void bind(const SocketAddress & address) override {
        m_native.bind(address);
    }

    void bind(const std::string& address, std::uint16_t port) {
        SocketAddress local_address;
        if (!SocketAddress::resolve(address.c_str(), port, local_address, AF_UNSPEC, m_socktype, 0, 0)) {
            throw std::runtime_error("AsyncServerSocket::bind(): could not resolve address");
        }
        m_native.bind(local_address);
    }

    void listen(int backlog = 10) override {
        m_native.listen(backlog);
    }

    std::unique_ptr<IClientSocket> accept(SocketAddress & peerAddress) override {
        return std::make_unique<AsyncClientSocket>(m_native.accept(peerAddress), m_socktype);
    }

private:
    NativeSocket m_native;
    int m_socktype;
};

#endif  // __SOCKET_HPP
