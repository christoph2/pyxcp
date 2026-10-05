

#if !defined(__ETH_CONFIG_HPP)
#define __ETH_CONFIG_HPP

#include <optional>
#include <string>
#include <tuple>
#include <cstdint>

enum class EthProtocol : std::uint8_t {
    UDP,
    TCP
};

struct EthConfig {
	std::string m_host{""};
	std::uint16_t m_port{0};
	EthProtocol m_protocol{EthProtocol::UDP};
	bool m_ipv6{false};
	bool m_use_tcp_no_delay{false};
	bool m_multicast_enabled{false};
	bool m_ptp_timestamping{false};
	std::optional<std::tuple<std::string, std::uint16_t>> m_bind_to{std::nullopt};
	std::optional<std::uint16_t> m_iocp_buffer_size{std::nullopt};
	std::optional<std::uint16_t> m_iocp_receive_queue_depth{std::nullopt};

	bool use_tcp() const noexcept {
        return m_protocol == EthProtocol::TCP;
    }
};

#endif  // __ETH_CONFIG_HPP
