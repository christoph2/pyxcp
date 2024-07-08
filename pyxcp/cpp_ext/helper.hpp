
#if !defined(__HELPER_HPP)
    #define __HELPER_HPP

    #include <chrono>
    #include <iostream>
    #include <map>
    #include <utility>
    #include <variant>

    #if (__cplusplus >= 202302L) || (__STDC_VERSION__ >= 202302L)
        #include <stdfloat>

        #if defined(__STDCPP_BFLOAT16_T__)
            #define HAS_BFLOAT16 (1)
        #else
            #define HAS_BFLOAT16 (0)
        #endif

        #if defined(__STDCPP_FLOAT16_T__)
            #define HAS_FLOAT16 (1)
        #else
            #define HAS_FLOAT16 (0)
        #endif
    #else
        #define HAS_FLOAT16  (0)
        #define HAS_BFLOAT16 (0)
    #endif

template<typename... Args>
constexpr void DBG_PRINTN(Args &&...args) noexcept {
    ((std::cout << std::forward<Args>(args) << " "), ...);
}

// NOTE: C++23 has std::byteswap()
constexpr auto _bswap(std::uint64_t v) noexcept {
    return ((v & UINT64_C(0x0000'0000'0000'00FF)) << 56) | ((v & UINT64_C(0x0000'0000'0000'FF00)) << 40) |
           ((v & UINT64_C(0x0000'0000'00FF'0000)) << 24) | ((v & UINT64_C(0x0000'0000'FF00'0000)) << 8) |
           ((v & UINT64_C(0x0000'00FF'0000'0000)) >> 8) | ((v & UINT64_C(0x0000'FF00'0000'0000)) >> 24) |
           ((v & UINT64_C(0x00FF'0000'0000'0000)) >> 40) | ((v & UINT64_C(0xFF00'0000'0000'0000)) >> 56);
}

constexpr auto _bswap(std::uint32_t v) noexcept {
    return ((v & UINT32_C(0x0000'00FF)) << 24) | ((v & UINT32_C(0x0000'FF00)) << 8) | ((v & UINT32_C(0x00FF'0000)) >> 8) |
           ((v & UINT32_C(0xFF00'0000)) >> 24);
}

constexpr auto _bswap(std::uint16_t v) noexcept {
    return ((v & UINT16_C(0x00FF)) << 8) | ((v & UINT16_C(0xFF00)) >> 8);
}

template<typename T>
inline std::string to_binary(const T &value) {
    std::string result;

    auto ptr = reinterpret_cast<const std::string::value_type *>(&value);
    for (std::size_t idx = 0; idx < sizeof(T); ++idx) {
        auto ch = ptr[idx];
        result.push_back(ch);
    }
    return result;
}

template<>
inline std::string to_binary<std::string>(const std::string &value) {
    std::string result;

    auto              ptr    = reinterpret_cast<const std::string::value_type *>(value.c_str());
    const std::size_t length = std::size(value);

    // We are using Pascal strings as serialization format.
    auto len_bin = to_binary(length);
    std::copy(len_bin.begin(), len_bin.end(), std::back_inserter(result));
    for (std::size_t idx = 0; idx < length; ++idx) {
        auto ch = ptr[idx];
        result.push_back(ch);
    }
    return result;
}

inline auto bool_to_string(bool value) {
    return (value == true) ? "True" : "False";
}

inline auto byte_order_to_string(int value) {
    switch (value) {
        case 0:
            return "INTEL";
        case 1:
            return "MOTOROLA";
        default:
            return "<UNKNOWN>";
    }
    return "<UNKNOWN>";
}

template<typename K, typename V>
static std::map<V, K> reverse_map(const std::map<K, V> &m) {
    std::map<V, K> result;
    for (const auto &[k, v] : m) {
        result[v] = k;
    }
    return result;
}

enum class TimestampType : std::uint8_t {
    ABSOLUTE_TS,
    RELATIVE_TS
};

enum class ClockType : std::uint8_t {
    SYSTEM_CLK,
    GPS_CLK,
    TAI_CLK,
    UTC_CLK,
};

class Timestamp {
   public:

    using clock_variant =
        std::variant<std::chrono::system_clock, std::chrono::tai_clock, std::chrono::utc_clock, std::chrono::gps_clock>;

    explicit Timestamp(TimestampType ts_type, ClockType clk_type) : m_type(ts_type) {
        switch (clk_type) {
            case ClockType::SYSTEM_CLK:
                m_clk = std::make_unique<clock_variant>(std::chrono::system_clock());
                break;
            case ClockType::GPS_CLK:
                m_clk = std::make_unique<clock_variant>(std::chrono::gps_clock());
                break;
            case ClockType::TAI_CLK:
                m_clk = std::make_unique<clock_variant>(std::chrono::tai_clock());
                break;
            case ClockType::UTC_CLK:
                m_clk = std::make_unique<clock_variant>(std::chrono::utc_clock());
                break;
        }
        std::cout << static_cast<std::uint16_t>(ts_type) << " : " << static_cast<std::uint16_t>(clk_type) << std::endl;
        m_initial = absolute();
        std::cout << "initial: " << m_initial << std::endl;
    }

    Timestamp(const Timestamp &) = delete;
    Timestamp(Timestamp &&)      = delete;

    std::uint64_t get_value() const noexcept {
        if (m_type == TimestampType::ABSOLUTE_TS) {
            return absolute();
        } else if (m_type == TimestampType::RELATIVE_TS) {
            return relative();
        }
    }

    std::uint64_t get_initial_value() const noexcept {
        return m_initial;
    }

    std::uint64_t absolute() const noexcept {
        std::uint64_t current;

        std::visit(
            [&current](auto &&arg) {
                using T = std::decay_t<decltype(arg)>;

                if constexpr (std::is_same_v<T, std::chrono::system_clock>) {
                    current = std::chrono::duration_cast<std::chrono::nanoseconds>(arg.now().time_since_epoch()).count();
                } else if constexpr (std::is_same_v<T, std::chrono::gps_clock>) {
                    current = std::chrono::duration_cast<std::chrono::nanoseconds>(arg.now().time_since_epoch()).count();
                } else if constexpr (std::is_same_v<T, std::chrono::tai_clock>) {
                    current = std::chrono::duration_cast<std::chrono::nanoseconds>(arg.now().time_since_epoch()).count();
                } else if constexpr (std::is_same_v<T, std::chrono::utc_clock>) {
                    current = std::chrono::duration_cast<std::chrono::nanoseconds>(arg.now().time_since_epoch()).count();
                }
            },
            *m_clk
        );
        return current;
    }

    std::uint64_t relative() const noexcept {
        return absolute() - m_initial;
    }

   private:

    TimestampType                  m_type;
    std::unique_ptr<clock_variant> m_clk;
    std::uint64_t                  m_initial;
};

#endif  // __HELPER_HPP
