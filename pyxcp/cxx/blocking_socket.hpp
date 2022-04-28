
#include <array>

#include "utils.hpp"

#if !defined(__BLOCKING_SOCKET_HPP)
#define __BLOCKING_SOCKET_HPP

#if defined(_WIN32)
    #include <WinSock2.h>
    #include <Ws2tcpip.h>
    #include <Mstcpip.h>
    #include <MSWSock.h>
    #include <Windows.h>
#elif defined(__unix__)
    #include <ctype.h>
    #include <errno.h>
    #include <fcntl.h>
    #include <limits.h>
    #include <signal.h>
    #include <stdlib.h>
    #include <stdio.h>
    #include <string.h>
    #include <time.h>
    #include <stdbool.h>
    #include <unistd.h>
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netdb.h>
    #include <arpa/inet.h>
    #include <sys/wait.h>

    #define INVALID_SOCKET          (-1)
    #define SOCKET_ERROR            (-1)
    #define ADDRINFO                addrinfo
    #define SOCKADDR                struct sockaddr
    #define SOCKADDR_STORAGE        sockaddr_storage

    typedef int SOCKET;
#endif

#include <pthread.h>

#define ADDR_LEN                    sizeof(SOCKADDR_STORAGE)

template <std::size_t N> using buffer_t = std::array<unsigned char, N>;

void * blockingReceiverThread(void * param);

struct CAddress {
    int length;
    struct sockaddr address;
};

class Socket {
    public:

    explicit Socket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) : m_family(family), m_socktype(socktype),
        m_protocol(protocol), m_connected(false),  m_addr(nullptr), m_thread(0) {
        m_socket = ::socket(m_family, m_socktype, m_protocol);
        m_connected_socket = 0;
        if (m_socket == INVALID_SOCKET) {
            SocketErrorExit("Socket::Socket()");
        }
        blocking(true);
        ZeroOut(&m_peerAddress, sizeof(SOCKADDR_STORAGE));
    }

    ~Socket() {
#if defined(__unix__)
        ::close(m_socket);
#elif #defined(_WIN32)
        ::closesocket(m_socket);
#endif
    }

    void blocking(bool enabled) {
        int flags = ::fcntl(m_socket, F_GETFL);

        if (flags == -1) {
            SocketErrorExit("blocking::fcntl()");
        }
        flags = enabled ? (flags & ~O_NONBLOCK) : (flags | O_NONBLOCK);
        if (::fcntl(m_socket, F_SETFL, flags) == -1) {
            SocketErrorExit("blocking::fcntl()");
        }
    }

    void set_option(int optname, int level, int value) {

        if (::setsockopt(m_socket, level, optname, (const char*) &value, sizeof(value)) == SOCKET_ERROR) {
            SocketErrorExit("Socket::set_option()");
        }
    }

    int get_option(int optname, int level) {
        int value;
        socklen_t len;

        len = sizeof(value);
        if (::getsockopt(m_socket, level, optname, (char*) &value, &len) == SOCKET_ERROR) {
            SocketErrorExit("Socket::get_option()");
        }
        return value;
    }

    bool get_reuse_addr() {
        return static_cast<bool>(get_option(SO_REUSEADDR, SOL_SOCKET));
    }

    void set_reuse_addr(bool on) {
        set_option(SO_REUSEADDR, SOL_SOCKET, static_cast<int>(on));
    }

    int get_send_buffer_size() {
        return get_option(SO_SNDBUF, SOL_SOCKET);
    }

    void set_send_buffer_size(int size) {
        set_option(SO_SNDBUF, SOL_SOCKET, size);
    }

    int get_rcv_buffer_size() {
        return get_option(SO_RCVBUF, SOL_SOCKET);
    }

    void set_rcv_buffer_size(int size) {
        set_option(SO_RCVBUF, SOL_SOCKET, size);
    }

    bool getaddrinfo(int family, int socktype, int protocol, const char * hostname, int port, CAddress & address, int flags = AI_PASSIVE) {
        int err;
        ADDRINFO hints;
        ADDRINFO * t_addr;
        char port_str[16] = {0};

        ZeroOut(&hints, sizeof(hints));
        hints.ai_family = family;
        hints.ai_socktype = socktype;
        hints.ai_protocol = protocol;
        hints.ai_flags = flags;
        ::sprintf(port_str, "%d", port);
        err = ::getaddrinfo(hostname, port_str, &hints, &t_addr);
        if (err != 0) {
            printf("%s\n", gai_strerror(err));
            ::freeaddrinfo(t_addr);
            SocketErrorExit("getaddrinfo()");
            return false;
        }
        address.length = t_addr->ai_addrlen;
        CopyMemory(&address.address, t_addr->ai_addr, sizeof(SOCKADDR));
        ::freeaddrinfo(t_addr);
        return true;
    }

    void connect(CAddress & address) {
        if (::connect(m_socket, &address.address, address.length) == SOCKET_ERROR) {
            SocketErrorExit("Socket::connect()");
        }
        m_connected_socket = m_socket;
        printf("Sock-conn: %d\n", m_connected_socket);
    }

    void bind(CAddress & address) {
        if (::bind(m_socket, &address.address, address.length) == SOCKET_ERROR) {
            SocketErrorExit("Socket::bind()");
        }
    }

    void listen(int backlog = 1) {
        if (::listen(m_socket, backlog) == SOCKET_ERROR) {
            SocketErrorExit("Socket::listen()");
        }
    }

    void accept(CAddress & peerAddress) {

        peerAddress.length = sizeof peerAddress.address;
        m_connected_socket = ::accept(m_socket, (SOCKADDR *)&peerAddress.address, (socklen_t*)&peerAddress.length);

        if (m_connected_socket  == INVALID_SOCKET) {
            SocketErrorExit("Socket::accept()");
        }
    }

    void startReceiverThread() {
        int res = 0;

        res = ::pthread_create(&m_thread, NULL, blockingReceiverThread, this);
        if (res == -1) {
            OsErrorExit("startReceiverThread::pthread_create");
        }
    }

    void shutdownReceiverThread() {
        int res = 0;

        res = ::pthread_kill(m_thread, SIGINT);
        if (res == -1) {
            OsErrorExit("shutdownReceiverThread::pthread_kill");
        }
        res = pthread_join(m_thread, NULL);
        if (res == -1) {
            OsErrorExit("shutdownReceiverThread::pthread_join");
        }
    }

    template <typename T, size_t N>
    int read(std::array<T, N>& arr, size_t len) {
        int nbytes;

        nbytes = ::recv(m_connected_socket, (char*)arr.data(), len, 0);
        if (nbytes == -1) {
            OsErrorExit("read::recv");
        }

        return nbytes;
    }

    template <typename T, size_t N>
    void write(std::array<T, N>& arr) {
        if (m_socktype == SOCK_DGRAM) {
#if 0
            if (sendto(m_socket, (char const *)arr.data(), arr.size(), 0,
                        (SOCKADDR * )(SOCKADDR_STORAGE const *)&XcpTl_Connection.connectionAddress, ADDR_LEN) == SOCKET_ERROR) {
                SocketErrorExit("send::sendto()");
            }
#endif
        } else if (m_socktype == SOCK_STREAM) {
            if (::send(m_connected_socket, (char const *)arr.data(), arr.size(), 0) == SOCKET_ERROR) {
                SocketErrorExit("send::send()");
#if defined(_WIN32)
                closesocket(m_connected_socket);
#elif defined(__unix__)
                close(m_connected_socket);
#endif
            }
        }
    }

    SOCKET getSocket() const {
        return m_socket;
    }

protected:


private:
    int m_family;
    int m_socktype;
    int m_protocol;
    bool m_connected;
    addrinfo * m_addr;
    pthread_t m_thread;
    //TimeoutTimer m_timeout {150};

    SOCKET m_socket;
    SOCKET m_connected_socket;
    //CAddress ourAddress;
    SOCKADDR_STORAGE m_peerAddress;
};


#endif // __BLOCKING_SOCKET_HPP

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


#include <array>
#include <functional>
#include <thread>

#include "utils.hpp"

#if !defined(__BLOCKING_SOCKET_HPP)
#define __BLOCKING_SOCKET_HPP

#if defined(_WIN32)
    #include <WinSock2.h>
    #include <Ws2tcpip.h>
    #include <Mstcpip.h>
    #include <MSWSock.h>
    #include <Windows.h>
#elif defined(__unix__)
    #include <ctype.h>
    #include <errno.h>
    #include <fcntl.h>
    #include <limits.h>
    #include <signal.h>
    #include <stdlib.h>
    #include <stdio.h>
    #include <string.h>
    #include <time.h>
    #include <stdbool.h>
    #include <unistd.h>
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netdb.h>
    #include <arpa/inet.h>
    #include <sys/wait.h>

    #define INVALID_SOCKET          (-1)
    #define SOCKET_ERROR            (-1)
    #define ADDRINFO                addrinfo
    #define SOCKADDR                struct sockaddr
    #define SOCKADDR_STORAGE        sockaddr_storage

    typedef int SOCKET;
#endif

#include <pthread.h>

#define ADDR_LEN                    sizeof(SOCKADDR_STORAGE)

template <std::size_t N> using buffer_t = std::array<unsigned char, N>;

class Socket;

[[noreturn]] void blockingReceiverThread(Socket * socket);

struct CAddress {
    int length;
    struct sockaddr address;
};

class Socket {
public:

    using listen_thread_t = std::function<void(const Socket&)>;

    explicit Socket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) : m_family(family), m_socktype(socktype),
        m_protocol(protocol), m_connected(false),  m_addr(nullptr) {
        m_socket = ::socket(m_family, m_socktype, m_protocol);
        m_connected_socket = 0;
        if (m_socket == INVALID_SOCKET) {
            SocketErrorExit("Socket::Socket()");
        }
        blocking(true);
        ZeroOut(&m_peerAddress, sizeof(SOCKADDR_STORAGE));
    }

    ~Socket() {
#if defined(__unix__)
        ::close(m_socket);
#elif #defined(_WIN32)
        ::closesocket(m_socket);
#endif
    }

    void blocking(bool enabled) {
        int flags = ::fcntl(m_socket, F_GETFL);

        if (flags == -1) {
            SocketErrorExit("blocking::fcntl()");
        }
        flags = enabled ? (flags & ~O_NONBLOCK) : (flags | O_NONBLOCK);
        if (::fcntl(m_socket, F_SETFL, flags) == -1) {
            SocketErrorExit("blocking::fcntl()");
        }
    }

    void set_option(int optname, int level, int value) {

        if (::setsockopt(m_socket, level, optname, (const char*) &value, sizeof(value)) == SOCKET_ERROR) {
            SocketErrorExit("Socket::set_option()");
        }
    }

    int get_option(int optname, int level) {
        int value;
        socklen_t len;

        len = sizeof(value);
        if (::getsockopt(m_socket, level, optname, (char*) &value, &len) == SOCKET_ERROR) {
            SocketErrorExit("Socket::get_option()");
        }
        return value;
    }

    bool get_reuse_addr() {
        return static_cast<bool>(get_option(SO_REUSEADDR, SOL_SOCKET));
    }

    void set_reuse_addr(bool on) {
        set_option(SO_REUSEADDR, SOL_SOCKET, static_cast<int>(on));
    }

    int get_send_buffer_size() {
        return get_option(SO_SNDBUF, SOL_SOCKET);
    }

    void set_send_buffer_size(int size) {
        set_option(SO_SNDBUF, SOL_SOCKET, size);
    }

    int get_rcv_buffer_size() {
        return get_option(SO_RCVBUF, SOL_SOCKET);
    }

    void set_rcv_buffer_size(int size) {
        set_option(SO_RCVBUF, SOL_SOCKET, size);
    }

    bool getaddrinfo(int family, int socktype, int protocol, const char * hostname, int port, CAddress & address, int flags = AI_PASSIVE) {
        int err;
        ADDRINFO hints;
        ADDRINFO * t_addr;
        char port_str[16] = {0};

        ZeroOut(&hints, sizeof(hints));
        hints.ai_family = family;
        hints.ai_socktype = socktype;
        hints.ai_protocol = protocol;
        hints.ai_flags = flags;
        ::sprintf(port_str, "%d", port);
        err = ::getaddrinfo(hostname, port_str, &hints, &t_addr);
        if (err != 0) {
            printf("%s\n", gai_strerror(err));
            ::freeaddrinfo(t_addr);
            SocketErrorExit("getaddrinfo()");
            return false;
        }
        address.length = t_addr->ai_addrlen;
        CopyMemory(&address.address, t_addr->ai_addr, sizeof(SOCKADDR));
        ::freeaddrinfo(t_addr);
        return true;
    }

    void connect(CAddress & address) {
        if (::connect(m_socket, &address.address, address.length) == SOCKET_ERROR) {
            SocketErrorExit("Socket::connect()");
        }
        m_connected_socket = m_socket;
        printf("Sock-conn: %d\n", m_connected_socket);
    }

    void bind(CAddress & address) {
        if (::bind(m_socket, &address.address, address.length) == SOCKET_ERROR) {
            SocketErrorExit("Socket::bind()");
        }
    }

    void listen(int backlog = 1) {
        if (::listen(m_socket, backlog) == SOCKET_ERROR) {
            SocketErrorExit("Socket::listen()");
        }
    }

    void accept(CAddress & peerAddress) {

        peerAddress.length = sizeof peerAddress.address;
        m_connected_socket = ::accept(m_socket, (SOCKADDR *)&peerAddress.address, (socklen_t*)&peerAddress.length);

        if (m_connected_socket  == INVALID_SOCKET) {
            SocketErrorExit("Socket::accept()");
        }
    }

    void startReceiverThread() {
        int res = 0;

        m_thread = new std::thread(blockingReceiverThread, this);
    }

    void shutdownReceiverThread() {
        int res = 0;

        //res = ::pthread_kill(m_thread->native_handle(), SIGINT);
        res = ::pthread_cancel(m_thread->native_handle());
        if (res == -1) {
            OsErrorExit("shutdownReceiverThread::pthread_kill");
        }
        m_thread->join();
        delete m_thread;
    }

    template <typename T, size_t N>
    int read(std::array<T, N>& arr, size_t len) {
        int nbytes;

        nbytes = ::recv(m_connected_socket, (char*)arr.data(), len, 0);
        if (nbytes == -1) {
            OsErrorExit("read::recv");
        }

        return nbytes;
    }

    template <typename T, size_t N>
    void write(std::array<T, N>& arr) {
        if (m_socktype == SOCK_DGRAM) {
#if 0
            if (sendto(m_socket, (char const *)arr.data(), arr.size(), 0,
                        (SOCKADDR * )(SOCKADDR_STORAGE const *)&XcpTl_Connection.connectionAddress, ADDR_LEN) == SOCKET_ERROR) {
                SocketErrorExit("send::sendto()");
            }
#endif
        } else if (m_socktype == SOCK_STREAM) {
            if (::send(m_connected_socket, (char const *)arr.data(), arr.size(), 0) == SOCKET_ERROR) {
                SocketErrorExit("send::send()");
#if defined(_WIN32)
                closesocket(m_connected_socket);
#elif defined(__unix__)
                close(m_connected_socket);
#endif
            }
        }
    }

    SOCKET getSocket() const {
        return m_socket;
    }

protected:


private:
    int m_family;
    int m_socktype;
    int m_protocol;
    bool m_connected;
    addrinfo * m_addr;
    std::thread * m_thread = nullptr;
    //TimeoutTimer m_timeout {150};

    SOCKET m_socket;
    SOCKET m_connected_socket;
    //CAddress ourAddress;
    SOCKADDR_STORAGE m_peerAddress;
};


#endif // __BLOCKING_SOCKET_HPP
