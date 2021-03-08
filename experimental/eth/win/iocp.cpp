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
#include "iocp.hpp"
#include "socket.hpp"
#include "exceptions.hpp"

#include <iostream>
#include <cstdio>
#include <cstddef>


/*
 *
 *
 *
 */


static DWORD WINAPI WorkerThread(LPVOID lpParameter);

IOCP::IOCP(DWORD numProcessors)
{
    m_port.handle  = ::CreateIoCompletionPort(INVALID_HANDLE_VALUE, NULL, static_cast<ULONG_PTR>(0), numProcessors);
    if (m_port.handle == NULL) {
        throw WindowsException();
    }

    m_numWorkerThreads = numProcessors * 2; // Hard-coded for now.

    m_threads.reserve(m_numWorkerThreads);

    HANDLE hThread;

    for (DWORD idx = 0; idx < m_numWorkerThreads; ++idx) {
        hThread = ::CreateThread(NULL, 0, WorkerThread, reinterpret_cast<LPVOID>(this), 0, NULL);
        SetThreadPriority(hThread, THREAD_PRIORITY_ABOVE_NORMAL);
        m_threads.push_back(hThread);
    }
}

IOCP::~IOCP()
{
    DWORD numThreads = static_cast<DWORD>(m_threads.size());
    std::ldiv_t divres = std::ldiv(numThreads, MAXIMUM_WAIT_OBJECTS);
    DWORD rounds = static_cast<DWORD>(divres.quot);
    DWORD remaining = static_cast<DWORD>(divres.rem);
    HANDLE * thrArray = NULL;
    DWORD offset = 0;
    DWORD idx = 0;

    postQuitMessage();

    thrArray = new HANDLE[MAXIMUM_WAIT_OBJECTS];
    for (DWORD r = 0; r < rounds; ++r) {
        for (idx = 0; idx < MAXIMUM_WAIT_OBJECTS; ++idx) {
            thrArray[idx] = m_threads.at(idx + offset);
        }
        WaitForMultipleObjects(MAXIMUM_WAIT_OBJECTS, thrArray, TRUE, INFINITE);
        for (idx = 0; idx < MAXIMUM_WAIT_OBJECTS; ++idx) {
            CloseHandle(thrArray[idx]);
        }
        offset += MAXIMUM_WAIT_OBJECTS;
    }

    if (remaining > 0) {
        for (idx = 0; idx < remaining; ++idx) {
            thrArray[idx] = m_threads.at(idx + offset);
        }
        WaitForMultipleObjects(remaining, thrArray, TRUE, INFINITE);
        for (idx = 0; idx < remaining; ++idx) {
            CloseHandle(thrArray[idx]);
        }
    }
    delete[] thrArray;
    CloseHandle(m_port.handle);
}

bool IOCP::registerHandle(PerHandleData * object)
{
    HANDLE handle;

    handle = ::CreateIoCompletionPort(object->m_socket->getHandle(), m_port.handle, reinterpret_cast<ULONG_PTR>(object), 0);
    printf("Registered Handle: %p\n", handle);
    if (handle == NULL) {
        throw WindowsException();
    }
    return (handle == m_port.handle);
}

void IOCP::postQuitMessage() const
{
    if (!::PostQueuedCompletionStatus(m_port.handle, 0, static_cast<ULONG_PTR>(NULL), NULL)) {
        throw WindowsException();
    }
}

HANDLE IOCP::getHandle() const
{
    return m_port.handle;
}

void IOCP::postUserMessage() const
{
    ::PostQueuedCompletionStatus(m_port.handle, 0, static_cast<ULONG_PTR>(NULL), NULL);
}


static DWORD WINAPI WorkerThread(LPVOID lpParameter)
{
    IOCP const * const iocp = reinterpret_cast<IOCP const * const>(lpParameter);
    DWORD numBytesRecv = 0;
    ULONG_PTR CompletionKey;
    PerIoData * iod = NULL;
    PerHandleData * phd = NULL;
    Socket * sock = NULL;
    OVERLAPPED * olap = NULL;
    bool exitLoop = FALSE;
    static WSABUF wsaBuffer;
    DWORD flags = (DWORD)0;
    DWORD error;


    printf("Entering thread with [%p] [%d]...\n", iocp, iocp->getHandle());
    while (!exitLoop) {
        if (::GetQueuedCompletionStatus(iocp->getHandle(), &numBytesRecv, &CompletionKey, (LPOVERLAPPED*)&olap, INFINITE)) {
            if ((numBytesRecv == 0) &&  (CompletionKey == NULL)) {
                iocp->postQuitMessage();    // "Broadcast"
                exitLoop = TRUE;
            } else {
                phd = reinterpret_cast<PerHandleData *>(CompletionKey);
                iod = reinterpret_cast<PerIoData* >(olap);
                printf("\tOPCODE: %d bytes: %d\n", iod->m_opcode, numBytesRecv);
                switch (iod->m_opcode) {
                    case IoType::IO_WRITE:
                        iod->m_bytesRemaining -= numBytesRecv;
                        phd->m_socket->triggerRead(1024);
                        if (iod->m_bytesRemaining == 0) {
                            delete iod;
                        } else {
                            iod->m_wsabuf.buf = iod->m_wsabuf.buf + (iod->m_bytesToXfer - iod->m_bytesRemaining);
                            iod->m_wsabuf.len = iod->m_bytesRemaining;
                            iod->reset();
                        }
                        break;
                    case IoType::IO_READ:
                        printf("IO_READ() numBytes: %d\n", numBytesRecv);
                        break;
                    case IoType::IO_ACCEPT:
                        break;
                }
            }
        } else {
            error = GetLastError();
            if (olap == NULL) {

            } else {
                // Failed I/O operation.
                // The function stores information in the variables pointed to by lpNumberOfBytes, lpCompletionKey.
            }
            //Win_ErrorMsg("IOWorkerThread::GetQueuedCompletionStatus()", error);
        }
    }
    printf("Exiting thread...\n");
    ExitThread(0);
    return 0;
}
