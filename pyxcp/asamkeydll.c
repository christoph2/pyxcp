

#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>

#if defined(_WIN32)
#include <windows.h>

#define LOAD_LIB(name)  LoadLibrary((name))
#define GET_SYM(module, sym) GetProcAddress((module), (sym))

struct TRange {
    char *pMem;
    unsigned long lLen;
};

typedef int (__cdecl *CalcChecksumType)(struct TRange *ptr, int nRanges, uint8_t *pnChecksum, int *pnSignificant, uint16_t nFlags);

#else

#define _GNU_SOURCE
#include <dlfcn.h>

typedef uint8_t BYTE;
typedef uint32_t DWORD;
typedef void * HANDLE;
typedef uint16_t WORD;

#define LOAD_LIB(name)  dlopen((name), RTLD_LAZY)
#define GET_SYM(module, sym) dlsym((module), (sym))

struct TRange {
    char *pMem;
    unsigned long lLen;
};

typedef int (*CalcChecksumType)(struct TRange *ptr, int nRanges, uint8_t *pnChecksum, int *pnSignificant, uint16_t nFlags);

#endif

#define NP_BUFSIZE  (4096)
#define KEY_BUFSIZE (255)

#define ERR_OK                      (0)

#define ERR_INVALID_CMD_LINE        (2)

#define ERR_COULD_NOT_LOAD_DLL      (16)
#define ERR_COULD_NOT_LOAD_FUNC     (17)


char dllname[NP_BUFSIZE] = {0};

DWORD GetKey(char * const dllName, BYTE privilege, BYTE lenSeed, BYTE * seed, BYTE * lenKey, BYTE * key);
DWORD DoChecksum(char * const dllName, uint8_t * data, uint32_t len, uint8_t * checksum, int * significant);
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

DWORD DoChecksum(char * const dllName, uint8_t * data, uint32_t len, uint8_t * checksum, int * significant)
{
    HANDLE hModule = LOAD_LIB(dllName);
    CalcChecksumType CalcChecksum;

    if (hModule != NULL) {
        CalcChecksum = (CalcChecksumType)GET_SYM(hModule, "CalcChecksum");
        if (CalcChecksum != NULL) {
            struct TRange range;
            range.pMem = (char *)data;
            range.lLen = (unsigned long)len;
            return CalcChecksum(&range, 1, checksum, significant, 0);
        } else {
            return ERR_COULD_NOT_LOAD_FUNC;
        }
    } else {
        return ERR_COULD_NOT_LOAD_DLL;
    }
}



int main(int argc, char ** argv)
{
    BYTE privilege = 0;
    int idx;
    DWORD res;
    char cbuf[3] = {0};
    int is_checksum = 0;
    char *data_hex = NULL;
    int start_idx = 1;

    if (argc > 1 && strcmp(argv[1], "--checksum") == 0) {
        is_checksum = 1;
        start_idx = 2;
    }

    for (idx = start_idx; idx < argc; ++idx) {
        if (idx == start_idx) {
            strcpy(dllname, argv[idx]);
        } else if (idx == start_idx + 1) {
            if (is_checksum) {
                data_hex = argv[idx];
            } else {
                privilege = atoi(argv[idx]);
            }
        } else if (idx == start_idx + 2) {
            data_hex = argv[idx];
        }
    }

    if (data_hex) {
        seedlen = strlen(data_hex) >> 1;
        for (idx = 0; idx < seedlen; ++idx) {
            cbuf[0] = data_hex[idx * 2];
            cbuf[1] = data_hex[(idx * 2) + 1 ];
            cbuf[2] = '\x00';
            seedBuffer[idx] = (uint8_t)strtol(cbuf, 0, 16);
        }
    }

    if (is_checksum) {
        int significant = 0;
        res = DoChecksum((char *)&dllname, seedBuffer, seedlen, keyBuffer, &significant);
        printf("%u\n", res);
        if (res != 0xFFFF) { // Assuming CalcChecksum returns something other than error codes on success
            hexlify(keyBuffer, (uint16_t)significant);
            printf("\n");
        }
    } else {
        res = GetKey((char *)&dllname, privilege, seedlen, (BYTE *)&seedBuffer, &keylen, (BYTE *)&keyBuffer);
        printf("%u\n", res);
        if (res == 0) {
            hexlify(keyBuffer, keylen);
            printf("\n");
        }
    }
    return 0;
}
