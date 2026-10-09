#if !defined(__IO_TYPES_HPP)
#define __IO_TYPES_HPP

#include <cstdint>

enum class IoType : std::uint8_t {
    IO_ACCEPT,
    IO_CONNECT,
    IO_READ,
    IO_WRITE
};

#endif  // __IO_TYPES_HPP
