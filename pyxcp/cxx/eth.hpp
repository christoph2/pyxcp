#if !defined(__ETH_HPP)
#define __ETH_HPP

#if defined(_WIN32)
    #include <WinSock2.h>
#else
    #include <ctype.h>
    #include <errno.h>
    #include <fcntl.h>
    #include <limits.h>
    #include <signal.h>
    #include <stdlib.h>
    #include <stdio.h>
    #include <string.h>
    #include <time.h>
    #include <stdbool.h>
    #include <unistd.h>
    #include <sys/types.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netdb.h>
    #include <arpa/inet.h>
    #include <sys/wait.h>
#endif

#include "config.h"
#include "utils.hpp"

#include <stdio.h>

#if defined(_WIN32)

struct Eth {

    Eth() {
        WSAData data;
        if (::WSAStartup(MAKEWORD(2, 2), &data) != 0) {
            OsErrorExit("Eth::Eth() -- WSAStartup");
        }
    }

    ~Eth() {
        ::WSACleanup();
    }
};

#else

struct Eth {

    Eth() = default;
    ~Eth() = default;
};

#endif

#endif // __ETH_HPP
