

#if !defined(__COMMON_H)
#define __COMMON_H

#include <WinSock2.h>
#include <Ws2tcpip.h>
#include <Mstcpip.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <memory.h>

#include "config.h"

typedef enum tagAppType {
    APP_CLIENT,
    APP_SERVER
} AppType;

extern SOCKET sock;

void error(char const * const func, unsigned int code);
void init(AppType app_type);
void cleanup(void);

uint16_t get_word(char const * const buf, uint8_t offs);
void set_word(char * buf, uint8_t offs, uint16_t value);
void hexdump(unsigned char const * buf, uint16_t sz);

#endif /* __COMMON_H */
