

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


constexpr auto megabytes(std::size_t value) -> std::size_t
{
    return value * 1024 * 1024;
}

void hexdump(char const * buf, std::uint16_t sz)
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

using payload_t = std::uint8_t *;

struct RecordType
{
    uint8_t category;
    uint16_t counter;
    double timestamp;
    uint16_t length;
    payload_t payload;
};
#pragma pack(pop)

using XcpFrames = std::vector<RecordType>;

namespace detail
{
    const auto VERSION = 0x0100;
    const std::string FILE_EXTENSION(".xmraw");
    const std::string MAGIC{"ASAMINT::XCP_RAW"};
    const auto FILE_HEADER_SIZE = sizeof(FileHeaderType);
    const auto CONTAINER_SIZE = sizeof(ContainerHeaderType);
    const auto FRAME_SIZE = sizeof(RecordType) - sizeof(payload_t);
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
    explicit XcpLogFileWriter(const std::string& file_name, uint32_t prealloc = 10UL, uint32_t chunk_size = 1, uint32_t compression_level = 9)
    {
        m_file_name = file_name + detail::FILE_EXTENSION;
        m_fd = open(m_file_name.c_str(), O_CREAT | O_RDWR | O_TRUNC, 0666);
        truncate(megabytes(prealloc));
        m_mmap = new mio::mmap_sink(m_fd);
        m_chunk_size = megabytes(chunk_size);
        m_compression_level = compression_level;
        m_intermediate_storage = new std::byte[m_chunk_size + megabytes(1)];
        m_offset = detail::FILE_HEADER_SIZE + detail::CONTAINER_SIZE;
    }

    ~XcpLogFileWriter() {
        if (m_container_record_count) {
            compress_frames();
        }
        //printf("offset: %u %u\n", m_intermediate_storage_offset, m_container_record_count);
        Write_Header(detail::VERSION, 0x0000, m_num_containers, m_record_count, m_total_size_compressed, m_total_size_uncompressed);
        truncate(m_offset);
        close(m_fd);
        delete m_mmap;
        delete[] m_intermediate_storage;
    }

    void add_frames(const XcpFrames& xcp_frames) {
        for (auto const& frame: xcp_frames) {

//            hexdump((const char*)frame.payload, frame.length);

            // TODO: factor out!!!
            std::memcpy(m_intermediate_storage + m_intermediate_storage_offset, &frame, detail::FRAME_SIZE);
            m_intermediate_storage_offset += detail::FRAME_SIZE;
            // TODO: copy data!!!
            std::memcpy(m_intermediate_storage + m_intermediate_storage_offset, frame.payload, frame.length);
            m_intermediate_storage_offset += frame.length;

            m_container_record_count += 1;

            //m_intermediate_storage
            //m_intermediate_storage_offset



            m_container_size_uncompressed += (detail::FRAME_SIZE + frame.length);
            if (m_container_size_uncompressed > m_chunk_size) {
                compress_frames();
    /*
            frame.category
            frame.counter
            frame.timestamp
            frame.length


            length = len(raw_data)
            item = DAQ_RECORD_STRUCT.pack(1, counter, timestamp, length) + raw_data
            self.intermediate_storage.append(item)
            self.container_size_uncompressed += len(item)

            if self.container_size_uncompressed > self.chunk_size:
                self._compress_framez()
     */
            }
        }
    }

    void compress_frames() {
/*
        compressed_data = lz4block.compress(b''.join(self.intermediate_storage), compression = self.compression_level)
        record_count = len(self.intermediate_storage)
        hdr = CONTAINER_HEADER_STRUCT.pack(record_count, len(compressed_data), self.container_size_uncompressed)
        self.set(self.current_offset, compressed_data)
        self.set(self.container_header_offset, hdr)
        self.container_header_offset = self.current_offset + len(compressed_data)
        self.current_offset = self.container_header_offset + CONTAINER_HEADER_STRUCT.size
        self.intermediate_storage = []
        self.total_record_count += record_count
        self.num_containers +=1
        self.total_size_uncompressed += self.container_size_uncompressed
        self.total_size_compressed += len(compressed_data)


 */
        auto container = ContainerHeaderType{};

        //printf("Compressing %u frames...\n", m_container_record_count);

        const int cp_size = ::LZ4_compress_default(reinterpret_cast<char*>(m_intermediate_storage), ptr(m_offset + detail::CONTAINER_SIZE) , m_intermediate_storage_offset, LZ4_COMPRESSBOUND(m_intermediate_storage_offset));

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
        m_record_count += m_container_record_count;

        m_container_size_uncompressed = 0;
        m_container_size_compressed = 0;
        m_container_record_count = 0;
        m_intermediate_storage_offset = 0;
    }

protected:
    void truncate(off_t size) const
    {
        ::ftruncate(m_fd, size);
    }

    char * ptr(std::size_t pos = 0) const
    {
        return m_mmap->data() + pos;
    }

    void Write_Bytes(std::size_t pos, std::size_t count, char const * buf)
    {
        auto addr = ptr(pos);

        std::memcpy(addr, buf, count);
    }

    void Write_Header(uint16_t version, uint16_t options, uint32_t num_containers,
                      uint32_t record_count, uint32_t size_compressed, uint32_t size_uncompressed) {
        auto header = FileHeaderType{};

        Write_Bytes(0x00000000UL, detail::MAGIC.size(), detail::MAGIC.c_str());
        header.hdr_size = detail::FILE_HEADER_SIZE;
        header.version = version;
        header.options = options;
        header.num_containers = num_containers;
        header.record_count = record_count;
        header.size_compressed = size_compressed;
        header.size_uncompressed = size_uncompressed;
        Write_Bytes(0x00000000UL + detail::MAGIC.size(), detail::FILE_HEADER_SIZE, reinterpret_cast<char *>(&header));
    }

private:
    std::string m_file_name;
    std::size_t m_offset{0};
    std::size_t m_chunk_size{0};
    std::size_t m_compression_level{0};
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
        std::byte magic[msize + 1];

        Read_Bytes(0ul, msize, magic);
        if (memcmp(detail::MAGIC.c_str(), magic, msize))
        {
            throw std::runtime_error("Invalid file magic.");
        }
        m_offset = msize;

        Read_Bytes(m_offset, detail::FILE_HEADER_SIZE, (std::byte *)&m_header);
        printf("Containers: %u Records: %u\n", m_header.num_containers, m_header.record_count);
        printf("%u %u %.3f\n", m_header.size_uncompressed,
               m_header.size_compressed,
               float(m_header.size_uncompressed) / float(m_header.size_compressed));
        if (m_header.hdr_size != detail::FILE_HEADER_SIZE + msize)
        {
            throw std::runtime_error("File header size does not match.");
        }
        if (detail::VERSION != (m_header.version >> 8))
        {
            throw std::runtime_error("File version mismatch.");
        }

        m_offset += detail::FILE_HEADER_SIZE;
        auto container = ContainerHeaderType{};
        auto total = 0;
        for (std::size_t idx = 0; idx < m_header.num_containers; ++idx) {
            Read_Bytes(m_offset, detail::CONTAINER_SIZE, (std::byte *)&container);
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

    void Read_Bytes(std::size_t pos, std::size_t count, std::byte *buf) const
    {
        auto addr = ptr(pos);

        std::memcpy(buf, addr, count);
    }

private:
    std::string m_file_name;
    std::size_t m_offset{0};
    mio::mmap_source * m_mmap{nullptr};
    FileHeaderType m_header{0, 0, 0, 0, 0, 0, 0};
};

void some_records(XcpLogFileWriter& writer)
{
    const auto COUNT = 1024 * 10 * 5;
    auto my_frames = XcpFrames{};
    auto buffer = std::vector<std::uint8_t*>{};
    unsigned filler = 0x00;

    for (auto idx = 0; idx < COUNT; ++idx) {
        auto&& fr = RecordType{};
        fr.category = 1;
        fr.counter = idx;
        fr.timestamp = std::clock();
        fr.length = 10 + (rand() % 240);
        auto * payload = new std::uint8_t[fr.length];
        filler = (filler + 1) % 16;
        ::memset(payload, filler, fr.length);
        buffer.emplace_back(payload);
        fr.payload = payload;
        my_frames.emplace_back(std::move(fr));
    }
    std::for_each(buffer.begin(), buffer.end(), [](std::uint8_t *v) {delete[] v;});
    writer.add_frames(my_frames);
    printf("Added %u frames.\n", my_frames.size());
}


int main(int argc, char *argv[])
{
    //auto reader = XcpLogFileReader("test_logger");

    srand(42);

    auto writer = XcpLogFileWriter("test_logger");

    some_records(writer);

    printf("Finished.\n");
}

