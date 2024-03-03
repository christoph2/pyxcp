
#ifndef RECORDER_WRITER_HPP
#define RECORDER_WRITER_HPP

class XcpLogFileWriter {
   public:

    explicit XcpLogFileWriter(const std::string &file_name, uint32_t prealloc = 10UL, uint32_t chunk_size = 1, std::string_view metadata="") noexcept {
        if (!file_name.ends_with(detail::FILE_EXTENSION)) {
            m_file_name = file_name + detail::FILE_EXTENSION;
        } else {
            m_file_name = file_name;
        }

#if defined(_WIN32)
        m_fd = CreateFileA(
            m_file_name.c_str(), GENERIC_READ | GENERIC_WRITE, 0, (LPSECURITY_ATTRIBUTES) nullptr, CREATE_ALWAYS,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_RANDOM_ACCESS, nullptr
        );
#else
        m_fd = open(m_file_name.c_str(), O_CREAT | O_RDWR | O_TRUNC, 0666);
#endif
        truncate(megabytes(prealloc));
        m_mmap                 = new mio::mmap_sink(m_fd);
        m_chunk_size           = megabytes(chunk_size);
        m_intermediate_storage = new blob_t[m_chunk_size + megabytes(1)];
        m_offset               = detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE;
        m_metadata             = metadata;

        if (!metadata.empty()) {
            std::cout << "XMRAW_HAS_METADATA: " << std::size(metadata) << std::endl;
            m_offset += std::size(metadata);
        }

        start_thread();
    }

    ~XcpLogFileWriter() noexcept {
        finalize();
#ifdef __APPLE__
        if (collector_thread.joinable()) {
            collector_thread.join();
        }
#endif
    }

    void finalize() {
        if (!m_finalized) {
            m_finalized = true;
            stop_thread();
            if (m_container_record_count) {
                compress_frames();
            }

            std::uint16_t options = m_metadata.empty() ? 0 : XMRAW_HAS_METADATA;

            write_header(
                detail::VERSION, options, m_num_containers, m_record_count, m_total_size_compressed, m_total_size_uncompressed
            );
            m_mmap->unmap();
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

    void add_frame(uint8_t category, uint16_t counter, double timestamp, uint16_t length, char const *data) noexcept {
        auto payload = new char[length];
        // auto payload = mem.acquire();

        _fcopy(payload, data, length);
        my_queue.put(std::make_tuple(category, counter, timestamp, length, payload));
    }

   protected:

    void truncate(off_t size) const noexcept {
#if defined(_WIN32)
        if (SetFilePointer(m_fd, size, nullptr, FILE_BEGIN) == INVALID_SET_FILE_POINTER) {
            // TODO: Errorhandling.
        }
        if (SetEndOfFile(m_fd) == 0) {
            // TODO: Errorhandling.
        }
#else
        ftruncate(m_fd, size);
#endif
    }

    blob_t *ptr(std::uint32_t pos = 0) const noexcept {
        return (blob_t *)(m_mmap->data() + pos);
    }

    template<typename T>
    void store_im(T const *data, std::uint32_t length) noexcept {
        _fcopy(
            reinterpret_cast<char *>(m_intermediate_storage + m_intermediate_storage_offset), reinterpret_cast<char const *>(data),
            length
        );
        m_intermediate_storage_offset += length;
    }

    void compress_frames() {
        auto container = ContainerHeaderType{};
        // printf("Compressing %u frames... [%d]\n", m_container_record_count, m_intermediate_storage_offset);
        const int cp_size = ::LZ4_compress_default(
            reinterpret_cast<char const *>(m_intermediate_storage),
            reinterpret_cast<char *>(ptr(m_offset + detail::CONTAINER_SIZE)), m_intermediate_storage_offset,
            LZ4_COMPRESSBOUND(m_intermediate_storage_offset)
        );
        if (cp_size < 0) {
            throw std::runtime_error("LZ4 compression failed.");
        }
        // printf("comp: %d %d [%f]\n", m_intermediate_storage_offset,  cp_size, double(m_intermediate_storage_offset) /
        // double(cp_size));
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

    void write_bytes(std::uint32_t pos, std::uint32_t count, char const *buf) const noexcept {
        auto addr = reinterpret_cast<char *>(ptr(pos));

        _fcopy(addr, buf, count);
    }

    void write_header(
        uint16_t version, uint16_t options, uint32_t num_containers, uint32_t record_count, uint32_t size_compressed,
        uint32_t size_uncompressed
    ) noexcept {
        auto header = FileHeaderType{};
        auto has_metadata =!m_metadata.empty();
        write_bytes(0x00000000UL, detail::MAGIC_SIZE, detail::MAGIC.c_str());
        header.hdr_size          = detail::FILE_HEADER_SIZE + detail::MAGIC_SIZE;
        header.version           = version;
        header.options           = options;
        header.num_containers    = num_containers;
        header.record_count      = record_count;
        header.size_compressed   = size_compressed;
        header.size_uncompressed = size_uncompressed;
        write_bytes(0x00000000UL + detail::MAGIC_SIZE, detail::FILE_HEADER_SIZE, reinterpret_cast<char const *>(&header));
        if (has_metadata) {
            //std::cout << "MD-offset:" << detail::MAGIC_SIZE + detail::FILE_HEADER_SIZE << std::endl;
            write_bytes(detail::MAGIC_SIZE + detail::FILE_HEADER_SIZE, m_metadata.size(), m_metadata.c_str());
        }
    }

    bool start_thread() noexcept {
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

    bool stop_thread() noexcept {
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
    std::uint32_t         m_offset{ 0 };
    std::uint32_t         m_chunk_size{ 0 };
    std::string           m_metadata;
    std::uint32_t         m_num_containers{ 0 };
    std::uint32_t         m_record_count{ 0UL };
    std::uint32_t         m_container_record_count{ 0UL };
    std::uint32_t         m_total_size_uncompressed{ 0UL };
    std::uint32_t         m_total_size_compressed{ 0UL };
    std::uint32_t         m_container_size_uncompressed{ 0UL };
    std::uint32_t         m_container_size_compressed{ 0UL };
    __ALIGN blob_t       *m_intermediate_storage{ nullptr };
    std::uint32_t         m_intermediate_storage_offset{ 0 };
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
