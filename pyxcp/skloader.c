

#include <windows.h>

#include <stdint.h>
#include <stdio.h>


#define NP_BUFSIZE  (4096)

#define KEY_BUFSIZE (255)

#define ERR_OK                      (0)

#define ERR_COULD_NOT_LOAD_DLL      (16)
#define ERR_COULD_NOT_LOAD_FUNC     (17)

#define GET_KEY                     (0x20)
#define QUIT                        (0x30)

uint8_t buffer[NP_BUFSIZE];
DWORD nRead;
DWORD dwError;

DWORD GetKey(char * const dllName, BYTE privilege, BYTE lenSeed, BYTE * seed, BYTE * lenKey, BYTE * key);

typedef DWORD (*XCP_GetAvailablePrivilegesType)(BYTE * privilege);
typedef DWORD (*XCP_ComputeKeyFromSeedType)(BYTE privilege, BYTE lenSeed, BYTE *seed, BYTE * lenKey, BYTE * key);


XCP_GetAvailablePrivilegesType XCP_GetAvailablePrivileges;
XCP_ComputeKeyFromSeedType XCP_ComputeKeyFromSeed;

const uint8_t seed[10] = {0x61, 0x2b, 0x8d, 0xbb, 0x4d, 0x65, 0xdb, 0x78, 0x49, 0xb5};
uint8_t key[10] = {0};

uint8_t keyBuffer[KEY_BUFSIZE] = {0};
uint8_t seedBuffer[KEY_BUFSIZE] = {0};
char nameBuffer[KEY_BUFSIZE] = {0};
uint8_t keylen = KEY_BUFSIZE;


void hexdump(uint8_t const * const buf, uint16_t len)
{
    for (uint16_t idx = 0; idx < len; ++idx) {
        printf("%02X ", buf[idx]);
    }
    printf("\n");
}

DWORD GetKey(char * const dllName, BYTE privilege, BYTE lenSeed, BYTE * seed, BYTE * lenKey, BYTE * key)
{
    //DWORD err;
    HANDLE hModule = LoadLibrary(dllName);
    XCP_ComputeKeyFromSeedType XCP_ComputeKeyFromSeed;

    printf("hModule: %p\n", hModule);

    printf("seed: ");
    hexdump(seed, lenSeed);

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



int main()
{
    HANDLE hModule = LoadLibrary("SeedNKeyXcp.dll");
    //BYTE priv;
    XCP_GetAvailablePrivileges = (XCP_GetAvailablePrivilegesType)GetProcAddress(hModule, "XCP_GetAvailablePrivileges");
    XCP_ComputeKeyFromSeed = (XCP_ComputeKeyFromSeedType)GetProcAddress(hModule, "XCP_ComputeKeyFromSeed");


    uint8_t cmd, privilege, lenSeed;
    uint16_t nameOffset, nameLen;
    DWORD res;
    DWORD bytesWritten;
    DWORD bytesToWrite;

/*
    printf("XCP_GetAvailablePrivileges: %p\n", XCP_GetAvailablePrivileges);
    (XCP_GetAvailablePrivileges)(&priv);
    printf("privileges: %02X\n", priv);
*/

/*
  res = XCP_ComputeKeyFromSeed(0x01, 10, (BYTE*)&seed, &keylen, (BYTE*)&key);
  printf("err: %ld keylen: %d key: ", res, keylen);
  hexdump(key, keylen);

//  return 1;
*/
    for (;;) {
        HANDLE hPipe = CreateNamedPipe("\\\\.\\pipe\\XcpSendNKey", PIPE_ACCESS_DUPLEX , PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                                   /* PIPE_UNLIMITED_INSTANCES */1, 1024, 1024, NMPWAIT_USE_DEFAULT_WAIT, NULL
                                  );
        if (hPipe != INVALID_HANDLE_VALUE) {
    //        printf("hModule: %p hPipe: %p\n", hModule, hPipe);

            if (ConnectNamedPipe(hPipe, NULL)) {
                //printf("OK, connected.\n");
                if (!ReadFile(hPipe, buffer, NP_BUFSIZE, &nRead, NULL)) {
                    dwError = GetLastError();
                    printf("ReadFile failed with [%ld]\n", dwError);
                } else {
                    printf("Received: ");
                    hexdump(buffer, nRead);
                    cmd = buffer[0];
                    if (cmd == GET_KEY) {
                        keylen = KEY_BUFSIZE;
                        privilege = buffer[1];
                        lenSeed = buffer[2];
                        nameOffset = lenSeed + 3;
                        nameLen = nRead - nameOffset;
                        printf("privilege: %u - seed-len: %u - offs: %u - slen: %u\n", buffer[1], buffer[2], nameOffset, nameLen);
                        CopyMemory(nameBuffer, &buffer[nameOffset], nameLen);
                        nameBuffer[nameLen] = '\x00';
                        CopyMemory(seedBuffer, &buffer[3], lenSeed);
                        ZeroMemory(buffer, NP_BUFSIZE);
                        printf("dllname: ");
                        printf("%s\n", nameBuffer);

                        res = GetKey((char *)&nameBuffer, privilege, lenSeed, (BYTE *)&seedBuffer, &keylen, (BYTE *)&keyBuffer);
                        //res = XCP_ComputeKeyFromSeed(privilege, lenSeed, (BYTE*)&seedBuffer, &keylen, (BYTE*)&keyBuffer);

                        printf("GetKey() returnd: %lu kl: %u\n", res, keylen);  // 1C F8 05 DF 00 00 00 00 00
                        hexdump(keyBuffer, keylen);
                        buffer[0] = LOWORD(LOBYTE(res));
                        buffer[1] = LOWORD(HIBYTE(res));
                        buffer[2] = HIWORD(LOBYTE(res));
                        buffer[3] = HIWORD(HIBYTE(res));

                        if (res == ERR_OK) {
                            //buffer[0] = 0x55;
                            bytesToWrite = 4 + keylen;
                            CopyMemory(buffer + 4, keyBuffer, keylen);
                        } else {
                            bytesToWrite = 4;
                        }
                        if (!WriteFile(hPipe, buffer, bytesToWrite, &bytesWritten, NULL)) {

                        }
                    } else if (cmd == QUIT) {
                        CloseHandle(hPipe);
                        printf("Finished.\n");
                        return 0;
                    }
                }
                //DisconnectNamedPipe(hPipe);
            } else {
                printf("could not connect to NamedPipe. [%ld]\n", GetLastError());

            }
            CloseHandle(hPipe);
        }
    }
    printf("Finished.\n");
}

