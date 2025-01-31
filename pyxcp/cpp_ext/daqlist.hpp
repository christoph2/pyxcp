
#if !defined(__DAQ_LIST_HPP)
    #define __DAQ_LIST_HPP

    #include "bin.hpp"
    #include "helper.hpp"
    #include "mcobject.hpp"

using flatten_odts_t = std::vector<std::vector<std::tuple<std::string, std::uint32_t, std::uint8_t, std::uint16_t, std::int16_t>>>;

class DaqList {
   public:

    using daq_list_initialzer_t = std::tuple<std::string, std::uint32_t, std::uint16_t, std::string>;

    DaqList(
        std::string_view meas_name, std::uint16_t event_num, bool stim, bool enable_timestamps,
        const std::vector<daq_list_initialzer_t>& measurements, std::uint8_t priority=0x00, std::uint8_t prescaler=0x01
    ) :
        m_name(meas_name), m_event_num(event_num), m_priority(priority), m_prescaler(prescaler), m_stim(stim), m_enable_timestamps(enable_timestamps) {
        for (const auto& measurement : measurements) {
            auto const& [name, address, ext, dt_name] = measurement;
            m_measurements.emplace_back(McObject(name, address, static_cast<std::uint8_t>(ext), 0, dt_name));
        }
    }

    bool get_enable_timestamps() const {
        return m_enable_timestamps;
    }

    const std::string& get_name() const {
        return m_name;
    }

    std::uint16_t get_event_num() const {
        return m_event_num;
    }

    std::uint8_t get_priority() const {
        return m_priority;
    }

    std::uint8_t get_prescaler() const {
        return m_prescaler;
    }

    void set_event_num(std::uint16_t event_num) {
        m_event_num = event_num;
    }

    bool get_stim() const {
        return m_stim;
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

    const std::vector<std::tuple<std::string, std::string>>& get_headers() const noexcept {
        return m_headers;
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
                    m_headers.emplace_back(component.get_name(), TYPE_MAP_REV.at(component.get_type_index()));
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

    std::string dumps() const {
        std::stringstream ss;

        ss << to_binary(m_name);
        ss << to_binary(m_event_num);
        ss << to_binary(m_stim);
        ss << to_binary(m_enable_timestamps);

        ss << to_binary(m_odt_count);
        ss << to_binary(m_total_entries);
        ss << to_binary(m_total_length);

        std::size_t meas_size = m_measurements.size();
        ss << to_binary(meas_size);
        for (const auto& mc_obj : m_measurements) {
            ss << mc_obj.dumps();
        }
        std::size_t meas_opt_size = m_measurements_opt.size();
        ss << to_binary(meas_opt_size);
        for (const auto& mc_obj : m_measurements_opt) {
            ss << mc_obj.dumps();
        }
        std::size_t hname_size = m_header_names.size();
        ss << to_binary(hname_size);
        for (const auto& hdr_obj : m_header_names) {
            ss << to_binary(hdr_obj);
        }
        /////
        std::size_t odt_size = m_flatten_odts.size();
        ss << to_binary(odt_size);
        for (const auto& odt : m_flatten_odts) {
            ss << to_binary(odt.size());
            for (const auto& odt_entry : odt) {
                const auto& [name, address, ext, size, type_index] = odt_entry;
                ss << to_binary(name);
                ss << to_binary(address);
                ss << to_binary(ext);
                ss << to_binary(size);
                ss << to_binary(type_index);
            }
        }
        return ss.str();
    }

    std::string to_string() const {
        std::stringstream ss;

        ss << "DaqList(";
        ss << "name=\"" << m_name << "\", ";
        ss << "event_num=" << static_cast<std::uint16_t>(m_event_num) << ", ";
        ss << "stim=" << bool_to_string(m_stim) << ", ";
        ss << "enable_timestamps" << bool_to_string(m_enable_timestamps) << ", ";
        ss << "measurements=[\n";
        for (const auto& meas : m_measurements) {
            ss << ::to_string(meas) << ",\n";
        }
        ss << "],\n";
        ss << "measurements_opt=[\n";
        for (const auto& meas : m_measurements_opt) {
            ss << ::to_string(meas) << ",\n";
        }
        ss << "],\n";
        ss << "header_names=[\n";
        for (const auto& header : m_header_names) {
            ss << "\"" << header << "\",";
        }
        ss << "\n]";
        ss << ")";
        return ss.str();
    }

    static void loads(std::string_view buffer) {
    }

   private:

    std::string                                       m_name;
    std::uint16_t                                     m_event_num;
    std::uint8_t                                      m_priority;
    std::uint8_t                                      m_prescaler;
    bool                                              m_stim;
    bool                                              m_enable_timestamps;
    std::vector<McObject>                             m_measurements;
    std::vector<Bin>                                  m_measurements_opt;
    std::vector<std::string>                          m_header_names;
    std::vector<std::tuple<std::string, std::string>> m_headers;
    std::uint16_t                                     m_odt_count;
    std::uint16_t                                     m_total_entries;
    std::uint16_t                                     m_total_length;
    flatten_odts_t                                    m_flatten_odts;
};

#endif  // __DAQ_LIST_HPP
