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
#if !defined(__PERIODATA_HPP)
#define __PERIODATA_HPP

#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <memory_resource>
#include "utils.hpp"
#include "../io_types.hpp"
#include <WinSock2.h>
#include <Ws2tcpip.h>
#include <Mstcpip.h>

enum class RcvState : std::uint8_t{
    FREE,
    POSTED,
    RECEIVED,
    PROCESSING,
};

class PerIoData {

public:

    explicit PerIoData(size_t bufferSize = 128, std::pmr::memory_resource * resource = std::pmr::get_default_resource()) :
        m_xferBuffer(resource) {
        m_xferBuffer.resize(bufferSize);
		m_wsabuf.buf = m_xferBuffer.data();
        m_wsabuf.len = static_cast<ULONG>(bufferSize);
        m_bytesRemaining = 0;
        m_bytes_to_xfer = 0;
    }

    // Copies the payload into the pooled buffer (call after reset()).
    void set_payload(const void * data, size_t length) {
        if (m_xferBuffer.size() < length) {
            m_xferBuffer.resize(length);
        }
        std::memcpy(m_xferBuffer.data(), data, length);
        m_wsabuf.buf = m_xferBuffer.data();
        m_wsabuf.len = static_cast<ULONG>(length);
        m_bytesRemaining = m_bytes_to_xfer = length;
    }

    void set_peer(const sockaddr * address, int length) {
        std::memcpy(&m_peerAddress, address, static_cast<size_t>(length));
        m_peerAddressLength = length;
    }

    // Prepares the remainder of a partially completed send for re-posting.
    void advance(size_t amount) {
        ZeroOut(&m_overlapped, sizeof(OVERLAPPED));
        m_wsabuf.buf += amount;
        m_wsabuf.len -= static_cast<ULONG>(amount);
    }

    void set_opcode(IoType opcode) {
        m_opcode = opcode;
    }

    template <typename T, size_t N> void set_buffer(std::array<T, N>& arr) {

        m_wsabuf.buf = arr.data();
        m_wsabuf.len = static_cast<ULONG>(arr.size());
    }

    WSABUF * get_buffer() {
        return &m_wsabuf;
    }

    sockaddr * get_peer_address() {
        return reinterpret_cast<sockaddr *>(&m_peerAddress);
    }

    int * get_peer_address_length() {
        return &m_peerAddressLength;
    }

    IoType get_opcode() const {
        return m_opcode;
    }

    void set_transfer_length(size_t length) {
        m_bytesRemaining = m_bytes_to_xfer = length;
    }

    size_t get_bytes_to_xfer() const {
        return m_bytes_to_xfer;
    }

    void decr_bytes_to_xfer(size_t amount) {
        assert((static_cast<int64_t>(m_bytesRemaining) - static_cast<int64_t>(amount)) >= 0);

        m_bytesRemaining -= amount;
    }

    bool xfer_finished() const {
        return m_bytesRemaining == 0;
    }

    OVERLAPPED * get_overlapped() {
        return &m_overlapped;
    }

    // Prepares the WSAMSG used by WSARecvMsg (PTP timestamping) from the current buffer/peer/control state.
    WSAMSG * prepare_msg() {
        ZeroOut(&m_msg, sizeof(m_msg));
        m_msg.name = reinterpret_cast<LPSOCKADDR>(&m_peerAddress);
        m_msg.namelen = m_peerAddressLength;
        m_msg.lpBuffers = &m_wsabuf;
        m_msg.dwBufferCount = 1;
        m_msg.Control.buf = m_control;
        m_msg.Control.len = static_cast<ULONG>(sizeof(m_control));
        m_msg.dwFlags = 0;
        return &m_msg;
    }

    // Receive timestamp (ns) from the SO_TIMESTAMP control message of the last WSARecvMsg; 0 if absent.
    std::uint64_t get_timestamp_ns() {
        for (WSACMSGHDR * cmsg = WSA_CMSG_FIRSTHDR(&m_msg); cmsg != nullptr; cmsg = WSA_CMSG_NXTHDR(&m_msg, cmsg)) {
            if (cmsg->cmsg_level == SOL_SOCKET && cmsg->cmsg_type == SO_TIMESTAMP) {
                std::uint64_t ticks = 0;
                std::memcpy(&ticks, WSA_CMSG_DATA(cmsg), sizeof(ticks));
                return ticks * 100;  // 100 ns resolution
            }
        }
        return 0;
    }

    void reset() {
        ZeroOut(&m_overlapped, sizeof(OVERLAPPED));
        m_wsabuf.buf = m_xferBuffer.data();
        m_wsabuf.len = static_cast<ULONG>(m_xferBuffer.size());
        m_bytesRemaining = 0;
        m_bytes_to_xfer = 0;
        ZeroOut(&m_peerAddress, sizeof(m_peerAddress));
        m_peerAddressLength = sizeof(m_peerAddress);
        ZeroOut(&m_msg, sizeof(m_msg));
    }

private:
    OVERLAPPED m_overlapped;
    IoType m_opcode;
    WSABUF m_wsabuf;
    std::pmr::vector<char> m_xferBuffer;
    size_t m_bytes_to_xfer;
    size_t m_bytesRemaining;
    sockaddr_storage m_peerAddress {};
    int m_peerAddressLength {sizeof(sockaddr_storage)};
    WSAMSG m_msg {};
    alignas(8) char m_control[128] {};
};

#endif // __PERIODATA_HPP
