
#ifndef RECORDER_READER_HPP
#define RECORDER_READER_HPP

#include <iostream>

class XcpLogFileReader {
   public:

    explicit XcpLogFileReader(const std::string &file_name) {
        if (!file_name.ends_with(detail::FILE_EXTENSION)) {
            m_file_name = file_name + detail::FILE_EXTENSION;
        } else {
            m_file_name = file_name;
        }

        m_mmap = new mio::mmap_source(m_file_name);
        blob_t magic[detail::MAGIC_SIZE + 1];

        read_bytes(0UL, detail::MAGIC_SIZE, magic);
        if (memcmp(detail::MAGIC.c_str(), magic, detail::MAGIC_SIZE) != 0) {
            throw std::runtime_error("Invalid file magic.");
        }
        m_offset = detail::MAGIC_SIZE;

        read_bytes(m_offset, detail::FILE_HEADER_SIZE, reinterpret_cast<blob_t *>(&m_header));
        // printf("Sizes: %u %u %.3f\n", m_header.size_uncompressed,
        //        m_header.size_compressed,
        //        float(m_header.size_uncompressed) / float(m_header.size_compressed));
        if (m_header.hdr_size != detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE) {
            throw std::runtime_error("File header size does not match.");
        }
        if (detail::VERSION != m_header.version) {
            throw std::runtime_error("File version mismatch.");
        }
#if 0
        if (m_header.num_containers < 1) {
            throw std::runtime_error("At least one container required.");
        }
#endif
        m_offset += detail::FILE_HEADER_SIZE;

        if ((m_header.options & XMRAW_HAS_METADATA) == XMRAW_HAS_METADATA) {
            std::size_t metadata_length = 0;
            std::size_t data_start      = m_offset + sizeof(std::size_t);

            read_bytes(m_offset, sizeof(std::size_t), reinterpret_cast<blob_t *>(&metadata_length));

            std::copy(ptr(data_start), ptr(data_start + metadata_length), std::back_inserter(m_metadata));
            // std::cout << "Metadata: " << m_metadata << std::endl;
            m_offset += (metadata_length + sizeof(std::size_t));
        }
    }

    [[nodiscard]] FileHeaderType get_header() const noexcept {
        return m_header;
    }

    [[nodiscard]] auto get_header_as_tuple() const noexcept -> HeaderTuple {
        auto hdr = get_header();

        return std::make_tuple(
            hdr.version, hdr.options, hdr.num_containers, hdr.record_count, hdr.size_uncompressed, hdr.size_compressed,
            (double)((std::uint64_t)(((double)hdr.size_uncompressed / (double)hdr.size_compressed * 100.0) + 0.5)) / 100.0
        );
    }

    [[nodiscard]] auto get_metadata() const noexcept {
        return m_metadata;
    }

    void reset() noexcept {
        m_current_container = 0;
        m_offset            = file_header_size();
    }

    std::optional<FrameVector> next_block() {
        auto          container = ContainerHeaderType{};
        auto          frame     = frame_header_t{};
        std::uint64_t boffs     = 0;
        auto          result    = FrameVector{};
        payload_t     payload;

        if (m_current_container >= m_header.num_containers) {
            return std::nullopt;
        }
        read_bytes(m_offset, detail::CONTAINER_SIZE, reinterpret_cast<blob_t *>(&container));
        __ALIGN auto buffer = new blob_t[container.size_uncompressed];
        m_offset += detail::CONTAINER_SIZE;
        result.reserve(container.record_count);
        const int uc_size = ::LZ4_decompress_safe(
            reinterpret_cast<char const *>(ptr(m_offset)), reinterpret_cast<char *>(buffer), container.size_compressed,
            container.size_uncompressed
        );
        if (uc_size < 0) {
            throw std::runtime_error("LZ4 decompression failed.");
        }
        boffs = 0;
        for (std::uint64_t idx = 0; idx < container.record_count; ++idx) {
            _fcopy(reinterpret_cast<char *>(&frame), reinterpret_cast<char const *>(&(buffer[boffs])), sizeof(frame_header_t));
            boffs += sizeof(frame_header_t);
            result.emplace_back(
                frame.category, frame.counter, frame.timestamp, frame.length, create_payload(frame.length, &buffer[boffs])
            );
            boffs += frame.length;
        }
        m_offset += container.size_compressed;
        m_current_container += 1;
        delete[] buffer;

        return std::optional<FrameVector>{ result };
    }

    ~XcpLogFileReader() noexcept {
        delete m_mmap;
    }

   protected:

    [[nodiscard]] blob_t const *ptr(std::uint64_t pos = 0) const {
        return reinterpret_cast<blob_t const *>(m_mmap->data() + pos);
    }

    void read_bytes(std::uint64_t pos, std::uint64_t count, blob_t *buf) const {
        auto addr = reinterpret_cast<char const *>(ptr(pos));
        _fcopy(reinterpret_cast<char *>(buf), addr, count);
    }

   private:

    std::string       m_file_name;
    std::uint64_t     m_offset{ 0 };
    std::uint64_t     m_current_container{ 0 };
    mio::mmap_source *m_mmap{ nullptr };
    FileHeaderType    m_header;
    std::string       m_metadata;
};

#endif  // RECORDER_READER_HPP
