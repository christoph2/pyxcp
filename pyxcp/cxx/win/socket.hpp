
#if !defined(__SOCKET_HPP)
#define __SOCKET_HPP

#include <array>

#include <WinSock2.h>
#include <Ws2tcpip.h>
#include <Mstcpip.h>
#include <MSWSock.h>
#include <Windows.h>

#include "isocket.hpp"
#include "timeout.hpp"
#include "periodata.hpp"
#include "perhandledata.hpp"
#include "pool.hpp"
#include "poolmgr.hpp"

class IOCP;

class Socket : public ISocket {
public:

    using Pool_t = Pool<PerIoData, 16>;

    Socket(int family = PF_INET, int socktype = SOCK_STREAM, int protocol = IPPROTO_TCP) :
        m_family(family), m_socktype(socktype), m_protocol(protocol), m_connected(false),
        m_pool_mgr(PoolManager()), m_addr(nullptr) {
        m_socket = ::WSASocket(m_family, m_socktype, m_protocol, NULL, 0, WSA_FLAG_OVERLAPPED);
        if (m_socket == INVALID_SOCKET) {
            SocketErrorExit("Socket::Socket()");
        }
        ZeroOut(&m_peerAddress, sizeof(SOCKADDR_STORAGE));
    }

    ~Socket() {
        ::closesocket(m_socket);
    }

    void option(int optname, int level, int * value) {
        int len;

        len = sizeof(*value);
        if (*value == 0) {
            ::getsockopt(m_socket, level, optname, (char*) value, &len);
        } else {
            ::setsockopt(m_socket, level, optname, (const char*) value, len);
        }
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
        ::CopyMemory(&address.address, t_addr->ai_addr, sizeof(struct sockaddr));

        ::freeaddrinfo(t_addr);
        return true;
    }

    void connect(CAddress & address) {
        if (::connect(m_socket, &address.address, address.length) == SOCKET_ERROR) {
            SocketErrorExit("Socket::connect()");
        }
        PerHandleData handleData(HandleType::HANDLE_SOCKET, getHandle());
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
        SOCKET sock;

        peerAddress.length = sizeof peerAddress.address;
        sock = ::accept(m_socket, (sockaddr *)&peerAddress.address, &peerAddress.length);

        if (sock  == INVALID_SOCKET) {
            SocketErrorExit("Socket::accept()");
        }
    }

    template <typename T, size_t N>
    void write(std::array<T, N>& arr, bool alloc = true) {
        DWORD bytesWritten = 0;
        int addrLen;
        //PerIoData * iod = new PerIoData(128);
        PerIoData * iod;

        if (alloc == true) {
            iod = m_pool_mgr.get_iod().acquire();
            //iod = m_iod_pool.acquire();
        }
        m_timeout.arm();
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
        printf("Status: %d bytes_written: %d\n", WSAGetLastError(), bytesWritten);
    }
    void triggerRead(unsigned int len);

    HANDLE getHandle() const {
        return reinterpret_cast<HANDLE>(m_socket);
    }

    const TimeoutTimer& getTimeoutTimer() const {
        return m_timeout;
    }

    void setIOCP(IOCP * iocp) {
        m_iocp = iocp;
        m_timeout.setIOCP(iocp);
    }

private:
    int m_family;
    int m_socktype;
    int m_protocol;
    bool m_connected;
    PoolManager m_pool_mgr;
    ADDRINFO * m_addr;
    SOCKET m_socket;
    //CAddress ourAddress;
    SOCKADDR_STORAGE m_peerAddress;
    TimeoutTimer m_timeout {150};
    IOCP * m_iocp = nullptr;
};

#endif  // __SOCKET_HPP
