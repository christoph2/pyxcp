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

#include "blocking_socket.hpp"


void * blockingReceiverThread(void * param)  {
    Socket * const socket = reinterpret_cast<Socket * const>(param);
    std::array<char, 1024> buffer;
    int nbytes;

    printf("Starting thread... [%d]\n", socket->getSocket());

    nbytes = socket->read(buffer, 128);

    printf("[%d] bytes received.\n", nbytes);
    if (nbytes) {
        printf("data: [%s]\n", buffer.data());
    }

    printf("Exiting thread...\n");

    return NULL;
}
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

#include "blocking_socket.hpp"


[[noreturn]] void  blockingReceiverThread(Socket * socket)  {
    //Socket * const socket = reinterpret_cast<Socket * const>(param);
    std::array<char, 1024> buffer;
    int nbytes;

    printf("Starting thread... [%d]\n", socket->getSocket());

    while (true) {
        nbytes = socket->read(buffer, 128);

        printf("[%d] bytes received.\n", nbytes);
        if (nbytes) {
            printf("data: [%s]\n", buffer.data());
        }
    }
    printf("Exiting thread...\n");
}
