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

