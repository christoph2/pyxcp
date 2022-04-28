#if !defined(__UTILS_HPP)
#define __UTILS_HPP

#if defined(_WIN32)
    #define ZeroOut(p, s)               ::SecureZeroMemory((p), (s))
    #define GET_LAST_SOCKET_ERROR()     WSAGetLastError()
    #define GET_LAST_ERROR()            GetLastError()
#else
    #include <stdlib.h>
    #include <errno.h>
    #include <time.h>

    #define ZeroOut(p, s)               ::memset((p), 0, (s))
    #define CopyMemory(d, s, l)         ::memcpy((d), (s), (l))
    #define GET_LAST_SOCKET_ERROR()     errno
    #define GET_LAST_ERROR()            errno
    void Sleep(unsigned ms);
#endif

#if defined(NDEBUG)
    #define DBG_PRINT(...)
#else
    #define DBG_PRINT(...)              printf(VA_ARGS)
#endif

void SocketErrorExit(const char * method);
void OsErrorExit(const char * method);

#endif // __UTILS_HPP
