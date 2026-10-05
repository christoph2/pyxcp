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

#include "poolmgr.hpp"

#include <memory_resource>

// Shared by IOCP workers and sockets so pooled allocations can be reused across handles.
std::pmr::synchronized_pool_resource PoolManager::m_resource;

PerIoData * PoolManager::acquire_iod(size_t bufferSize) {
    std::pmr::polymorphic_allocator<PerIoData> allocator {&m_resource};
    PerIoData * data = allocator.allocate(1);
    try {
        std::allocator_traits<decltype(allocator)>::construct(allocator, data, bufferSize, &m_resource);
    } catch (...) {
        allocator.deallocate(data, 1);
        throw;
    }
    return data;
}

void PoolManager::release_iod(PerIoData * data) {
    std::pmr::polymorphic_allocator<PerIoData> allocator {&m_resource};
    std::allocator_traits<decltype(allocator)>::destroy(allocator, data);
    allocator.deallocate(data, 1);
}
