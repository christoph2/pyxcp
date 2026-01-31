
#if !defined(__ETH_UTILS_HPP)
#define __ETH_UTILS_HPP

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iphlpapi.h>
#include <netioapi.h>
#pragma comment(lib, "Ws2_32.lib")
#pragma comment(lib, "iphlpapi.lib")
#elif defined(_LINUX) || defined(__linux__)

#include <memory.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <linux/ethtool.h>
#include <linux/net_tstamp.h>
#include <linux/rtnetlink.h>
#include <linux/sockios.h>
#include <sys/ioctl.h>
#else

#endif

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <cstring>
#include <optional>
#include <string>

struct InterfaceInfo {
#ifdef _WIN32
  std::wstring name;
  std::wstring description;
  NET_IFINDEX index;
#else
  std::string name;
  std::string description;
  unsigned int index;
#endif
};

struct TimestampingInfo {
  bool timestamping_supported;
  bool rx_handware;
  bool tx_hardware;
};

#if defined(_WIN32)

#elif defined(_LINUX) || defined(__linux__)

TimestampingInfo check_timestamping_support(const std::string& ifname) {
    int fd = socket(AF_INET, SOCK_DGRAM, 0);

    if (fd < 0) {
        perror("socket");
        return TimestampingInfo{false, false, false};
    }

    ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, ifname.c_str(), IFNAMSIZ-1);

    ethtool_ts_info info;
    memset(&info, 0, sizeof(info));
    info.cmd = ETHTOOL_GET_TS_INFO;
    ifr.ifr_data = (char *)&info;

    if (ioctl(fd, SIOCETHTOOL, &ifr) < 0) {
        perror("ioctl");
        close(fd);
        return TimestampingInfo{false, false, false};
    }

    close(fd);

	return TimestampingInfo{
		(info.so_timestamping & SOF_TIMESTAMPING_RAW_HARDWARE) == SOF_TIMESTAMPING_RAW_HARDWARE,
		(info.so_timestamping & SOF_TIMESTAMPING_RX_HARDWARE) == SOF_TIMESTAMPING_RX_HARDWARE,
		(info.so_timestamping & SOF_TIMESTAMPING_TX_HARDWARE) == SOF_TIMESTAMPING_TX_HARDWARE
	};
}

#else

TimestampingInfo check_timestamping_support(const std::string& ifname) {
    return TimestampingInfo{false, false, false};
}

#endif

#endif // __ETH_UTILS_HPP
