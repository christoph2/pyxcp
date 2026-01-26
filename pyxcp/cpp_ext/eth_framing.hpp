#if !defined (__ETH_FRAMING_HPP)
#define __ETH_FRAMING_HPP

#include <cstdint>
#include <functional>
#include <vector>
#include <string_view>
#include <cstring>
#include <algorithm>

class EthReceiver {
public:
    // Handler signature: (payload, length, counter, timestamp)
    using dispatch_t = std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t, uint64_t)>;

    explicit EthReceiver(dispatch_t dispatch_handler)
        : m_dispatch(std::move(dispatch_handler)), m_state(State::Idle), m_expected_len(0), m_counter(0), m_timestamp(0) {
        m_buffer.reserve(4096);
    }

    void feed_bytes(const std::string& data, uint64_t timestamp = 0) {
        feed_frame(std::string_view(data), timestamp);
    }

    void feed_frame(std::string_view data, uint64_t timestamp = 0) {
        const uint8_t* ptr = reinterpret_cast<const uint8_t*>(data.data());
        size_t len = data.size();

        while (len > 0) {
            switch (m_state) {
                case State::Idle:
                case State::UntilHeader: {
                    if (m_buffer.empty()) {
                        m_timestamp = timestamp;
                    }
                    size_t needed = 4 - m_buffer.size();
                    size_t to_copy = (std::min)(len, needed);
                    m_buffer.insert(m_buffer.end(), ptr, ptr + to_copy);
                    ptr += to_copy;
                    len -= to_copy;

                    if (m_buffer.size() == 4) {
                        m_expected_len = m_buffer[0] | (static_cast<uint16_t>(m_buffer[1]) << 8);
                        m_counter = m_buffer[2] | (static_cast<uint16_t>(m_buffer[3]) << 8);
                        m_buffer.clear();
                        if (m_expected_len == 0) {
                            m_state = State::Idle;
                        } else {
                            m_buffer.reserve(m_expected_len);
                            m_state = State::UntilPayload;
                        }
                    } else {
                        m_state = State::UntilHeader;
                    }
                    break;
                }
                case State::UntilPayload: {
                    size_t needed = m_expected_len - m_buffer.size();
                    size_t to_copy = (std::min)(len, needed);
                    m_buffer.insert(m_buffer.end(), ptr, ptr + to_copy);
                    ptr += to_copy;
                    len -= to_copy;

                    if (m_buffer.size() == m_expected_len) {
                        m_dispatch(m_buffer, m_expected_len, m_counter, m_timestamp);
                        m_buffer.clear();
                        m_state = State::Idle;
                    }
                    break;
                }
            }
        }
    }

    void reset() {
        m_buffer.clear();
        m_state = State::Idle;
        m_expected_len = 0;
        m_counter = 0;
    }

private:
    enum class State {
        Idle,
        UntilHeader,
        UntilPayload
    };

    dispatch_t m_dispatch;
    State m_state;
    uint16_t m_expected_len;
    uint16_t m_counter;
    uint64_t m_timestamp;
    std::vector<uint8_t> m_buffer;
};

#endif // __ETH_FRAMING_HPP
