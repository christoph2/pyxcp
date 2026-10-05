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
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>

#include <WinSock2.h>
#include <Ws2tcpip.h>
#include <Mstcpip.h>
#include <MSWSock.h>
#include <Windows.h>

#include "../isocket.hpp"
#include "native_socket.hpp"
#include "perhandledata.hpp"
#include "periodata.hpp"
#include "poolmgr.hpp"
#include "timeout.hpp"

class IOCP;

/*
 * Overlapped (IOCP based) connection oriented socket, used both for
 * outgoing connections (connect()) and for connections accepted by an
 * AsyncServerSocket. Every raw Winsock call goes through NativeSocket --
 * this class only adds the overlapped-I/O bookkeeping (per-IO-data pool,
 * timeout timer, IOCP registration) on top of it.
 */
class AsyncClientSocket : public IClientSocket {
public:
    explicit AsyncClientSocket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) :
        m_native(family, socktype, protocol), m_socktype(socktype), m_family(family),
        m_handleData(HandleType::HANDLE_SOCKET, reinterpret_cast<HANDLE>(m_native.handle()), this) {
        ZeroOut(&m_peerAddress, sizeof(SOCKADDR_STORAGE));
    }

    explicit AsyncClientSocket(NativeSocket && native, int socktype) :
        m_native(std::move(native)), m_socktype(socktype), m_family(AF_UNSPEC),
        m_handleData(HandleType::HANDLE_SOCKET, reinterpret_cast<HANDLE>(m_native.handle()), this) {
        ZeroOut(&m_peerAddress, sizeof(SOCKADDR_STORAGE));
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
        m_native.connect(address);
    }

    /*
     * Binds a connectionless (UDP) socket to a local address. Not part of
     * IClientSocket, since bind() makes no sense for stream sockets --
     * only use this for SOCK_DGRAM sockets that act as their own
     * "server" (no separate listen/accept phase exists for datagrams).
     */
    void bind(const SocketAddress & address) {
        m_native.bind(address);
    }

    void bind(const std::string & address, std::uint16_t port) {
        SocketAddress localAddress;
        if (!SocketAddress::resolve(address.c_str(), port, localAddress, m_family, m_socktype, 0, 0)) {
            throw std::runtime_error("AsyncClientSocket::bind(): could not resolve address");
        }
        m_native.bind(localAddress);
    }

    int send(const void * data, std::size_t length) override {
        return m_native.send(data, length);
    }

    int receive(void * data, std::size_t length) override {
        return m_native.receive(data, length);
    }

    /*
     * Queues an asynchronous send. The payload is copied into a pooled
     * PerIoData, so the caller's buffer may be reused right away. Returns
     * 0 on success (completion is reported through
     * IoCallbacks::on_send_complete) or the Winsock error code; never
     * terminates the process. Datagram sockets send to the peer set via
     * setPeerAddress()/connect(), or use writeTo().
     */
    int write(const void * data, std::size_t length) noexcept {
        return writeTo(reinterpret_cast<const sockaddr *>(&m_peerAddress), m_peerAddressLength, data, length);
    }

    template <typename T, size_t N>
    int write(const std::array<T, N> & arr) noexcept {
        return write(arr.data(), sizeof(T) * N);
    }

    int writeTo(const SocketAddress & address, const void * data, std::size_t length) noexcept {
        return writeTo(address.data(), address.length(), data, length);
    }

    int writeTo(const sockaddr * address, int addressLength, const void * data, std::size_t length) noexcept;

    // Re-posts (the remainder of) a write request; takes ownership of `iod`.
    int postWrite(PerIoData * iod) noexcept;

    void setPeerAddress(const SocketAddress & address) {
        std::memcpy(&m_peerAddress, address.data(), static_cast<std::size_t>(address.length()));
        m_peerAddressLength = address.length();
    }
    void triggerRead(unsigned int len = 1024);

    // Non-throwing/non-terminating variant: returns 0 or the Winsock error code.
    int tryTriggerRead(unsigned int len = 1024) noexcept;

    int getSocketType() const {
        return m_socktype;
    }

    int getSocketFamily() const {
        return m_family;
    }

    const TimeoutTimer & getTimeoutTimer() const {
        return m_timeout;
    }

    const PerHandleData & getHandleData() const {
        return m_handleData;
    }

    void setIOCP(IOCP * iocp) {
        m_iocp = iocp;
        m_timeout.setIOCP(iocp);
    }

private:
    NativeSocket m_native;
    int m_socktype;
    int m_family;
    SOCKADDR_STORAGE m_peerAddress;
    int m_peerAddressLength = 0;
    TimeoutTimer m_timeout {150};
    IOCP * m_iocp = nullptr;
    PerHandleData m_handleData;
};

/*
 * Listening socket counterpart of AsyncClientSocket: bind()/listen()/
 * accept() only, hands every accepted connection off as an
 * AsyncClientSocket (which can then be registered with the IOCP).
 */
class AsyncServerSocket : public IServerSocket {
public:
    explicit AsyncServerSocket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) :
        m_native(family, socktype, protocol), m_socktype(socktype) {
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
