
#include "common.h"

#define MAX(l, r) (((l) > (r)) ? (l) : (r))
#define MIN(l, r) (((l) < (r)) ? (l) : (r))


char NETWORK_MSG[MAX_MSG_LEN] = {0};


void run(void)
{
    unsigned short msg_len = 0;
    unsigned total_length = 0;
    unsigned short counter = 0;

    while (total_length < TOTAL_BYTES) {
        msg_len = (unsigned short)(rand() + MIN_MSG_LEN);
        msg_len = MIN(msg_len, MAX_MSG_LEN);
        set_word(NETWORK_MSG, 0, msg_len);
        set_word(NETWORK_MSG, 2, counter);
        //printf("%04x   ", msg_len);
        //hexdump(NETWORK_MSG, 8);
        if (send(sock, (const void *)NETWORK_MSG, msg_len, 0) == -1) {
            error("run::send()", WSAGetLastError());
            exit(EXIT_FAILURE);
        }
        total_length += msg_len;
        counter ++;
    }
}

int main(void)
{
    init(APP_CLIENT);
    run();
    cleanup();
    return 0;
}

