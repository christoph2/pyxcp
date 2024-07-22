
#if !defined(__DECODERS_HPP)
    #define __DECODERS_HPP

    #include "rekorder.hpp"

// template<int T>
class SequentialFileWriter {
   public:

    SequentialFileWriter(const std::string& file_name, const std::string& type_str) :
        m_file_name(file_name), m_type_code(TYPE_TO_TYPE_CODE_MAP.at(type_str)), m_opened(false) {
    #if defined(_WIN32)
        m_fd = CreateFileA(
            m_file_name.c_str(), GENERIC_WRITE, 0, (LPSECURITY_ATTRIBUTES) nullptr, CREATE_ALWAYS,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN, nullptr
        );
    #else
        m_fd = open(m_file_name.c_str(), O_CREAT | O_WRONLY | O_TRUNC, 0666);
    #endif

        m_opened = true;
    }

    ~SequentialFileWriter() {
        std::cout << "Closing " << m_file_name << std::endl;

        if (m_opened) {
    #if defined(_WIN32) || defined(_WIN64)
            if (!CloseHandle(m_fd)) {
                std::cout << error_string("CloseHandle", get_last_error());
            }
    #else
            if (close(m_fd) == -1) {
                std::cout << error_string("close", get_last_error());
            }
    #endif

            m_opened = false;
        }
    }

    void write(const measurement_value_t& variant_value) {
        std::string str_value;
        auto        type_code = m_type_code;

        std::visit(
            [&str_value, type_code](auto&& value) {
                using T = std::decay_t<decltype(value)>;
                if constexpr (std::is_same_v<T, std::monostate>) {
                } else if constexpr (std::is_same_v<T, std::uint64_t>) {
                    if (type_code == TypeCode::U8) {
                        str_value = to_binary<std::uint8_t>(value);
                    } else if (type_code == TypeCode::U16) {
                        str_value = to_binary<std::uint16_t>(value);
                    } else if (type_code == TypeCode::U32) {
                        str_value = to_binary<std::uint32_t>(value);
                    } else if (type_code == TypeCode::U64) {
                        str_value = to_binary<std::uint64_t>(value);
                    }
                } else if constexpr (std::is_same_v<T, std::int64_t>) {
                    if (type_code == TypeCode::I8) {
                        str_value = to_binary<std::int8_t>(value);
                    } else if (type_code == TypeCode::I16) {
                        str_value = to_binary<std::int16_t>(value);
                    } else if (type_code == TypeCode::I32) {
                        str_value = to_binary<std::int32_t>(value);
                    } else if (type_code == TypeCode::I64) {
                        str_value = to_binary<std::int64_t>(value);
                    }
                } else if constexpr (std::is_same_v<T, long double>) {
                    if (type_code == TypeCode::F32) {
                        str_value = to_binary<float>(value);
                    } else if (type_code == TypeCode::F64) {
                        str_value = to_binary<double>(value);
                    }
    #if HAS_FLOAT16
                    else if (type_code == TypeCode::F16) {
                        str_value = to_binary<std::float16_t>(value);
                    }
    #endif
    #if HAS_BFLOAT16
                    else if (type_code == TypeCode::BF16) {
                        str_value = to_binary<std::bfloat16_t>(value);
                    }
    #endif
                }
            },
            variant_value
        );

    #if defined(_WIN32) || defined(_WIN64)
        DWORD dwBytesWritten;

        WriteFile(m_fd, str_value.c_str(), std::size(str_value), &dwBytesWritten, nullptr);
    #else
        write(m_fd, str_value.c_str(), str_value.size());
    #endif
    }

   private:

    std::string m_file_name;
    TypeCode    m_type_code;
    bool        m_opened = false;
    #if defined(_WIN32) || defined(_WIN64)
    HANDLE m_fd;
    #else
    int m_fd;
    #endif
};

class NumpyDecoder : public XcpLogFileUnfolder {
   public:

    using writer_t = std::unique_ptr<SequentialFileWriter>;

    explicit NumpyDecoder(const std::string& file_name) : XcpLogFileUnfolder(file_name), m_path(file_name) {
        std::cout << "\n creating directory: " << m_path.stem() << std::endl;
        //        std::filesystem::create_directory(m_path.stem());
    }

    void initialize() override {
        std::cout << "initialize()" << std::endl;
        for (const auto& dl : get_daq_lists()) {
            std::vector<writer_t> dl_writers;
            // std::cout << "DAQ List: " << m_path.stem() / dl.get_name() << std::endl;
            create_dir(dl.get_name());
            for (const auto& [name, tp] : dl.get_headers()) {
                // std::cout << "\tName: " << name << " TP: " << tp << std::endl;
                const auto file_name = (m_path.stem() / dl.get_name() / name).replace_extension(".dat").string();
                dl_writers.emplace_back(std::make_unique<SequentialFileWriter>(file_name, tp));
            }
            m_writers.emplace_back(std::move(dl_writers));
        }
        std::cout << "initialized -- GO!!!" << std::endl;
    }

    void finalize() override {
        std::cout << "finalize()" << std::endl;
    }

    void on_daq_list(
        std::uint16_t daq_list_num, std::uint64_t timestamp0, std::uint64_t timestamp1,
        const std::vector<measurement_value_t>& measurement
    ) override {
        auto&         dl_writer = m_writers[daq_list_num];
        std::uint16_t count     = 0;

        for (const auto& value : measurement) {
            dl_writer[count]->write(value);
            ++count;
        }
    }

   protected:

    void create_dir(const std::string& sub_dir) const {
        std::filesystem::create_directory(m_path.stem());
        std::filesystem::create_directory(m_path.stem() / sub_dir);
    }

   private:

    std::filesystem::path              m_path;
    std::vector<std::vector<writer_t>> m_writers{};
};

#endif  // __DECODERS_HPP
