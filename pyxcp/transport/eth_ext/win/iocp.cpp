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

#include "iocp.hpp"
#include "socket.hpp"
#include "exceptions.hpp"
#include "timeout.hpp"

#include <cstdio>
#include <cstddef>
#include <utility>

#if defined(IOCP_TRACE_ENABLED)
    #define IOCP_TRACE(...) printf(__VA_ARGS__)
#else
    #define IOCP_TRACE(...) ((void)0)
#endif


IOCP::IOCP(IoCallbacks callbacks, size_t numProcessors, size_t multiplier, std::size_t readQueueDepth, std::optional<std::uint16_t> receiveLength) :
    m_callbacks(std::move(callbacks)), m_readQueueDepth(readQueueDepth), m_receiveLength(receiveLength) {
    m_numWorkerThreads = static_cast<DWORD>(numProcessors * multiplier);
    m_port.handle = ::CreateIoCompletionPort(INVALID_HANDLE_VALUE, nullptr, static_cast<ULONG_PTR>(0), m_numWorkerThreads);
    if (m_port.handle == nullptr) {
        OsErrorExit("IOCP::IOCP()");
    }

    m_threads.reserve(m_numWorkerThreads);
    for (DWORD idx = 0; idx < m_numWorkerThreads; ++idx) {
        m_threads.emplace_back([this](std::stop_token) { workerThreadMain(); });
        ::SetThreadPriority(reinterpret_cast<HANDLE>(m_threads.back().native_handle()), THREAD_PRIORITY_ABOVE_NORMAL);
    }
}

IOCP::~IOCP() {
    for (size_t idx = 0; idx < m_threads.size(); ++idx) {
        postQuitMessage();
    }
    m_threads.clear();
    ::CloseHandle(m_port.handle);
}

void IOCP::registerHandle(const PerHandleData& object) {
    const HANDLE handle = ::CreateIoCompletionPort(object.m_handle, m_port.handle, reinterpret_cast<ULONG_PTR>(&object), 0);
    if ((handle == nullptr) || (handle != m_port.handle)) {
        OsErrorExit("IOCP::registerHandle()");
    }
}

void IOCP::registerSocket(AsyncClientSocket& socket) {
    socket.setIOCP(this);
    registerHandle(socket.getHandleData());
    if (!m_receiveLength.has_value()) {
        // Use save defaults.
        if (socket.getSocketFamily() == PF_INET6) {
            m_receiveLength = MaxDontDefragIPv6;
        } else {
            m_receiveLength = MaxDontDefragIPv4;
        }
    }
    fillReadQueue(&socket);
}

void IOCP::postUserMessage(MessageCode messageCode, void * data) const {
    if (!::PostQueuedCompletionStatus(m_port.handle, 0, static_cast<ULONG_PTR>(messageCode), (OVERLAPPED*)data)) {
        OsErrorExit("IOCP::postUserMessage()");
    }
}

void IOCP::postQuitMessage() const {
    postUserMessage(MessageCode::QUIT, nullptr);
}

HANDLE IOCP::getHandle() const {
    return m_port.handle;
}

void IOCP::releaseIoData(PerIoData * data) const {
    PoolManager::release_iod(data);
}

void IOCP::reportError(AsyncClientSocket * socket, IoType operation, DWORD error) const noexcept {
    try {
        if (m_callbacks.on_error) {
            m_callbacks.on_error(socket, operation, error);
        } else {
            fprintf(stderr, "I/O operation failed (Windows error %lu)\n", error);
        }
    } catch (...) {
        // A throwing error handler must not take down the worker thread.
    }
}

void IOCP::fillReadQueue(AsyncClientSocket * socket) const noexcept {
    auto & posted = m_statistics.numIoReadsPosted;
    while (posted.load(std::memory_order_relaxed) < m_readQueueDepth) {
        posted.fetch_add(1, std::memory_order_relaxed);
        const int rc = socket->tryTriggerRead(m_receiveLength.value());
        if (rc == 0) {
            continue;
        }
        posted.fetch_sub(1, std::memory_order_relaxed);
        if (socket->getSocketType() == SOCK_DGRAM && (rc == WSAECONNRESET || rc == ERROR_PORT_UNREACHABLE)) {
            continue;
        }
        reportError(socket, IoType::IO_READ, static_cast<DWORD>(rc));
        return;
    }
}

void IOCP::workerThreadMain() {
    DWORD bytesTransferred = 0;
    ULONG_PTR completionKey = 0;
    OVERLAPPED * overlapped = nullptr;

    IOCP_TRACE("Entering worker thread %lu.\n", ::GetCurrentThreadId());
    for (;;) {
        overlapped = nullptr;
        const BOOL ok = ::GetQueuedCompletionStatus(getHandle(), &bytesTransferred, &completionKey, &overlapped, INFINITE);

        if (overlapped == nullptr) {
            if (!ok) {
                // The port itself failed; nothing sensible left to wait for.
                reportError(nullptr, IoType::IO_READ, ::GetLastError());
                break;
            }
            // No I/O completed -- this is one of our own user messages.
            const auto messageCode = static_cast<MessageCode>(completionKey);
            if (messageCode == MessageCode::QUIT) {
                break;
            }
            if (messageCode == MessageCode::TIMEOUT && m_callbacks.on_timeout) {
                try {
                    m_callbacks.on_timeout();
                } catch (...) {
                }
            }
            continue;
        }

        auto * phd = reinterpret_cast<PerHandleData *>(completionKey);
        auto * iod = reinterpret_cast<PerIoData *>(overlapped);
        auto * socket = reinterpret_cast<AsyncClientSocket *>(phd->m_owner);
        const IoType opcode = iod->get_opcode();

        if (!ok) {
            // Failed I/O operation (e.g. connection reset, cancelled read).
            const DWORD error = ::GetLastError();
            releaseIoData(iod);
            if (opcode == IoType::IO_READ) {
                m_statistics.numIoReadsPosted.fetch_sub(1, std::memory_order_relaxed);
            }
            // ICMP "port unreachable" (a previous reply hit a closed client port) is expected
            // on UDP and not an error of this operation.
            const bool benignUdp = opcode == IoType::IO_READ && socket != nullptr && socket->getSocketType() == SOCK_DGRAM &&
                                   (error == ERROR_PORT_UNREACHABLE || error == WSAECONNRESET);
            if (!benignUdp) {
                reportError(socket, opcode, error);
            }
            // Datagram receives survive e.g. ICMP "port unreachable" (WSAECONNRESET);
            // keep them going unless the operation was cancelled (socket closing).
            if (opcode == IoType::IO_READ && socket != nullptr && socket->getSocketType() == SOCK_DGRAM &&
                error != ERROR_OPERATION_ABORTED) {
                fillReadQueue(socket);
            }
            continue;
        }

        switch (opcode) {
            case IoType::IO_WRITE:
                iod->decr_bytes_to_xfer(bytesTransferred);
                if (iod->xfer_finished()) {
                    if (m_callbacks.on_send_complete && socket != nullptr) {
                        try {
                            m_callbacks.on_send_complete(*socket, iod->get_bytes_to_xfer());
                        } catch (...) {
                        }
                    }
                    releaseIoData(iod);
                } else {
                    // Partial send: post the remainder (stream sockets only).
                    iod->advance(bytesTransferred);
                    if (socket != nullptr) {
                        if (const int rc = socket->postWrite(iod); rc != 0) {
                            reportError(socket, IoType::IO_WRITE, static_cast<DWORD>(rc));
                        }
                    } else {
                        releaseIoData(iod);
                    }
                }
                break;
            case IoType::IO_READ:
                m_statistics.numIoCompleted.fetch_add(1, std::memory_order_relaxed);
                m_statistics.numIoReadsPosted.fetch_sub(1, std::memory_order_relaxed);
                if (bytesTransferred == 0 && socket != nullptr && socket->getSocketType() == SOCK_STREAM) {
                    // Peer performed an orderly shutdown; stop reading.
                    releaseIoData(iod);
                    if (m_callbacks.on_disconnect) {
                        try {
                            m_callbacks.on_disconnect(*socket);
                        } catch (...) {
                        }
                    }
                    break;
                }
                if (m_callbacks.on_receive && socket != nullptr) {
                    // Zero-copy: the buffer is handed out as-is and recycled right after the call.
                    const sockaddr * peer = (socket->getSocketType() == SOCK_DGRAM) ? iod->get_peer_address() : nullptr;
                    try {
                        m_callbacks.on_receive(*socket, iod->get_buffer()->buf, bytesTransferred, peer);
                    } catch (...) {
                    }
                }
                releaseIoData(iod);
                if (socket != nullptr) {
                    fillReadQueue(socket);  // Keep the queue at its configured depth.
                }
                break;
            case IoType::IO_ACCEPT:
            case IoType::IO_CONNECT:
                break;
        }
    }
    IOCP_TRACE("Exiting worker thread %lu\n", ::GetCurrentThreadId());
}

void CALLBACK Timeout_CB(void * lpParam, unsigned char /*TimerOrWaitFired*/) {
    IOCP const * const iocp = reinterpret_cast<IOCP const * const>(lpParam);

    iocp->postUserMessage(MessageCode::TIMEOUT);
}

void AsyncClientSocket::triggerRead(unsigned int len) {
    if (const int err = tryTriggerRead(len); err != 0) {
        ::WSASetLastError(err);
        SocketErrorExit("AsyncClientSocket::triggerRead()");
    }
}

int AsyncClientSocket::tryTriggerRead(unsigned int len) noexcept {
    DWORD numReceived = 0;
    DWORD flags = 0;
    int result = 0;

    PerIoData * iod = PoolManager::acquire_iod(len);
    iod->reset();
    iod->set_opcode(IoType::IO_READ);
    iod->set_transfer_length(len);

    if (m_socktype == SOCK_STREAM) {
        result = ::WSARecv(getHandle(), iod->get_buffer(), 1, &numReceived, &flags, (LPWSAOVERLAPPED)iod, nullptr);
    } else if (m_socktype == SOCK_DGRAM) {
        result = ::WSARecvFrom(
            getHandle(), iod->get_buffer(), 1, &numReceived, &flags, iod->get_peer_address(), iod->get_peer_address_length(),
            (LPWSAOVERLAPPED)iod, nullptr
        );
    }
    if (result == SOCKET_ERROR) {
        const int err = ::WSAGetLastError();
        if (err != WSA_IO_PENDING) {
            PoolManager::release_iod(iod);
            return err;
        }
    }
    return 0;
}


int AsyncClientSocket::postWrite(PerIoData * iod) noexcept {
    DWORD bytesWritten = 0;
    int result = 0;

    if (m_socktype == SOCK_DGRAM) {
        result = ::WSASendTo(
            getHandle(), iod->get_buffer(), 1, &bytesWritten, 0, iod->get_peer_address(), *iod->get_peer_address_length(),
            (LPWSAOVERLAPPED)iod, nullptr
        );
    } else {
        result = ::WSASend(getHandle(), iod->get_buffer(), 1, &bytesWritten, 0, (LPWSAOVERLAPPED)iod, nullptr);
    }
    if (result == SOCKET_ERROR) {
        const int err = ::WSAGetLastError();
        if (err != WSA_IO_PENDING) {
            PoolManager::release_iod(iod);
            return err;
        }
    }
    return 0;
}

int AsyncClientSocket::writeTo(const sockaddr * address, int addressLength, const void * data, std::size_t length) noexcept {
    if (m_socktype == SOCK_DGRAM && (address == nullptr || addressLength <= 0 || addressLength > static_cast<int>(sizeof(SOCKADDR_STORAGE)))) {
        return WSAEDESTADDRREQ;
    }
    PerIoData * iod = nullptr;
    try {
        iod = PoolManager::acquire_iod(length);
    } catch (...) {
        return WSA_NOT_ENOUGH_MEMORY;
    }
    iod->reset();
    iod->set_opcode(IoType::IO_WRITE);
    iod->set_payload(data, length);
    if (m_socktype == SOCK_DGRAM) {
        iod->set_peer(address, addressLength);
    }
    return postWrite(iod);
}
