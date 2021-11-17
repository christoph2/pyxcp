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
#if !defined(__PERIODATA_HPP)
#define __PERIODATA_HPP

#include <array>
#include <cassert>
#include "utils.hpp"
#include <WinSock2.h>

enum class IoType {
    IO_ACCEPT,
    IO_CONNECT,
    IO_READ,
    IO_WRITE
};

class PerIoData {

public:

    explicit PerIoData(size_t bufferSize = 128) {
        m_xferBuffer = nullptr;
        m_xferBuffer = new char[bufferSize];
        m_wsabuf.buf = m_xferBuffer;

        m_wsabuf.len = bufferSize;
        m_bytesRemaining = 0;
        m_bytes_to_xfer = 0;
    }

    ~PerIoData() {
        if (m_xferBuffer) {
            delete[] m_xferBuffer;
        }
    }

    void setup_write_request() {

    }

    void set_opcode(IoType opcode) {
        m_opcode = opcode;
    }

    template <typename T, size_t N> void set_buffer(std::array<T, N>& arr) {

        m_wsabuf.buf = arr.data();
        m_wsabuf.len = arr.size();
    }

    WSABUF * get_buffer() {
        return &m_wsabuf;
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
        printf("remaining: %d amount: %d\n",m_bytesRemaining, amount);
        assert((static_cast<int64_t>(m_bytesRemaining) - static_cast<int64_t>(amount)) >= 0);

        m_bytesRemaining -= amount;
    }

    bool xfer_finished() const {
        return m_bytesRemaining == 0;
    }

    OVERLAPPED * get_overlapped() {
        return &m_overlapped;
    }

    void reset() {
        ZeroOut(&m_overlapped, sizeof(OVERLAPPED));
        m_wsabuf.len = 0;
        m_bytesRemaining = 0;
        m_bytes_to_xfer = 0;
    }

private:
    OVERLAPPED m_overlapped;
    IoType m_opcode;
    WSABUF m_wsabuf;
    char * m_xferBuffer;
    size_t m_bytes_to_xfer;
    size_t m_bytesRemaining;
};

#endif // __PERIODATA_HPP

