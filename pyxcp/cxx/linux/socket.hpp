#if !defined(__SOCKET_HPP)
#define __SOCKET_HPP

#include <array>
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

#include "isocket.hpp"
#include "utils.hpp"
#include "timeout.hpp"

#define SOCKET_ERROR (-1)
#define INVALID_SOCKET (-1)

using HANDLE = int;
using SOCKET = int;

class Socket : public ISocket {
public:

    Socket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) :
        m_family(family), m_socktype(socktype), m_protocol(protocol), m_connected(false),
        m_addr(nullptr), m_timeout(150) {
        m_socket = ::socket(m_family, m_socktype, m_protocol);
        if (m_socket == INVALID_SOCKET) {
            SocketErrorExit("Socket::Socket()");
        }
        blocking(false);
        ZeroOut(&m_peerAddress, sizeof(sockaddr_storage));
    }

    ~Socket() {
        ::close(m_socket);
    }

    void blocking(bool enabled) {
        int flags = fcntl(m_socket, F_GETFL);

        if (flags == -1) {
            SocketErrorExit("Socket::blocking()");
        }
        flags = enabled ? (flags & ~O_NONBLOCK) : (flags | O_NONBLOCK);
        if (fcntl(m_socket, F_SETFL, flags) == -1) {
            SocketErrorExit("Socket::blocking()");
        }
    }

    void option(int optname, int level, int * value) {
        socklen_t len;

        len = sizeof(*value);
        if (*value == 0) {
            ::getsockopt(m_socket, level, optname, (char*) value, &len);
        } else {
            ::setsockopt(m_socket, level, optname, (const char*) value, len);
        }
    }

    bool getaddrinfo(int family, int socktype, int protocol, const char * hostname, int port, CAddress & address, int flags = AI_PASSIVE) {
        int err;
        addrinfo hints;
        addrinfo * t_addr;
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
        ::memcpy(&address.address, t_addr->ai_addr, sizeof(struct sockaddr));

        ::freeaddrinfo(t_addr);
        return true;
    }

    void connect(CAddress & address) {
        blocking(true);
        if (::connect(m_socket, &address.address, address.length) == SOCKET_ERROR) {
            if (errno != EINPROGRESS) {
                SocketErrorExit("Socket::connect()");
            }
        }
        blocking(false);
    }

    void bind(CAddress & address) {
        if (::bind(m_socket, &address.address, address.length) == SOCKET_ERROR) {
            SocketErrorExit("Socket::bind()");
        }
    }

    void listen(int backlog = 5) {
        if (::listen(m_socket, backlog) == SOCKET_ERROR) {
            SocketErrorExit("Socket::listen()");
        }
    }

    void accept(CAddress & peerAddress) {
        int sock;

        peerAddress.length = sizeof peerAddress.address;
        sock = ::accept(m_socket, (sockaddr *)&peerAddress.address, (socklen_t*)&peerAddress.length);

        if (sock  == INVALID_SOCKET) {
            SocketErrorExit("Socket::accept()");
        }
    }

    template <typename T, size_t N>
    void write(std::array<T, N>& arr, bool alloc = true) {
        size_t bytesWritten = 0;
        int addrLen;

        m_timeout.arm();

        if (m_socktype == SOCK_DGRAM) {
#if 0
            if (sendto(m_socket, (char const *)arr.data(), arr.size(), 0, (struct sockaddr const *)&XcpTl_Connection.connectionAddress, addrSize) == -1) {
                SocketErrorExit("Socket::write() -- sendto()");
            }
#endif
        } else if (m_socktype == SOCK_STREAM) {
            if (send(m_socket, (char const *)arr.data(), arr.size(), 0) == -1) {
                SocketErrorExit("Socket::write() -- send()");
            }
        }
#if 0
        //PerIoData * iod = new PerIoData(128);
        PerIoData * iod;

        if (alloc == true) {
            iod = m_pool_mgr.get_iod().acquire();
            //iod = m_iod_pool.acquire();
        }
        iod->reset();
        iod->set_buffer(arr);
        iod->set_opcode(IoType::IO_WRITE);
        iod->set_transfer_length(arr.size());
        if (m_socktype == SOCK_DGRAM) {
            addrLen = sizeof(SOCKADDR_STORAGE);
            if (::WSASendTo(m_socket,
                iod->get_buffer(),
                1,
                &bytesWritten,
                0,
                (LPSOCKADDR)&m_peerAddress,
                addrLen,
                (LPWSAOVERLAPPED)iod,
                nullptr
            ) == SOCKET_ERROR) {
                // WSA_IO_PENDING
                SocketErrorExit("Socket::send()");
            }
        } else if (m_socktype == SOCK_STREAM) {
            if (::WSASend(
                m_socket,
                iod->get_buffer(),
                1,
                &bytesWritten,
                0,
                (LPWSAOVERLAPPED)iod,
                nullptr) == SOCKET_ERROR) {
                    SocketErrorExit("Socket::send()");
                closesocket(m_socket);
            }
        }
#endif
        printf("Status: %d bytes_written: %d\n", errno, bytesWritten);
    }
#if 0
    void read(size_t count) {
    if ( (n = read(sockfd, line, MAXLINE)) < 0) {
        if (errno == ECONNRESET) {
            close(sockfd);
            events[i].data.fd = -1;
    } else printf("readline error\n");
                                                                                                                                } else if (n == 0) {
                                                                                                                                                        close(sockfd);
                                                                                                                                                                            events[i].data.fd = -1;
                                                                                                                                                                                            }

    }
#endif

    void triggerRead(unsigned int len);

    HANDLE getHandle() const {
        return m_socket;
    }

    const TimeoutTimer& getTimeout() const {
        return m_timeout;
    }

private:
    int m_family;
    int m_socktype;
    int m_protocol;
    bool m_connected;
//    PoolManager m_pool_mgr;
    addrinfo * m_addr;
    TimeoutTimer m_timeout {150};
    int m_socket;
    //CAddress ourAddress;
    sockaddr_storage m_peerAddress;
};

#endif  // __SOCKET_HPP
