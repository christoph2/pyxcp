

#if !defined(__DAQ_LIST_HPP)
    #define __DAQ_LIST_HPP

    #include "bin.hpp"
    #include "mcobject.hpp"

class DaqList {
   public:

    using daq_list_initialzer_t = std::tuple<std::string, std::uint32_t, std::uint16_t, std::string>;
    using flatten_odts_t =
        std::vector<std::vector<std::tuple<std::string, std::uint32_t, std::uint8_t, std::uint16_t, std::int16_t>>>;

    DaqList(std::uint16_t event_num, bool enable_timestamps, const std::vector<daq_list_initialzer_t>& measurements) :
        m_event_num(event_num), m_enable_timestamps(enable_timestamps) {
        for (const auto& measurement : measurements) {
            auto const& [name, address, ext, dt_name] = measurement;
            m_measurements.emplace_back(McObject(name, address, ext, 0, dt_name));
        }
    }

    bool get_enable_timestamps() const {
        return m_enable_timestamps;
    }

    bool get_event_num() const {
        return m_event_num;
    }

    const std::vector<McObject>& get_measurements() const {
        return m_measurements;
    }

    const std::vector<Bin>& get_measurements_opt() const {
        return m_measurements_opt;
    }

    const std::vector<std::string>& get_header_names() const {
        return m_header_names;
    }

    std::uint16_t get_odt_count() const {
        return m_odt_count;
    }

    std::uint16_t get_total_entries() const {
        return m_total_entries;
    }

    std::uint16_t get_total_length() const {
        return m_total_length;
    }

    const flatten_odts_t& get_flatten_odts() const {
        return m_flatten_odts;
    }

    void set_measurements_opt(const std::vector<Bin>& measurements_opt) {
        m_measurements_opt = measurements_opt;

        auto odt_count     = 0u;
        auto total_entries = 0u;
        auto total_length  = 0u;
        for (const auto& bin : measurements_opt) {
            odt_count++;
            std::vector<std::tuple<std::string, std::uint32_t, std::uint8_t, std::uint16_t, std::int16_t>> flatten_odt{};
            for (const auto& mc_obj : bin.get_entries()) {
                for (const auto& component : mc_obj.get_components()) {
                    m_header_names.emplace_back(component.get_name());
                    flatten_odt.emplace_back(
                        component.get_name(), component.get_address(), component.get_ext(), component.get_length(),
                        component.get_type_index()
                    );
                    total_entries++;
                    total_length += component.get_length();
                }
            }
            m_flatten_odts.emplace_back(flatten_odt);
        }
        m_odt_count     = odt_count;
        m_total_entries = total_entries;
        m_total_length  = total_length;
    }

   private:

    std::uint16_t            m_event_num;
    bool                     m_enable_timestamps;
    std::vector<McObject>    m_measurements;
    std::vector<Bin>         m_measurements_opt;
    std::vector<std::string> m_header_names;
    std::uint16_t            m_odt_count;
    std::uint16_t            m_total_entries;
    std::uint16_t            m_total_length;
    flatten_odts_t           m_flatten_odts;
};

#endif  // __DAQ_LIST_HPP
