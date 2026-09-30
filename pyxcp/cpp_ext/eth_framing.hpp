#ifndef ETH_FRAMING_HPP
#define ETH_FRAMING_HPP

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <span>
#include <string_view>
#include <utility>
#include <vector>

enum class FramingError : std::uint8_t {
    TruncatedHeader,
    TruncatedPayload,
    PayloadTooLarge
};

enum class EthProtocol : std::uint8_t {
    UDP,
    TCP
};

class EthReceiver {
   public:

    using byte      = std::uint8_t;
    using payload_t = std::span<const byte>;

    using dispatch_t = std::function<void(payload_t payload, std::uint16_t counter, std::uint64_t timestamp)>;
    using error_handler_t = std::function<void(FramingError error, std::size_t offset)>;

    static constexpr std::size_t header_size = 4;

    explicit EthReceiver(EthProtocol proto, dispatch_t dispatch, error_handler_t error_handler = {}, std::size_t max_payload_size = 0xFFFF) :
        m_proto(proto), m_dispatch(std::move(dispatch)), m_error_handler(std::move(error_handler)), m_max_payload_size(max_payload_size) {
        m_buffer.reserve(4096);
    }

    void feed_frame(std::span<const byte> frame, std::uint64_t timestamp = 0) {
        if (m_proto == EthProtocol::TCP) {
            feed_stream(frame, timestamp);
        } else {
            feed_datagram(frame, timestamp);
        }
    }

    void feed_frame(std::string_view frame, std::uint64_t timestamp = 0) {
        feed_frame(as_bytes(frame), timestamp);
    }

    // -----------------------------------------------------------------

    void reset_stream() noexcept {
        m_state        = State::Header;
        m_header_used  = 0;
        m_expected_len = 0;
        m_counter      = 0;
        m_timestamp    = 0;
        m_buffer.clear();
    }

   private:

    void feed_stream(std::span<const byte> data, std::uint64_t timestamp = 0) {
        while (!data.empty()) {
            switch (m_state) {
                case State::Header:
                    consume_stream_header(data, timestamp);
                    break;
                case State::Payload:
                    consume_stream_payload(data);
                    break;
            }
        }
    }

    void feed_stream(std::string_view data, std::uint64_t timestamp = 0) {
        feed_stream(as_bytes(data), timestamp);
    }

    void feed_datagram(std::span<const byte> datagram, std::uint64_t timestamp = 0) {
        std::size_t offset = 0;
        while (!datagram.empty()) {
            if (datagram.size() < header_size) {
                report_error(FramingError::TruncatedHeader, offset);
                return;
            }
            const auto length  = load_le16(datagram.data());
            const auto counter = load_le16(datagram.data() + 2);
            datagram           = datagram.subspan(header_size);
            offset += header_size;
            if (length > m_max_payload_size) {
                report_error(FramingError::PayloadTooLarge, offset);
                return;
            }
            if (datagram.size() < length) {
                report_error(FramingError::TruncatedPayload, offset);
                return;
            }

            const auto payload = datagram.first(static_cast<std::size_t>(length));
            dispatch(payload, counter, timestamp);
            datagram = datagram.subspan(static_cast<std::size_t>(length));
            offset += length;
        }
    }

    void feed_datagram(std::string_view datagram, std::uint64_t timestamp = 0) {
        feed_datagram(as_bytes(datagram), timestamp);
    }

    enum class State {
        Header,
        Payload
    };

    // ================================================================
    // Common
    // ================================================================

    static std::uint16_t load_le16(const byte* ptr) noexcept {
        return static_cast<std::uint16_t>(ptr[0]) | (static_cast<std::uint16_t>(ptr[1]) << 8);
    }

    static std::span<const byte> as_bytes(std::string_view data) noexcept {
        return { reinterpret_cast<const byte*>(data.data()), data.size() };
    }

    void dispatch(payload_t payload, std::uint16_t counter, std::uint64_t timestamp) {
        if (m_dispatch) {
            m_dispatch(payload, counter, timestamp);
        }
    }

    void report_error(FramingError error, std::size_t offset) {
        if (m_error_handler) {
            m_error_handler(error, offset);
        }
    }

    void consume_stream_header(std::span<const byte>& input, std::uint64_t timestamp) {
        if (m_header_used == 0 && input.size() >= header_size) {
            m_timestamp    = timestamp;
            m_expected_len = load_le16(input.data());
            m_counter      = load_le16(input.data() + 2);
            input          = input.subspan(header_size);
            begin_payload();
            return;
        }
        if (m_header_used == 0) {
            m_timestamp = timestamp;
        }
        const std::size_t needed = header_size - m_header_used;
        const std::size_t count  = (std::min)(needed, input.size());
        std::copy_n(input.data(), count, m_header.data() + m_header_used);
        m_header_used += count;
        input = input.subspan(count);
        if (m_header_used != header_size) {
            return;
        }
        m_expected_len = load_le16(m_header.data());
        m_counter      = load_le16(m_header.data() + 2);
        m_header_used  = 0;
        begin_payload();
    }

    void begin_payload() {
        if (m_expected_len > m_max_payload_size) {
            report_error(FramingError::PayloadTooLarge, 0);
            reset_stream();
            return;
        }
        if (m_expected_len == 0) {
            dispatch({}, m_counter, m_timestamp);
            m_state = State::Header;
            return;
        }
        m_buffer.clear();
        m_state = State::Payload;
    }

    void consume_stream_payload(std::span<const byte>& input) {
        const std::size_t payload_length = static_cast<std::size_t>(m_expected_len);

        if (m_buffer.empty() && input.size() >= payload_length) {
            const auto payload = input.first(payload_length);

            input = input.subspan(payload_length);

            dispatch(payload, m_counter, m_timestamp);

            finish_stream_packet();
            return;
        }
        const std::size_t needed = payload_length - m_buffer.size();
        const std::size_t count = (std::min)(needed, input.size());

        m_buffer.insert(m_buffer.end(), input.begin(), input.begin() + static_cast<std::ptrdiff_t>(count));
        input = input.subspan(count);
        if (m_buffer.size() != payload_length) {
            return;
        }
        dispatch(m_buffer, m_counter, m_timestamp);
        finish_stream_packet();
    }

    void finish_stream_packet() noexcept {
        m_buffer.clear();
        m_expected_len = 0;
        m_counter      = 0;
        m_state        = State::Header;
    }

   private:

    dispatch_t      m_dispatch;
    error_handler_t m_error_handler;
    std::size_t m_max_payload_size;

    // TCP stream state
    State m_state{ State::Header };

    std::array<byte, header_size> m_header{};
    std::size_t                   m_header_used{ 0 };

    std::uint16_t m_expected_len{ 0 };
    std::uint16_t m_counter{ 0 };
    std::uint64_t m_timestamp{ 0 };

    std::vector<byte> m_buffer;
    EthProtocol m_proto;
};

#endif  // ETH_FRAMING_HPP
