
#ifndef RECORDER_WRITER_HPP
#define RECORDER_WRITER_HPP

constexpr std::uint64_t MASK32 = (1ULL << 32) - 1;

class XcpLogFileWriter {
   public:

    explicit XcpLogFileWriter(
        const std::string &file_name, uint32_t prealloc = 10UL, uint32_t chunk_size = 1, std::string_view metadata = ""
    ) {
        if (!file_name.ends_with(detail::FILE_EXTENSION)) {
            m_file_name = file_name + detail::FILE_EXTENSION;
        } else {
            m_file_name = file_name;
        }
        m_opened = false;

#if defined(_WIN32)
        m_fd = CreateFileA(
            m_file_name.c_str(), GENERIC_READ | GENERIC_WRITE, 0, (LPSECURITY_ATTRIBUTES) nullptr, CREATE_ALWAYS,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_RANDOM_ACCESS, nullptr
        );
        if (m_fd == INVALID_HANDLE_VALUE) {
            throw std::runtime_error(error_string("XcpLogFileWriter::CreateFileA", get_last_error()));
        } else {
            m_opened = true;
        }
#else
        m_fd = open(m_file_name.c_str(), O_CREAT | O_RDWR | O_TRUNC, 0666);
        if (m_fd == -1) {
            throw std::runtime_error(error_string("XcpLogFileWriter::open", get_last_error()));
        } else {
            m_opened = true;
        }
#endif
        m_hard_limit = megabytes(prealloc);
        resize(m_hard_limit);
        m_mmap                 = new mio::mmap_sink(m_fd);
        m_chunk_size           = 512 * 1024;  // megabytes(chunk_size);
        m_intermediate_storage = new blob_t[m_chunk_size + megabytes(1)];
        m_offset               = detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE;
        m_metadata             = metadata;

        if (!metadata.empty()) {
            m_offset += std::size(metadata);
            write_metadata();
        }
        start_thread();
    }

    ~XcpLogFileWriter() {
        finalize();
#ifdef __APPLE__
        if (collector_thread.joinable()) {
            collector_thread.join();
        }
#endif
    }

    void finalize() {
        std::error_code ec;
        if (!m_finalized) {
            m_finalized = true;
            stop_thread();

            if (!m_opened) {
                return;
            }

            if (m_container_record_count) {
                compress_frames();
            }

            std::uint16_t options = m_metadata.empty() ? 0 : XMRAW_HAS_METADATA;

            write_header(
                detail::VERSION, options, m_num_containers, m_record_count, m_total_size_compressed, m_total_size_uncompressed
            );
            m_mmap->unmap();
            ec = mio::detail::last_error();
            if (ec.value() != 0) {
                throw std::runtime_error(error_string("XcpLogFileWriter::mio::unmap", ec));
            }

            resize(m_offset);
#if defined(_WIN32)
            if (!CloseHandle(m_fd)) {
                throw std::runtime_error(error_string("XcpLogFileWriter::CloseHandle", get_last_error()));
            }
#else
            if (close(m_fd) == -1) {
                throw std::runtime_error(error_string("XcpLogFileWriter::close", get_last_error()));
            }
#endif
            delete m_mmap;
            delete[] m_intermediate_storage;
        }
    }

    void add_frame(uint8_t category, uint16_t counter, std::uint64_t timestamp, uint16_t length, char const *data) {
        auto payload = new char[length];

        _fcopy(payload, data, length);
        my_queue.put(std::make_tuple(category, counter, timestamp, length, payload));
    }

   protected:

    void resize(std::uint64_t size, bool remap = false) {
        std::error_code ec;

        if (remap) {
            m_mmap->unmap();
            ec = mio::detail::last_error();
            if (ec.value() != 0) {
                throw std::runtime_error(error_string("XcpLogFileWriter::mio::unmap", ec));
            }
        }

#if defined(_WIN32)
        LONG low_part  = (MASK32 & size);
        LONG high_part = size >> 32;

        if (SetFilePointer(m_fd, low_part, &high_part, FILE_BEGIN) == INVALID_SET_FILE_POINTER) {
            auto err = get_last_error();

            if (err.value() != NO_ERROR) {
                throw std::runtime_error(error_string("XcpLogFileWriter::SetFilePointer", err));
            }
        }
        if (SetEndOfFile(m_fd) == 0) {
            throw std::runtime_error(error_string("XcpLogFileWriter::SetEndOfFile", get_last_error()));
        }
#else
        if (ftruncate(m_fd, size) == -1) {
            throw std::runtime_error(error_string("XcpLogFileWriter::ftruncate", get_last_error()));
        }
#endif
        if (remap) {
            m_mmap->map(m_fd, 0, size, ec);
            if (ec.value() != 0) {
                throw std::runtime_error(error_string("XcpLogFileWriter::mio::map", ec));
            }
        }
    }

    blob_t *ptr(std::uint64_t pos = 0) const {
        return (blob_t *)(m_mmap->data() + pos);
    }

    template<typename T>
    void store_im(T const *data, std::uint32_t length) {
        _fcopy(
            reinterpret_cast<char *>(m_intermediate_storage + m_intermediate_storage_offset), reinterpret_cast<char const *>(data),
            length
        );
        m_intermediate_storage_offset += length;
    }

    void compress_frames() {
        auto container = ContainerHeaderType{};
        // printf("Compressing %u frames... [%d]\n", m_container_record_count, m_intermediate_storage_offset);
        const int cp_size = ::LZ4_compress_HC(
            reinterpret_cast<char const *>(m_intermediate_storage),
            reinterpret_cast<char *>(ptr(m_offset + detail::CONTAINER_SIZE)), m_intermediate_storage_offset,
            LZ4_COMPRESSBOUND(m_intermediate_storage_offset), LZ4HC_CLEVEL_MAX
        );

        if (cp_size < 0) {
            throw std::runtime_error("XcpLogFileWriter - LZ4 compression failed.");
        }

        if (m_offset > (m_hard_limit >> 1)) {
            std::cout << "[INFO] " << current_timestamp() << ": Doubling measurement file size." << std::endl;
            m_hard_limit <<= 1;
            resize(m_hard_limit, true);
            write_header(
                detail::VERSION, m_metadata.empty() ? 0 : XMRAW_HAS_METADATA, m_num_containers, m_record_count,
                m_total_size_compressed, m_total_size_uncompressed
            );
        }
        container.record_count      = m_container_record_count;
        container.size_compressed   = cp_size;
        container.size_uncompressed = m_container_size_uncompressed;

        _fcopy(reinterpret_cast<char *>(ptr(m_offset)), reinterpret_cast<char const *>(&container), detail::CONTAINER_SIZE);

        m_offset += (detail::CONTAINER_SIZE + cp_size);
        m_total_size_uncompressed += m_container_size_uncompressed;
        m_total_size_compressed += cp_size;
        m_record_count += m_container_record_count;
        m_container_size_uncompressed = 0;
        m_container_size_compressed   = 0;
        m_container_record_count      = 0;
        m_intermediate_storage_offset = 0;
        m_num_containers += 1;
    }

    void write_bytes(std::uint64_t pos, std::uint64_t count, char const *buf) const {
        auto addr = reinterpret_cast<char *>(ptr(pos));

        _fcopy(addr, buf, count);
    }

    void write_header(
        std::uint16_t version, std::uint16_t options, std::uint64_t num_containers, std::uint64_t record_count,
        std::uint64_t size_compressed, std::uint64_t size_uncompressed
    ) {
        auto header = FileHeaderType{};
        write_bytes(0x00000000UL, detail::MAGIC_SIZE, detail::MAGIC.c_str());
        header.hdr_size          = detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE;
        header.version           = version;
        header.options           = options;
        header.num_containers    = num_containers;
        header.record_count      = record_count;
        header.size_compressed   = size_compressed;
        header.size_uncompressed = size_uncompressed;
        write_bytes(0x00000000UL + detail::MAGIC_SIZE, detail::FILE_HEADER_SIZE, reinterpret_cast<char const *>(&header));
    }

    void write_metadata() {
        if (!m_metadata.empty()) {
            write_bytes(detail::MAGIC_SIZE + detail::FILE_HEADER_SIZE, m_metadata.size(), m_metadata.c_str());
        }
    }

    bool start_thread() {
        if (collector_thread.joinable()) {
            return false;
        }
        stop_collector_thread_flag = false;
#ifdef __APPLE__
        collector_thread = std::thread([this]() {
#else
        collector_thread = std::jthread([this]() {
#endif
            while (!stop_collector_thread_flag) {
                auto       item    = my_queue.get();
                const auto content = item.get();
                if (stop_collector_thread_flag == true) {
                    break;
                }
                const auto [category, counter, timestamp, length, payload] = *content;
                const frame_header_t frame{ category, counter, timestamp, length };
                store_im(&frame, sizeof(frame));
                store_im(payload, length);
                delete[] payload;
                m_container_record_count += 1;
                m_container_size_uncompressed += (sizeof(frame) + length);
                if (m_container_size_uncompressed > m_chunk_size) {
                    compress_frames();
                }
            }
        });

        return true;
    }

    bool stop_thread() {
        if (!collector_thread.joinable()) {
            return false;
        }
        stop_collector_thread_flag = true;
        my_queue.put(FrameTupleWriter{});  // Put something into the queue, otherwise the thread will hang forever.
        collector_thread.join();
        return true;
    }

   private:

    std::string           m_file_name;
    std::uint64_t         m_offset{ 0 };
    std::uint32_t         m_chunk_size{ 0 };
    std::string           m_metadata;
    bool                  m_opened{ false };
    std::uint64_t         m_num_containers{ 0 };
    std::uint64_t         m_record_count{ 0UL };
    std::uint32_t         m_container_record_count{ 0UL };
    std::uint64_t         m_total_size_uncompressed{ 0UL };
    std::uint64_t         m_total_size_compressed{ 0UL };
    std::uint32_t         m_container_size_uncompressed{ 0UL };
    std::uint32_t         m_container_size_compressed{ 0UL };
    __ALIGN blob_t       *m_intermediate_storage{ nullptr };
    std::uint32_t         m_intermediate_storage_offset{ 0 };
    std::uint64_t         m_hard_limit{ 0 };
    mio::file_handle_type m_fd{ INVALID_HANDLE_VALUE };
    mio::mmap_sink       *m_mmap{ nullptr };
    bool                  m_finalized{ false };
#ifdef __APPLE__
    std::thread collector_thread{};
#else
    std::jthread collector_thread{};
#endif
    std::mutex                             mtx;
    TsQueue<FrameTupleWriter>              my_queue;
    BlockMemory<char, XCP_PAYLOAD_MAX, 16> mem{};
    std::atomic_bool                       stop_collector_thread_flag{ false };
};

#endif  // RECORDER_WRITER_HPP
