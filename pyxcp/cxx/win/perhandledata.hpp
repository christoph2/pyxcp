#if !defined(__PERHANDLEDATA_HPP)
#define __PERHANDLEDATA_HPP

#include <Windows.h>

enum class HandleType {
    HANDLE_SOCKET,
    HANDLE_FILE,
    HANDLE_NAMED_PIPE,
    HANDLE_USER,
};


struct PerHandleData {
    HandleType m_handleType;
    HANDLE m_handle;
    DWORD m_seqNoSend;
    DWORD m_seqNoRecv;

    PerHandleData(HandleType handleType, const HANDLE& handle) : m_handleType(handleType), m_handle(handle), m_seqNoSend(0), m_seqNoRecv(0) {}
};


#endif // __PERHANDLEDATA_HPP
