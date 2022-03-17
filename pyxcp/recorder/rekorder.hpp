

#if !defined(__REKORDER_HPP)
#define __REKORDER_HPP

#if !defined(STANDALONE_REKORDER)
    #define STANDALONE_REKORDER     0
#endif /* STANDALONE_REKORDER */

#include <array>
#include <atomic>
#include <functional>
#include <optional>
#include <condition_variable>
#include <mutex>
#include <queue>

#include <string>
#include <stdexcept>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <cstdio>

#include <ctime>
#include <thread>
#include <vector>

#if defined(_WIN32)
    #include <io.h>
    #include <fcntl.h>

    #include <Windows.h>
#endif /* _WIN32 */

#include <stdlib.h>

#include "lz4.h"
#include "mio.hpp"

#if STANDALONE_REKORDER == 0
    #include <pybind11/pybind11.h>
    #include <pybind11/numpy.h>
    #include <pybind11/stl.h>

    namespace py = pybind11;
    using namespace pybind11::literals;

    struct DType {
        uint8_t category {0};
        uint16_t counter {0};
        double timestamp  {0.0};
        uint8_t payload[];
    };


#endif /* STANDALONE_REKORDER */

#if !defined(__BIGGEST_ALIGNMENT__)
    #define __BIGGEST_ALIGNMENT__   (8)
#endif


#define __ALIGNMENT_REQUIREMENT     __BIGGEST_ALIGNMENT__
#define __ALIGN                     alignas(__ALIGNMENT_REQUIREMENT)


constexpr auto kilobytes(std::size_t value) -> std::size_t
{
    return value * 1024;
}

constexpr auto megabytes(std::size_t value) -> std::size_t
{
    return kilobytes(value) * 1024;
}


/*
byte-order is, where applicable little ending (LSB first).
*/
#pragma pack(push)
#pragma pack(1)
struct FileHeaderType
{
    uint16_t hdr_size;
    uint16_t version;
    uint16_t options;
    uint32_t num_containers;
    uint32_t record_count;
    uint32_t size_compressed;
    uint32_t size_uncompressed;
};

static_assert(sizeof(FileHeaderType) == 22);

struct ContainerHeaderType
{
    uint32_t record_count;
    uint32_t size_compressed;
    uint32_t size_uncompressed;
};

using blob_t = char;    // Signedness doesn't matter in this use-case.

#if STANDALONE_REKORDER == 1
    using payload_t = std::shared_ptr<blob_t[]>;
    //using payload_t = std::unique_ptr<blob_t[]>;
#else
    using payload_t = py::array_t<blob_t>;
#endif /* STANDALONE_REKORDER */


struct frame_header_t
{
    uint8_t category {0};
    uint16_t counter {0};
    double timestamp {0.0};
    uint16_t length {0};
};
#pragma pack(pop)

using FrameTuple = std::tuple<std::uint8_t, std::uint16_t, double, std::uint16_t, payload_t>;
using FrameVector = std::vector<FrameTuple>;


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


namespace detail
{
    const std::string FILE_EXTENSION(".xmraw");
    const std::string MAGIC{"ASAMINT::XCP_RAW"};
    constexpr auto MAGIC_SIZE = 16;
    constexpr auto VERSION = 0x0100;
    constexpr auto FILE_HEADER_SIZE = sizeof(FileHeaderType);
    constexpr auto CONTAINER_SIZE = sizeof(ContainerHeaderType);
}


inline auto file_header_size() -> std::size_t {
    return (detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE);
}

using rounding_func_t = std::function<std::size_t(std::size_t)>;

const rounding_func_t create_rounding_func(std::size_t multiple) {
    return [=](std::size_t value) -> std::size_t {
        return (value + (multiple - 1)) & ~(multiple -1 );
    };
}

const auto round_to_alignment = create_rounding_func(__ALIGNMENT_REQUIREMENT);


inline void _fcopy(blob_t * dest, const blob_t * src, std::size_t n)
{
    for (std::size_t i = 0; i < n; ++i) {
        dest[i] = src[i];
    }
}

#if STANDALONE_REKORDER == 1
    inline blob_t * get_payload_ptr(const payload_t& payload) {
        return payload.get();
    }

    payload_t create_payload(std::size_t size, blob_t const * data) {
        auto pl = std::make_unique<blob_t[]>(size);
        //auto pl = std::make_shared<blob_t[]>(size);
        _fcopy(pl.get(), data, size);
        return pl;
    }
#else
    payload_t create_payload(std::size_t size, blob_t const * data) {
        return py::array_t<blob_t>(size, data);
    }

    inline blob_t * get_payload_ptr(const payload_t& payload) {
        py::buffer_info buf = payload.request();

        return  static_cast<blob_t *>(buf.ptr);
    }
#endif /* STANDALONE_REKORDER */

inline void hexdump(blob_t const * buf, std::uint16_t sz)
{
    std::uint16_t idx;

    for (idx = 0; idx < sz; ++idx)
    {
        printf("%02X ", buf[idx]);
    }
    printf("\n\r");
}


template <typename T>
class TsQueue {
public:
    explicit  TsQueue() {}

    TsQueue(const TsQueue& other) {
        std::lock_guard<std::mutex> lock(other.m_mtx);
        m_queue = other.m_queue;
    }

    void put(T value) {
        std::lock_guard<std::mutex> lock(m_mtx);
        m_queue.push(value);
        m_cond.notify_one();
    }

    std::shared_ptr<T> get() {
        std::unique_lock<std::mutex> lock(m_mtx);
        m_cond.wait(lock, [this]{return !m_queue.empty();});
        std::shared_ptr<T> result(std::make_shared<T>(m_queue.front()));
        m_queue.pop();
        return result;
    }

    bool empty() const {
        std::lock_guard<std::mutex> lock(m_mtx);
        return m_queue.empty();
    }

private:
    mutable std::mutex m_mtx;
    std::queue<T> m_queue;
    std::condition_variable m_cond;
};


class Event {
public:
     explicit Event() : m_mtx{}, m_flag{false}, m_cond{} {}

    Event(const Event& other) {
        std::lock_guard<std::mutex> lock(other.m_mtx);
        m_flag = other.m_flag;
    }

    void signal() {
        std::lock_guard<std::mutex> lock(m_mtx);
        m_flag = true;
        m_cond.notify_one();
    }

    void wait() {
        std::unique_lock<std::mutex> lock(m_mtx);
        m_cond.wait(lock, [this]{return m_flag;});
        m_flag = false;
    }

    bool state() const {
        std::lock_guard<std::mutex> lock(m_mtx);
        return m_flag;
    }

private:
    mutable std::mutex m_mtx;
    bool m_flag {false};
    std::condition_variable m_cond;
};


/**
 */
class XcpLogFileWriter
{
public:
    explicit XcpLogFileWriter(const std::string& file_name, uint32_t prealloc = 10UL, uint32_t chunk_size = 1)
    {
        m_file_name = file_name + detail::FILE_EXTENSION;
#if defined(_WIN32)
        m_fd = CreateFile(
            m_file_name.c_str(),
            GENERIC_READ | GENERIC_WRITE,
            NULL,
            (LPSECURITY_ATTRIBUTES)NULL,
            CREATE_NEW, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_RANDOM_ACCESS,
            NULL
        );
#else
        m_fd = open(m_file_name.c_str(), O_CREAT | O_RDWR | O_TRUNC, 0666);
#endif
        truncate(megabytes(prealloc));
        m_mmap = new mio::mmap_sink(m_fd);
        m_chunk_size = megabytes(chunk_size);
        m_intermediate_storage = new blob_t[m_chunk_size + megabytes(1)];
        m_offset = detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE;
    }

    ~XcpLogFileWriter() {
        finalize();
    }

    void finalize() {
        if (!m_finalized) {
            m_finalized = true;
            if (m_container_record_count) {
                compress_frames();
            }
            write_header(detail::VERSION, 0x0000, m_num_containers, m_record_count, m_total_size_compressed, m_total_size_uncompressed);
            truncate(m_offset);
#if defined(_WIN32)
            CloseHandle(m_fd);
#else
            close(m_fd);
#endif
            delete m_mmap;
            delete[] m_intermediate_storage;
        }
    }

    void add_frame(uint8_t category, uint16_t counter, double timestamp, uint16_t length, const  payload_t& payload) {
        frame_header_t frame {category, counter, timestamp, length};

        store_im(&frame, sizeof(frame));
        store_im(get_payload_ptr(payload), length);
        m_container_record_count += 1;
        m_container_size_uncompressed += (sizeof(frame) + length);
        if (m_container_size_uncompressed > m_chunk_size) {
            compress_frames();
        }
    }

protected:
    void truncate(off_t size) const
    {
#if defined(_WIN32)
        SetFilePointer(m_fd, size, NULL, FILE_BEGIN);
        SetEndOfFile(m_fd);
#else
        ftruncate(m_fd, size);
#endif
    }

    blob_t * ptr(std::size_t pos = 0) const
    {
        return m_mmap->data() + pos;
    }

    void store_im(void const * data, std::size_t length) {
        _fcopy(m_intermediate_storage + m_intermediate_storage_offset, (const blob_t*)data, length);
        m_intermediate_storage_offset += length;
    }

    void compress_frames() {
        auto container = ContainerHeaderType{};
        //printf("Compressing %u frames... [%d]\n", m_container_record_count, m_intermediate_storage_offset);
        const int cp_size = ::LZ4_compress_default(
            reinterpret_cast<blob_t*>(m_intermediate_storage), ptr(m_offset + detail::CONTAINER_SIZE),
            m_intermediate_storage_offset, LZ4_COMPRESSBOUND(m_intermediate_storage_offset)
        );
        if (cp_size < 0) {
            throw std::runtime_error("LZ4 compression failed.");
        }
        //printf("comp: %d %d [%f]\n", m_intermediate_storage_offset,  cp_size, double(m_intermediate_storage_offset) / double(cp_size));
        container.record_count = m_container_record_count;
        container.size_compressed = cp_size;
        container.size_uncompressed = m_container_size_uncompressed;
        _fcopy(ptr(m_offset), (blob_t*)&container, detail::CONTAINER_SIZE);
        m_offset += (detail::CONTAINER_SIZE + cp_size);
        m_total_size_uncompressed += m_container_size_uncompressed;
        m_total_size_compressed += cp_size;
        m_record_count += m_container_record_count;
        m_container_size_uncompressed = 0;
        m_container_size_compressed = 0;
        m_container_record_count = 0;
        m_intermediate_storage_offset = 0;
        m_num_containers += 1;
    }

    void write_bytes(std::size_t pos, std::size_t count, blob_t const * buf)
    {
        auto addr = ptr(pos);

        _fcopy(addr, buf, count);
    }

    void write_header(uint16_t version, uint16_t options, uint32_t num_containers,
                      uint32_t record_count, uint32_t size_compressed, uint32_t size_uncompressed) {
        auto header = FileHeaderType{};
        write_bytes(0x00000000UL, detail::MAGIC_SIZE, detail::MAGIC.c_str());
        header.hdr_size = detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE;
        header.version = version;
        header.options = options;
        header.num_containers = num_containers;
        header.record_count = record_count;
        header.size_compressed = size_compressed;
        header.size_uncompressed = size_uncompressed;
        write_bytes(0x00000000UL + detail::MAGIC_SIZE, detail::FILE_HEADER_SIZE, reinterpret_cast<blob_t *>(&header));
    }

private:
    std::string m_file_name;
    std::size_t m_offset{0};
    std::size_t m_chunk_size{0};
    std::size_t m_num_containers{0};
    std::size_t m_record_count{0};
    std::size_t m_container_record_count{0};
    std::size_t m_total_size_uncompressed{0};
    std::size_t m_total_size_compressed{0};
    std::size_t m_container_size_uncompressed{0};
    std::size_t m_container_size_compressed{0};
    __ALIGN blob_t * m_intermediate_storage{nullptr};
    std::size_t m_intermediate_storage_offset{0};
    mio::file_handle_type m_fd{INVALID_HANDLE_VALUE};
    mio::mmap_sink * m_mmap{nullptr};
    bool m_finalized{false};
};


/**
 */
class XcpLogFileReader
{
public:
    explicit XcpLogFileReader(const std::string& file_name)
    {
        m_file_name = file_name + detail::FILE_EXTENSION;
        m_mmap = new mio::mmap_source(m_file_name);
        blob_t magic[detail::MAGIC_SIZE + 1];

        read_bytes(0ul, detail::MAGIC_SIZE, magic);
        if (memcmp(detail::MAGIC.c_str(), magic, detail::MAGIC_SIZE))
        {
            throw std::runtime_error("Invalid file magic.");
        }
        m_offset = detail::MAGIC_SIZE;

        read_bytes(m_offset, detail::FILE_HEADER_SIZE, reinterpret_cast<blob_t*>(&m_header));
        //printf("Sizes: %u %u %.3f\n", m_header.size_uncompressed,
        //       m_header.size_compressed,
        //       float(m_header.size_uncompressed) / float(m_header.size_compressed));
        if (m_header.hdr_size != detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE)
        {
            throw std::runtime_error("File header size does not match.");
        }
        if (detail::VERSION != m_header.version)
        {
            throw std::runtime_error("File version mismatch.");
        }

        if (m_header.num_containers < 1) {
            throw std::runtime_error("At least one container required.");
        }

        m_offset += detail::FILE_HEADER_SIZE;
    }

    const FileHeaderType get_header() const {

        return m_header;
    }

    void reset() {
        m_current_container = 0;
        m_offset = file_header_size();
    }


    std::optional<FrameVector> next_block() {
        auto container = ContainerHeaderType{};
        auto total = 0;
        auto frame = frame_header_t{};
        size_t boffs = 0;
        auto result = FrameVector{};
        payload_t payload;

        if (m_current_container >= m_header.num_containers) {
            return std::nullopt;
        }
        read_bytes(m_offset, detail::CONTAINER_SIZE, reinterpret_cast<blob_t*>(&container));
        //printf("rc: %d c: %d u: %d \n", container.record_count, container.size_compressed, container.size_uncompressed);

        __ALIGN auto buffer = new blob_t[container.size_uncompressed];

        m_offset += detail::CONTAINER_SIZE;
        total += container.record_count;
        result.reserve(container.record_count);
        const int uc_size = ::LZ4_decompress_safe(ptr(m_offset), buffer, container.size_compressed, container.size_uncompressed);
        if (uc_size < 0) {
            throw std::runtime_error("LZ4 decompression failed.");
        }
        boffs = 0;
        for (std::uint32_t idx = 0; idx < container.record_count; ++idx) {
            _fcopy((blob_t*)&frame, &(buffer[boffs]), sizeof(frame_header_t));
            boffs += sizeof(frame_header_t);
            //result.emplace_back(std::make_tuple(frame.category, frame.counter, frame.timestamp, frame.length, create_payload(frame.length, &buffer[boffs])));
            result.push_back(std::make_tuple(frame.category, frame.counter, frame.timestamp, frame.length, create_payload(frame.length, &buffer[boffs])));
            boffs += frame.length;
            //result.emplace_back(std::make_tuple(frame.category, frame.counter, frame.timestamp, frame.length, std::move(payload)));
        }
        m_offset += container.size_compressed;
        m_current_container += 1;
        delete[] buffer;
        //printf("OK, retuning from next -- Total: %u\n", total);
        return std::optional<FrameVector>{result};
    }

    ~XcpLogFileReader()
    {
        delete m_mmap;
    }

protected:
    blob_t const *ptr(std::size_t pos = 0) const
    {
        return m_mmap->data() + pos;
    }

    void read_bytes(std::size_t pos, std::size_t count, blob_t * buf) const
    {
        auto addr = ptr(pos);
        _fcopy(buf, addr, count);
    }

    bool start_thread() {
        if (decomp_thrd.joinable()) {
            return false;
        }
        stop_thread_flag = false;
        decomp_thrd = std::thread([this]() {
            while (!stop_thread_flag) {
            //    std::this_thread::sleep_for(std::chrono::milliseconds(100));
            //    if (cb_) cb_(1234);
            }
        });
        return true;
    }

    bool stop_thread() {
        if (!decomp_thrd.joinable()) {
            return false;
        }
        stop_thread_flag = true;
        decomp_thrd.join();
        return true;
    }

private:
    std::string m_file_name;
    std::size_t m_offset{0};
    std::size_t m_current_container{0};
    mio::mmap_source * m_mmap{nullptr};
    //FileHeaderType m_header{0, 0, 0, 0, 0, 0, 0};
    FileHeaderType m_header;
    std::thread decomp_thrd{};
    std::mutex mtx;
    std::queue<FrameVector> data_queue;
    std::condition_variable data_cond;
    std::atomic_bool stop_thread_flag{false};
    std::atomic_bool request_decompression{false};
    std::atomic_bool final_block{false};
};

#endif // __REKORDER_HPP
