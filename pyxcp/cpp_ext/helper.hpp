
#if !defined(__HELPER_HPP)
    #define __HELPER_HPP

    #if defined(_WIN32) || defined(_WIN64)

    #else
        #include <sys/time.h>
        #include <time.h>
    #endif

    #include <bit>
    #include <chrono>
    #include <iostream>
    #include <map>
    #include <utility>
    #include <variant>

    #if __has_include(<version>)
        #include <version>  // Needed for feature testing.
    #endif

    #ifdef __has_include
        #if __has_include(<stdfloat>)
            #include <stdfloat>
        #endif
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

constexpr std::endian target_byteorder() {
    return std::endian::native;
}

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
    result.resize(sizeof(T));
    std::memcpy(result.data(), &value, sizeof(T));
    return result;
}

inline std::string to_binary_str(const std::string &value) {
    std::string result;
    std::uint64_t length = static_cast<std::uint64_t>(value.size());
    auto len_bin = to_binary<std::uint64_t>(length);
    result.reserve(sizeof(std::uint64_t) + value.size());
    result.append(len_bin);
    result.append(value);
    return result;
}

template<>
inline std::string to_binary<std::string>(const std::string &value) {
    return to_binary_str(value);
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

class EventInfo {
   public:

    EventInfo(const EventInfo &)            = default;
    EventInfo(EventInfo &&)                 = default;
    EventInfo &operator=(const EventInfo &) = default;
    EventInfo &operator=(EventInfo &&)      = default;
    virtual ~EventInfo() {}

    EventInfo() : m_event_cycle_ns(0) {
    }

    explicit EventInfo(std::uint64_t event_cycle_ns) : m_event_cycle_ns(event_cycle_ns) {
    }

    std::uint64_t get_event_cycle_ns() const noexcept {
        return m_event_cycle_ns;
    }

    void set_event_cycle_ns(std::uint64_t value) noexcept {
        m_event_cycle_ns = value;
    }

    std::string to_string() const noexcept {
        std::stringstream ss;
        ss << "EventInfo(event_cycle_ns=" << m_event_cycle_ns << ")";
        return ss.str();
    }

   private:
    std::uint64_t m_event_cycle_ns;
};

class TimestampInfo {
   public:

    TimestampInfo(const TimestampInfo &)            = default;
    TimestampInfo(TimestampInfo &&)                 = default;
    TimestampInfo &operator=(const TimestampInfo &) = default;
    TimestampInfo &operator=(TimestampInfo &&)      = default;
    virtual ~TimestampInfo() {}

    TimestampInfo() : m_timestamp_ns(0), m_timezone{}, m_utc_offset(0), m_dst_offset(0) {
    }

    TimestampInfo(std::uint64_t timestamp_ns, const std::string &timezone, std::int16_t utc_offset, std::int16_t dst_offset) :
        m_timestamp_ns(timestamp_ns), m_timezone(timezone), m_utc_offset(utc_offset), m_dst_offset(dst_offset) {
    }

    explicit TimestampInfo(std::uint64_t timestamp_ns) : m_timestamp_ns(timestamp_ns) {
    #if defined(_WIN32) || defined(_WIN64)
        m_timezone = std::chrono::current_zone()->name();
    #else
        tzset();
        m_timezone = tzname[0];

    #endif  // _WIN32 || _WIN64
    }

    std::string get_timezone() const noexcept {
        return m_timezone;
    }

    void set_timezone(const std::string &value) noexcept {
        m_timezone = value;
    }

    std::uint64_t get_timestamp_ns() const noexcept {
        return m_timestamp_ns;
    }

    void set_utc_offset(std::int16_t value) noexcept {
        m_utc_offset = value;
    }

    std::int16_t get_utc_offset() const noexcept {
        return m_utc_offset;
    }

    void set_dst_offset(std::int16_t value) noexcept {
        m_dst_offset = value;
    }

    std::int16_t get_dst_offset() const noexcept {
        return m_dst_offset;
    }

    std::string to_string() const noexcept {
        std::stringstream ss;
        ss << "TimestamInfo(\n";
        ss << "\ttimestamp_ns=" << m_timestamp_ns << ",\n";
        ss << "\ttimezone=\"" << m_timezone << "\",\n";
        ss << "\tutc_offset=" << m_utc_offset << ",\n";
        ss << "\tdst_offset=" << m_dst_offset << "\n";
        ss << ");";
        return ss.str();
    }

    virtual void dummy() const noexcept {};

   private:

    std::uint64_t m_timestamp_ns;
    std::string   m_timezone{};
    std::int16_t  m_utc_offset{ 0 };
    std::int16_t  m_dst_offset{ 0 };
};

class Timestamp {
   public:

    explicit Timestamp(TimestampType ts_type) : m_type(ts_type) {
        m_initial = absolute();
    }

    Timestamp(const Timestamp &) = default;
    Timestamp(Timestamp &&)      = default;

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

    #if defined(_WIN32) || defined(_WIN64)
        current = std::chrono::duration_cast<std::chrono::nanoseconds>(m_clk.now().time_since_epoch()).count();
    #else
        // On MacOS `clock_gettime_nsec_np` could be used.
        timespec ts;
        clock_gettime(CLOCK_REALTIME, &ts);
        current = static_cast<std::uint64_t>(ts.tv_sec) * 1'000'000'000 + ts.tv_nsec;
    #endif  // _WIN32 || _WIN64
        return current;
    }

    std::uint64_t relative() const noexcept {
        return absolute() - m_initial;
    }

   private:

    TimestampType m_type;
    #if defined(_WIN32) || defined(_WIN64)
    std::chrono::utc_clock m_clk;
    #else

    #endif  // _WIN32 || _WIN64
    std::uint64_t m_initial;
};

template<typename T, typename V>
T variant_get(V&& value) {

    T result;

    const T* value_ptr = std::get_if<T>(&value);
    if (value_ptr == nullptr) {
        result = T{};
    }
    else {
        result = *value_ptr;
    }

    return result;
}

#if 0
inline void sleep_ms(std::uint64_t milliseconds) {
    std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

inline void sleep_ns(std::uint64_t nanoseconds) {
    std::this_thread::sleep_for(std::chrono::nanoseconds(nanoseconds));
}
#endif

#endif  // __HELPER_HPP
