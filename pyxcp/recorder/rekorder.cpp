

#include <array>
#include <string>
#include <stdexcept>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <cstdio>

#include <ctime>

#include <vector>

#include "lz4.h"
#include "mio.hpp"

void XcpUtl_Hexdump(std::uint8_t const *buf, std::uint16_t sz)
{
    std::uint16_t idx;

    for (idx = 0; idx < sz; ++idx)
    {
        printf("%02X ", buf[idx]);
    }
    printf("\n\r");
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

struct RecordType
{
    uint8_t category;
    uint16_t counter;
    double timestamp;
    uint16_t length;
    // payload;
};
#pragma pack(pop)

using XcpFrames = std::vector<RecordType>;

namespace detail
{
    const auto VERSION_MAJOR = 1;
    const auto BLOCKSIZE = 8192;
    const std::string FILE_EXTENSION(".xmraw");
    const std::string MAGIC{"ASAMINT::XCP_RAW"};
    const auto FILE_HEADER_SIZE = sizeof(FileHeaderType);
    const auto CONTAINER_SIZE = sizeof(ContainerHeaderType);
} // namespace detail

typedef enum tagDatatypeCode
{
    DT_RAW,
    DT_UINT8,
    DT_SINT8,
    DT_UINT16,
    DT_SINT16,
    DT_UINT32,
    DT_SINT32,
    DT_UINT64,
    DT_SINT64,
    DT_FLOAT,
} DatatypeCode;

typedef struct tagDatatype
{
    DatatypeCode type;
    union {
        uint64_t raw;
        uint8_t u8;
        int8_t i8;
        uint16_t u16;
        int16_t i16;
        uint32_t u32;
        int32_t i32;
        uint64_t u64;
        int64_t i64;
        long double fl64;
    } value;
} Datatype;

typedef struct tagMeasurementType
{
    clock_t now;
    uint32_t odt;
    uint16_t len;
    uint8_t const *data;
    // Datatype datatype;
} MeasurementType;


/**
 */
class XcpLogFileWriter
{
  public:

#if 0
def __init__(self, file_name: str, prealloc: int = 10, chunk_size: int = 1024,
        compression_level: int = 9
    ):
        self.container_header_offset = FILE_HEADER_STRUCT.size
        self.current_offset = self.container_header_offset + CONTAINER_HEADER_STRUCT.size
        self.total_size_uncompressed = self.total_size_compressed = 0
        self.container_size_uncompressed = self.container_size_compressed = 0
        self.total_record_count = 0
        self.chunk_size = chunk_size * 1024
        self.num_containers = 0
        self.intermediate_storage = []
        self.compression_level = compression_level
        self.prealloc = prealloc
        self._is_closed = False

    def add_xcp_frames(self, xcp_frames: list):
        for counter, timestamp, raw_data in xcp_frames:
            length = len(raw_data)
            item = DAQ_RECORD_STRUCT.pack(1, counter, timestamp, length) + raw_data
#endif
    explicit XcpLogFileWriter(const std::string &file_name, uint32_t prealloc = 10UL, uint32_t chunk_size = 1024, uint32_t compression_level = 9)
    {
        m_file_name = file_name + detail::FILE_EXTENSION;
        m_fd = open(m_file_name.c_str(), O_CREAT | O_RDWR | O_TRUNC, 0666);
        preallocate(prealloc * 1000 * 1000);
        m_mmap = new mio::mmap_sink(m_fd);
        m_chunk_size = chunk_size;
        m_compression_level = compression_level;
    }

    ~XcpLogFileWriter() {
        close(m_fd);
        delete m_mmap;
    }

    void add_frames(const XcpFrames& xcp_frames) {
        for (auto const& frame: xcp_frames) {

        }
    }

  protected:
    void preallocate(off_t size) const
    {
        ::ftruncate(m_fd, size);
    }

    char *ptr(std::size_t pos = 0) const
    {
        return m_mmap->data() + pos;
    }

    void Write_Bytes(std::size_t pos, std::size_t count, char *buf)
    {
        auto addr = ptr(pos);

        std::memcpy(addr, buf, count);
    }

  private:
    std::string m_file_name;
    std::size_t m_offset{0};
    std::size_t m_chunk_size{0};
    std::size_t m_compression_level{0};
    std::size_t m_num_containers{0};

    std::size_t m_total_size_uncompressed{0};
    std::size_t m_total_size_compressed{0};
    std::size_t m_container_size_uncompressed{0};
    std::size_t m_container_size_compressed{0};
    mio::file_handle_type m_fd{INVALID_HANDLE_VALUE};
    mio::mmap_sink *m_mmap{nullptr};
};


/**
 */
class XcpLogFileReader
{
  public:
    explicit XcpLogFileReader(const std::string &file_name)
    {
        m_file_name = file_name + detail::FILE_EXTENSION;
        m_mmap = new mio::mmap_source(m_file_name);
        const auto msize = detail::MAGIC.size();
        char magic[msize + 1];

        Read_Bytes(0ul, msize, magic);
        if (memcmp(detail::MAGIC.c_str(), magic, msize))
        {
            throw std::runtime_error("Invalid file magic.");
        }
        m_offset = msize;

        Read_Bytes(m_offset, detail::FILE_HEADER_SIZE, (char *)&m_header);
        printf("Containers: %u Records: %u\n", m_header.num_containers, m_header.record_count);
        printf("%u %u %.3f\n", m_header.size_uncompressed,
               m_header.size_compressed,
               float(m_header.size_uncompressed) / float(m_header.size_compressed));
        if (m_header.hdr_size != detail::FILE_HEADER_SIZE + msize)
        {
            throw std::runtime_error("File header size does not match.");
        }
        if (detail::VERSION_MAJOR != (m_header.version >> 8))
        {
            throw std::runtime_error("File version mismatch.");
        }

        m_offset += detail::FILE_HEADER_SIZE;
        auto container = ContainerHeaderType{};
        auto total = 0;
        for (std::size_t idx = 0; idx < m_header.num_containers; ++idx) {
            Read_Bytes(m_offset, detail::CONTAINER_SIZE, (char *)&container);
            printf("RC: %u C: %u U: %u\n", container.record_count, container.size_compressed, container.size_uncompressed);
            auto buffer = new char[container.size_uncompressed << 2];

            m_offset += detail::CONTAINER_SIZE;
            total += container.record_count;
            //auto xxx = decoder.open((char**)ptr(m_offset), &container.size_compressed);
            const int xxx = LZ4_decompress_safe(ptr(m_offset), buffer, container.size_compressed, container.size_uncompressed << 2);
            printf("fl: %d\n", xxx);
            /*
            uncompressed_data = memoryview(lz4block.decompress(self.get(offset, size_compressed)))
            frame_offset = 0
            for _ in range(record_count):
                category, counter, timestamp, frame_length = DAQ_RECORD_STRUCT.unpack(
                    uncompressed_data[frame_offset : frame_offset + DAQ_RECORD_STRUCT.size]
                )
                frame_offset += DAQ_RECORD_STRUCT.size
                frame_data = uncompressed_data[frame_offset : frame_offset + frame_length] # .tobytes()
                frame_offset += len(frame_data)
                frame = DAQRecord(category, counter, timestamp, frame_data)
                yield frame
            */
            m_offset += container.size_compressed;
            delete[] buffer;
        }
        printf("Total: %u\n", total);
    }

    ~XcpLogFileReader()
    {
        delete m_mmap;
    }

  protected:
    char const *ptr(std::size_t pos = 0) const
    {
        return m_mmap->data() + pos;
    }

    std::uint16_t Read_Word(std::size_t pos) const
    {
        auto addr = ptr(pos);
    }

    std::uint32_t Read_DWord(std::size_t pos) const
    {
        auto addr = ptr(pos);
    }

    std::uint64_t Read_QWord(std::size_t pos) const
    {
        auto addr = ptr(pos);
    }

    void Read_Bytes(std::size_t pos, std::size_t count, char *buf) const
    {
        auto addr = ptr(pos);

        std::memcpy(buf, addr, count);
    }

private:
    std::string m_file_name;
    std::size_t m_offset{0};
    mio::mmap_source *m_mmap{nullptr};
    FileHeaderType m_header{0};
};

void some_records(const XcpLogFileWriter& writer)
{
    const auto COUNT = 1024 * 10 * 5;
    auto my_frames = XcpFrames{};

    for (auto idx = 0; idx < COUNT; ++idx) {
        auto&& fr = RecordType{};
        fr.category = 1;
        fr.counter = idx;
        fr.timestamp = std::clock();
        //fr.length =
        my_frames.emplace_back(std::move(fr));
    }
    writer.add_frames(my_frames);
    printf("Added %u frames.\n", my_frames.size());
}


int main(int argc, char *argv[])
{
    //auto reader = XcpLogFileReader("test_logger");
    auto writer = XcpLogFileWriter("test_logger");

    some_records(writer);

    printf("Finished.\n");
}

