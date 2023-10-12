
#ifndef RECORDER_UNFOLDER_HPP
#define RECORDER_UNFOLDER_HPP

#include <bit>
#include <iostream>
#include <map>
#include <variant>

#include "daqlist.hpp"
#include "mcobject.hpp"

// NOTE: C++23 has std::byteswap()
constexpr auto _bswap(std::uint64_t v) noexcept {
    return ((v & UINT64_C(0x0000'0000'0000'00FF)) << 56) | ((v & UINT64_C(0x0000'0000'0000'FF00)) << 40) |
           ((v & UINT64_C(0x0000'0000'00FF'0000)) << 24) | ((v & UINT64_C(0x0000'0000'FF00'0000)) << 8) |
           ((v & UINT64_C(0x0000'00FF'0000'0000)) >> 8) | ((v & UINT64_C(0x0000'FF00'0000'0000)) >> 24) |
           ((v & UINT64_C(0x00FF'0000'0000'0000)) >> 40) | ((v & UINT64_C(0xFF00'0000'0000'0000)) >> 56);
}

constexpr auto _bswap(std::uint32_t v) noexcept {
    return ((v & UINT32_C(0x0000'00FF)) << 24) | ((v & UINT32_C(0x0000'FF00)) << 8) | ((v & UINT32_C(0x00FF'0000)) >> 8) |
           ((v & UINT32_C(0xFF00'0000)) >> 24);
}

constexpr auto _bswap(std::uint16_t v) noexcept {
    return ((v & UINT16_C(0x00FF)) << 8) | ((v & UINT16_C(0xFF00)) >> 8);
}

using measurement_value_t        = std::variant<std::int64_t, std::uint64_t, long double, std::string>;
using measurement_value_vector_t = std::vector<measurement_value_t>;

template<typename Ty>
auto get_value(blob_t const * buf, std::uint32_t offset) -> Ty {
    return *reinterpret_cast<Ty const *>(&buf[offset]);
}

template<typename Ty>
auto get_value_swapped(blob_t const * buf, std::uint32_t offset) -> Ty {
    return _bswap(get_value<Ty>(buf, offset));
}

template<>
auto get_value<float>(blob_t const * buf, std::uint32_t offset) -> float {
    return static_cast<float>(get_value<uint32_t>(buf, offset));
}

template<>
auto get_value<double>(blob_t const * buf, std::uint32_t offset) -> double {
    return static_cast<double>(get_value<uint64_t>(buf, offset));
}

template<>
auto get_value_swapped<float>(blob_t const * buf, std::uint32_t offset) -> float {
    return static_cast<float>(get_value_swapped<uint32_t>(buf, offset));
}

template<>
auto get_value_swapped<double>(blob_t const * buf, std::uint32_t offset) -> double {
    return static_cast<double>(get_value_swapped<uint64_t>(buf, offset));
}

template<>
auto get_value<std::int16_t>(blob_t const * buf, std::uint32_t offset) -> std::int16_t {
    return static_cast<std::int16_t>(get_value<uint16_t>(buf, offset));
}

template<>
auto get_value_swapped<std::int16_t>(blob_t const * buf, std::uint32_t offset) -> std::int16_t {
    return static_cast<std::int16_t>(get_value_swapped<uint16_t>(buf, offset));
}

template<>
auto get_value<std::int32_t>(blob_t const * buf, std::uint32_t offset) -> std::int32_t {
    return static_cast<std::int32_t>(get_value<uint32_t>(buf, offset));
}

template<>
auto get_value_swapped<std::int32_t>(blob_t const * buf, std::uint32_t offset) -> std::int32_t {
    return static_cast<std::int32_t>(get_value_swapped<uint32_t>(buf, offset));
}

template<>
auto get_value<std::int64_t>(blob_t const * buf, std::uint32_t offset) -> std::int64_t {
    return static_cast<std::int64_t>(get_value<uint64_t>(buf, offset));
}

template<>
auto get_value_swapped<std::int64_t>(blob_t const * buf, std::uint32_t offset) -> std::int64_t {
    return static_cast<std::int64_t>(get_value_swapped<uint64_t>(buf, offset));
}

/*
** Get primitive datatypes, consider byte-order.
*/
struct Getter {
    Getter() = default;

    explicit Getter(bool swap, std::uint8_t id_size, std::uint8_t ts_size) : m_id_size(id_size), m_ts_size(ts_size) {
        int8  = get_value<std::int8_t>;
        uint8 = get_value<std::uint8_t>;

        if (swap) {
            int16   = get_value_swapped<std::int16_t>;
            int32   = get_value_swapped<std::int32_t>;
            int64   = get_value_swapped<std::int64_t>;
            uint16  = get_value_swapped<std::uint16_t>;
            uint32  = get_value_swapped<std::uint32_t>;
            uint64  = get_value_swapped<std::uint64_t>;
            float_  = get_value_swapped<float>;
            double_ = get_value_swapped<double>;
        } else {
            int16   = get_value<std::int16_t>;
            int32   = get_value<std::int32_t>;
            int64   = get_value<std::int64_t>;
            uint16  = get_value<std::uint16_t>;
            uint32  = get_value<std::uint32_t>;
            uint64  = get_value<std::uint64_t>;
            float_  = get_value<float>;
            double_ = get_value<double>;
        }
    }

    std::uint32_t get_timestamp(blob_t const * buf) {
        switch (m_ts_size) {
            case 0:
                return 0;
            case 1:
                return uint8(buf, m_id_size);
            case 2:
                return uint16(buf, m_id_size);
            case 4:
                return uint32(buf, m_id_size);
            default:
                throw std::runtime_error("Unsupported timestamp size: " + std::to_string(m_ts_size));
        }
    }

    measurement_value_t reader(std::uint16_t tp, blob_t const * buf, std::uint16_t offset) const {
        switch (tp) {
            case 0:
                return static_cast<std::uint64_t >(uint8(buf, offset));
            case 1:
                return int8(buf, offset);
            case 2:
                return static_cast<std::uint64_t >(uint16(buf, offset));
            case 3:
                return int16(buf, offset);
            case 4:
                return static_cast<std::uint64_t >(uint32(buf, offset));
            case 5:
                return int32(buf, offset);
            case 6:
                return uint64(buf, offset);
            case 7:
                return int64(buf, offset);
            case 8:
                return float_(buf, offset);
            case 9:
                return double_(buf, offset);
            default:
                throw std::runtime_error("Unsupported data type: " + std::to_string(tp));
        }
    }

    void set_first_pids(const std::vector<DaqList>& daq_lists, const std::vector<std::uint16_t>& first_pids) {
        m_first_pids = first_pids;

        if (m_id_size == 1) {
            // In case of 1-byte ID field (absolute ODT number) we need a mapping.

            std::uint16_t daq_list_num = 0;
            for (const auto& daq_list : daq_lists) {
                auto first_pid = m_first_pids[daq_list_num];

                for (std::uint16_t idx = first_pid; idx < daq_list.get_odt_count() + first_pid; ++idx) {
                    m_odt_to_daq_map[idx] = { daq_list_num, (idx - first_pid) };
                }
                daq_list_num++;
            }
        }
    }

    std::tuple<std::uint16_t, std::uint16_t> get_id(blob_t const * buf) {
        std::uint16_t odt_num = 0;

        switch (m_id_size) {
            case 1:
                odt_num = uint8(buf, 0);           // Get 1-byte ODT number...
                return m_odt_to_daq_map[odt_num];  // ...and return mapped values.
            case 2:
                return { uint8(buf, 1), uint8(buf, 0) };
            case 3:
                return { uint16(buf, 1), uint8(buf, 0) };
            case 4:
                return { uint16(buf, 2), uint8(buf, 0) };
            default:
                throw std::runtime_error("Unsupported ID size: " + std::to_string(m_id_size));
        }
    }

    std::uint8_t                                                           m_id_size;
    std::uint8_t                                                           m_ts_size;
    std::function<std::int8_t(blob_t const * buf, std::uint32_t offset)>   int8;
    std::function<std::uint8_t(blob_t const * buf, std::uint32_t offset)>  uint8;
    std::function<std::int16_t(blob_t const * buf, std::uint32_t offset)>  int16;
    std::function<std::int32_t(blob_t const * buf, std::uint32_t offset)>  int32;
    std::function<std::int64_t(blob_t const * buf, std::uint32_t offset)>  int64;
    std::function<std::uint16_t(blob_t const * buf, std::uint32_t offset)> uint16;
    std::function<std::uint32_t(blob_t const * buf, std::uint32_t offset)> uint32;
    std::function<std::uint64_t(blob_t const * buf, std::uint32_t offset)> uint64;
    std::function<float(blob_t const * buf, std::uint32_t offset)>         float_;
    std::function<double(blob_t const * buf, std::uint32_t offset)>        double_;
    std::vector<std::uint16_t>                                             m_first_pids;
    std::map<std::uint16_t, std::tuple<std::uint16_t, std::uint16_t>>      m_odt_to_daq_map;
};

struct UnfoldingParameters {
    UnfoldingParameters() = delete;

    explicit UnfoldingParameters(
        std::uint8_t byte_order, std::uint8_t id_field_size, bool timestamps_supported, bool ts_fixed, bool prescaler_supported,
        bool selectable_timestamps, double ts_scale_factor, std::uint8_t ts_size, std::uint16_t min_daq,
        const std::vector<DaqList>& daq_lists
    ) :
        m_byte_order(byte_order),
        m_id_field_size(id_field_size),
        m_timestamps_supported(timestamps_supported),
        m_ts_fixed(ts_fixed),
        m_prescaler_supported(prescaler_supported),
        m_selectable_timestamps(selectable_timestamps),
        m_ts_scale_factor(ts_scale_factor),
        m_ts_size(ts_size),
        m_min_daq(min_daq),
        m_daq_lists(daq_lists) {
    }

    std::uint8_t         m_byte_order;  // INTEL(LITTLE)=0, MOTOROLA(BIG)=1
    std::uint8_t         m_id_field_size;
    bool                 m_timestamps_supported;
    bool                 m_ts_fixed;
    bool                 m_prescaler_supported;
    double               m_ts_scale_factor;
    std::uint8_t         m_ts_size;
    std::uint16_t        m_min_daq;
    bool                 m_selectable_timestamps;
    std::vector<DaqList> m_daq_lists;
};

class DaqListState {
   public:

    enum class state_t : std::uint8_t {
        IDLE       = 0,
        COLLECTING = 1,
        FINISHED   = 2,
        _IGNORE    = 3,  // Duplicate frame.
        _ERROR     = 4,  // Out-of-order/missing sequence/ODT number.
    };

    DaqListState(
        std::uint16_t num_odts, std::uint16_t total_entries, bool enable_timestamps, std::uint16_t initial_offset,
        const DaqList::flatten_odts_t& flatten_odts, const Getter& getter, UnfoldingParameters params
    ) :
        m_num_odts(num_odts),
        m_total_entries(total_entries),
        m_enable_timestamps(enable_timestamps),
        m_initial_offset(initial_offset),
        m_flatten_odts(flatten_odts),
        m_getter(getter),
        m_params(params),
        m_state(state_t::IDLE) {
        m_buffer.resize(m_total_entries);
    }

    state_t check_state(uint16_t odt_num) {
        // std::cout << "\t\tDAQListState::check: " << odt_num << "/" << m_next_odt << std::endl;
        if ((m_state == state_t::IDLE) && (odt_num == 0x00)) {
            // "synch pulse".
            // std::cout << "\t\tDAQListState::check: synch pulse" << ": " << m_num_odts << std::endl;
            if (m_num_odts == 0x01) {
                // std::cout << "\t\t\tDAQListState::check: single fin" << std::endl;
                resetSM();
                return state_t::FINISHED;
            } else {
                m_state    = state_t::COLLECTING;
                m_next_odt = 1;
            }
        } else if (m_state == state_t::COLLECTING) {
            if (odt_num == m_next_odt) {
                // std::cout << "\t\tDAQListState::check: next odt" << std::endl;
                m_next_odt++;
                if (m_next_odt == m_num_odts) {
                    // std::cout << "\t\t\tDAQListState::check: final odt" << std::endl;
                    resetSM();
                    return state_t::FINISHED;
                }
            } else {
                std::cout << "\t\tDAQListState::check: out of order" << odt_num << ": " << m_next_odt << std::endl;
                resetSM();
                return state_t::_ERROR;
            }
        }
        return m_state;
    }

    void feed(uint16_t odt_num, double timestamp, const payload_t& payload) {
        auto state = check_state(odt_num);
        // std::cout << "\t\tDAQListState::feed: " << static_cast<int>(state) << std::endl;
        if (state == state_t::COLLECTING) {
            m_timestamp0 = timestamp;
            parse_Odt(odt_num, payload);
        } else if (state == state_t::FINISHED) {
            m_timestamp0 = timestamp;
            parse_Odt(odt_num, payload);
            // std::cout << "\t\tDAQListState::feed: FINISHED" << std::endl;
        }
    }

   protected:

    void resetSM() {
        m_state       = state_t::IDLE;
        m_next_odt    = 0;
        m_current_idx = 0;
        m_timestamp0  = 0.0;
        m_timestamp1  = 0.0;
    }

    void parse_Odt(uint16_t odt_num, const payload_t& payload) {
        auto offset = m_initial_offset;  // consider ID field size.
        // const auto& [category, counter, frame_timestamp, frame_length, payload] = frame;
        auto payload_data = payload.data();
        auto payload_size = payload.size();

        // auto [daq_num, odt_num] = m_getter.get_id(payload_data);
        // m_offset += m_params.m_id_field_size;
        // std::cout << "CTR: " << counter << " ID: " << daq_num << ": " << odt_num << std::endl;

        if (odt_num == 0) {
            if (m_params.m_timestamps_supported &&
                (m_params.m_ts_fixed || (m_params.m_selectable_timestamps && m_enable_timestamps == true))) {
                m_timestamp1 = static_cast<double>(m_getter.get_timestamp(payload_data)) * m_params.m_ts_scale_factor;
                offset += m_params.m_ts_size;
            } else {
                m_timestamp1 = 0.0;
            }
            std::cout << "\tSTART DAQ-LIST [" << m_timestamp0 << ", " << m_timestamp1 << std::endl;
        }

        for (const auto& param : m_flatten_odts[odt_num]) {
            const auto& [name, address, ext, size, type_index] = param;

            std::cout << "\t" << name << " " << offset << " : " << size << " ==> ";

            if (offset >= payload_size) {
                throw std::runtime_error(
                    "Offset is out of range! " + std::to_string(offset) + " >= " + std::to_string(payload_size)
                );
            }
            auto data = m_getter.reader(type_index, payload_data, offset);

            if (std::holds_alternative<std::uint64_t>(data)) {
                std::cout << std::get<std::uint64_t>(data) << " " << std::endl;
            } else if (std::holds_alternative<std::int64_t>(data)) {
                std::cout << std::get<std::int64_t>(data) << "(+/-) " << std::endl;
            } else if (std::holds_alternative<long double>(data)) {
                std::cout << std::get<long double>(data) << " (double) " << std::endl;
            }
            m_buffer[m_current_idx++] = std::move(data);
            offset += size;
        }
    }

   private:

    std::uint16_t                    m_num_odts          = 0;
    std::uint16_t                    m_total_entries     = 0;
    bool                             m_enable_timestamps = false;
    std::uint16_t                    m_initial_offset;
    std::uint16_t                    m_next_odt    = 0;
    std::uint16_t                    m_current_idx = 0;
    double                           m_timestamp0  = 0.0;
    double                           m_timestamp1  = 0.0;
    state_t                          m_state       = state_t::IDLE;
    std::vector<measurement_value_t> m_buffer;
    DaqList::flatten_odts_t          m_flatten_odts;
    Getter                           m_getter;
    UnfoldingParameters              m_params;
};

class XcpLogFileUnfolder {
   public:

    explicit XcpLogFileUnfolder(const std::string& file_name, const UnfoldingParameters& params) :
        m_reader(file_name), m_byte_order(std::endian::native), m_params(params) {
        std::endian target_byte_order;
        bool        requires_swap;

        if (m_params.m_byte_order == 0) {
            target_byte_order = std::endian::little;
        } else if (m_params.m_byte_order == 1) {
            target_byte_order = std::endian::big;
        }
        if (target_byte_order != m_byte_order) {
            requires_swap = true;
        } else {
            requires_swap = false;
        }
        m_getter = Getter(requires_swap, params.m_id_field_size, params.m_ts_size);

        auto num_daq_lists = params.m_daq_lists.size();
        m_buffers.resize(num_daq_lists);
        for (auto idx = 0; idx < num_daq_lists; ++idx) {
            m_buffers[idx].resize(params.m_daq_lists[idx].get_total_entries());
            m_state.emplace_back(DaqListState(
                params.m_daq_lists[idx].get_odt_count(), params.m_daq_lists[idx].get_total_entries(),
                m_params.m_daq_lists[idx].get_enable_timestamps(), m_params.m_id_field_size,
                m_params.m_daq_lists[idx].get_flatten_odts(), m_getter, m_params
            ));
        }
    }

    void start(const std::vector<std::uint16_t>& first_pids) {
        m_getter.set_first_pids(m_params.m_daq_lists, first_pids);
    }

    std::optional<measurement_value_vector_t> next_block() {
        std::uint16_t offset = 0;
        double        ts     = 0.0;

        while (true) {
            const auto& block = m_reader.next_block();

            if (!block) {
                break;
            }

            for (const auto& frame : block.value()) {
                if (std::get<0>(frame) != static_cast<std::uint8_t>(FrameCategory::DAQ)) {
                    continue;
                }
                unfold(frame);
            }
            return std::nullopt;
        }
        return std::nullopt;
    }

    void unfold(const FrameTuple& frame) {
        const auto& [category, counter, frame_timestamp, frame_length, payload] = frame;
        auto [daq_num, odt_num]                                                 = m_getter.get_id(payload.data());

        m_state[daq_num].feed(odt_num, frame_timestamp, payload);
    }

   private:

    XcpLogFileReader                              m_reader;
    std::endian                                   m_byte_order;
    UnfoldingParameters                           m_params;
    Getter                                        m_getter;
    std::map<std::uint16_t, std::uint16_t>        m_first_pids;
    std::vector<std::vector<measurement_value_t>> m_buffers;
    std::vector<DaqListState>                     m_state;
};

#endif  // RECORDER_UNFOLDER_HPP
