

#if !defined(__REKORDER_HPP)
    #define __REKORDER_HPP

    #if !defined(STANDALONE_REKORDER)
        #define STANDALONE_REKORDER 0
    #endif /* STANDALONE_REKORDER */

    #include <array>
    #include <atomic>
    #include <bitset>
    #include <cerrno>
    #include <condition_variable>
    #include <cstdint>
    #include <cstdio>
    #include <cstdlib>
    #include <cstring>
    #include <ctime>
    #include <exception>
    #include <functional>
    #include <mutex>
    #include <optional>
    #include <queue>
    #include <stdexcept>
    #include <string>
    #include <thread>
    #include <utility>
    #include <variant>
    #include <vector>

    #if defined(_WIN32)
        #include <Windows.h>
        #include <fcntl.h>
        #include <io.h>
    #endif /* _WIN32 */

    #include "lz4.h"
    #include "mio.hpp"

    #if STANDALONE_REKORDER == 0
        #include <pybind11/numpy.h>
        #include <pybind11/pybind11.h>
        #include <pybind11/stl.h>

namespace py = pybind11;
using namespace pybind11::literals;
    #endif /* STANDALONE_REKORDER */

    #if !defined(__BIGGEST_ALIGNMENT__)
        #define __BIGGEST_ALIGNMENT__ (8)
    #endif

    #define __ALIGNMENT_REQUIREMENT __BIGGEST_ALIGNMENT__
    #define __ALIGN                 alignas(__ALIGNMENT_REQUIREMENT)

constexpr auto kilobytes(std::uint32_t value) -> std::uint32_t {
    return value * 1024;
}

constexpr auto megabytes(std::uint32_t value) -> std::uint32_t {
    return kilobytes(value) * 1024;
}

constexpr uint16_t XCP_PAYLOAD_MAX = 0xFFFF;

    /*
    byte-order is, where applicable little ending (LSB first).
    */
    #pragma pack(push)
    #pragma pack(1)

struct FileHeaderType {
    uint16_t hdr_size;
    uint16_t version;
    uint16_t options;
    uint32_t num_containers;
    uint32_t record_count;
    uint32_t size_compressed;
    uint32_t size_uncompressed;
};

using HeaderTuple = std::tuple<std::uint32_t, std::uint32_t, std::uint32_t, std::uint32_t, double>;

static_assert(sizeof(FileHeaderType) == 22);

struct ContainerHeaderType {
    uint32_t record_count;
    uint32_t size_compressed;
    uint32_t size_uncompressed;
};

using blob_t = unsigned char;

    #if STANDALONE_REKORDER == 1
using payload_t = std::shared_ptr<blob_t[]>;
    #else
using payload_t = py::array_t<blob_t>;
    #endif /* STANDALONE_REKORDER */

struct frame_header_t {
    uint8_t  category{ 0 };
    uint16_t counter{ 0 };
    double   timestamp{ 0.0 };
    uint16_t length{ 0 };
};

    #pragma pack(pop)

using FrameTuple       = std::tuple<std::uint8_t, std::uint16_t, double, std::uint16_t, payload_t>;
using FrameVector      = std::vector<FrameTuple>;
using FrameTupleWriter = std::tuple<std::uint8_t, std::uint16_t, double, std::uint16_t, char*>;

enum class FrameCategory : std::uint8_t {
    META,
    CMD,
    RES,
    ERR,
    EV,
    SERV,
    DAQ,
    STIM,
};

namespace detail {
const std::string FILE_EXTENSION(".xmraw");
const std::string MAGIC{ "ASAMINT::XCP_RAW" };
constexpr auto    MAGIC_SIZE       = 16;
constexpr auto    VERSION          = 0x0100;
constexpr auto    FILE_HEADER_SIZE = sizeof(FileHeaderType);
constexpr auto    CONTAINER_SIZE   = sizeof(ContainerHeaderType);
}  // namespace detail

constexpr auto file_header_size() -> std::uint32_t {
    return (detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE);
}

using rounding_func_t = std::function<std::uint32_t(std::uint32_t)>;

inline rounding_func_t create_rounding_func(std::uint32_t multiple) {
    return [multiple](std::uint32_t value) {
        return (value + (multiple - 1)) & ~(multiple - 1);
    };
}

const auto round_to_alignment = create_rounding_func(__ALIGNMENT_REQUIREMENT);

inline void _fcopy(char* dest, char const * src, std::uint32_t n) noexcept {
    for (std::uint32_t i = 0; i < n; ++i) {
        dest[i] = src[i];
    }
}

    #if STANDALONE_REKORDER == 1
inline blob_t* get_payload_ptr(const payload_t& payload) noexcept {
    return payload.get();
}

inline payload_t create_payload(std::uint32_t size, blob_t const * data) noexcept {
    auto pl = std::make_shared<blob_t[]>(size);
    _fcopy(reinterpret_cast<char*>(pl.get()), reinterpret_cast<char const *>(data), size);
    return pl;
}
    #else
inline payload_t create_payload(std::uint32_t size, blob_t const * data) {
    return py::array_t<blob_t>(size, data);
}

inline blob_t* get_payload_ptr(const payload_t& payload) noexcept {
    py::buffer_info buf = payload.request();

    return static_cast<blob_t*>(buf.ptr);
}
    #endif /* STANDALONE_REKORDER */

inline void hexdump(blob_t const * buf, std::uint16_t sz) {
    for (std::uint16_t idx = 0; idx < sz; ++idx) {
        printf("%02X ", buf[idx]);
    }
    printf("\n\r");
}

template<typename T>
class TsQueue {
   public:

    TsQueue() = default;

    TsQueue(const TsQueue& other) noexcept {
        std::scoped_lock lock(other.m_mtx);
        m_queue = other.m_queue;
    }

    void put(T value) noexcept {
        std::scoped_lock lock(m_mtx);
        m_queue.push(value);
        m_cond.notify_one();
    }

    std::shared_ptr<T> get() noexcept {
        std::unique_lock lock(m_mtx);
        m_cond.wait(lock, [this] { return !m_queue.empty(); });
        std::shared_ptr<T> result(std::make_shared<T>(m_queue.front()));
        m_queue.pop();
        return result;
    }

    bool empty() const noexcept {
        std::scoped_lock lock(m_mtx);
        return m_queue.empty();
    }

   private:

    mutable std::mutex      m_mtx;
    std::queue<T>           m_queue;
    std::condition_variable m_cond;
};

class Event {
   public:

    Event(const Event& other) noexcept {
        std::scoped_lock lock(other.m_mtx);
        m_flag = other.m_flag;
    }

    ~Event() = default;
    Event()  = default;

    void signal() noexcept {
        std::scoped_lock lock(m_mtx);
        m_flag = true;
        m_cond.notify_one();
    }

    void wait() noexcept {
        std::unique_lock lock(m_mtx);
        m_cond.wait(lock, [this] { return m_flag; });
        m_flag = false;
    }

    bool state() const noexcept {
        std::scoped_lock lock(m_mtx);
        return m_flag;
    }

   private:

    mutable std::mutex      m_mtx{};
    bool                    m_flag{ false };
    std::condition_variable m_cond{};
};

/*
 *
 * Super simplicistic block memory manager.
 *
 */
template<typename T, int _IS, int _NB>
class BlockMemory {
   public:

    using mem_block_t = std::array<T, _IS>;

    explicit BlockMemory() noexcept : m_memory{ nullptr }, m_allocation_count{ 0 } {
        m_memory = new T[_IS * _NB];
    }

    ~BlockMemory() noexcept {
        if (m_memory) {
            delete[] m_memory;
        }
    }

    BlockMemory(const BlockMemory&) = delete;

    T* acquire() noexcept {
        const std::scoped_lock lock(m_mtx);

        if (m_allocation_count >= _NB) {
            return nullptr;
        }
        T* ptr = reinterpret_cast<T*>(m_memory + (m_allocation_count * _IS));
        m_allocation_count++;
        return ptr;
    }

    void release() noexcept {
        const std::scoped_lock lock(m_mtx);
        if (m_allocation_count == 0) {
            return;
        }
        m_allocation_count--;
    }

   private:

    T*            m_memory;
    std::uint32_t m_allocation_count;
    std::mutex    m_mtx;
};

    #include "reader.hpp"
    #include "unfolder.hpp"
    #include "writer.hpp"

#endif  // __REKORDER_HPP
