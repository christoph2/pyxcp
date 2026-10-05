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
#if !defined(__IOCP_HPP)
#define __IOCP_HPP

#include "../iasyncioservice.hpp"
#include "socket.hpp"
#include "perhandledata.hpp"
#include "periodata.hpp"
#include "../poolmgr.hpp"
#include <cassert>
#include <cstdint>
#include <thread>
#include <vector>
#include <optional>

#if !defined(__GNUC__)
#pragma comment(lib,"ws2_32.lib") // MSVC only.
#endif


struct PerPortData {
    HANDLE handle;
};

struct Statistics {
    std::atomic<std::uint64_t> numIoReadsPosted;
    std::atomic<std::uint64_t> numIoWritesPosted;
    std::atomic<std::uint64_t> numIoCompleted;
    std::atomic<std::uint64_t> numIoErrors;
    std::atomic<std::uint64_t> numIoTimeouts;

    Statistics() : numIoReadsPosted(0), numIoWritesPosted(0), numIoCompleted(0), numIoErrors(0), numIoTimeouts(0) {};
};

class IOCP : public IAsyncIoService {
    constexpr static std::uint16_t MaxDontDefragIPv4 = 1472;
    constexpr static std::uint16_t MaxDontDefragIPv6 = 1452;

public:
    explicit IOCP(
        IoCallbacks callbacks = {}, size_t numProcessors = 1, size_t multiplier = 1, std::uint16_t readQueueDepth = 64,
        std::optional<std::uint16_t> bufferSize = std::nullopt
    );
    ~IOCP();
    void registerSocket(AsyncClientSocket& socket);
    void postUserMessage(MessageCode messageCode, void * data = nullptr) const;
    void postQuitMessage() const;
    HANDLE getHandle() const;
    void releaseIoData(PerIoData * data) const;

protected:
     void registerHandle(const PerHandleData& object);
     void workerThreadMain();
     void reportError(AsyncClientSocket * socket, IoType operation, DWORD error) const noexcept;
     void fillReadQueue(AsyncClientSocket * socket) const noexcept;

    uint16_t getBufferSize() const noexcept {
        return m_bufferSize.value_or(MaxDontDefragIPv4);
    }

    uint16_t getQueueDepth() const noexcept {
        return m_readQueueDepth;
    }

private:
    IoCallbacks m_callbacks;
    PerPortData m_port;
    DWORD m_numWorkerThreads;
    std::uint16_t m_readQueueDepth;
    std::optional<std::uint16_t> m_bufferSize;
    std::vector<std::jthread> m_threads;
    mutable Statistics m_statistics;
};

#endif // __IOCP_HPP
