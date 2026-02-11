
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
    std::string name;
    std::string description;
    NET_LUID luid;
#else
    std::string name;
    std::string description;
    unsigned int index;
#endif
};

struct TimestampingInfo {
    std::string interface_name;
    bool timestamping_supported;
    bool rx_handware;
    bool tx_hardware;
};

#if defined(_WIN32)

void init_networking() {
  WSADATA wsa;
  if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
    printf("WSAStartup failed\n");
  }
}

static std::optional<InterfaceInfo> get_best_route(const std::string &ip_str) {
  addrinfo hints, *res = NULL;
  memset(&hints, 0, sizeof(hints));
  hints.ai_family = AF_UNSPEC; // Allow both IPv4 and IPv6
  hints.ai_socktype = SOCK_STREAM;

  if (getaddrinfo(ip_str.c_str(), NULL, &hints, &res) != 0) {
    return std::nullopt;
  }

  MIB_IPFORWARD_ROW2 route;
  SOCKADDR_INET sourceAddr;
  SOCKADDR_INET destAddr;
  memset(&destAddr, 0, sizeof(destAddr));

  if (res->ai_family == AF_INET) {
    destAddr.si_family = AF_INET;
    destAddr.Ipv4 = *(SOCKADDR_IN *)res->ai_addr;
  } else if (res->ai_family == AF_INET6) {
    destAddr.si_family = AF_INET6;
    destAddr.Ipv6 = *(SOCKADDR_IN6 *)res->ai_addr;
  } else {
    freeaddrinfo(res);
    return std::nullopt;
  }
  freeaddrinfo(res);

  DWORD dwRetVal = GetBestRoute2(NULL, 0, NULL, &destAddr, 0, &route, &sourceAddr);
  if (dwRetVal != NO_ERROR) {
    return std::nullopt;
  }

  NET_IFINDEX bestIfIndex = route.InterfaceIndex;
  DWORD dwSize = 0;
  IP_ADAPTER_ADDRESSES *pAddresses = NULL;

  dwRetVal = GetAdaptersAddresses(AF_UNSPEC, GAA_FLAG_INCLUDE_PREFIX, NULL,
                                  pAddresses, &dwSize);
  if (dwRetVal == ERROR_BUFFER_OVERFLOW) {
    pAddresses = (IP_ADAPTER_ADDRESSES *)malloc(dwSize);
    if (!pAddresses) {
      return std::nullopt;
    }
  } else {
    return std::nullopt;
  }

  dwRetVal = GetAdaptersAddresses(AF_UNSPEC, GAA_FLAG_INCLUDE_PREFIX, NULL,
                                  pAddresses, &dwSize);
  if (dwRetVal != NO_ERROR) {
    free(pAddresses);
    return std::nullopt;
  }

  IP_ADAPTER_ADDRESSES *pCurrAddresses = pAddresses;
  while (pCurrAddresses) {
    if (pCurrAddresses->IfIndex == bestIfIndex) {
      InterfaceInfo info;
      std::wstring wstr(pCurrAddresses->FriendlyName);
      info.name = std::string(wstr.begin(), wstr.end());
      wstr = std::wstring(pCurrAddresses->Description);
      // info.description = std::string(wstr.begin(), wstr.end());
      info.luid = pCurrAddresses->Luid;
      free(pAddresses);
      return info;
    }
    pCurrAddresses = pCurrAddresses->Next;
  }

  free(pAddresses);
  return  std::nullopt;
}

bool hw_timestamping_on_ipv4(PINTERFACE_TIMESTAMP_CAPABILITIES caps)
{
  if (((caps->HardwareCapabilities.PtpV2OverUdpIPv4EventMessageReceive) ||
       (caps->HardwareCapabilities.PtpV2OverUdpIPv4AllMessageReceive) ||
       (caps->HardwareCapabilities.AllReceive))
       &&
      ((caps->HardwareCapabilities.PtpV2OverUdpIPv4EventMessageTransmit) ||
       (caps->HardwareCapabilities.PtpV2OverUdpIPv4AllMessageTransmit) ||
       (caps->HardwareCapabilities.TaggedTransmit) ||
       (caps->HardwareCapabilities.AllTransmit)))
  {
    return true;
  }
  return false;
}

bool hw_timestamping_on_ipv6(PINTERFACE_TIMESTAMP_CAPABILITIES caps) {
  if (((caps->HardwareCapabilities.PtpV2OverUdpIPv6EventMessageReceive) ||
       (caps->HardwareCapabilities.PtpV2OverUdpIPv6AllMessageReceive) ||
       (caps->HardwareCapabilities.AllReceive))
       &&
      ((caps->HardwareCapabilities.PtpV2OverUdpIPv6EventMessageTransmit) ||
       (caps->HardwareCapabilities.PtpV2OverUdpIPv6AllMessageTransmit) ||
       (caps->HardwareCapabilities.TaggedTransmit) ||
       (caps->HardwareCapabilities.AllTransmit)))
  {
    return false;
  }
  return false;
}

TimestampingInfo check_timestamping_support(const std::string &host_name) {
    TimestampingInfo result {"", false, false, false};
    INTERFACE_TIMESTAMP_CAPABILITIES caps;
    NET_LUID luid;

    auto host_route = get_best_route(host_name);
    if (!host_route.has_value()) {
        return result;
    }
    auto hvr = *host_route;
    result.interface_name = host_route->name;
    if (GetInterfaceSupportedTimestampCapabilities(&hvr.luid, &caps) == NO_ERROR) {
        result.timestamping_supported = hw_timestamping_on_ipv4(&caps) || hw_timestamping_on_ipv6(&caps);
    } else {

    }
    return result;
}

#elif defined(_LINUX) || defined(__linux__)

void init_networking() {

}

struct best_route_base {
    int oif;
    int table;
    int metric;
	std::string iface_name;
};

struct best_route : public best_route_base {
    in_addr gateway;
    in_addr prefsrc;
};

struct best_route6 : public best_route_base {
    in6_addr gateway;
    in6_addr prefsrc;
};

static void parse_rtattr(rtattr **tb, int max, rtattr *rta, int len)
{
    while (RTA_OK(rta, len)) {
        if (rta->rta_type <= max)
            tb[rta->rta_type] = rta;
        rta = RTA_NEXT(rta, len);
    }
}

std::string iface_name(int if_index) {
	char ifname[IF_NAMESIZE];

	if (if_indextoname(if_index, ifname) != NULL) {
		return ifname;
	}
	return {};
}

static int linux_get_best_route(in_addr dst, best_route *out)
{
    int sock = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    if (sock < 0) {
        return -1;
	}

    struct {
        nlmsghdr nl;
        rtmsg rt;
        char buf[256];
    } req;

    memset(&req, 0, sizeof(req));

    req.nl.nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
    req.nl.nlmsg_type = RTM_GETROUTE;
    req.nl.nlmsg_flags = NLM_F_REQUEST;
    req.nl.nlmsg_seq = 1;

    req.rt.rtm_family = AF_INET;
    req.rt.rtm_table = RT_TABLE_MAIN;

    rtattr *rta = (rtattr *)(((char *)&req) + req.nl.nlmsg_len);
    rta->rta_type = RTA_DST;
    rta->rta_len = RTA_LENGTH(4);
    memcpy(RTA_DATA(rta), &dst, 4);

    req.nl.nlmsg_len += rta->rta_len;

    sockaddr_nl nladdr = { .nl_family = AF_NETLINK };
    if (sendto(sock, &req, req.nl.nlmsg_len, 0,
               (sockaddr *)&nladdr, sizeof(nladdr)) < 0) {
        close(sock);
        return -2;
    }

    char buffer[8192];
    int len = recv(sock, buffer, sizeof(buffer), 0);
    if (len < 0) {
        close(sock);
        return -3;
    }

    nlmsghdr *nlh = (nlmsghdr *)buffer;
    for (; NLMSG_OK(nlh, len); nlh = NLMSG_NEXT(nlh, len)) {

        if (nlh->nlmsg_type == NLMSG_ERROR)
            return -4;

        if (nlh->nlmsg_type == RTM_NEWROUTE) {
            rtmsg *rtm = static_cast<rtmsg*>(NLMSG_DATA(nlh));
            int rtl = RTM_PAYLOAD(nlh);

            rtattr *tb[RTA_MAX+1];
            memset(tb, 0, sizeof(tb));

            parse_rtattr(tb, RTA_MAX, RTM_RTA(rtm), rtl);

            memset(out, 0, sizeof(*out));

            if (tb[RTA_OIF]) {
                out->oif = *(int *)RTA_DATA(tb[RTA_OIF]);
				out->iface_name = iface_name(out->oif);
			}

            if (tb[RTA_GATEWAY]) {
                memcpy(&out->gateway, RTA_DATA(tb[RTA_GATEWAY]), 4);
			}

            if (tb[RTA_PREFSRC]) {
                memcpy(&out->prefsrc, RTA_DATA(tb[RTA_PREFSRC]), 4);
			}

            if (tb[RTA_TABLE]) {
                out->table = *(int *)RTA_DATA(tb[RTA_TABLE]);
			} else {
                out->table = rtm->rtm_table;
			}

            if (tb[RTA_METRICS]) {
                rtattr *metric_tb[RTA_MAX+1];
                memset(metric_tb, 0, sizeof(metric_tb));
                parse_rtattr(metric_tb, RTA_MAX,
                             static_cast<rtattr*>(RTA_DATA(tb[RTA_METRICS])),
                             RTA_PAYLOAD(tb[RTA_METRICS]));

                if (metric_tb[RTA_PRIORITY])
                    out->metric = *(int *)RTA_DATA(metric_tb[RTA_PRIORITY]);
            }

            close(sock);
            return 0;
        }
    }

    close(sock);
    return -5;
}

static int linux_get_best_route6(in6_addr dst, best_route6 *out)
{
    int sock = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    if (sock < 0) {
        return -1;
	}

    struct {
        nlmsghdr nl;
        rtmsg rt;
        char buf[256];
    } req;

    memset(&req, 0, sizeof(req));

    req.nl.nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
    req.nl.nlmsg_type = RTM_GETROUTE;
    req.nl.nlmsg_flags = NLM_F_REQUEST;
    req.nl.nlmsg_seq = 1;

    req.rt.rtm_family = AF_INET6;
    req.rt.rtm_table = RT_TABLE_MAIN;

    rtattr *rta = (rtattr *)(((char *)&req) + req.nl.nlmsg_len);
    rta->rta_type = RTA_DST;
    rta->rta_len = RTA_LENGTH(16);
    memcpy(RTA_DATA(rta), &dst, 16);

    req.nl.nlmsg_len += rta->rta_len;

    sockaddr_nl nladdr = { .nl_family = AF_NETLINK };
    if (sendto(sock, &req, req.nl.nlmsg_len, 0,
               (sockaddr *)&nladdr, sizeof(nladdr)) < 0) {
        close(sock);
        return -2;
    }

    char buffer[8192];
    int len = recv(sock, buffer, sizeof(buffer), 0);
    if (len < 0) {
        close(sock);
        return -3;
    }

    nlmsghdr *nlh = (nlmsghdr *)buffer;
    for (; NLMSG_OK(nlh, len); nlh = NLMSG_NEXT(nlh, len)) {

        if (nlh->nlmsg_type == NLMSG_ERROR) {
            return -4;
		}

        if (nlh->nlmsg_type == RTM_NEWROUTE) {
            rtmsg *rtm = static_cast<rtmsg*>(NLMSG_DATA(nlh));
            int rtl = RTM_PAYLOAD(nlh);

            rtattr *tb[RTA_MAX+1];
            memset(tb, 0, sizeof(tb));

            parse_rtattr(tb, RTA_MAX, RTM_RTA(rtm), rtl);

            memset(out, 0, sizeof(*out));

            if (tb[RTA_OIF]) {
                out->oif = *(int *)RTA_DATA(tb[RTA_OIF]);
			}

            if (tb[RTA_GATEWAY]) {
                memcpy(&out->gateway, RTA_DATA(tb[RTA_GATEWAY]), 16);
			}

            if (tb[RTA_PREFSRC]) {
                memcpy(&out->prefsrc, RTA_DATA(tb[RTA_PREFSRC]), 16);
			}

            if (tb[RTA_TABLE]) {
                out->table = *(int *)RTA_DATA(tb[RTA_TABLE]);
            } else {
                out->table = rtm->rtm_table;
			}

            if (tb[RTA_METRICS]) {
                rtattr *metric_tb[RTA_MAX+1];
                memset(metric_tb, 0, sizeof(metric_tb));
                parse_rtattr(metric_tb, RTA_MAX,
                             static_cast<rtattr*>(RTA_DATA(tb[RTA_METRICS])),
                             RTA_PAYLOAD(tb[RTA_METRICS]));

                if (metric_tb[RTA_PRIORITY]) {
                    out->metric = *(int *)RTA_DATA(metric_tb[RTA_PRIORITY]);
				}
            }

            close(sock);
            return 0;
        }
    }

    close(sock);
    return -5;
}

static std::optional<InterfaceInfo> get_best_route(const std::string &ip_str) {
	InterfaceInfo res{};
	in_addr addr4;
	if (inet_pton(AF_INET, ip_str.c_str(), &addr4) == 1) {
		best_route br4;
		if (linux_get_best_route(addr4, &br4) == 0) {
			res.index = br4.oif;
			res.name = iface_name(br4.oif);
			res.description = iface_name(br4.oif);
			#if 0
			char gw[INET_ADDRSTRLEN] = "0.0.0.0";
			char ps[INET_ADDRSTRLEN] = "0.0.0.0";
			inet_ntop(AF_INET, &br4.gateway, gw, sizeof(gw));
			inet_ntop(AF_INET, &br4.prefsrc, ps, sizeof(ps));
			res.gateway = gw;
			res.prefsrc = ps;
			res.table = br4.table;
			res.metric = br4.metric;
			#endif
		}
	} else {
		in6_addr addr6;
		if (inet_pton(AF_INET6, ip_str.c_str(), &addr6) == 1) {
			best_route6 br6;
			if (linux_get_best_route6(addr6, &br6) == 0) {
				res.index = br6.oif;
				res.name = iface_name(br6.oif);
				res.description = iface_name(br6.oif);
				#if 0
				char gw[INET6_ADDRSTRLEN] = "::";
				char ps[INET6_ADDRSTRLEN] = "::";
				inet_ntop(AF_INET6, &br6.gateway, gw, sizeof(gw));
				inet_ntop(AF_INET6, &br6.prefsrc, ps, sizeof(ps));
				res.gateway = gw;
				res.prefsrc = ps;
				res.table = br6.table;
				res.metric = br6.metric;
				#endif
			}
		}
	}

	return std::nullopt;
}


TimestampingInfo check_timestamping_support(const std::string& host_name) {
    const std::string& ifname{};
    auto host_route = get_best_route(host_name);
    if (!host_route.has_value()) {
        return TimestampingInfo{"", false, false, false};
    }
    auto hvr = *host_route;
    ifname = host_route->name;

    int fd = socket(AF_INET, SOCK_DGRAM, 0);

    if (fd < 0) {
        perror("socket");
        return TimestampingInfo{"", false, false, false};
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
        return TimestampingInfo{"", false, false, false};
    }

    close(fd);

	return TimestampingInfo{
	    host_route->name,
		(info.so_timestamping & SOF_TIMESTAMPING_RAW_HARDWARE) == SOF_TIMESTAMPING_RAW_HARDWARE,
		(info.so_timestamping & SOF_TIMESTAMPING_RX_HARDWARE) == SOF_TIMESTAMPING_RX_HARDWARE,
		(info.so_timestamping & SOF_TIMESTAMPING_TX_HARDWARE) == SOF_TIMESTAMPING_TX_HARDWARE
	};
}

#else

void init_networking() {

}


TimestampingInfo check_timestamping_support(const std::string& host_name) {
    return TimestampingInfo{"", false, false, false};
}

#endif

#endif // __ETH_UTILS_HPP
