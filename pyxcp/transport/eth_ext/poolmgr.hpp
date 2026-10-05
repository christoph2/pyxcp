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


#if !defined(__POOLMGR_H)
#define __POOLMGR_H

#include "win/periodata.hpp"
#include <memory>
#include <memory_resource>

/*
 *
 * PoolManager holds various resource pools.
 *
 *
 */

class PoolManager {
public:
    static PerIoData * acquire_iod(size_t bufferSize = 128);
    static void release_iod(PerIoData * data);

private:
    static std::pmr::synchronized_pool_resource m_resource;
};


#endif // __POOLMGR_H
