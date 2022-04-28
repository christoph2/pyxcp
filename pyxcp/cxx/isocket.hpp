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
