
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
#include <variant>
#include <vector>
#include <cstring>

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
	result.reserve(bc);

	switch (bc) {
		case 4:
			result.push_back(static_cast<std::uint8_t>(static_cast<std::uint32_t>(((value & 0xff000000UL)) >> 24)));
			[[fallthrough]];
		case 3:
			result.push_back(static_cast<std::uint8_t>(static_cast<std::uint32_t>(((value & 0xff0000UL)) >> 16)));
			[[fallthrough]];
		case 2:
			result.push_back(static_cast<std::uint8_t>(static_cast<std::uint16_t>(((value & 0xff00UL)) >> 8)));
			[[fallthrough]];
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
    // Zero-copy view into Python bytes; lifetime is tied to 'data' which
    // outlives this function call.
    char* buf = nullptr;
    Py_ssize_t len = 0;
    // PyBytes_AsStringAndSize returns 0 on success.
    if (PyBytes_AsStringAndSize(data.ptr(), &buf, &len) != 0 || buf == nullptr || len < 0) {
        // Fallback: empty view on error (should be rare)
        return std::string_view{};
    }
    return std::string_view(buf, static_cast<std::size_t>(len));
}

enum class ChecksumType : std::uint8_t {
    NO_CHECKSUM = 0,
    BYTE_CHECKSUM = 1,
    WORD_CHECKSUM = 2
};

enum class XcpTransportLayerType : std::uint8_t {
    CAN,
    ETH,
    SXI,
    USB
};

struct XcpFramingConfig {
    XcpTransportLayerType transport_layer_type;
    std::uint8_t header_len;
    std::uint8_t header_ctr;
    std::uint8_t header_fill;

    bool tail_fill;
    ChecksumType tail_cs;

};

class XcpFraming {
public:

    XcpFraming(const XcpFramingConfig& framing_type) : m_counter_send(0),
        m_framing_type(framing_type) {

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

		if (m_framing_type.transport_layer_type == XcpTransportLayerType::SXI) {
			if (m_framing_type.tail_fill == true) {
				// Align to a word boundary if word checksum is used
				if (m_framing_type.tail_cs == ChecksumType::WORD_CHECKSUM && (current_send_buffer_pointer() % 2 != 0)) {
					fill_send_buffer(1);
				}
			}

			if (m_framing_type.tail_cs != ChecksumType::NO_CHECKSUM) {
				if (m_framing_type.tail_cs == ChecksumType::BYTE_CHECKSUM) {
					auto cs = checksum_byte(0, current_send_buffer_pointer());
					set_send_buffer(cs);
					frame_tail_size += 1;
				}
				else if (m_framing_type.tail_cs == ChecksumType::WORD_CHECKSUM) {
					// Align to a word boundary before calculating word checksum
					if (current_send_buffer_pointer() % 2 != 0) {
						fill_send_buffer(1);
					}
					auto cs = checksum_word(0, current_send_buffer_pointer());
					auto cs_bytes = serialize_word_le(cs);
					set_send_buffer(cs_bytes);
					frame_tail_size += 2;
				}
			}
		}

		m_counter_send++;
		py::bytes result(reinterpret_cast<const char*>(m_send_buffer), current_send_buffer_pointer());
		return result;
	}

	    FrameType prepare_request(std::uint32_t cmd, const std::vector<std::uint8_t>& data_vec) {
        py::tuple data_tuple(data_vec.size());
        for (size_t i = 0; i < data_vec.size(); ++i) {
            data_tuple[i] = py::int_(data_vec[i]);
        }
        return prepare_request(cmd, data_tuple);
    }

    std::optional<std::tuple<std::uint16_t, std::uint16_t>> unpack_header(const py::bytes& data, std::uint16_t initial_offset=0) const noexcept {
        auto data_view = bytes_as_string_view(data);
        if (std::size(data_view) >= (get_header_size() + initial_offset)) {
            auto offset = initial_offset;
            std::uint16_t length = 0U;
            std::uint16_t counter = 0U;

            // Read length field starting at current offset (if present)
            if (m_framing_type.header_len > 0) {
                if (m_framing_type.header_len == 1) {
                    length = static_cast<std::uint16_t>(static_cast<std::uint8_t>(data_view[offset]));
                } else {
                    auto b0 = static_cast<std::uint8_t>(data_view[offset]);
                    auto b1 = static_cast<std::uint8_t>(data_view[offset + 1]);
                    length = static_cast<std::uint16_t>(static_cast<std::uint16_t>(b0) | (static_cast<std::uint16_t>(b1) << 8));
                }
                offset += m_framing_type.header_len;
            }
            // Read counter field starting after length (if present)
            if (m_framing_type.header_ctr > 0) {
                if (m_framing_type.header_ctr == 1) {
                    counter = static_cast<std::uint16_t>(static_cast<std::uint8_t>(data_view[offset]));
                } else {
                    auto c0 = static_cast<std::uint8_t>(data_view[offset]);
                    auto c1 = static_cast<std::uint8_t>(data_view[offset + 1]);
                    counter = static_cast<std::uint16_t>(static_cast<std::uint16_t>(c0) | (static_cast<std::uint16_t>(c1) << 8));
                }
            }
            return std::make_tuple(length, counter);
        }
        return std::nullopt;
    }

    bool verify_checksum(const py::bytes& data) const noexcept {
        if (m_framing_type.transport_layer_type != XcpTransportLayerType::SXI || m_framing_type.tail_cs == ChecksumType::NO_CHECKSUM) {
            return true; // No checksum verification needed
        }

        auto data_view = bytes_as_string_view(data);
        auto data_size = std::size(data_view);

        if (m_framing_type.tail_cs == ChecksumType::BYTE_CHECKSUM) {
            if (data_size < 1) return false;
            std::uint8_t received_cs = static_cast<std::uint8_t>(data_view[data_size - 1]);
            std::uint8_t calculated_cs = 0;
            for (size_t i = 0; i < data_size - 1; ++i) {
                calculated_cs += static_cast<std::uint8_t>(data_view[i]);
            }
            return received_cs == calculated_cs;
        }
        else if (m_framing_type.tail_cs == ChecksumType::WORD_CHECKSUM) {
            if (data_size < 2 || data_size % 2 != 0) return false; // Must have even length for word checksum

            std::uint16_t received_cs = static_cast<std::uint16_t>(
                static_cast<std::uint8_t>(data_view[data_size - 2]) |
                (static_cast<std::uint16_t>(static_cast<std::uint8_t>(data_view[data_size - 1])) << 8)
            );

            std::uint16_t calculated_cs = 0;
            for (size_t i = 0; i < data_size - 2; i += 2) {
                calculated_cs += static_cast<std::uint16_t>(
                    static_cast<std::uint8_t>(data_view[i]) |
                    (static_cast<std::uint16_t>(static_cast<std::uint8_t>(data_view[i + 1])) << 8)
                );
            }
            return received_cs == calculated_cs;
        }

        return true; // Should not be reached if NO_CHECKSUM is handled
    }

    std::uint16_t get_header_size() const noexcept {
        return m_framing_type.header_len + m_framing_type.header_ctr + m_framing_type.header_fill;
    }

    std::uint16_t get_counter_send() const noexcept {
    	return m_counter_send;
    }

	void set_counter_send(std::uint16_t counter) noexcept {
    	m_counter_send = counter;
    }


private:
	void set_send_buffer(std::uint8_t value) noexcept {
	    m_send_buffer[m_send_buffer_offset] = value;
   	   m_send_buffer_offset++;
	}

	void set_send_buffer(const std::vector<std::uint8_t>& values) noexcept {
		if (!values.empty()) {
			std::memcpy(m_send_buffer + m_send_buffer_offset, values.data(), values.size());
			m_send_buffer_offset += static_cast<std::uint16_t>(values.size());
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

	std::uint16_t checksum_word(std::uint16_t begin, std::uint16_t end) const noexcept {
		std::uint16_t cs = 0UL;

		for (auto idx = begin; idx < end; idx+=2) {
			cs += static_cast<std::uint16_t>(m_send_buffer[idx] | (m_send_buffer[idx + 1] << 8));
		}
		return cs;
	}

private:
    std::uint16_t m_counter_send;
    XcpFramingConfig m_framing_type;
    std::uint8_t * m_send_buffer = nullptr;
    std::uint16_t m_send_buffer_offset = 0UL;
};

#endif // __FRAMING_HPP
