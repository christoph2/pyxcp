
#if !defined(__HELPER_HPP)
    #define __HELPER_HPP

    #include <iostream>
    #include <utility>

    #if __cplusplus >= 202302L
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

#endif  // __HELPER_HPP
