#if !defined(__ASYNCHIOFACTORY_HPP)
#define __ASYNCHIOFACTORY_HPP

#include <memory>

#include "iasyncioservice.hpp"

#if defined(_WIN32)
    #include "iocp.hpp"
#else
    #include "epoll.hpp"
#endif


inline std::unique_ptr<IAsyncIoService> createAsyncIoService()
{
#if defined(_WIN32)
    return std::make_unique<IOCP>();
#else
    return std::make_unique<Epoll>();
#endif
}

#endif // __ASYNCHIOFACTORY_HPP
