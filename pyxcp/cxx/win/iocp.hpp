#if !defined(__IOCP_HPP)
#define __IOCP_HPP

#include "iasyncioservice.hpp"
#include "socket.hpp"
#include "perhandledata.hpp"
#include "periodata.hpp"
#include "poolmgr.hpp"
#include <cassert>
#include <cstdint>
#include <vector>

#if !defined(__GNUC__)
#pragma comment(lib,"ws2_32.lib") // MSVC only.
#endif


struct PerPortData {
    HANDLE handle;
};


class IOCP : public IAsyncIoService {
public:
    IOCP(size_t numProcessors = 1, size_t multiplier = 1);
    ~IOCP();
    void registerSocket(Socket& socket);
    void postUserMessage(MessageCode messageCode, void * data = nullptr) const;
    void postQuitMessage() const;
    HANDLE getHandle() const;

protected:
     void registerHandle(const PerHandleData& object);

private:
    PerPortData m_port;
    DWORD m_numWorkerThreads;
    std::vector<HANDLE> m_threads;
    PoolManager m_pool_mgr;
};

#endif // __IOCP_HPP
