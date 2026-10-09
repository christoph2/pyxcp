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

#if !defined(__ASYNCHIOFACTORY_HPP)
#define __ASYNCHIOFACTORY_HPP

#include <memory>

#include "iasyncioservice.hpp"

#if defined(_WIN32)
    #include "iocp.hpp"
#elif defined(__APPLE__) || defined(__FreeBSD__)
    #include "kqueue.hpp"
#else
    #include "epoll.hpp"
#endif


inline std::unique_ptr<IAsyncIoService> createAsyncIoService(IoCallbacks callbacks = {}, std::uint16_t readQueueDepth = 64, std::optional<std::uint16_t> bufferSize = std::nullopt)
{
#if defined(_WIN32)
    return std::make_unique<IOCP>(std::move(callbacks), 1, 1, readQueueDepth, bufferSize);
#elif defined(__APPLE__) || defined(__FreeBSD__)
    return std::make_unique<Kqueue>(std::move(callbacks), readQueueDepth, std::move(bufferSize));
#else
    return std::make_unique<Epoll>(std::move(callbacks), readQueueDepth, std::move(bufferSize));
#endif
}

#endif // __ASYNCHIOFACTORY_HPP
