
#if !defined(__DAQ_LIST_HPP)
    #define __DAQ_LIST_HPP

    #include "bin.hpp"
    #include "helper.hpp"
    #include "mcobject.hpp"

using flatten_odts_t = std::vector<std::vector<std::tuple<std::string, std::uint32_t, std::uint8_t, std::uint16_t, std::int16_t>>>;

class Odt {
   public:
    using odt_entry_initializer_t = std::tuple<std::string, std::string>;

    Odt(const std::vector<odt_entry_initializer_t>& entries) {
        for (const auto& entry : entries) {
            const auto& [name, dt_name] = entry;
            m_entries.emplace_back(McObject(name, 0, 0, 0, dt_name));
        }
    }

    const std::vector<McObject>& get_entries() const {
        return m_entries;
    }

    std::string dumps() const {
        std::stringstream ss;
        ss << to_binary(m_entries.size());
        for (const auto& entry : m_entries) {
            ss << entry.dumps();
        }
        return ss.str();
    }

    std::string to_string() const {
        std::stringstream ss;
        ss << "Odt(entries=[";
        for (std::size_t i = 0; i < m_entries.size(); ++i) {
            ss << ::to_string(m_entries[i]);
            if (i + 1 < m_entries.size()) {
                ss << ", ";
            }
        }
        ss << "])";
        return ss.str();
    }

   private:
    std::vector<McObject> m_entries;
};

inline std::string to_string(const Odt& odt) {
    return odt.to_string();
}

class DaqListBase {
   public:
    DaqListBase(std::string_view name, std::uint16_t event_num, bool stim, bool enable_timestamps, std::uint8_t priority, std::uint8_t prescaler) :
        m_name(name),
        m_event_num(event_num),
        m_priority(priority),
        m_prescaler(prescaler),
        m_stim(stim),
        m_enable_timestamps(enable_timestamps),
        m_odt_count(0),
        m_total_entries(0),
        m_total_length(0) {
    }

    virtual ~DaqListBase() = default;

    virtual std::string dumps() const = 0;
    virtual std::string to_string() const = 0;

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
        m_header_names.clear();
        m_headers.clear();
        m_flatten_odts.clear();

        auto odt_count     = 0u;
        auto total_entries = 0u;
        auto total_length  = 0u;
        for (const auto& bin : measurements_opt) {
            odt_count++;
            std::vector<std::tuple<std::string, std::uint32_t, std::uint8_t, std::uint16_t, std::int16_t>> flatten_odt{};
            for (const auto& mc_obj : bin.get_entries()) {
                const auto& components = mc_obj.get_components();
                if (!components.empty()) {
                    for (const auto& component : components) {
                        m_header_names.emplace_back(component.get_name());
                        flatten_odt.emplace_back(
                            component.get_name(), component.get_address(), component.get_ext(), component.get_length(),
                            component.get_type_index()
                        );
                        // TYPE_MAP_REV::at may throw if key is invalid; this indicates a programming error upstream.
                        m_headers.emplace_back(component.get_name(), TYPE_MAP_REV.at(static_cast<std::uint16_t>(component.get_type_index())));
                        total_entries++;
                        total_length += component.get_length();
                    }
                } else {
                    // Treat the McObject itself as an entry when it has no components.
                    m_header_names.emplace_back(mc_obj.get_name());
                    flatten_odt.emplace_back(
                        mc_obj.get_name(), mc_obj.get_address(), mc_obj.get_ext(), mc_obj.get_length(), mc_obj.get_type_index()
                    );
                    m_headers.emplace_back(mc_obj.get_name(), TYPE_MAP_REV.at(static_cast<std::uint16_t>(mc_obj.get_type_index())));
                    total_entries++;
                    total_length += mc_obj.get_length();
                }
            }
            m_flatten_odts.emplace_back(std::move(flatten_odt));
        }
        m_odt_count     = static_cast<std::uint16_t>(odt_count);
        m_total_entries = static_cast<std::uint16_t>(total_entries);
        m_total_length  = static_cast<std::uint16_t>(total_length);
    }

   protected:
    std::string                                       m_name;
    std::uint16_t                                     m_event_num;
    std::uint8_t                                      m_priority;
    std::uint8_t                                      m_prescaler;
    bool                                              m_stim;
    bool                                              m_enable_timestamps;
    std::vector<Bin>                                  m_measurements_opt;
    std::vector<std::string>                          m_header_names;
    std::vector<std::tuple<std::string, std::string>> m_headers;
    std::uint16_t                                     m_odt_count;
    std::uint16_t                                     m_total_entries;
    std::uint16_t                                     m_total_length;
    flatten_odts_t                                    m_flatten_odts;
};

class DaqList : public DaqListBase {
   public:

    using daq_list_initialzer_t = std::tuple<std::string, std::uint32_t, std::uint16_t, std::string>;

    DaqList(
        std::string_view meas_name, std::uint16_t event_num, bool stim, bool enable_timestamps,
        const std::vector<daq_list_initialzer_t>& measurements, std::uint8_t priority=0x00, std::uint8_t prescaler=0x01
    ) :
        DaqListBase(meas_name, event_num, stim, enable_timestamps, priority, prescaler) {
        for (const auto& measurement : measurements) {
            auto const& [name, address, ext, dt_name] = measurement;
            m_measurements.emplace_back(McObject(name, address, static_cast<std::uint8_t>(ext), 0, dt_name));
        }
    }

    const std::vector<McObject>& get_measurements() const {
        return m_measurements;
    }

    std::string dumps() const override {
        std::stringstream ss;

		std::uint8_t discr=1;

        ss << to_binary(discr);
        ss << to_binary(m_name);
        ss << to_binary(m_event_num);
        ss << to_binary(m_stim);
        ss << to_binary(m_enable_timestamps);
        ss << to_binary(m_priority);
        ss << to_binary(m_prescaler);

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
        return ss.str();
    }

    std::string to_string() const override {
        std::stringstream ss;
        ss << "DaqList(";
        ss << "name='" << m_name << "', ";
        ss << "event_num=" << static_cast<std::uint16_t>(m_event_num) << ", ";
        ss << "stim=" << bool_to_string(m_stim) << ", ";
        ss << "enable_timestamps=" << bool_to_string(m_enable_timestamps) << ", ";
        ss << "priority=" << static_cast<std::uint16_t>(m_priority) << ", ";
        ss << "prescaler=" << static_cast<std::uint16_t>(m_prescaler) << ", ";
        ss << "odt_count=" << static_cast<std::uint16_t>(m_odt_count) << ", ";
        ss << "total_entries=" << static_cast<std::uint16_t>(m_total_entries) << ", ";
        ss << "total_length=" << static_cast<std::uint16_t>(m_total_length) << ", ";
        ss << "measurements=[";
        for (std::size_t i = 0; i < m_measurements.size(); ++i) {
            ss << ::to_string(m_measurements[i]);
            if (i + 1 < m_measurements.size()) ss << ", ";
        }
        ss << "], ";
        ss << "measurements_opt=[";
        for (std::size_t i = 0; i < m_measurements_opt.size(); ++i) {
            ss << ::to_string(m_measurements_opt[i]);
            if (i + 1 < m_measurements_opt.size()) ss << ", ";
        }
        ss << "], ";
        ss << "header_names=[";
        for (std::size_t i = 0; i < m_header_names.size(); ++i) {
            ss << "'" << m_header_names[i] << "'";
            if (i + 1 < m_header_names.size()) ss << ", ";
        }
        ss << "])";
        return ss.str();
    }

    static void loads(std::string_view buffer) {
    }

   private:
    std::vector<McObject> m_measurements;
};

class PredefinedDaqList : public DaqListBase {
   public:
    using odt_initializer_t = std::vector<Odt::odt_entry_initializer_t>;
    using predefined_daq_list_initializer_t = std::vector<odt_initializer_t>;

    PredefinedDaqList(
        std::string_view name, std::uint16_t event_num, bool stim, bool enable_timestamps,
        const predefined_daq_list_initializer_t& odts, std::uint8_t priority = 0x00, std::uint8_t prescaler = 0x01) :
        DaqListBase(name, event_num, stim, enable_timestamps, priority, prescaler) {
        std::vector<Bin> bins;
        bins.reserve(odts.size());
        for (const auto& odt_init : odts) {
            Bin bin(0);
            std::uint16_t total_length = 0;
            for (const auto& entry : odt_init) {
                const auto& [name, dt_name] = entry;
                // McObject will validate dt_name and set length accordingly.
                McObject obj(name, 0, 0, 0, dt_name);
                total_length = static_cast<std::uint16_t>(total_length + obj.get_length());
                bin.append(obj);
            }
            // Derive Bin size and residual capacity from sum of entry lengths.
            bin.set_size(total_length);
            bin.set_residual_capacity(total_length);
            bins.emplace_back(std::move(bin));
        }
        set_measurements_opt(bins);
    }

    std::string dumps() const override {
        std::stringstream ss;

		std::uint8_t discr=2;

        ss <<  to_binary(discr);

        ss << to_binary(m_name);
        ss << to_binary(m_event_num);
        ss << to_binary(m_stim);
        ss << to_binary(m_enable_timestamps);
        ss << to_binary(m_priority);
        ss << to_binary(m_prescaler);

        ss << to_binary(m_odt_count);
        ss << to_binary(m_total_entries);
        ss << to_binary(m_total_length);

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
        return ss.str();
    }

    std::string to_string() const override {
        std::stringstream ss;
        ss << "PredefinedDaqList(";
        ss << "name='" << m_name << "', ";
        ss << "event_num=" << static_cast<std::uint16_t>(m_event_num) << ", ";
        ss << "stim=" << bool_to_string(m_stim) << ", ";
        ss << "enable_timestamps=" << bool_to_string(m_enable_timestamps) << ", ";
        ss << "priority=" << static_cast<std::uint16_t>(m_priority) << ", ";
        ss << "prescaler=" << static_cast<std::uint16_t>(m_prescaler) << ", ";
        ss << "odt_count=" << static_cast<std::uint16_t>(m_odt_count) << ", ";
        ss << "total_entries=" << static_cast<std::uint16_t>(m_total_entries) << ", ";
        ss << "total_length=" << static_cast<std::uint16_t>(m_total_length) << ", ";
        ss << "measurements_opt=[";
        for (std::size_t i = 0; i < m_measurements_opt.size(); ++i) {
            ss << ::to_string(m_measurements_opt[i]);
            if (i + 1 < m_measurements_opt.size()) ss << ", ";
        }
        ss << "], ";
        ss << "header_names=[";
        for (std::size_t i = 0; i < m_header_names.size(); ++i) {
            ss << "'" << m_header_names[i] << "'";
            if (i + 1 < m_header_names.size()) ss << ", ";
        }
        ss << "])";
        return ss.str();
    }
};

#endif  // __DAQ_LIST_HPP
