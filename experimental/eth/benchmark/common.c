
#include "common.h"

static WSADATA wsa;
SOCKET sock;

static unsigned set_int_option(int sock_, int layer, int option, int value);
static void set_client_options(void);
static void set_server_options(void);

uint16_t get_word(char const * const buf, uint8_t offs)
{
  return ((*(buf + offs)) & 0xff) | ((*(buf + 1 + offs)) << 8);
}

void set_word(char * buf, uint8_t offs, uint16_t value)
{
    (*(buf + offs)) = value & 0xff;
    (*(buf + 1 + offs)) = (value & 0xff00) >> 8;
}

static unsigned set_int_option(int sock_, int layer, int option, int value)
{
    if (setsockopt(sock_, layer, option, (const char*)&value, sizeof(int)) < 0) {
        error("set_int_option()", WSAGetLastError());
        return 0;
    }
    return 1;
}

void hexdump(unsigned char const * buf, uint16_t sz)
{
    uint16_t idx;

    for (idx = 0; idx < sz; ++idx) {
        printf("%02X ", buf[idx]);
    }
    printf("\n");
}

static void set_client_options(void)
{
    set_int_option(sock, SOL_SOCKET, SO_REUSEADDR, 1);
    set_int_option(sock, IPPROTO_TCP, TCP_NODELAY, NO_DELAY);
    set_int_option(sock, SOL_SOCKET, SO_SNDBUF, SOCKET_SNDBUF);
}

static void set_server_options(void)
{
    set_int_option(sock, SOL_SOCKET, SO_REUSEADDR, 1);
    set_int_option(sock, SOL_SOCKET, SO_RCVBUF, SOCKET_RCVBUF);
}

void error(char const * const func, unsigned int code)
{
    printf("%s failed with: %u\n", func, code);
}

void init(AppType app_type)
{
    ADDRINFO hints, *res;

    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        error("init::WSAStartup()", WSAGetLastError());
        exit(EXIT_FAILURE);
    } else {

    }
    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;

    if ((getaddrinfo(HOST, PORT, &hints, &res)) != 0) {
        error("init::getaddrinfo()", WSAGetLastError());
        exit(EXIT_FAILURE);
    }

    sock = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (sock == INVALID_SOCKET) {
        error("init::sockcket()", WSAGetLastError());
        exit(EXIT_FAILURE);
    }

    if (app_type == APP_CLIENT) {
        set_client_options();
        if (connect(sock, res->ai_addr, res->ai_addrlen) == -1) {
            error("init::connect()", WSAGetLastError());
            exit(EXIT_FAILURE);
        }
    } else {
        set_server_options();
        if (bind(sock, res->ai_addr, res->ai_addrlen) == -1) {
            error("init::bind()", WSAGetLastError());
            exit(EXIT_FAILURE);
        }
        if (listen(sock, 1) == -1) {
            error("init::listen()", WSAGetLastError());
            exit(EXIT_FAILURE);
        }
    }

    freeaddrinfo(res);

    srand(23);
}

void cleanup(void)
{
    closesocket(sock);
    WSACleanup();
}

