
#if !defined(__BIN_HPP)
    #define __BIN_HPP

    #include <cstdint>
    #include <iostream>
    #include <map>
    #include <optional>
    #include <string>
    #include <vector>

    #include "mcobject.hpp"

class Bin {
   public:

    Bin(std::uint16_t size) : m_size(size), m_residual_capacity(size) {
    }

    Bin(std::uint16_t size, uint16_t residual_capacity, const std::vector<McObject>& entries) :
        m_size(size), m_residual_capacity(residual_capacity), m_entries(entries) {
    }

    void append(const McObject& bin) {
        m_entries.emplace_back(bin);
    }

    void set_entries(std::vector<McObject>&& entries) {
        m_entries = std::move(entries);
    }

    std::uint16_t get_size() const {
        return m_size;
    }

    void set_size(const std::uint16_t size) {
        m_size = size;
    }

    std::uint16_t get_residual_capacity() const {
        return m_residual_capacity;
    }

    void set_residual_capacity(const std::uint16_t residual_capacity) {
        m_residual_capacity = residual_capacity;
    }

    const std::vector<McObject>& get_entries() const {
        return m_entries;
    }

    bool operator==(const Bin& other) const {
        return (m_size == other.m_size) && (m_residual_capacity == other.m_residual_capacity) && (m_entries == other.m_entries);
    }

    std::string dumps() const {
        std::stringstream ss;

        ss << to_binary(m_size);
        ss << to_binary(m_residual_capacity);

        std::size_t entries_size = m_entries.size();
        ss << to_binary(entries_size);
        for (const auto& entry : m_entries) {
            ss << entry.dumps();
        }

        return ss.str();
    }

   private:

    std::uint16_t         m_size;
    std::uint16_t         m_residual_capacity;
    std::vector<McObject> m_entries{};
};

std::string bin_entries_to_string(const std::vector<McObject>& entries);

std::string to_string(const Bin& obj) {
    std::stringstream ss;

    ss << "Bin(residual_capacity=" << obj.get_residual_capacity() << ", entries=[" << bin_entries_to_string(obj.get_entries())
       << "])";
    return ss.str();
}

std::string bin_entries_to_string(const std::vector<McObject>& entries) {
    std::stringstream ss;

    for (const auto& entry : entries) {
        ss << to_string(entry) << ",\n ";
    }
    return ss.str();
}

    #if 0

    @property
    def __len__(self) -> int:
        return len(self.entries)
    #endif

#endif  // __BIN_HPP
