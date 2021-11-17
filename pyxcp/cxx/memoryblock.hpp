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
#if !defined(__MEMORYBLOCK_HPP)
#define __MEMORYBLOCK_HPP

#include "iresource.hpp"

/*
 *
 * Fixed size memory block.
 *
 */
template <typename T, int N> class MemoryBlock : IResource {

public:

    explicit MemoryBlock() : m_memory(nullptr) {
        m_memory = new T[N];
        //printf("MemBlock-ctor: %p\n", m_memory);
    }

    ~MemoryBlock() {
        //printf("MemoryBlock-dtor: %p\n", m_memory);
        if (m_memory) {
            delete[] m_memory;
        }
    }

    T * data() {
        return m_memory;
    }

    void reset() {
    #if !defined(NDEBUG)

    #endif
    }

private:
    T * m_memory;

};

#endif // __MEMORYBLOCK_HPP

