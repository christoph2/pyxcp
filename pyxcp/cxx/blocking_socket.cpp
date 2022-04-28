
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
