
#include <cstdio>

#include "utils.hpp"

#if defined(_WIN32)
    #include <Windows.h>
#else

#endif

void SocketErrorExit(const char * method)
{
    fprintf(stderr, "%s failed with: %d\n", method, GET_LAST_SOCKET_ERROR());
    exit(1);
}

void OsErrorExit(const char * method)
{
    fprintf(stderr, "%s failed with: %d\n", method, GET_LAST_ERROR());
    exit(1);
}

#if !defined(_WIN32)
/*
 *
 * Window-ish Sleep function for Linux.
 *
 */
void Sleep(unsigned ms)
{
    struct timespec value = {0}, rem = {0};

    value.tv_sec = ms / 1000;
    value.tv_nsec = (ms % 1000) * 1000 * 1000;
    nanosleep(&value, &rem);
}
#endif
