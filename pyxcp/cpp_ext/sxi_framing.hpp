#if !defined (__SXI_FRAMING_HPP)
#define __SXI_FRAMING_HPP

#include <array>
#include <bit>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>
#include <iomanip>
#include <iostream>

// Header format options
enum class SxiHeaderFormat {
    LenByte,
    LenCtrByte,
    LenFillByte,
    LenWord,
    LenCtrWord,
    LenFillWord,
};

// Checksum type options
enum class SxiChecksumType {
    None,
    Sum8,
    Sum16
};

namespace detail {
inline uint16_t make_word_le(const uint8_t* p) {
    return p[0] | p[1] << 8;
}

inline void put_word_le(uint8_t* p, uint16_t v) {
    if constexpr (std::endian::native == std::endian::big) {
        p[0] = static_cast<uint8_t>(v & 0xFF);
        p[1] = static_cast<uint8_t>((v >> 8) & 0xFF);
    } else {
        std::memcpy(p, &v, sizeof(v));
    }
}
}  // namespace detail

class RestartableTimer {
   public:

    /**
     * @brief Constructs the timer.
     * @param timeout The duration after which the timer expires.
     * @param on_timeout The function to call upon timeout.
     */
    RestartableTimer(std::chrono::milliseconds timeout, std::function<void()> on_timeout) :
        m_timeout(timeout), m_on_timeout(std::move(on_timeout)), m_running(false) {
    }

    ~RestartableTimer() {
        stop();
        if (m_thread.joinable()) {
            m_thread.join();
        }
    }

    // Disable copy and move semantics
    RestartableTimer(const RestartableTimer&)            = delete;
    RestartableTimer& operator=(const RestartableTimer&) = delete;
    RestartableTimer(RestartableTimer&&)                 = delete;
    RestartableTimer& operator=(RestartableTimer&&)      = delete;

    /**
     * @brief Starts the timer. If already running, it resets the countdown.
     */
    void start() {
        if (m_timeout == std::chrono::milliseconds(0)) {
            return;
        }
        std::unique_lock<std::mutex> lock(m_mutex);
        if (!m_running) {
            m_running = true;
            if (m_thread.joinable()) {
                m_thread.join();  // Ensure previous thread is finished
            }
            m_thread = std::thread(&RestartableTimer::run, this);
        } else {
            // Already running, just signal a reset
            m_cv.notify_one();
        }
    }

    /**
     * @brief Stops the timer.
     */
    void stop() {
        if (m_timeout == std::chrono::milliseconds(0)) {
            return;
        }
        std::unique_lock<std::mutex> lock(m_mutex);
        if (!m_running) {
            return;
        }
        m_running = false;
        m_cv.notify_one();
    }

    /**
     * @brief Resets the timer's countdown.
     */
    void reset_timeout() {
        if (m_timeout == std::chrono::milliseconds(0)) {
            return;
        }
        std::unique_lock<std::mutex> lock(m_mutex);
        if (m_running) {
            m_cv.notify_one();
        }
    }

   private:

    void run() {
        std::unique_lock<std::mutex> lock(m_mutex);
        while (m_running) {
            // wait_for returns cv_status::timeout if the time expires without a notification
            if (m_cv.wait_for(lock, m_timeout) == std::cv_status::timeout) {
                // Timeout occurred. Check m_running again in case stop() was called
                // while we were waiting for the lock.
                if (m_running) {
                    m_on_timeout();
                    m_running = false;  // Stop the timer thread after firing
                }
            }
        }
    }

    std::thread               m_thread;
    std::mutex                m_mutex;
    std::condition_variable   m_cv;
    std::chrono::milliseconds m_timeout;
    std::function<void()>     m_on_timeout;
    std::atomic<bool>         m_running;
};


template<SxiHeaderFormat Format, SxiChecksumType Checksum>
class SxiReceiver {
   public:

    explicit SxiReceiver(
        std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)> dispatch_handler,
        std::chrono::milliseconds /*timeout*/ = std::chrono::milliseconds(0)
    ) :
        dispatch_(std::move(dispatch_handler)) {
        reset();
    }

    void feed_bytes(const std::string& data) {
        for (const auto& c : data) {
            //feed(static_cast<uint8_t>(c));
            feed(c);
        }
    }

    void feed(uint8_t octet) {
        if (index_ >= buffer_.size()) {
            reset();
            return;
        }
        buffer_[index_] = octet;
        if (state_ == State::Idle) {
            state_ = State::UntilLength;
            fill_ = 0;
        }
        if (state_ == State::UntilLength) {
            bool header_complete = false;
            if constexpr (Format == SxiHeaderFormat::LenByte) {
                if (index_ == 0) {
                    dlc_            = buffer_[0];
                    remaining_      = dlc_;
                    header_complete = true;
                }
            } else if constexpr (Format == SxiHeaderFormat::LenCtrByte || Format == SxiHeaderFormat::LenFillByte) {
                if (index_ == 1) {
                    dlc_            = buffer_[0];
                    if constexpr (Format == SxiHeaderFormat::LenCtrByte) {
                        ctr_ = buffer_[1];
                    }
                    remaining_      = dlc_;
                    header_complete = true;
                }
            } else if constexpr (Format == SxiHeaderFormat::LenWord) {
                if (index_ == 1) {
                    dlc_            = detail::make_word_le(&buffer_[0]);
                    remaining_      = dlc_;
                    header_complete = true;
                }
            } else if constexpr (Format == SxiHeaderFormat::LenCtrWord || Format == SxiHeaderFormat::LenFillWord) {
                if (index_ == 3) {
                    dlc_            = detail::make_word_le(&buffer_[0]);
                    if constexpr (Format == SxiHeaderFormat::LenCtrWord) {
                        ctr_ = detail::make_word_le(&buffer_[2]);
                    }
                    remaining_      = dlc_;
                    header_complete = true;
                }
            }
            if (header_complete) {
                if constexpr (Checksum == SxiChecksumType::Sum8) {
                    remaining_ += 1;
                } else if constexpr (Checksum == SxiChecksumType::Sum16) {
                    uint16_t header_size = 0;
                    if constexpr (Format == SxiHeaderFormat::LenByte) header_size = 1;
                    else if constexpr (Format == SxiHeaderFormat::LenCtrByte || Format == SxiHeaderFormat::LenFillByte) header_size = 2;
                    else if constexpr (Format == SxiHeaderFormat::LenWord) header_size = 2;
                    else if constexpr (Format == SxiHeaderFormat::LenCtrWord || Format == SxiHeaderFormat::LenFillWord) header_size = 4;

                    fill_ = ((header_size + dlc_) % 2 != 0) ? 1u : 0u;
                    remaining_ += (2 + fill_);
                }
                state_ = State::Remaining;
                if (remaining_ != 0) {
                    index_++;
                    return;
                }
            }
        }
        if (state_ == State::Remaining) {
            if (remaining_ > 0) {
                remaining_--;
            }
            if (remaining_ == 0) {
                uint16_t payload_off = 0;
                if constexpr (Format == SxiHeaderFormat::LenByte) {
                    payload_off = 1;
                } else if constexpr (Format == SxiHeaderFormat::LenCtrByte || Format == SxiHeaderFormat::LenFillByte) {
                    payload_off = 2;
                } else if constexpr (Format == SxiHeaderFormat::LenWord) {
                    payload_off = 2;
                } else if constexpr (Format == SxiHeaderFormat::LenCtrWord || Format == SxiHeaderFormat::LenFillWord) {
                    payload_off = 4;
                }

                // verify checksum
                if constexpr (Checksum == SxiChecksumType::Sum8) {
                    uint8_t sum = 0;
                    for (uint16_t i = 0; i < (payload_off + dlc_ + fill_); ++i) {
                        sum += buffer_[i];
                    }
                    uint8_t rx = buffer_[payload_off + dlc_];
                    if (sum != rx) {
                        log_checksum_error(sum, rx, payload_off + dlc_ + 1);
                        reset();
                        return;
                    }
                } else if constexpr (Checksum == SxiChecksumType::Sum16) {
                    uint16_t           count = (payload_off + dlc_ + fill_);
                    uint16_t sum      = 0;

                    for (uint16_t idx = 0; idx < count; idx += 2) {
                        sum = static_cast<uint16_t>(sum + detail::make_word_le(&buffer_[idx]));
                    }
                    uint16_t rx = detail::make_word_le(&buffer_[payload_off + dlc_ + fill_]);
                    if (sum != rx) {
                        log_checksum_error(sum, rx, payload_off + dlc_ + fill_ + 2);
                        reset();
                        return;
                    }
                }
                if (dispatch_) {
                    dispatch_({ buffer_.data() + payload_off, buffer_.data() + payload_off + dlc_ }, dlc_, ctr_);
                    #if defined(XCP_TL_TEST_HOOKS)
                    std::fill(buffer_.begin(), buffer_.end(), 0xcc);
                    #endif
                }
                reset();
                return;
            }
        }
        index_++;
    }

   private:

    enum class State {
        Idle,
        UntilLength,
        Remaining
    };

    template<typename T>
    void log_checksum_error(T calculated, T received, uint16_t packet_len) {
        std::cerr << "SXI checksum error: Calculated " << std::hex << "0x" << static_cast<int>(calculated)
                  << ", but received " << "0x" << static_cast<int>(received) << "." << std::dec << std::endl;
        std::cerr << "Packet dump (" << packet_len << " bytes):" << std::endl;
        std::cerr << "[";
        std::ios_base::fmtflags flags(std::cerr.flags()); // save flags
        for (uint16_t i = 0; i < packet_len; ++i) {
            std::cerr << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(buffer_[i]) << " ";
            if ((i + 1) % 16 == 0) {
                std::cerr << std::endl;
            }
        }
        std::cerr << "]" << std::endl;
        std::cerr.flags(flags); // restore flags
    }

    void reset() {
        state_     = State::Idle;
        index_     = 0;
        dlc_       = 0;
        remaining_ = 0;
        ctr_       = 0;
        fill_       = 0;
        #if defined(XCP_TL_TEST_HOOKS)
        std::fill(buffer_.begin(), buffer_.end(), 0xcc);
        #endif
    }

    std::array<uint8_t, 1024>                        buffer_{};
    State                                            state_{ State::Idle };
    uint32_t                                         index_{ 0 };
    uint16_t                                         dlc_{ 0 };
    uint16_t                                         ctr_{ 0 };
    uint32_t                                         remaining_{ 0 };
    uint16_t                                         fill_ {0};
    std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)> dispatch_;
};

#endif // __SXI_FRAMING_HPP
