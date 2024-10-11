
#if !defined(__MC_OBJECT_HPP)
    #define __MC_OBJECT_HPP

    #include <cstdint>
    #include <map>
    #include <optional>
    #include <ranges>
    #include <string>
    #include <vector>

    #include "helper.hpp"

const std::map<const std::string, std::tuple<std::uint16_t, std::uint16_t>> TYPE_MAP = {
    { "U8",   { 0, 1 }  },
    { "I8",   { 1, 1 }  },
    { "U16",  { 2, 2 }  },
    { "I16",  { 3, 2 }  },
    { "U32",  { 4, 4 }  },
    { "I32",  { 5, 4 }  },
    { "U64",  { 6, 8 }  },
    { "I64",  { 7, 8 }  },
    { "F32",  { 8, 4 }  },
    { "F64",  { 9, 8 }  },
    #if HAS_FLOAT16
    { "F16",  { 10, 2 } },
    #endif
    #if HAS_BFLOAT16
    { "BF16", { 11, 2 } },
    #endif
};

enum class TypeCode : std::uint8_t {
    U8,
    I8,
    U16,
    I16,
    U32,
    I32,
    U64,
    I64,
    F32,
    F64,
    F16,
    BF16,
};

const std::map<const std::string, TypeCode> TYPE_TO_TYPE_CODE_MAP = {
    { "U8",   TypeCode::U8   },
    { "I8",   TypeCode::I8   },
    { "U16",  TypeCode::U16  },
    { "I16",  TypeCode::I16  },
    { "U32",  TypeCode::U32  },
    { "I32",  TypeCode::I32  },
    { "U64",  TypeCode::U64  },
    { "I64",  TypeCode::I64  },
    { "F32",  TypeCode::F32  },
    { "F64",  TypeCode::F64  },
    #if HAS_FLOAT16
    { "F16",  TypeCode::F16  },
    #endif
    #if HAS_BFLOAT16
    { "BF16", TypeCode::BF16 },
    #endif
};

const std::map<std::uint16_t, const std::string> TYPE_MAP_REV = {
    { 0,  "U8"   },
    { 1,  "I8"   },
    { 2,  "U16"  },
    { 3,  "I16"  },
    { 4,  "U32"  },
    { 5,  "I32"  },
    { 6,  "U64"  },
    { 7,  "I64"  },
    { 8,  "F32"  },
    { 9,  "F64"  },
    #if HAS_FLOAT16
    { 10, "F16"  },
    #endif
    #if HAS_BFLOAT16
    { 11, "BF16" },
    #endif
};

inline std::vector<std::string> get_data_types() {
    std::vector<std::string> result;

    for (const auto& [k, v] : TYPE_MAP) {
        result.emplace_back(k);
    }

    return result;
}

class McObject {
   public:

    explicit McObject(
        std::string_view name, std::uint32_t address, std::uint8_t ext, std::uint16_t length, const std::string& data_type,
        const std::vector<McObject>& components = std::vector<McObject>()
    ) :
        m_name(name),
        m_address(address),
        m_ext(ext),
        m_length(length),
        m_data_type(data_type),
        m_type_index(-1),
        m_components(components) {
        if (data_type != "") {
            std::string dt_toupper;

            dt_toupper.resize(data_type.size());

            std::transform(data_type.begin(), data_type.end(), dt_toupper.begin(), [](unsigned char c) -> unsigned char {
                return std::toupper(c);
            });

            if (!TYPE_MAP.contains(dt_toupper)) {
                throw std::runtime_error("Invalid data type: " + data_type);
            }

            const auto [ti, len] = TYPE_MAP.at(dt_toupper);
            m_type_index         = ti;
            m_length             = len;
        }
    }

    McObject(const McObject& obj)        = default;
    McObject(McObject&& obj)             = default;
    McObject& operator=(const McObject&) = default;
    McObject& operator=(McObject&&)      = default;

    const std::string& get_name() const {
        return m_name;
    }

    void set_name(std::string_view name) {
        m_name = name;
    }

    std::uint32_t get_address() const {
        return m_address;
    }

    void set_address(std::uint32_t address) {
        m_address = address;
    }

    std::uint8_t get_ext() const {
        return m_ext;
    }

    void set_ext(std::uint8_t ext) {
        m_ext = ext;
    }

    const std::string& get_data_type() const {
        return m_data_type;
    }

    void set_data_type(const std::string& value) {
        m_data_type = value;
    }

    std::uint16_t get_length() const {
        return m_length;
    }

    void set_length(std::uint16_t length) {
        m_length = length;
    }

    std::int32_t get_type_index() const {
        return m_type_index;
    }

    const std::vector<McObject>& get_components() const {
        return m_components;
    }

    void add_component(const McObject& obj) {
        m_components.emplace_back(obj);
    }

    bool operator==(const McObject& other) const {
        return (m_name == other.m_name) && (m_address == other.m_address) && (m_ext == other.m_ext) &&
               (m_length == other.m_length) && (m_data_type == other.m_data_type) &&
               (std::equal(m_components.begin(), m_components.end(), other.m_components.begin(), other.m_components.end()));
    }

    std::string dumps() const noexcept {
        std::stringstream ss;

        ss << to_binary(m_name);
        ss << to_binary(m_address);
        ss << to_binary(m_ext);
        ss << to_binary(m_length);
        ss << to_binary(m_data_type);
        ss << to_binary(m_type_index);

        std::size_t ccount = m_components.size();
        ss << to_binary(ccount);
        for (const auto& obj : m_components) {
            ss << obj.dumps();
        }
        return ss.str();
    }

    auto get_hash() const noexcept {
        std::hash<std::string> hash_fn;
        return hash_fn(dumps());
    }

   private:

    std::string           m_name;
    std::uint32_t         m_address;
    std::uint8_t          m_ext;
    std::uint16_t         m_length;
    std::string           m_data_type;
    std::int16_t          m_type_index;
    std::vector<McObject> m_components{};
};

std::string mc_components_to_string(const std::vector<McObject>& components);

std::string to_string(const McObject& obj) {
    std::stringstream ss;

    ss << "McObject(name='" << obj.get_name() << "', address=" << obj.get_address()
       << ", ext=" << static_cast<std::uint16_t >(obj.get_ext()) << ", data_type='" << obj.get_data_type()
       << "', length=" << obj.get_length() << ", components=[" << mc_components_to_string(obj.get_components()) << "])";
    return ss.str();
}

std::string mc_components_to_string(const std::vector<McObject>& components) {
    std::stringstream ss;

    for (const auto& obj : components) {
        ss << to_string(obj) << ",\n ";
    }
    return ss.str();
}

#endif  // __MC_OBJECT_HPP
