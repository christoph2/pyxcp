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

#if !defined(__SOCKET_HPP)
#define __SOCKET_HPP

#include "iocp.hpp"

struct CAddress {
    int length;
    struct sockaddr address;
};

class Socket {
public:

    Socket(IOCP * iocp, int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP, int options = 0);
    Socket(const Socket&) = default;
    operator=(const Socket&) = delete;
    ~Socket();

    void getOption(int option, char * optval, int * optlen);
    void setOption(int option, const char * optval, int optlen);
    bool getaddrinfo(int family, int socktype, int protocol, const char * hostname, int port, CAddress & address, int flags = AI_PASSIVE);
    bool connect(CAddress & address);
    bool disconnect();
    bool bind(CAddress & address);
    bool listen(int backlog = 10);
    bool accept(CAddress & peerAddress);
    void write(char * buf, unsigned int len);
    void triggerRead(unsigned int len);
    HANDLE getHandle() const;
    LPFN_CONNECTEX connectEx;
protected:

    void loadFunctions();

private:
    int m_family;
    int m_socktype;
    int m_protocol;
    bool m_connected;
    IOCP * m_iocp;
    ADDRINFO * m_addr;
    SOCKET m_socket;
    SOCKADDR_STORAGE m_peerAddress;

    PerIoData * m_acceptOlap;
    PerIoData * m_recvOlap;
    PerIoData * m_sendOlap;
};

#endif  // __SOCKET_HPP

