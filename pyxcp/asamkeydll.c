

#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>

#if defined(_WIN32)
#include <windows.h>

#define LOAD_LIB(name)  LoadLibrary((name))
#define GET_SYM(module, sym) GetProcAddress((module), (sym))

#else

#define _GNU_SOURCE
#include <dlfcn.h>

typedef uint8_t BYTE;
typedef uint32_t DWORD;
typedef void * HANDLE;

#define LOAD_LIB(name)  dlopen((name), RTLD_LAZY)
#define GET_SYM(module, sym) dlsym((module), (sym))


#endif




#define NP_BUFSIZE  (4096)
#define KEY_BUFSIZE (255)

#define ERR_OK                      (0)

#define ERR_INVALID_CMD_LINE        (2)

#define ERR_COULD_NOT_LOAD_DLL      (16)
#define ERR_COULD_NOT_LOAD_FUNC     (17)


char dllname[NP_BUFSIZE] = {0};

DWORD GetKey(char * const dllName, BYTE privilege, BYTE lenSeed, BYTE * seed, BYTE * lenKey, BYTE * key);
void hexlify(uint8_t const * const buf, uint16_t len);

typedef DWORD (*XCP_GetAvailablePrivilegesType)(BYTE * privilege);
typedef DWORD (*XCP_ComputeKeyFromSeedType)(BYTE privilege, BYTE lenSeed, BYTE *seed, BYTE * lenKey, BYTE * key);


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
    HANDLE hModule = LOAD_LIB(dllName);
    XCP_ComputeKeyFromSeedType XCP_ComputeKeyFromSeed;

    if (hModule != NULL) {
        XCP_ComputeKeyFromSeed = (XCP_ComputeKeyFromSeedType)GET_SYM(hModule, "XCP_ComputeKeyFromSeed");
        //printf("fp: %p\n", XCP_ComputeKeyFromSeed);
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
    if (res == 0) {
        hexlify(keyBuffer, keylen);
    }
}
