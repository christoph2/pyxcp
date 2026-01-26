#if !defined (__ETH_PTP_HPP)
#define __ETH_PTP_HPP

#include <cstdint>
#include <string>
#include <vector>
#include <optional>
#include <tuple>

#if defined(_WIN32) || defined(_WIN64)
#include <winsock2.h>
#include <ws2tcpip.h>
#include <mstcpip.h>
#include <ntddndis.h>
#include <mswsock.h>
#else
#include <sys/socket.h>
#include <linux/net_tstamp.h>
#include <linux/sockios.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <unistd.h>
#include <cstring>
#endif
#include "helper.hpp"

struct PtpCapabilities {
    bool hw_transmit;
    bool hw_receive;
    bool hw_raw_all;
    bool sw_transmit;
    bool sw_receive;
};

class EthPtp {
public:
    static PtpCapabilities get_capabilities(const std::string& interface_name) {
        PtpCapabilities caps = {false, false, false, false, false};
#if defined(__linux__)
        int sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) return caps;

        struct ethtool_ts_info info;
        struct ifreq ifr;

        memset(&info, 0, sizeof(info));
        info.cmd = ETHTOOL_GET_TS_INFO;
        memset(&ifr, 0, sizeof(ifr));
        strncpy(ifr.ifr_name, interface_name.c_str(), IFNAMSIZ - 1);
        ifr.ifr_data = (char*)&info;

        if (ioctl(sock, SIOCETHTOOL, &ifr) == 0) {
            caps.hw_transmit = (info.so_timestamping & SOF_TIMESTAMPING_TX_HARDWARE);
            caps.hw_receive = (info.so_timestamping & SOF_TIMESTAMPING_RX_HARDWARE);
            caps.hw_raw_all = (info.rx_filters & (1 << HWTSTAMP_FILTER_ALL));
            caps.sw_transmit = (info.so_timestamping & SOF_TIMESTAMPING_TX_SOFTWARE);
            caps.sw_receive = (info.so_timestamping & SOF_TIMESTAMPING_RX_SOFTWARE);
        }
        close(sock);
#elif defined(_WIN32) || defined(_WIN64)
        // On Windows, checking capabilities is more complex via NDIS.
        // For now, we assume if we can enable it, it works, or we use a simplified check.
        // Actually, Windows 10/11 supports it on many modern NICs.
#endif
        return caps;
    }

    static bool enable_timestamping(int socket_fd) {
#if defined(__linux__)
        int flags = SOF_TIMESTAMPING_RX_HARDWARE | 
                    SOF_TIMESTAMPING_RX_SOFTWARE | 
                    SOF_TIMESTAMPING_RAW_HARDWARE | 
                    SOF_TIMESTAMPING_SOFTWARE;
        if (setsockopt(socket_fd, SOL_SOCKET, SO_TIMESTAMPING, &flags, sizeof(flags)) < 0) {
            return false;
        }
        return true;
#elif defined(_WIN32) || defined(_WIN64)
        SOCKET sock = static_cast<SOCKET>(socket_fd);
        TIMESTAMPING_CONFIG config;
        memset(&config, 0, sizeof(config));
        config.Flags = TIMESTAMPING_FLAG_RX; // We primarily care about RX for XCP DAQ

        DWORD bytesReturned = 0;
        if (WSAIoctl(sock, SIO_TIMESTAMPING, &config, sizeof(config), NULL, 0, &bytesReturned, NULL, NULL) == SOCKET_ERROR) {
            return false;
        }
        return true;
#endif
        return false;
    }

    static std::optional<std::tuple<std::vector<uint8_t>, uint64_t>> receive_with_timestamp(int socket_fd, size_t max_size) {
#if defined(_WIN32) || defined(_WIN64)
        SOCKET sock = static_cast<SOCKET>(socket_fd);
        std::vector<uint8_t> buffer(max_size);
        WSABUF wsabuf;
        wsabuf.len = static_cast<ULONG>(max_size);
        wsabuf.buf = reinterpret_cast<char*>(buffer.data());

        char control_buffer[1024];
        WSABUF control_wsabuf;
        control_wsabuf.len = sizeof(control_buffer);
        control_wsabuf.buf = control_buffer;

        WSAMSG msg;
        memset(&msg, 0, sizeof(msg));
        msg.lpBuffers = &wsabuf;
        msg.dwBufferCount = 1;
        msg.Control.len = control_wsabuf.len;
        msg.Control.buf = control_wsabuf.buf;

        DWORD bytesReceived = 0;
        static LPFN_WSARECVMSG lpfnWSARecvMsg = NULL;
        if (lpfnWSARecvMsg == NULL) {
            GUID guidWSARecvMsg = WSAID_WSARECVMSG;
            DWORD bytesReturned = 0;
            WSAIoctl(sock, SIO_GET_EXTENSION_FUNCTION_POINTER, &guidWSARecvMsg, sizeof(guidWSARecvMsg), &lpfnWSARecvMsg, sizeof(lpfnWSARecvMsg), &bytesReturned, NULL, NULL);
        }

        if (lpfnWSARecvMsg && lpfnWSARecvMsg(sock, &msg, &bytesReceived, NULL, NULL) != SOCKET_ERROR) {
            Timestamp ts(TimestampType::ABSOLUTE_TS);
            uint64_t timestamp = ts.get_value();
            for (WSACMSGHDR* cmsg = WSA_CMSG_FIRSTHDR(&msg); cmsg != NULL; cmsg = WSA_CMSG_NXTHDR(&msg, cmsg)) {
                if (cmsg->cmsg_level == SOL_SOCKET && cmsg->cmsg_type == SO_TIMESTAMP) {
                    timestamp = *reinterpret_cast<uint64_t*>(WSA_CMSG_DATA(cmsg));
                    break;
                }
            }
            buffer.resize(bytesReceived);
            return std::make_tuple(std::move(buffer), timestamp);
        }
#endif
        return std::nullopt;
    }
};

#endif // __ETH_PTP_HPP
