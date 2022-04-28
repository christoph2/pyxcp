/*
 *
 * Interface for asynchronous I/O services (IOCP, epoll, kqueue...).
 *
 *
 */

#if !defined(__IASYNCHIOSERVICE_HPP)
#define __IASYNCHIOSERVICE_HPP

#include <cstdlib>
#include <cstdint>

#include "socket.hpp"

enum class MessageCode : uint64_t {
    QUIT,
    TIMEOUT
};

class IAsyncIoService {
public:
    virtual ~IAsyncIoService() = default;
    virtual void registerSocket(Socket& socket) = 0;
    virtual void postUserMessage(MessageCode messageCode, void * data = nullptr) const = 0;
    virtual void postQuitMessage() const = 0;
    virtual HANDLE getHandle() const = 0;

};

#endif // __IASYNCHIOSERVICE_HPP
