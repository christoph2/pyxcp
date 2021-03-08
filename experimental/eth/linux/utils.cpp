
#include "utils.hpp"

/*
 *
 * Window-ish Sleep function.
 *
 */
void Sleep(unsigned ms)
{
    struct timespec value = {0}, rem = {0};

    value.tv_sec = ms / 1000;
    value.tv_nsec = (ms % 1000) * 1000 * 1000;
    nanosleep(&value, &rem);
}

