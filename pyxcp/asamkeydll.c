/*
 * pySART - Simplified AUTOSAR-Toolkit for Python.
 *
 * (C) 2007-2018 by Christoph Schueler <github.com/Christoph2,
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


#include <windows.h>

#include <stdint.h>
#include <string.h>
#include <stdio.h>

// TODO: asamdll


#define NP_BUFSIZE  (4096)
#define KEY_BUFSIZE (255)

#define ERR_OK                      (0)

#define ERR_INVALID_CMD_LINE        (2)

#define ERR_COULD_NOT_LOAD_DLL      (16)
#define ERR_COULD_NOT_LOAD_FUNC     (17)


uint8_t dllname[NP_BUFSIZE] = {0};
DWORD nRead;
DWORD dwError;

DWORD GetKey(char * const dllName, BYTE privilege, BYTE lenSeed, BYTE * seed, BYTE * lenKey, BYTE * key);
void hexlify(uint8_t const * const buf, uint16_t len);

typedef DWORD (*XCP_GetAvailablePrivilegesType)(BYTE * privilege);
typedef DWORD (*XCP_ComputeKeyFromSeedType)(BYTE privilege, BYTE lenSeed, BYTE *seed, BYTE * lenKey, BYTE * key);


XCP_GetAvailablePrivilegesType XCP_GetAvailablePrivileges;
XCP_ComputeKeyFromSeedType XCP_ComputeKeyFromSeed;

//const uint8_t seed[10] = {0x61, 0x2b, 0x8d, 0xbb, 0x4d, 0x65, 0xdb, 0x78, 0x49, 0xb5};
//uint8_t key[10] = {0};

uint8_t keyBuffer[KEY_BUFSIZE] = {0};
uint8_t seedBuffer[KEY_BUFSIZE] = {0};
char nameBuffer[KEY_BUFSIZE] = {0};
uint8_t keylen = KEY_BUFSIZE;
uint8_t seedlen = 0;


void hexlify(uint8_t const * const buf, uint16_t len)
{
    for (uint16_t idx = 0; idx < len; ++idx) {
        printf("%02X", buf[idx]);
    }
}

DWORD GetKey(char * const dllName, BYTE privilege, BYTE lenSeed, BYTE * seed, BYTE * lenKey, BYTE * key)
{
    HANDLE hModule = LoadLibrary(dllName);
    XCP_ComputeKeyFromSeedType XCP_ComputeKeyFromSeed;

    if (hModule != NULL) {
        XCP_ComputeKeyFromSeed = (XCP_ComputeKeyFromSeedType)GetProcAddress(hModule, "XCP_ComputeKeyFromSeed");
        if (XCP_ComputeKeyFromSeed != NULL) {
            return XCP_ComputeKeyFromSeed(privilege, lenSeed, seed, lenKey, key);
        } else {
            return ERR_COULD_NOT_LOAD_FUNC;
        }
    } else {
        return ERR_COULD_NOT_LOAD_DLL;
    }
    return ERR_OK;
}



int main(int argc, char ** argv)
{
    BYTE privilege = 0;
    int idx;
    DWORD res;
    char cbuf[3] = {0};

    for (idx = 1; idx < argc; ++idx) {
        if (idx == 1) {
            strcpy(dllname, argv[idx]);
        } else if (idx == 2) {
            privilege = atoi(argv[idx]);
        } else if (idx == 3) {
            strcpy(nameBuffer, argv[idx]);
        }
    }

    seedlen = strlen(nameBuffer) >> 1;
    for (idx = 0; idx < seedlen; ++idx) {
        cbuf[0] = nameBuffer[idx * 2];
        cbuf[1] = nameBuffer[(idx * 2) + 1 ];
        cbuf[2] = '\x00';
        seedBuffer[idx] = strtol(cbuf, 0, 16);
    }

    res = GetKey((char *)&dllname, privilege, seedlen, (BYTE *)&seedBuffer, &keylen, (BYTE *)&keyBuffer);
    printf("%d\n", res);
    if (res == 0) {
        hexlify(keyBuffer, keylen);
    }
}

