#include "common.h"
#include <stdbool.h>
#include <stdint.h>
#include <time.h>


char NETWORK_MSG[MAX_MSG_LEN];

void run(void)
{
    struct sockaddr_storage peer_addr;
    socklen_t addr_size;
    int new_fd;
    bool finished = false;
    bool received = false;
    unsigned int offset = 0;
    int total_length = 0;
    unsigned long msg_length = 0;
    int nbytes;
    uint8_t state = 0;
    uint16_t bytes_to_read = 0;
    clock_t start;
    float elapsed_time;

    addr_size = sizeof(peer_addr);
    new_fd = accept(sock, (struct sockaddr *)&peer_addr, &addr_size);
    if (new_fd == -1) {
        error("run::accept()", WSAGetLastError());
        exit(EXIT_FAILURE);
    }
    start = clock();
    while (!finished) {
        offset = 0;
        msg_length = 0;
        state = 0;
        received = false;
        bytes_to_read = 2;
        while (!received) {
            nbytes = recv(new_fd, (void*)(NETWORK_MSG + offset), bytes_to_read, 0);
            if (nbytes == -1) {
                error("run::recv()", WSAGetLastError());
                exit(EXIT_FAILURE);
            } else if (nbytes == 0) {
                finished = true;
                break;
            } else {
                offset += nbytes;
                if ((offset >= 2) && (state == 0)) {
                    msg_length = get_word(NETWORK_MSG, 0);
                    state = 1;
                    if (msg_length == 0) {
                        exit(1);
                    }
                    bytes_to_read = msg_length - 2;
                } else {
                    if (offset == msg_length) {
                        received = true;
                    } else {
                        bytes_to_read = msg_length - offset;
                    }
                }
            }
        }
        //hexdump(NETWORK_MSG, 8);
        total_length += offset;
        if (total_length >= TOTAL_BYTES) {
            finished = true;
            break;
        }
    }
    elapsed_time = (float)((clock() - start) /  CLOCKS_PER_SEC);
    printf("Elapsed time: %.2f - throughput: %.2f MB/s\n", elapsed_time, (total_length / elapsed_time) / (float)(1024 * 1024));
}

int main(void)
{
    init(APP_SERVER);
    run();
    cleanup();
    return 0;
}

