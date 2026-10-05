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

#if !defined(__ISOCKET_HPP)
#define __ISOCKET_HPP

#include <cstddef>
#include <memory>

#include "socketaddress.hpp"

#if defined(_WIN32)
    #include "win/native_socket.hpp"
#else
    #include "linux/native_socket.hpp"
#endif

/*
 * Capabilities shared by every socket, regardless of its role
 * (client/server) or I/O model (blocking, overlapped/IOCP, epoll, ...).
 *
 * No code outside of NativeSocket (win/native_socket.hpp,
 * linux/native_socket.hpp) is supposed to call raw platform socket
 * functions -- the rest of the project talks to sockets exclusively
 * through this interface (or IClientSocket / IServerSocket below).
 */
class ISocket {
public:
    virtual ~ISocket() = default;

    virtual native_handle_t getHandle() const = 0;
    virtual void setOption(int level, int optname, int value) = 0;
    virtual int getOption(int level, int optname) const = 0;
    virtual void setBlocking(bool enabled) = 0;
    virtual void close() = 0;
};

/*
 * A socket that is (or will be) connected to exactly one remote peer and
 * exchanges data with it -- either by actively connect()-ing, or as the
 * result of an IServerSocket::accept().
 */
class IClientSocket : public virtual ISocket {
public:
    virtual void connect(const SocketAddress & address) = 0;
    virtual int send(const void * data, std::size_t length) = 0;
    virtual int receive(void * data, std::size_t length) = 0;
};

/*
 * A socket that is bound to a local address, listens for incoming
 * connections and hands off every accepted connection as an
 * IClientSocket. A server socket never sends or receives payload data
 * itself.
 */
class IServerSocket : public virtual ISocket {
public:
    virtual void bind(const SocketAddress & address) = 0;
    virtual void listen(int backlog = 10) = 0;
    virtual std::unique_ptr<IClientSocket> accept(SocketAddress & peerAddress) = 0;
};

#endif  // __ISOCKET_HPP
