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

