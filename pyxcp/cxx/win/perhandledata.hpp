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
#if !defined(__PERHANDLEDATA_HPP)
#define __PERHANDLEDATA_HPP

#include <Windows.h>

enum class HandleType {
    HANDLE_SOCKET,
    HANDLE_FILE,
    HANDLE_NAMED_PIPE,
    HANDLE_USER,
};


struct PerHandleData {
    HandleType m_handleType;
    HANDLE m_handle;
    DWORD m_seqNoSend;
    DWORD m_seqNoRecv;

    PerHandleData(HandleType handleType, const HANDLE& handle) : m_handleType(handleType), m_handle(handle), m_seqNoSend(0), m_seqNoRecv(0) {}
};


#endif // __PERHANDLEDATA_HPP

