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

#include "epoll.hpp"

constexpr size_t MAX_EVENTS = 8;

static struct epoll_event events[MAX_EVENTS];

void * WorkerThread(void * param)
{
    Epoll const * const epoll = reinterpret_cast<Epoll const * const>(param);
    Socket const * socket;
    TimeoutTimer const * timeout_timer;
    EventRecord * event_record;
    int nfds;
    int idx;
    char buffer[128];
    int evt_mask;
    uint64_t timeout_value; 

    printf("Entering worker thread...\n");

    for (;;) {
        nfds = epoll_wait(epoll->getHandle() ,events, MAX_EVENTS, 500);
        for (idx = 0; idx < nfds; ++idx) {
            evt_mask = events[idx].events;
            event_record = reinterpret_cast<EventRecord*>(events[idx].data.ptr);
            printf("Evt#%d: %x %d\n", idx, evt_mask, event_record->event_type);
            if (event_record->event_type == EventType::SOCKET) {
                socket = event_record->obj.socket;
                printf("Socket-Handle: %d\n", socket->getHandle());
                if (evt_mask & EPOLLIN) {
                    read(socket->getHandle(), buffer, 128);
                    printf("R: %s\n", buffer);
                } else if (evt_mask & EPOLLHUP) {
                    printf("HANG-UP\n");
                    //SocketErrorExit("HANG-UP");
                } else if (evt_mask & EPOLLERR) {
                    SocketErrorExit("WorkerThread::epoll_wait()");
                }
            } else if (event_record->event_type == EventType::TIMEOUT) {
                timeout_timer = event_record->obj.timeout_timer;
                printf("Timeout-Handle: %d\n", timeout_timer->getHandle());
                read(timeout_timer->getHandle(), &timeout_value, sizeof(uint64_t));
                printf("Timeout\n");
            } else {
                printf("Invalid event type.\n");
            }
        }
    }

    return nullptr;
}

