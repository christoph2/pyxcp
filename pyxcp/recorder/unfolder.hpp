
#ifndef RECORDER_UNFOLDER_HPP
#define RECORDER_UNFOLDER_HPP

#include <bit>
#include <charconv>
#include <iostream>
#include <map>
#include <variant>

#include <cstring>

#include "daqlist.hpp"
#include "helper.hpp"
#include "mcobject.hpp"
#include "writer.hpp"

using measurement_value_t = std::variant<std::int64_t, std::uint64_t, long double, std::string>;
using measurement_tuple_t = std::tuple<std::uint16_t, double, double, std::vector<measurement_value_t>>;
using measurement_callback_t = std::function<void(std::uint16_t, double, double, std::vector<measurement_value_t>)>;

template<typename Ty>
auto get_value(blob_t const * buf, std::uint32_t offset) -> Ty {
    return *reinterpret_cast<Ty const *>(&buf[offset]);
}

template<typename Ty>
auto get_value_swapped(blob_t const * buf, std::uint32_t offset) -> Ty {
    return _bswap(get_value<Ty>(buf, offset));
}

#if HAS_FLOAT16==1
template<>
auto get_value<std::float16_t>(blob_t const * buf, std::uint32_t offset) -> std::float16_t {
    auto tmp = get_value<std::uint16_t>(buf, offset);

    return *(reinterpret_cast<std::float16_t*>(&tmp));
}
#endif

#if HAS_BFLOAT16==1
template<>
auto get_value<std::bfloat16_t>(blob_t const * buf, std::uint32_t offset) -> std::bfloat16_t {
    auto tmp = get_value<std::uint16_t>(buf, offset);

    return *(reinterpret_cast<std::bfloat16_t*>(&tmp));
}
#endif


template<>
auto get_value<float>(blob_t const * buf, std::uint32_t offset) -> float {
    auto tmp = get_value<std::uint32_t>(buf, offset);

    return *(reinterpret_cast<float*>(&tmp));
}

template<>
auto get_value<double>(blob_t const * buf, std::uint32_t offset) -> double {
    auto tmp = get_value<std::uint64_t>(buf, offset);

    return *(reinterpret_cast<double*>(&tmp));
}

#if HAS_FLOAT16==1
template<>
auto get_value_swapped<std::float16_t>(blob_t const * buf, std::uint32_t offset) -> std::float16_t {
    auto tmp = get_value_swapped<std::uint16_t>(buf, offset);

    return *(reinterpret_cast<std::float16_t*>(&tmp));
}
#endif

#if HAS_BFLOAT16==1
template<>
auto get_value_swapped<std::bfloat16_t>(blob_t const * buf, std::uint32_t offset) -> std::bfloat16_t {
    auto tmp = get_value_swapped<std::uint16_t>(buf, offset);

    return *(reinterpret_cast<std::bfloat16_t*>(&tmp));
}
#endif


template<>
auto get_value_swapped<float>(blob_t const * buf, std::uint32_t offset) -> float {
    auto tmp = get_value_swapped<std::uint32_t>(buf, offset);

    return *(reinterpret_cast<float*>(&tmp));
}

template<>
auto get_value_swapped<double>(blob_t const * buf, std::uint32_t offset) -> double {
    auto tmp = get_value_swapped<std::uint64_t>(buf, offset);

    return *(reinterpret_cast<double*>(&tmp));
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


/////////////////////////////////////////////////////
/////////////////////////////////////////////////////
template<typename Ty>
void set_value(blob_t * buf, std::uint32_t offset, Ty value) {
    ::memcpy(&buf[offset], &value, sizeof(Ty));
}

template<typename Ty>
void set_value_swapped(blob_t * buf, std::uint32_t offset, Ty value) {
    set_value<Ty>(buf, offset, _bswap(value));
}

template<>
void set_value<std::int8_t>(blob_t * buf, std::uint32_t offset, std::int8_t value) {
    buf[offset] = static_cast<blob_t>(value);
}

template<>
void set_value<std::uint8_t>(blob_t * buf, std::uint32_t offset, std::uint8_t value) {
    buf[offset] = static_cast<blob_t>(value);
}

template<>
void set_value<std::int16_t>(blob_t * buf, std::uint32_t offset, std::int16_t value) {
    set_value<std::uint16_t>(buf, offset, static_cast<std::uint16_t>(value));
}

template<>
void set_value_swapped<std::int16_t>(blob_t * buf, std::uint32_t offset, std::int16_t value) {
    set_value_swapped<std::uint16_t>(buf, offset, static_cast<std::uint16_t>(value));
}

template<>
void set_value<std::int32_t>(blob_t * buf, std::uint32_t offset, std::int32_t value) {
    set_value<std::uint32_t>(buf, offset, static_cast<std::uint32_t>(value));
}

template<>
void set_value_swapped<std::int32_t>(blob_t * buf, std::uint32_t offset, std::int32_t value) {
    set_value_swapped<std::uint32_t>(buf, offset, static_cast<std::uint32_t>(value));
}

template<>
void set_value<std::int64_t>(blob_t * buf, std::uint32_t offset, std::int64_t value) {
    set_value<std::uint64_t>(buf, offset, static_cast<std::uint64_t>(value));
}

template<>
void set_value_swapped<std::int64_t>(blob_t * buf, std::uint32_t offset, std::int64_t value) {
    set_value_swapped<std::uint64_t>(buf, offset, static_cast<std::uint64_t>(value));
}

#if HAS_FLOAT16==1
template<>
void set_value<std::float16_t>(blob_t * buf, std::uint32_t offset, std::float16_t value) {
    set_value<std::uint16_t>(buf, offset, *reinterpret_cast<std::uint16_t*>(&value));
}

template<>
void set_value_swapped<std::float16_t>(blob_t * buf, std::uint32_t offset, std::float16_t value) {
    set_value_swapped<std::uint16_t>(buf, offset, *reinterpret_cast<std::uint16_t*>(&value));
}
#endif

#if HAS_BFLOAT16==1
template<>
void set_value<std::bfloat16_t>(blob_t * buf, std::uint32_t offset, std::bfloat16_t value) {
    set_value<std::uint16_t>(buf, offset, *reinterpret_cast<std::uint16_t*>(&value));
}

template<>
void set_value_swapped<std::bfloat16_t>(blob_t * buf, std::uint32_t offset, std::bfloat16_t value) {
    set_value_swapped<std::uint16_t>(buf, offset, *reinterpret_cast<std::uint16_t*>(&value));
}
#endif

template<>
void set_value<float>(blob_t * buf, std::uint32_t offset, float value) {
    set_value<std::uint32_t>(buf, offset, *reinterpret_cast<std::uint32_t*>(&value));
}

template<>
void set_value_swapped<float>(blob_t * buf, std::uint32_t offset, float value) {
    set_value_swapped<std::uint32_t>(buf, offset, *reinterpret_cast<std::uint32_t*>(&value));
}

template<>
void set_value<double>(blob_t * buf, std::uint32_t offset, double value) {
    set_value<std::uint64_t>(buf, offset, *reinterpret_cast<std::uint64_t*>(&value));
}

template<>
void set_value_swapped<double>(blob_t * buf, std::uint32_t offset, double value) {
    set_value_swapped<std::uint64_t>(buf, offset, *reinterpret_cast<std::uint64_t*>(&value));
}


/*
** Get primitive datatypes, consider byte-order.
*/
struct Getter {
    Getter() = default;

    explicit Getter(bool requires_swap, std::uint8_t id_size, std::uint8_t ts_size) : m_id_size(id_size), m_ts_size(ts_size) {
        int8  = get_value<std::int8_t>;
        uint8 = get_value<std::uint8_t>;

        if (requires_swap) {
            int16   = get_value_swapped<std::int16_t>;
            int32   = get_value_swapped<std::int32_t>;
            int64   = get_value_swapped<std::int64_t>;
            uint16  = get_value_swapped<std::uint16_t>;
            uint32  = get_value_swapped<std::uint32_t>;
            uint64  = get_value_swapped<std::uint64_t>;
            float_  = get_value_swapped<float>;
            double_ = get_value_swapped<double>;
#if HAS_FLOAT16==1
            float16  = get_value_swapped<std::float16_t>;
#endif
#if HAS_BFLOAT16==1
            bfloat16  = get_value_swapped<std::bfloat16_t>;
#endif
        } else {
            int16   = get_value<std::int16_t>;
            int32   = get_value<std::int32_t>;
            int64   = get_value<std::int64_t>;
            uint16  = get_value<std::uint16_t>;
            uint32  = get_value<std::uint32_t>;
            uint64  = get_value<std::uint64_t>;
            float_  = get_value<float>;
            double_ = get_value<double>;
#if HAS_FLOAT16==1
            float16  = get_value<std::float16_t>;
#endif
#if HAS_BFLOAT16==1
            bfloat16  = get_value<std::bfloat16_t>;
#endif
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
#if HAS_FLOAT16==1
            case 10:
                return float16(buf, offset);
#endif
#if HAS_BFLOAT16==1
            case 11:
                return bfloat16(buf, offset);
#endif
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
#if HAS_FLOAT16==1
    std::function<std::float16_t(blob_t const * buf, std::uint32_t offset)>     float16;
#endif
#if HAS_BFLOAT16==1
    std::function<std::bfloat16_t(blob_t const * buf, std::uint32_t offset)>    bfloat16;
#endif
    std::vector<std::uint16_t>                                             m_first_pids;
    std::map<std::uint16_t, std::tuple<std::uint16_t, std::uint16_t>>      m_odt_to_daq_map;
};

//////////////////////////////////////////////////////////////////////////////////////////////
struct Setter {
    Setter() = default;

    explicit Setter(bool requires_swap, std::uint8_t id_size, std::uint8_t ts_size) : m_id_size(id_size), m_ts_size(ts_size) {
        int8  = set_value<std::int8_t>;
        uint8 = set_value<std::uint8_t>;

        if (requires_swap) {
            int16   = set_value_swapped<std::int16_t>;
            int32   = set_value_swapped<std::int32_t>;
            int64   = set_value_swapped<std::int64_t>;
            uint16  = set_value_swapped<std::uint16_t>;
            uint32  = set_value_swapped<std::uint32_t>;
            uint64  = set_value_swapped<std::uint64_t>;
            float_  = set_value_swapped<float>;
            double_ = set_value_swapped<double>;
#if HAS_FLOAT16==1
            float16  = set_value_swapped<std::float16_t>;
#endif
#if HAS_BFLOAT16==1
            bfloat16  = set_value_swapped<std::bfloat16_t>;
#endif
        } else {
            int16   = set_value<std::int16_t>;
            int32   = set_value<std::int32_t>;
            int64   = set_value<std::int64_t>;
            uint16  = set_value<std::uint16_t>;
            uint32  = set_value<std::uint32_t>;
            uint64  = set_value<std::uint64_t>;
            float_  = set_value<float>;
            double_ = set_value<double>;
#if HAS_FLOAT16==1
            float16  = set_value<std::float16_t>;
#endif
#if HAS_BFLOAT16==1
            bfloat16  = set_value<std::bfloat16_t>;
#endif
        }
    }

    void set_timestamp(blob_t * buf, std::uint32_t timestamp) {
        switch (m_ts_size) {
            case 0:
                break;
            case 1:
                uint8(buf, m_id_size, timestamp);
                break;
            case 2:
                uint16(buf, m_id_size, timestamp);
                break;
            case 4:
                uint32(buf, m_id_size, timestamp);
                break;
            default:
                throw std::runtime_error("Unsupported timestamp size: " + std::to_string(m_ts_size));
        }
    }

    void writer(std::uint16_t tp, blob_t * buf, std::uint16_t offset, const measurement_value_t& value) {
        switch (tp) {
            case 0:
                uint8(buf, offset, static_cast<std::uint8_t>(std::get<std::uint64_t>(value)));
                break;
            case 1:
                int8(buf, offset, static_cast<std::int8_t>(std::get<std::int64_t>(value)));
                break;
            case 2:
                uint16(buf, offset, static_cast<std::uint16_t>(std::get<std::uint64_t>(value)));
                break;
            case 3:
                int16(buf, offset, static_cast<std::int16_t>(std::get<std::int64_t>(value)));
                break;
            case 4:
                uint32(buf, offset, static_cast<std::uint32_t>(std::get<std::uint64_t>(value)));
                break;
            case 5:
                int32(buf, offset, static_cast<std::int32_t>(std::get<std::int64_t>(value)));
                break;
            case 6:
                uint64(buf, offset, std::get<std::uint64_t>(value));
                break;
            case 7:
                int64(buf, offset, std::get<std::int64_t>(value));
                break;
            case 8:
                float_(buf, offset, static_cast<float>(std::get<long double>(value)));
                break;
            case 9:
                double_(buf, offset, static_cast<double>(std::get<long double>(value)));
                break;
#if HAS_FLOAT16==1
            case 10:
                float16(buf, offset, static_cast<std::float16_t>(std::get<long double>(value)));
                break;
#endif
#if HAS_BFLOAT16==1
            case 11:
                bfloat16(buf, offset, static_cast<std::bfloat16_t>(std::get<long double>(value)));
                break;
#endif
            default:
                throw std::runtime_error("Unsupported data type: " + std::to_string(tp));
        }
    }

#if 0
    void set_first_pids(const std::vector<DaqList>& daq_lists, const std::vector<std::uint16_t>& first_pids) {
        m_first_pids = first_pids;

        if (m_id_size == 1) {
            // In case of 1-byte ID field (absolute ODT number) we need a mapping.
            std::uint16_t daq_list_num = 0;
            for (const auto& daq_list : daq_lists) {
                auto first_pid = m_first_pids[daq_list_num];

                for (std::uint16_t idx = first_pid; idx < daq_list.set_odt_count() + first_pid; ++idx) {
                    m_odt_to_daq_map[idx] = { daq_list_num, (idx - first_pid) };
                }
                daq_list_num++;
            }
        }
    }
#endif

#if 0
    std::tuple<std::uint16_t, std::uint16_t> set_id(blob_t const * buf) {
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
#endif
    std::uint8_t                                                           m_id_size;
    std::uint8_t                                                           m_ts_size;
    std::function<void(blob_t * buf, std::uint32_t offset, std::int8_t)>   int8;
    std::function<void(blob_t * buf, std::uint32_t offset, std::uint8_t)>  uint8;
    std::function<void(blob_t * buf, std::uint32_t offset, std::int16_t)>  int16;
    std::function<void(blob_t * buf, std::uint32_t offset, std::int32_t)>  int32;
    std::function<void(blob_t * buf, std::uint32_t offset, std::int64_t)>  int64;
    std::function<void(blob_t * buf, std::uint32_t offset, std::uint16_t)> uint16;
    std::function<void(blob_t * buf, std::uint32_t offset, std::uint32_t)> uint32;
    std::function<void(blob_t * buf, std::uint32_t offset, std::uint64_t)> uint64;
    std::function<void(blob_t * buf, std::uint32_t offset, float)>         float_;
    std::function<void(blob_t * buf, std::uint32_t offset, double)>        double_;
#if HAS_FLOAT16==1
    std::function<void(blob_t * buf, std::uint32_t offset, std::float16_t)> float16;
#endif
#if HAS_BFLOAT16==1
    std::function<void(blob_t * buf, std::uint32_t offset, std::bfloat16_t)> bfloat16;
#endif
    std::vector<std::uint16_t>                                             m_first_pids;
    std::map<std::uint16_t, std::tuple<std::uint16_t, std::uint16_t>>      m_odt_to_daq_map;
};
//////////////////////////////////////////////////////////////////////////////////////////////

struct MeasurementParameters {
    MeasurementParameters() = default;

    MeasurementParameters(MeasurementParameters&& ) = default;
    MeasurementParameters(const MeasurementParameters& ) = default;
    MeasurementParameters& operator=(MeasurementParameters&& ) = default;
    MeasurementParameters& operator=(const MeasurementParameters& ) = default;

    explicit MeasurementParameters(
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

    std::string dumps() const {
        std::stringstream ss;

        ss << to_binary(m_byte_order);
        ss << to_binary(m_id_field_size);
        ss << to_binary(m_timestamps_supported);
        ss << to_binary(m_ts_fixed);
        ss << to_binary(m_prescaler_supported);
        ss << to_binary(m_selectable_timestamps);
        ss << to_binary(m_ts_scale_factor);
        ss << to_binary(m_ts_size);
        ss << to_binary(m_min_daq);

        std::size_t dl_count = m_daq_lists.size();
        ss << to_binary(dl_count);
        for (const auto& daq_list : m_daq_lists) {
            ss << daq_list.dumps();
        }

        return to_binary(std::size(ss.str())) +  ss.str();
    }

    std::uint8_t         m_byte_order;
    std::uint8_t         m_id_field_size;
    bool                 m_timestamps_supported;
    bool                 m_ts_fixed;
    bool                 m_prescaler_supported;
    bool                 m_selectable_timestamps;
    double               m_ts_scale_factor;
    std::uint8_t         m_ts_size;
    std::uint16_t        m_min_daq;
    std::vector<DaqList> m_daq_lists;
};


class Deserializer {
public:
    explicit Deserializer(const std::string& buf) : m_buf(buf) {
    }

    MeasurementParameters run() {
        std::uint8_t         byte_order;
        std::uint8_t         id_field_size;
        bool                 timestamps_supported;
        bool                 ts_fixed;
        bool                 prescaler_supported;
        bool                 selectable_timestamps;
        double               ts_scale_factor;
        std::uint8_t         ts_size;
        std::uint16_t        min_daq;
        std::size_t          dl_count;
        std::vector<DaqList> daq_lists;

        byte_order = from_binary<std::uint8_t>();
        id_field_size = from_binary<std::uint8_t>();
        timestamps_supported = from_binary<bool>();
        ts_fixed = from_binary<bool>();
        prescaler_supported = from_binary<bool>();
        selectable_timestamps = from_binary<bool>();
        ts_scale_factor = from_binary<double>();
        ts_size = from_binary<std::uint8_t>();
        min_daq = from_binary<std::uint16_t>();
        dl_count = from_binary<std::size_t>();
        std::cout << (int)byte_order << " " << (int)id_field_size << " " << timestamps_supported << " " << ts_fixed << " " << prescaler_supported <<
            " " << selectable_timestamps << " " << ts_scale_factor << " " << (int)ts_size << " " << min_daq << std::endl;
        std::cout << "DL-count: " << (int)dl_count << std::endl;

        for (std::size_t i = 0; i < dl_count; i++) {
            daq_lists.push_back(create_daq_list());
        }
        return MeasurementParameters(byte_order, id_field_size, timestamps_supported, ts_fixed, prescaler_supported, selectable_timestamps,
            ts_scale_factor, ts_size, min_daq, daq_lists);
    }

protected:

    DaqList create_daq_list() {
        std::string              name;
        std::uint16_t            event_num;
        bool                     stim;
        bool                     enable_timestamps;
        std::vector<McObject>    measurements;
        std::vector<Bin>         measurements_opt;
        std::vector<std::string> header_names;

        std::uint16_t            odt_count;
        std::uint16_t            total_entries;
        std::uint16_t            total_length;

        flatten_odts_t           flatten_odts;

        std::vector<DaqList::daq_list_initialzer_t> initializer_list{};

        name = from_binary<std::string>();
        event_num = from_binary<std::uint16_t>();
        stim = from_binary<bool>();
        enable_timestamps = from_binary<bool>();

        odt_count = from_binary<std::uint16_t>();
        total_entries = from_binary<std::uint16_t>();
        total_length = from_binary<std::uint16_t>();

        std::cout << "Name: " << name << " " << event_num << " " << stim << " " << enable_timestamps << std::endl;
        std::cout << "Odt-count: " << (int)odt_count << " " << "Total-entries: " << (int)total_entries << " " << "Total-length: " << (int)total_length << std::endl;

        std::size_t meas_size = from_binary<std::size_t>();
        std::cout << "Meas-size: " << (int)meas_size << std::endl;

        for (auto i = 0; i < meas_size; ++i) {
            // name, address, ext, dt_name
            auto meas = create_mc_object();
            measurements.push_back(meas);
            initializer_list.push_back({meas.get_name(), meas.get_address(), meas.get_ext(), meas.get_data_type()});
        }

        std::size_t meas_opt_size = from_binary<std::size_t>();
        std::cout << "Meas-opt-size: " << (int)meas_opt_size << std::endl;
        for (auto i = 0; i < meas_opt_size; ++i) {
            measurements_opt.emplace_back(create_bin());
        }

        std::size_t hname_size = from_binary<std::size_t>();
        std::cout << "Hname-size: " << (int)hname_size << std::endl;
        for (auto i = 0; i < hname_size; ++i) {
            auto header = from_binary<std::string>();
            header_names.push_back(header);
            std::cout << header << " ";
        }
        std::cout << std::endl << std::endl;

        auto odts = create_flatten_odts();

        auto result = DaqList(name, event_num, stim, enable_timestamps, initializer_list);
        result.set_measurements_opt(measurements_opt);
        return result;
    }

    flatten_odts_t create_flatten_odts() {
        std::string name;
        std::uint32_t address;
        std::uint8_t ext;
        std::uint16_t size;
        std::int16_t type_index;

        flatten_odts_t odts;

        std::size_t odt_count = from_binary<std::size_t>();
        std::cout << "Odt-count: " << (int)odt_count << std::endl;
        for (auto i = 0; i < odt_count; ++i) {
            std::vector<std::tuple<std::string, std::uint32_t, std::uint8_t, std::uint16_t, std::int16_t>> flatten_odt{};
            std::size_t odt_entry_count = from_binary<std::size_t>();
            std::cout << "Odt-entry-count: " << (int)odt_entry_count << std::endl;
            for (auto j = 0; j < odt_entry_count; ++j) {
                name = from_binary<std::string>();
                address = from_binary<std::uint32_t>();
                ext = from_binary<std::uint8_t>();
                size = from_binary<std::uint16_t>();
                type_index = from_binary<std::int16_t>();
                std::cout << "\t" << name << " " << address << " " << (int)ext << " " << (int)size << " " << (int)type_index << std::endl;
                flatten_odt.push_back(std::make_tuple(name, address, ext, size, type_index));
            }
            odts.push_back(flatten_odt);
        }

        return odts;
    }

    McObject create_mc_object() {
        std::string           name;
        std::uint32_t         address;
        std::uint8_t          ext;
        std::uint16_t         length;
        std::string           data_type;
        std::int16_t          type_index;
        std::vector<McObject> components{};

        name       = from_binary<std::string>();
        address    = from_binary<std::uint32_t>();
        ext        = from_binary<std::uint8_t>();
        length     = from_binary<std::uint16_t>();
        data_type  = from_binary<std::string>();
        type_index = from_binary<std::int16_t>();
        std::cout << "Name: " << name << " " << address << " " << (int)ext << " " << (int)length << " " << data_type << " " << (int)type_index << std::endl;
        std::size_t comp_size = from_binary<std::size_t>();
        std::cout << "Comp-size: " << (int)comp_size << std::endl;
        for (auto i=0U; i < comp_size; i++) {
            components.push_back(create_mc_object());
        }

        return McObject(name, address, ext, length, data_type, components);
    }

    Bin create_bin() {
        std::uint16_t         size;
        std::uint16_t         residual_capacity;
        std::vector<McObject> entries{};

        size = from_binary<std::uint16_t>();
        residual_capacity = from_binary<std::uint16_t>();
        std::cout << "BinSize: " << (int)size << " " << "Residual-capacity: " << (int)residual_capacity << std::endl;
        std::size_t entry_size = from_binary<std::size_t>();
        std::cout << "\tEntry-count: " << (int)entry_size << std::endl;
        for (auto i=0U; i < entry_size; i++) {
            entries.push_back(create_mc_object());
        }

        return Bin(size, residual_capacity, entries);
    }

    template<typename T>
    inline T from_binary() {
        auto tmp = *reinterpret_cast<const T*>(&m_buf[m_offset]);
        m_offset += sizeof(T);
        return tmp;
    }

    template<>
    inline std::string from_binary<std::string>() {
        auto length = from_binary<std::size_t>();
        std::string result;
        auto start = m_buf.cbegin() + m_offset;

        std::copy(start, start + length, std::back_inserter(result));
        m_offset += length;
        return result;
    }

private:
    std::string     m_buf;
    std::size_t     m_offset = 0;
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
        std::uint16_t daq_list_num, std::uint16_t num_odts, std::uint16_t total_entries, bool enable_timestamps,
        std::uint16_t initial_offset, const flatten_odts_t& flatten_odts, const Getter& getter,
        MeasurementParameters params
    ) :
        m_daq_list_num(daq_list_num),
        m_num_odts(num_odts),
        m_total_entries(total_entries),
        m_enable_timestamps(enable_timestamps),
        m_initial_offset(initial_offset),
        m_next_odt(0),
        m_current_idx(0),
        m_timestamp0(0.0),
        m_timestamp1(0.0),
        m_state(state_t::IDLE),
        m_buffer{},
        m_flatten_odts(flatten_odts),
        m_getter(getter),
        m_params(params)
        {

        m_buffer.resize(m_total_entries);
    }

    state_t check_state(uint16_t odt_num) {
        if ((m_state == state_t::IDLE) && (odt_num == 0x00)) {
            // "synch pulse".
            if (m_num_odts == 0x01) {
                resetSM();
                return state_t::FINISHED;
            } else {
                m_state    = state_t::COLLECTING;
                m_next_odt = 1;
            }
        } else if (m_state == state_t::COLLECTING) {
            if (odt_num == m_next_odt) {
                m_next_odt++;
                if (m_next_odt == m_num_odts) {
                    resetSM();
                    return state_t::FINISHED;
                }
            } else {
                // std::cout << "\t\tODT num out of order: " << odt_num << " -- expected: " << m_next_odt << std::endl;
                resetSM();
                return state_t::_ERROR;
            }
        }
        return m_state;
    }

    bool feed(uint16_t odt_num, double timestamp, const std::string& payload) {
        auto state    = check_state(odt_num);
        auto finished = false;

        if (state == state_t::COLLECTING) {
            m_timestamp0 = timestamp;
            parse_Odt(odt_num, payload);
        } else if (state == state_t::FINISHED) {
            m_timestamp0 = timestamp;
            parse_Odt(odt_num, payload);
            finished = true;
        }
        return finished;
    }

    void add_result(std::vector<measurement_tuple_t>& result_buffer) {
        result_buffer.emplace_back(m_daq_list_num, m_timestamp0, m_timestamp1, m_buffer);
    }

    void add_result(measurement_tuple_t& result_buffer) {
        //std::cout << "add_result: " << m_daq_list_num << " " << m_timestamp0 << " " << m_timestamp1 << std::endl;
        result_buffer = { m_daq_list_num, m_timestamp0, m_timestamp1, m_buffer };
    }

   protected:

    void resetSM() {
        m_state      = state_t::IDLE;
        m_next_odt   = 0;
        m_timestamp0 = 0.0;
    }

    void parse_Odt(uint16_t odt_num, const std::string& payload) {
        auto offset       = m_initial_offset;  // consider ID field size.
        auto payload_data = reinterpret_cast<const blob_t*>(payload.data());
        auto payload_size = std::size(payload);

        if (odt_num == 0) {
            m_current_idx = 0;
            if (m_params.m_timestamps_supported &&
                (m_params.m_ts_fixed || (m_params.m_selectable_timestamps && m_enable_timestamps == true))) {
                m_timestamp1 = static_cast<double>(m_getter.get_timestamp(payload_data)) * m_params.m_ts_scale_factor;
                offset += m_params.m_ts_size;
            } else {
                m_timestamp1 = 0.0;
            }
        }

        for (const auto& param : m_flatten_odts[odt_num]) {
            const auto& [name, address, ext, size, type_index] = param;

            if (offset >= payload_size) {
                throw std::runtime_error(
                    "Offset is out of range! " + std::to_string(offset) + " >= " + std::to_string(payload_size)
                );
            }

            m_buffer[m_current_idx++] = m_getter.reader(type_index, payload_data, offset);
            offset += size;
        }
    }

   private:

    std::uint16_t                    m_daq_list_num      = 0;
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
    flatten_odts_t          m_flatten_odts;
    Getter                           m_getter;
    MeasurementParameters            m_params;
};

auto requires_swap(std::uint8_t byte_order) -> bool {
    // INTEL(LITTLE)=0, MOTOROLA(BIG)=1
    std::endian target_byte_order = (byte_order == 1) ? std::endian::big : std::endian::little;
    return (target_byte_order != std::endian::native) ? true : false;
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////


class DAQProcessor {
   public:

    explicit DAQProcessor(const MeasurementParameters& params) : m_params(params) {
        create_state_vars(params);
    }

    DAQProcessor()          = delete;
    virtual ~DAQProcessor() = default;

    void start(const std::vector<std::uint16_t>& first_pids) noexcept {
        m_getter.set_first_pids(m_params.m_daq_lists, first_pids);
    }

#if 0
    std::optional<std::vector<measurement_tuple_t>> next_block() {
        std::vector<measurement_tuple_t> result{};

        const auto& block = m_reader.next_block();

        if (!block) {
            return std::nullopt;
        }

        for (const auto& frame : block.value()) {
            if (std::get<0>(frame) != static_cast<std::uint8_t>(FrameCategory::DAQ)) {
                continue;
            }
            const auto& [category, counter, frame_timestamp, frame_length, payload] = frame;
            auto [daq_num, odt_num]                                                 = m_getter.get_id(payload.data());

            if (m_state[daq_num].feed(odt_num, frame_timestamp, payload)) {
                m_state[daq_num].add_result(result);
            }
        }
        return result;
    }

#endif

    std::optional<measurement_tuple_t> feed(double timestamp, const std::string& payload) noexcept {
        const auto data         = reinterpret_cast<blob_t const *>(payload.data());
        auto [daq_num, odt_num] = m_getter.get_id(data);

        if (m_state[daq_num].feed(odt_num, timestamp, payload)) {
            // DAQ list completed.
            measurement_tuple_t result;

            m_state[daq_num].add_result(result);    // get_result()???
            return result;
        }
        return std::nullopt;
    }

   private:

    void create_state_vars(const MeasurementParameters& params) noexcept {
        m_getter = Getter(requires_swap(params.m_byte_order), params.m_id_field_size, params.m_ts_size);
        for (std::uint16_t idx = 0; idx < params.m_daq_lists.size(); ++idx) {
            m_state.emplace_back(DaqListState(
                idx, params.m_daq_lists[idx].get_odt_count(), params.m_daq_lists[idx].get_total_entries(),
                params.m_daq_lists[idx].get_enable_timestamps(), params.m_id_field_size, params.m_daq_lists[idx].get_flatten_odts(),
                m_getter, params
            ));
        }
    }

    MeasurementParameters                  m_params;
    Getter                                 m_getter;
    std::map<std::uint16_t, std::uint16_t> m_first_pids;
    std::vector<DaqListState>              m_state;
};

////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////

#if 0
class XcpLogFileUnfolder {
   public:

    explicit XcpLogFileUnfolder(const std::string& file_name, const MeasurementParameters& params) :
        m_reader(file_name), m_params(params) {
        create_state_vars(params);
    }

    XcpLogFileUnfolder() = delete;

    void start(const std::vector<std::uint16_t>& first_pids) {
        m_getter.set_first_pids(m_params.m_daq_lists, first_pids);
    }

    std::optional<std::vector<measurement_tuple_t>> next_block() {
        std::vector<measurement_tuple_t> result{};

        const auto& block = m_reader.next_block();

        if (!block) {
            return std::nullopt;
        }

        for (const auto& frame : block.value()) {
            if (std::get<0>(frame) != static_cast<std::uint8_t>(FrameCategory::DAQ)) {
                continue;
            }
            const auto& [category, counter, frame_timestamp, frame_length, payload] = frame;
            auto [daq_num, odt_num]                                                 = m_getter.get_id(payload.data());

            if (m_state[daq_num].feed(odt_num, frame_timestamp, payload)) {
                m_state[daq_num].add_result(result);
            }
        }
        return result;
    }

   private:

    void create_state_vars(const MeasurementParameters& params) {
        m_getter = Getter(requires_swap(params.m_byte_order), params.m_id_field_size, params.m_ts_size);
        for (auto idx = 0; idx < params.m_daq_lists.size(); ++idx) {
            m_state.emplace_back(DaqListState(
                idx, params.m_daq_lists[idx].get_odt_count(), params.m_daq_lists[idx].get_total_entries(),
                params.m_daq_lists[idx].get_enable_timestamps(), params.m_id_field_size, params.m_daq_lists[idx].get_flatten_odts(),
                m_getter, params
            ));
        }
    }

    XcpLogFileReader                       m_reader;
    MeasurementParameters                  m_params;
    Getter                                 m_getter;
    std::map<std::uint16_t, std::uint16_t> m_first_pids;
    std::vector<DaqListState>              m_state;
};
#endif

////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////


class DAQPolicyBase {
   public:

    virtual ~DAQPolicyBase() {}

    virtual void set_parameters(const MeasurementParameters& params) noexcept {
        initialize();
    }

    virtual void feed(std::uint8_t frame_cat, std::uint16_t counter, double timestamp, const std::string& payload) = 0;

    virtual void initialize() = 0;

    virtual void finalize() = 0;

};


class DaqRecorderPolicy : public DAQPolicyBase {
public:

    ~DaqRecorderPolicy() {}

    DaqRecorderPolicy() = default;

    void set_parameters(const MeasurementParameters& params) noexcept override {
        m_params = params;
        DAQPolicyBase::set_parameters(params);
    }

    void feed(std::uint8_t frame_cat, std::uint16_t counter, double timestamp, const std::string& payload) {
        if (frame_cat != static_cast<std::uint8_t>(FrameCategory::DAQ)) {
            // Only record DAQ frames for now.
            return;
        }
        m_writer->add_frame(frame_cat, counter, timestamp, static_cast<std::uint16_t>(payload.size()), payload.c_str());
    }

    void create_writer(const std::string& file_name, std::uint32_t prealloc, std::uint32_t chunk_size, std::string_view metadata) {
        m_writer = std::make_unique<XcpLogFileWriter>(file_name, prealloc, chunk_size, metadata);
    }

    void initialize() {
        // TODO: Save meta-data.
    }

    void finalize() {
        m_writer->finalize();
    }

private:

    std::unique_ptr<XcpLogFileWriter> m_writer;
    MeasurementParameters m_params;
};


class DaqOnlinePolicy  : public DAQPolicyBase {
   public:

    ~DaqOnlinePolicy() {
    }

    DaqOnlinePolicy()          = default;

    void set_parameters(const MeasurementParameters& params) noexcept {
        m_unfolder = std::make_unique<DAQProcessor>(params);
        DAQPolicyBase::set_parameters(params);
    }

    virtual void on_daq_list(
        std::uint16_t daq_list_num, double timestamp0, double timestamp1, const std::vector<measurement_value_t>& measurement
    ) = 0;

    void feed(std::uint8_t frame_cat, std::uint16_t counter, double timestamp, const std::string& payload) {
        if (frame_cat != static_cast<std::uint8_t>(FrameCategory::DAQ)) {
            return;
        }
        auto result = m_unfolder->feed(timestamp, payload);
        if (result) {
             const auto& [daq_list, ts0, ts1, meas] = *result;
             on_daq_list(daq_list, ts0, ts1, meas);
        }
    }

    virtual void initialize() {
    }

    virtual void finalize() {
    }

   private:

    std::unique_ptr<DAQProcessor> m_unfolder;
};

#endif  // RECORDER_UNFOLDER_HPP
