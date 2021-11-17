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

#if !defined(__ISOCKET_HPP)
#define __ISOCKET_HPP

struct CAddress {
    int length;
    struct sockaddr address;
};


class ISocket {
public:
    ~ISocket() = default;

    virtual void connect(CAddress & address) = 0;
    virtual void bind(CAddress & address) = 0;
    virtual void listen(int backlog = 10) = 0;
    virtual void accept(CAddress & peerAddress) = 0;
    virtual void option(int optname, int level, int * value) = 0;
    virtual bool getaddrinfo(int family, int socktype, int protocol, const char * hostname, int port, CAddress & address, int flags = AI_PASSIVE) = 0;
};

#endif  // __ISOCKET_HPP

