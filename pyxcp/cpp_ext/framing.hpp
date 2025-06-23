
#if !defined(__FRAMING_HPP)
#define __FRAMING_HPP

#include <cstdint>

#include <atomic>
#include <bit>
#include <optional>
#include <iostream>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <thread>
#include <tuple>
#include <vector>

namespace py = pybind11;

using FrameType = py::bytes;
using CommandType = std::variant<std::monostate, std::uint8_t, std::uint16_t, std::uint32_t>;

std::uint8_t find_msb(std::uint32_t val) {
	std::uint8_t position = 0;

	if (val == 0) {
		return 1;
	}
	while ((val >>= 1)) {
		++position;
	}

	return position + 1;
}

std::uint8_t byte_count(std::uint32_t val) {
	std::uint8_t count = 1;

	auto high_bit = find_msb(val);
	if (high_bit > 24) {
		count = 4;
	} else if (high_bit > 16) {
		count = 3;
	} else if (high_bit > 8) {
		count = 2;
	}

	return count;
}

std::vector<std::uint8_t> serialize_cmd_value(std::uint32_t value) {
	std::vector<std::uint8_t> result;

	auto bc = byte_count(value);

	switch (bc) {
		case 4:
			result.push_back(static_cast<std::uint8_t>(static_cast<std::uint32_t>(((value & 0xff000000UL)) >> 24)));
		case 3:
			result.push_back(static_cast<std::uint8_t>(static_cast<std::uint32_t>(((value & 0xff0000UL)) >> 16)));
		case 2:
			result.push_back(static_cast<std::uint8_t>(static_cast<std::uint16_t>(((value & 0xff00UL)) >> 8)));
		case 1:
			result.push_back(static_cast<std::uint8_t>(value & 0xffUL));
			break;
	}

	return result;
}

std::vector<std::uint8_t> serialize_word_le(std::uint16_t value) {
	std::vector<std::uint8_t> result;
	result.reserve(2);

	result.push_back(static_cast<std::uint8_t>(value & 0xffUL));
	result.push_back(static_cast<std::uint8_t>(static_cast<std::uint16_t>(((value & 0xff00UL)) >> 8)));
	result.resize(2);
	return result;
}

std::string_view bytes_as_string_view(const py::bytes& data) {
    return std::string_view{data};
}

enum class XcpTransportLayerType : std::uint8_t {
	CAN,
	ETH,
	SXI,
	USB
};

struct XcpFramingConfig {
	std::uint8_t header_len;
	std::uint8_t header_ctr;
	std::uint8_t header_fill;

	bool tail_fill;
	std::uint8_t tail_cs;

};

class XcpFraming {
public:

    XcpFraming(/* XcpTransportLayerType transport_layer_type, */const XcpFramingConfig& framing_type) : m_counter_send(0),
        /* m_transport_layer_type(transport_layer_type), */ m_framing_type(framing_type) {

        m_send_buffer = new std::uint8_t[0xff + 8];
		reset_send_buffer_pointer();
    }

    XcpFraming() = delete;
    XcpFraming(const XcpFraming&) = delete;
    XcpFraming(XcpFraming&&) = delete;

	FrameType prepare_request(std::uint32_t cmd, py::args data) {

		std::vector<std::uint8_t> command_bytes{};
		std::uint8_t frame_header_size{0};
		std::uint8_t frame_tail_size{0};

		reset_send_buffer_pointer();

		command_bytes = serialize_cmd_value(cmd);

		auto xcp_packet_size = data.size() + command_bytes.size();

		if (m_framing_type.header_len > 0) {
			frame_header_size += m_framing_type.header_len;
			if (m_framing_type.header_len == 1) {
				set_send_buffer(static_cast<std::uint8_t>(xcp_packet_size & 0xff));
			} else {
				auto packet_size_bytes = serialize_word_le(xcp_packet_size);
				set_send_buffer(packet_size_bytes);
			}
		}
		if (m_framing_type.header_ctr > 0) {
			frame_header_size += m_framing_type.header_ctr;
			if (m_framing_type.header_ctr == 1) {
				set_send_buffer(static_cast<std::uint8_t>(m_counter_send & 0xff));
			} else {
				auto counter_bytes = serialize_word_le(m_counter_send);
				set_send_buffer(counter_bytes);
			}
		}
		if (m_framing_type.header_fill > 0) {
			fill_send_buffer(m_framing_type.header_fill);
			frame_header_size += m_framing_type.header_fill;
		}

		set_send_buffer(command_bytes);
		set_send_buffer(data);

		if (m_framing_type.tail_fill == true) {	// TODO: fix-me!!!
			frame_tail_size += m_framing_type.tail_fill;
		}
		if (m_framing_type.tail_cs > 0) {
			frame_tail_size += m_framing_type.tail_cs;
		}

		m_counter_send++;
		py::bytes result(reinterpret_cast<const char*>(m_send_buffer), current_send_buffer_pointer());
		return result;
	}

    std::optional<std::tuple<std::uint16_t, std::uint16_t>> unpack_header(const py::bytes& data, std::uint16_t initial_offset=0) const noexcept {
        auto data_view = bytes_as_string_view(data);
        if (std::size(data_view) >= (get_header_size() + initial_offset)) {
            auto offset = initial_offset;
            auto length = 0U;
            auto counter = 0U;

            if (m_framing_type.header_len > 0) {
                offset += m_framing_type.header_len;
                if (m_framing_type.header_len == 1) {
                    length = static_cast<std::uint16_t>(data_view[0]);
                } else {
                    length = static_cast<std::uint16_t>(data_view[0] | (data_view[1] << 8));
                }
            }
            if (m_framing_type.header_ctr > 0) {
                if (m_framing_type.header_ctr == 1) {
                    counter = static_cast<std::uint16_t>(data_view[offset]);
                } else {
                    counter = static_cast<std::uint16_t>(data_view[offset] | (data_view[offset + 1] << 8));
                }
		    }
		    return std::make_tuple(length, counter);
        }
        return std::nullopt;
    }

    std::uint16_t get_header_size() const noexcept {
        return m_framing_type.header_len + m_framing_type.header_ctr + m_framing_type.header_fill;
    }

    std::uint16_t get_counter_send() const noexcept {
    	return m_counter_send;
    }

private:
	void set_send_buffer(std::uint8_t value) noexcept {
	    m_send_buffer[m_send_buffer_offset] = value;
   	   m_send_buffer_offset++;
	}

	void set_send_buffer(const std::vector<std::uint8_t>& values) noexcept {
		for (auto idx=0; idx < values.size(); ++idx) {
			m_send_buffer[m_send_buffer_offset] = values[idx];
			m_send_buffer_offset++;
		}
	}

	void set_send_buffer(const py::args& values) noexcept {
		for (auto idx=0; idx < values.size(); ++idx) {
			m_send_buffer[m_send_buffer_offset] = values[idx].cast<std::uint8_t>();
			m_send_buffer_offset++;
		}
	}

	void fill_send_buffer(uint16_t n) noexcept {
		for (auto idx=0; idx < n; ++idx) {
			m_send_buffer[m_send_buffer_offset] = 0;
			m_send_buffer_offset++;
		}
	}

	void reset_send_buffer_pointer() noexcept {
		m_send_buffer_offset = 0UL;
	}

	std::uint16_t current_send_buffer_pointer() const noexcept {
		return m_send_buffer_offset;
	}

	std::uint8_t checksum_byte(std::uint16_t begin, std::uint16_t end) const noexcept {
		uint8_t cs = 0;
		for (auto idx = begin; idx < end; ++idx) {
			cs += m_send_buffer[idx];
		}
		return cs;
	}

	std::uint16_t checksum_word(std::uint16_t begin, std::uint16_t end, bool little_endian=true) const noexcept {
		std::uint16_t cs = 0UL;
		std::uint16_t offs0 = 0UL;
		std::uint16_t offs1 = 0UL;

		if (little_endian) {
			offs0 = 1;
		} else {
			offs1 = 1;
		}
		for (auto idx = begin; idx < end; idx+=2) {
			cs += static_cast<std::uint16_t>((m_send_buffer[idx + offs0] << 8) | m_send_buffer[idx + offs1]);;
		}
		return cs;
	}

private:
    std::uint16_t m_counter_send;
    // XcpTransportLayerType m_transport_layer_type;
    XcpFramingConfig m_framing_type;
    std::uint8_t * m_send_buffer = nullptr;
    std::uint16_t m_send_buffer_offset = 0UL;
};

#endif // __FRAMING_HPP
