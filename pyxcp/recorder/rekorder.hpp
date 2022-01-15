

#if !defined(__REKORDER_HPP)
#define __REKORDER_HPP

#if !defined(STANDALONE_REKORDER)
    #define STANDALONE_REKORDER     0
#endif /* STANDALONE_REKORDER */

#include <array>
#include <string>
#include <stdexcept>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <cstdio>

#include <ctime>

#include <vector>

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


constexpr auto megabytes(std::size_t value) -> std::size_t
{
    return value * 1024 * 1024;
}

#if 0
void hexdump(blob_t const * buf, std::uint16_t sz)
{
    std::uint16_t idx;

    for (idx = 0; idx < sz; ++idx)
    {
        printf("%02X ", buf[idx]);
    }
    printf("\n\r");
}
#endif

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
    using payload_t = std::unique_ptr<blob_t[]>;
#else
    using payload_t = py::array_t<blob_t>;
#endif /* STANDALONE_REKORDER */

struct FrameType
{

    explicit FrameType() = default;

    FrameType(FrameType&& rhs) {
        this->category = rhs.category;
        this->counter = rhs.counter;
        this->timestamp = rhs.timestamp;
        this->length = rhs.length;
        std::swap(this->payload, rhs.payload);
    }

    // No copy semantics due to unique_ptr.
    FrameType(FrameType const&) = delete;
    FrameType& operator=(FrameType const&) = delete;

    uint8_t category {0};
    uint16_t counter {0};
    double timestamp  {0.0};
    uint16_t length = {0};
    payload_t payload;
};
#pragma pack(pop)

using XcpFrames = std::vector<FrameType>;
using FrameTuple = std::tuple<std::uint8_t, std::uint16_t, double, std::uint16_t, std::unique_ptr<blob_t[]>>;
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
    constexpr auto VERSION = 0x0100;
    constexpr auto FILE_HEADER_SIZE = sizeof(FileHeaderType);
    constexpr auto CONTAINER_SIZE = sizeof(ContainerHeaderType);
    constexpr auto FRAME_SIZE = sizeof(FrameType) - sizeof(payload_t);
}

#if STANDALONE_REKORDER == 1
    inline blob_t * get_payload_ptr(const payload_t& payload) {
        return payload.get();
    }

    payload_t create_payload(std::size_t size) {
        return std::make_unique<blob_t[]>(size);
    }
#else
    payload_t create_payload(std::size_t size) {
        return py::array_t<blob_t>(size);
    }

    inline blob_t * get_payload_ptr(const payload_t& payload) {
        py::buffer_info buf = payload.request();

        return  static_cast<const blob_t *>(buf.ptr);
    }
#endif /* STANDALONE_REKORDER */

inline auto init_ptr(blob_t * const data, std::size_t length) -> std::unique_ptr<blob_t[]> {
    auto payload = std::make_unique<blob_t[]>(length);

    //std::copy_n(data, length, reinterpret_cast<blob_t*>(payload.get()));
    std::copy_n(data, length, payload.get());
    return payload;
}


inline auto file_header_size() -> std::size_t {
    const auto msize = detail::MAGIC.size();

    return (detail::FILE_HEADER_SIZE + msize);
}


/**
 */
class XcpLogFileWriter
{
public:
    explicit XcpLogFileWriter(const std::string& file_name, uint32_t prealloc = 10UL, uint32_t chunk_size = 1)
    {
        m_file_name = file_name + detail::FILE_EXTENSION;
        m_fd = open(m_file_name.c_str(), O_CREAT | O_RDWR | O_TRUNC, 0666);
        truncate(megabytes(prealloc));
        m_mmap = new mio::mmap_sink(m_fd);
        m_chunk_size = megabytes(chunk_size);
        m_intermediate_storage = new std::byte[m_chunk_size + megabytes(1)];
        m_offset = detail::FILE_HEADER_SIZE + detail::MAGIC.size();
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
            close(m_fd);
            delete m_mmap;
            delete[] m_intermediate_storage;
        }
    }

    void add_frames(const XcpFrames& xcp_frames) {
        for (auto const& frame: xcp_frames) {
            store_im(&frame, detail::FRAME_SIZE);
            //store_im(frame.payload.get(), frame.length);
            store_im(get_payload_ptr(frame.payload), frame.length);
            m_container_record_count += 1;
            m_container_size_uncompressed += (detail::FRAME_SIZE + frame.length);
            if (m_container_size_uncompressed > m_chunk_size) {
                compress_frames();
            }
        }
    }
protected:
    void truncate(off_t size) const
    {
        ::ftruncate(m_fd, size);
    }

    blob_t * ptr(std::size_t pos = 0) const
    {
        return m_mmap->data() + pos;
    }

    void store_im(void const * data, std::size_t length) {
        std::memcpy(m_intermediate_storage + m_intermediate_storage_offset, data, length);
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
        ::memcpy(ptr(m_offset), &container, detail::CONTAINER_SIZE);
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

        std::memcpy(addr, buf, count);
    }

    void write_header(uint16_t version, uint16_t options, uint32_t num_containers,
                      uint32_t record_count, uint32_t size_compressed, uint32_t size_uncompressed) {
        auto header = FileHeaderType{};
        write_bytes(0x00000000UL, detail::MAGIC.size(), detail::MAGIC.c_str());
        header.hdr_size = detail::FILE_HEADER_SIZE + detail::MAGIC.size();
        header.version = version;
        header.options = options;
        header.num_containers = num_containers;
        header.record_count = record_count;
        header.size_compressed = size_compressed;
        header.size_uncompressed = size_uncompressed;
        write_bytes(0x00000000UL + detail::MAGIC.size(), detail::FILE_HEADER_SIZE, reinterpret_cast<blob_t *>(&header));
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
    std:: byte * m_intermediate_storage{nullptr};
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
        const auto msize = detail::MAGIC.size();
        blob_t magic[msize + 1];

        read_bytes(0ul, msize, magic);
        if (memcmp(detail::MAGIC.c_str(), magic, msize))
        {
            throw std::runtime_error("Invalid file magic.");
        }
        m_offset = msize;

        read_bytes(m_offset, detail::FILE_HEADER_SIZE, reinterpret_cast<blob_t*>(&m_header));
        //printf("Sizes: %u %u %.3f\n", m_header.size_uncompressed,
        //       m_header.size_compressed,
        //       float(m_header.size_uncompressed) / float(m_header.size_compressed));
        if (m_header.hdr_size != detail::FILE_HEADER_SIZE + msize)
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


    FrameVector next() {
        auto container = ContainerHeaderType{};
        auto total = 0;
        auto frame = FrameType{};
        size_t boffs = 0;
        auto result = FrameVector{};
        for (std::size_t idx = 0; idx < m_header.num_containers; ++idx) {
            read_bytes(m_offset, detail::CONTAINER_SIZE, reinterpret_cast<blob_t*>(&container));

            auto buffer = new blob_t[container.size_uncompressed];

            m_offset += detail::CONTAINER_SIZE;
            total += container.record_count;
            const int uc_size = ::LZ4_decompress_safe(ptr(m_offset), buffer, container.size_compressed, container.size_uncompressed);
            if (uc_size < 0) {
                throw std::runtime_error("LZ4 decompression failed.");
            }
            boffs = 0;
            for (std::uint32_t idx = 0; idx < container.record_count; ++idx) {
                ::memcpy(&frame, &(buffer[boffs]), detail::FRAME_SIZE);
                boffs += detail::FRAME_SIZE;
                auto payload = std::make_unique<blob_t[]>(frame.length);
                std::copy_n(&buffer[boffs], frame.length, reinterpret_cast<blob_t*>(payload.get()));
                boffs += frame.length;
                result.emplace_back(std::make_tuple(frame.category, frame.counter, frame.timestamp, frame.length, std::move(payload)));
            }
            m_offset += container.size_compressed;
            m_current_container += 1;
            delete[] buffer;
        }
        //printf("Total: %u\n", total);
        return result;
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
        std::memcpy(buf, addr, count);
    }

private:
    std::string m_file_name;
    std::size_t m_offset{0};
    std::size_t m_current_container{0};
    mio::mmap_source * m_mmap{nullptr};
    FileHeaderType m_header{0, 0, 0, 0, 0, 0, 0};
};

#endif // __REKORDER_HPP

