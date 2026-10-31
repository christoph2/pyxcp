
#if !defined(__STIM_HPP)
    #define __STIM_HPP

    #if defined(_MSC_VER) && (defined(_WIN32) || defined(_WIN64))
        #if !defined(NOMINMAX)
            #define NOMINMAX
        #endif
    #endif

    #include <pybind11/functional.h>
    #include <pybind11/pybind11.h>
    #include <pybind11/stl.h>

    #include <algorithm>
    #include <bit>
    #include <chrono>
    #include <cmath>
    #include <cstdint>
    #include <cstring>
    #include <deque>
    #include <functional>
    #include <limits>
    #include <map>
    #include <mutex>
    #include <optional>
    #include <set>
    #include <stdexcept>
    #include <string>
    #include <string_view>
    #include <thread>
    #include <tuple>
    #include <type_traits>
    #include <vector>

    #if defined(_MSC_VER) && (defined(_WIN32) || defined(_WIN64))
        #include <Windows.h>
        // clang-format off
        #include <Avrt.h>
        // clang-format on
    #endif

namespace py = pybind11;

constexpr double TMR_RESOLUTION = 1.0 / 1000.0;  // Timer resolution is one millisecond.

constexpr std::uint8_t MIN_STIM_PID = 0x00;
constexpr std::uint8_t MAX_STIM_PID = 0xBF;

// Bits of SET_DAQ_LIST_MODE.
constexpr std::uint16_t MODE_ALTERNATING = 0x01;
constexpr std::uint16_t MODE_DIRECTION   = 0x02;
constexpr std::uint16_t MODE_DTO_CTR     = 0x08;
constexpr std::uint16_t MODE_TIMESTAMP   = 0x10;
constexpr std::uint16_t MODE_PID_OFF     = 0x20;

// Modifier bits of DTO_CTR_PROPERTIES.
constexpr std::uint16_t DTO_CTR_MODIFY_RELATED = 0x01;
constexpr std::uint16_t DTO_CTR_MODIFY_DAQ     = 0x02;
constexpr std::uint16_t DTO_CTR_MODIFY_STIM    = 0x04;

enum class IdFieldType : std::uint8_t {
    ABS_ODT_NUMBER            = 0,
    REL_ODT_ABS_DAQ_BYTE      = 1,
    REL_ODT_ABS_DAQ_WORD      = 2,
    REL_ODT_ABS_DAQ_WORD_ALGN = 3,
};

/*
 * Python's frame sender (`Transport.block_request`) expects an enum-like "command" object, we pass the PID.
 */
class FakeEnum {
   public:

    FakeEnum(std::uint8_t value) : m_value(value) {
    }

    const std::string get_name() const {
        return std::string("STIM");
    }

    const std::uint8_t get_value() const {
        return m_value;
    }

    operator int() const {
        return m_value;
    }

    int bit_length() const {
        return 8;
    }

    py::bytes to_bytes(std::uint8_t length, std::string_view encoding) const {
        return py::bytes(std::string(1, static_cast<char>(m_value)));
    }

   private:

    std::uint8_t m_value;
};

struct StimParameters {
    std::uint8_t  id_field{ 0 };                  // IdFieldType
    std::uint8_t  timestamp_size{ 0 };            // 0, 1, 2 or 4 bytes.
    std::uint16_t max_dto{ 0xFFFF };              // MAX_DTO of the slave.
    std::uint16_t min_st_stim{ 0 };               // MIN_ST_STIM in units of 100 microseconds.
    std::uint16_t min_daq{ 0 };                   // Number of first dynamic DAQ list.
    bool          big_endian{ false };            // Slave byte order (MOTOROLA == true).
};

struct DaqEventInfo {
    explicit DaqEventInfo(
        const std::string& name, std::int8_t unit_exp, std::size_t cycle, std::size_t maxDaqList, std::size_t priority,
        std::string_view consistency, bool daq, bool stim, bool packed
    ) :
        m_name(name),
        m_unit_exp(unit_exp),
        m_cycle(cycle),
        m_maxDaqList(maxDaqList),
        m_priority(priority),
        m_consistency(consistency),
        m_daq(daq),
        m_stim(stim),
        m_packed(packed) {
        if (cycle == 0) {
            m_periodic   = false;
            m_cycle_time = 0;
        } else {
            m_periodic      = true;
            auto cycle_time = cycle * std::pow(10, unit_exp);
            if (cycle_time < TMR_RESOLUTION) {
                cycle_time = TMR_RESOLUTION;
            }
            m_cycle_time = static_cast<std::size_t>(cycle_time * 1000.0);
        }
    }

   public:

    std::string             m_name;
    std::int8_t             m_unit_exp;
    std::size_t             m_cycle;
    std::size_t             m_maxDaqList;
    std::size_t             m_priority;
    std::string             m_consistency{};
    bool                    m_daq;
    bool                    m_stim;
    bool                    m_packed;
    bool                    m_periodic;
    std::size_t             m_cycle_time;
    std::set<std::uint16_t> m_daq_lists{};
};

/*
 * DTO CTR event channel properties (ASAM MCD-1 XCP, 4.3.5.2).
 */
struct DtoCtrEvent {
    std::uint16_t related_event_channel{ 0 };
    std::uint8_t  daq_mode{ 0 };    // 0 == INSERT_COUNTER, 1 == INSERT_STIM_COUNTER_COPY
    std::uint8_t  stim_mode{ 0 };   // 0 == DO_NOT_CHECK_COUNTER, 1 == CHECK_COUNTER
    bool          event_counter_present{ false };
    bool          stim_counter_copy_present{ false };
};

// Value types of STIM list elements.
struct FieldType {
    std::uint8_t code;
    std::uint8_t size;
};

inline FieldType parse_field_type(const std::string& name) {
    static const std::map<std::string, FieldType> TYPES = {
        { "U8", { 0, 1 } },  { "I8", { 1, 1 } },  { "U16", { 2, 2 } }, { "I16", { 3, 2 } }, { "U32", { 4, 4 } },
        { "I32", { 5, 4 } }, { "U64", { 6, 8 } }, { "I64", { 7, 8 } }, { "F32", { 8, 4 } }, { "F64", { 9, 8 } },
    };
    auto it = TYPES.find(name);
    if (it == TYPES.end()) {
        throw std::invalid_argument("Unsupported STIM value type: " + name);
    }
    return it->second;
}

inline void put_bytes(std::uint8_t* out, const void* src, std::size_t n, bool big_endian) {
    std::memcpy(out, src, n);
    if (big_endian != (std::endian::native == std::endian::big)) {
        std::reverse(out, out + n);
    }
}

inline void get_bytes(const std::uint8_t* in, void* dst, std::size_t n, bool big_endian) {
    std::memcpy(dst, in, n);
    if (big_endian != (std::endian::native == std::endian::big)) {
        std::reverse(static_cast<std::uint8_t*>(dst), static_cast<std::uint8_t*>(dst) + n);
    }
}

template<typename T>
inline T convert_integer(py::handle value) {
    try {
        if (py::isinstance<py::float_>(value)) {
            const auto d = value.cast<double>();
            if (!std::isfinite(d) || d < static_cast<double>(std::numeric_limits<T>::min()) ||
                d > static_cast<double>(std::numeric_limits<T>::max())) {
                throw std::invalid_argument("STIM value out of range");
            }
            return static_cast<T>(d);
        }
        if constexpr (std::is_signed_v<T>) {
            const auto v = value.cast<long long>();
            if (v < static_cast<long long>(std::numeric_limits<T>::min()) || v > static_cast<long long>(std::numeric_limits<T>::max())) {
                throw std::invalid_argument("STIM value out of range");
            }
            return static_cast<T>(v);
        } else {
            const auto v = value.cast<unsigned long long>();
            if (v > static_cast<unsigned long long>(std::numeric_limits<T>::max())) {
                throw std::invalid_argument("STIM value out of range");
            }
            return static_cast<T>(v);
        }
    } catch (const py::cast_error&) {
        throw std::invalid_argument("STIM value is not representable as integer of the requested type");
    }
}

inline void encode_value(py::handle value, const FieldType& type, bool big_endian, std::uint8_t* out) {
    switch (type.code) {
        case 0: {
            auto x = convert_integer<std::uint8_t>(value);
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        case 1: {
            auto x = convert_integer<std::int8_t>(value);
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        case 2: {
            auto x = convert_integer<std::uint16_t>(value);
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        case 3: {
            auto x = convert_integer<std::int16_t>(value);
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        case 4: {
            auto x = convert_integer<std::uint32_t>(value);
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        case 5: {
            auto x = convert_integer<std::int32_t>(value);
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        case 6: {
            auto x = convert_integer<std::uint64_t>(value);
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        case 7: {
            auto x = convert_integer<std::int64_t>(value);
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        case 8: {
            auto x = static_cast<float>(value.cast<double>());
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
        default: {
            auto x = value.cast<double>();
            put_bytes(out, &x, sizeof(x), big_endian);
            break;
        }
    }
}

inline py::object decode_value(const std::uint8_t* in, const FieldType& type, bool big_endian) {
    #define DECODE_AS(T, PYTYPE)               \
        {                                      \
            T x;                               \
            get_bytes(in, &x, sizeof(x), big_endian); \
            return PYTYPE(x);                  \
        }
    switch (type.code) {
        case 0: DECODE_AS(std::uint8_t, py::int_)
        case 1: DECODE_AS(std::int8_t, py::int_)
        case 2: DECODE_AS(std::uint16_t, py::int_)
        case 3: DECODE_AS(std::int16_t, py::int_)
        case 4: DECODE_AS(std::uint32_t, py::int_)
        case 5: DECODE_AS(std::int32_t, py::int_)
        case 6: DECODE_AS(std::uint64_t, py::int_)
        case 7: DECODE_AS(std::int64_t, py::int_)
        case 8: DECODE_AS(float, py::float_)
        default: DECODE_AS(double, py::float_)
    }
    #undef DECODE_AS
}

struct StimEntry {
    std::uint32_t address{ 0 };
    std::uint16_t address_extension{ 0 };
    std::uint16_t bit_offset{ 0 };
    std::uint32_t size{ 0 };
};

struct StimOdt {
    std::vector<StimEntry> entries{};
    std::size_t            offset{ 0 };  // Offset of this ODT's payload inside StimList::data.
    std::size_t            size{ 0 };
};

struct StimList {
    std::uint16_t mode{ 0 };
    std::uint16_t event_channel_number{ 0 };
    std::uint16_t prescaler{ 1 };
    std::uint16_t priority{ 0 };
    std::uint16_t first_pid{ 0 };
    bool          selected{ false };
    bool          running{ false };
    bool          layout_dirty{ true };
    bool          data_valid{ false };
    std::uint8_t  ctr{ 0 };
    std::uint64_t triggers{ 0 };

    std::vector<StimOdt>      odts{};
    std::vector<FieldType>    fields{};
    std::vector<std::size_t>  field_offsets{};
    std::vector<std::uint8_t> data{};

    bool is_stim() const {
        return (mode & MODE_DIRECTION) == MODE_DIRECTION;
    }

    void layout() {
        if (!layout_dirty) {
            return;
        }
        std::size_t offset = 0;
        for (auto& odt : odts) {
            odt.offset = offset;
            odt.size   = 0;
            for (const auto& e : odt.entries) {
                odt.size += e.size;
            }
            offset += odt.size;
        }
        data.resize(offset, 0);
        layout_dirty = false;
    }
};

// Connects DAQ lists (inputs) via a function to STIM lists (outputs); see ASAM MCD-1 XCP 4.3.
struct Bypass {
    std::string                name;
    std::vector<std::uint16_t> inputs;
    std::vector<std::uint16_t> outputs;
    py::object                 function;
    std::size_t                delay{ 0 };
    bool                       prime{ true };
    py::object                 on_inconsistent;

    std::map<std::uint16_t, py::object> values{};
    std::set<std::uint16_t>             received{};
    std::deque<std::pair<std::uint8_t, std::vector<py::object>>> pending{};
    bool                       primed{ false };
    std::uint8_t               internal_ctr{ 0 };
    std::uint8_t               current_ctr{ 0 };
    std::optional<std::uint8_t> last_input_ctr{ std::nullopt };
    std::uint64_t              cycles{ 0 };
    std::uint64_t              overruns{ 0 };
    std::uint64_t              ctr_errors{ 0 };
};

class Stim {
   public:

    using feed_function_t = std::function<void(std::size_t, std::size_t, float, std::vector<std::uint8_t>)>;
    using send_function_t = std::function<void(FakeEnum, std::vector<std::uint8_t>)>;

    explicit Stim(bool activate = true) : m_activate(activate) {
    }

    /*
     * Optional: raise OS timer resolution / thread priority (Windows only), important for tight bypass cycles.
     */
    static void enableHighResolutionTimer() {
    #if defined(_MSC_VER) && (defined(_WIN32) || defined(_WIN64))
        timeBeginPeriod(1);
        DWORD task_index = 0UL;
        AvSetMmThreadCharacteristics("Pro Audio", &task_index);
    #endif
    }

    void activate(bool value) {
        m_activate = value;
    }

    bool isActive() const {
        return m_activate;
    }

    void setParameters(const StimParameters& params) {
        std::lock_guard lock(m_mutex);
        m_params = params;
    }

    StimParameters getParameters() const {
        return m_params;
    }

    void setDaqEventInfo(const std::vector<DaqEventInfo>& daq_event_info) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        std::uint16_t   idx = 0;
        for (const auto& event : daq_event_info) {
            m_daq_event_info.insert_or_assign(idx, event);
            idx++;
        }
    }

    // ---- Mirror of the XCP DAQ configuration commands. ----

    void setDaqPtr(std::uint16_t daqListNumber, std::uint16_t odtNumber, std::uint16_t odtEntryNumber) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        if (!valid_entry(daqListNumber, odtNumber, odtEntryNumber)) {
            m_daq_ptr.reset();
            return;
        }
        m_daq_ptr = std::make_tuple(daqListNumber, odtNumber, odtEntryNumber);
    }

    void clearDaqList(std::uint16_t daqListNumber) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        if (auto* l = find_list(daqListNumber)) {
            for (auto& odt : l->odts) {
                for (auto& e : odt.entries) {
                    e = StimEntry{};
                }
            }
            l->layout_dirty = true;
            l->data_valid   = false;
        }
    }

    void writeDaq(std::uint16_t bitOffset, std::uint16_t entrySize, std::uint16_t addressExt, std::uint32_t address) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        if (!m_daq_ptr) {
            return;
        }
        auto [d, o, e] = *m_daq_ptr;
        if (!valid_entry(d, o, e)) {
            return;
        }
        auto& list  = m_daq_lists.at(d);
        auto& entry = list.odts[o].entries[e];

        entry.bit_offset        = bitOffset;
        entry.address           = address;
        entry.address_extension = addressExt;
        entry.size              = entrySize;
        list.layout_dirty       = true;
        list.data_valid         = false;

        // WRITE_DAQ post-increments the ODT entry pointer.
        m_daq_ptr = std::make_tuple(d, o, static_cast<std::uint16_t>(e + 1));
    }

    void writeDaqMultiple(const std::vector<std::tuple<std::uint16_t, std::uint16_t, std::uint16_t, std::uint32_t>>& elements) {
        for (const auto& [bit_offset, size, ext, address] : elements) {
            writeDaq(bit_offset, size, ext, address);
        }
    }

    void setDaqListMode(
        std::uint16_t mode, std::uint16_t daqListNumber, std::uint16_t eventChannelNumber, std::uint16_t prescaler,
        std::uint16_t priority
    ) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        auto*           list = find_list(daqListNumber);
        if (!list) {
            return;
        }
        const bool is_stim = (mode & MODE_DIRECTION) == MODE_DIRECTION;
        if (is_stim && (mode & MODE_PID_OFF)) {
            throw std::runtime_error("PID_OFF is not supported for STIM DAQ lists.");
        }
        auto event = m_daq_event_info.find(eventChannelNumber);
        if (event != m_daq_event_info.end()) {
            if (is_stim && !event->second.m_stim) {
                throw std::runtime_error("Event channel " + std::to_string(eventChannelNumber) + " does not support STIM.");
            }
            event->second.m_daq_lists.emplace(daqListNumber);
        }
        list->mode                 = mode;
        list->prescaler            = prescaler;  // Prescaler is only meaningful for direction DAQ.
        list->priority             = priority;
        list->event_channel_number = eventChannelNumber;
    }

    void startStopDaqList(std::uint16_t mode, std::uint16_t daqListNumber) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        auto*           list = find_list(daqListNumber);
        if (!list) {
            return;
        }
        // 0 = stop, 1 = start, 2 = select
        if (mode == 0) {
            list->selected = false;
            list->running  = false;
        } else if (mode == 1) {
            list->running = true;
        } else if (mode == 2) {
            list->selected = true;
        }
    }

    void startStopSynch(std::uint16_t mode) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        // 0 = stop all, 1 = start selected, 2 = stop selected
        for (auto& [number, list] : m_daq_lists) {
            if (mode == 0) {
                list.running  = false;
                list.selected = false;
            } else if (mode == 1 && list.selected) {
                list.running  = true;
                list.selected = false;
            } else if (mode == 2 && list.selected) {
                list.running  = false;
                list.selected = false;
            }
        }
        if (mode == 0) {
            for (auto& [name, bypass] : m_bypasses) {
                reset_bypass(bypass);
            }
        }
    }

    void dtoCtrProperties(
        std::uint16_t modifier, std::uint16_t eventChannel, std::uint16_t relatedEventChannel, std::uint16_t mode
    ) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        auto&           props = m_dto_ctr_events[eventChannel];
        if (modifier & DTO_CTR_MODIFY_RELATED) {
            props.related_event_channel = relatedEventChannel;
        }
        if (modifier & DTO_CTR_MODIFY_DAQ) {
            props.daq_mode = mode & 0x01;
        }
        if (modifier & DTO_CTR_MODIFY_STIM) {
            props.stim_mode = (mode >> 1) & 0x01;
        }
    }

    void setDtoCtrEvent(std::uint16_t eventChannel, const DtoCtrEvent& props) {
        std::lock_guard lock(m_mutex);
        m_dto_ctr_events[eventChannel] = props;
    }

    DtoCtrEvent getDtoCtrEvent(std::uint16_t eventChannel) const {
        std::lock_guard lock(m_mutex);
        auto            it = m_dto_ctr_events.find(eventChannel);
        return (it == m_dto_ctr_events.end()) ? DtoCtrEvent{} : it->second;
    }

    void setDaqPackedMode(
        std::uint16_t, std::uint16_t daqListNumber, std::uint16_t daqPackedMode, std::uint16_t dpmTimestampMode = 0,
        std::uint16_t dpmSampleCount = 0
    ) {
        if (!m_activate) {
            return;
        }
        if (daqPackedMode != 0) {
            // Packed STIM DTOs are not supported (no layout to pack to).
            std::lock_guard lock(m_mutex);
            if (auto* l = find_list(daqListNumber); l && l->is_stim()) {
                throw std::runtime_error("Packed mode is not supported for STIM DAQ lists.");
            }
        }
    }

    void clear() {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        m_daq_lists.clear();
        m_daq_ptr.reset();
        for (auto& [name, bypass] : m_bypasses) {
            reset_bypass(bypass);
        }
    }

    void freeDaq() {
        clear();
    }

    void allocDaq(std::uint16_t daqCount) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        m_daq_lists.clear();
        for (std::uint16_t idx = 0; idx < daqCount; ++idx) {
            m_daq_lists[static_cast<std::uint16_t>(m_params.min_daq + idx)] = StimList{};
        }
    }

    void allocOdt(std::uint16_t daqListNumber, std::uint16_t odtCount) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        if (auto* l = find_list(daqListNumber)) {
            l->odts.assign(odtCount, StimOdt{});
            l->layout_dirty = true;
        }
    }

    void allocOdtEntry(std::uint16_t daqListNumber, std::uint16_t odtNumber, std::uint16_t odtEntriesCount) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        if (auto* l = find_list(daqListNumber); l && odtNumber < l->odts.size()) {
            l->odts[odtNumber].entries.assign(odtEntriesCount, StimEntry{});
            l->layout_dirty = true;
        }
    }

    void set_first_pid(std::uint16_t daqListNumber, std::uint16_t firstPid) {
        if (!m_activate) {
            return;
        }
        std::lock_guard lock(m_mutex);
        if (auto* l = find_list(daqListNumber)) {
            l->first_pid = firstPid;
        }
    }

    void set_policy_feeder(const feed_function_t& fun) {
        m_feed_function = fun;
    }

    void set_frame_sender(const send_function_t& fun) {
        m_send_function = fun;
    }

    // ---- STIM data. ----

    /*
     * Declare the value types (U8, I16, F32, ...) of the elements of a STIM list in ODT order.
     * Required for `setValues`, `setValue`, `getValues`.
     */
    void setFieldTypes(std::uint16_t daqListNumber, const std::vector<std::string>& types) {
        std::lock_guard lock(m_mutex);
        auto&           l = stim_list(daqListNumber);
        l.layout();
        std::vector<FieldType>   fields;
        std::vector<std::size_t> offsets;
        std::size_t              offset = 0;
        for (const auto& t : types) {
            auto ft = parse_field_type(t);
            fields.push_back(ft);
            offsets.push_back(offset);
            offset += ft.size;
        }
        if (offset != l.data.size()) {
            throw std::invalid_argument(
                "Field types describe " + std::to_string(offset) + " bytes, but the DAQ list has " +
                std::to_string(l.data.size()) + " bytes."
            );
        }
        l.fields        = std::move(fields);
        l.field_offsets = std::move(offsets);
    }

    std::size_t dataSize(std::uint16_t daqListNumber) {
        std::lock_guard lock(m_mutex);
        auto&           l = stim_list(daqListNumber);
        l.layout();
        return l.data.size();
    }

    // Set the complete payload of a STIM list (all ODTs concatenated).
    void setData(std::uint16_t daqListNumber, const py::buffer& buffer) {
        auto            info = buffer.request();
        std::lock_guard lock(m_mutex);
        auto&           l = stim_list(daqListNumber);
        l.layout();
        const auto size = static_cast<std::size_t>(info.size * info.itemsize);
        if (size != l.data.size()) {
            throw std::invalid_argument(
                "Expected " + std::to_string(l.data.size()) + " bytes of STIM data, got " + std::to_string(size) + "."
            );
        }
        std::memcpy(l.data.data(), info.ptr, size);
        l.data_valid = true;
    }

    // Set the payload of a single ODT.
    void setOdtData(std::uint16_t daqListNumber, std::uint16_t odtNumber, const py::buffer& buffer) {
        auto            info = buffer.request();
        std::lock_guard lock(m_mutex);
        auto&           l = stim_list(daqListNumber);
        l.layout();
        if (odtNumber >= l.odts.size()) {
            throw std::out_of_range("Invalid ODT number.");
        }
        const auto& odt  = l.odts[odtNumber];
        const auto  size = static_cast<std::size_t>(info.size * info.itemsize);
        if (size != odt.size) {
            throw std::invalid_argument(
                "Expected " + std::to_string(odt.size) + " bytes for ODT " + std::to_string(odtNumber) + ", got " +
                std::to_string(size) + "."
            );
        }
        std::memcpy(l.data.data() + odt.offset, info.ptr, size);
        l.data_valid = true;
    }

    py::bytes getData(std::uint16_t daqListNumber) {
        std::lock_guard lock(m_mutex);
        auto&           l = stim_list(daqListNumber);
        l.layout();
        return py::bytes(reinterpret_cast<const char*>(l.data.data()), l.data.size());
    }

    // Set all elements of a STIM list from a sequence of Python numbers.
    void setValues(std::uint16_t daqListNumber, const py::sequence& values) {
        std::lock_guard lock(m_mutex);
        set_values_locked(stim_list(daqListNumber), values);
    }

    void setValue(std::uint16_t daqListNumber, std::size_t index, const py::object& value) {
        std::lock_guard lock(m_mutex);
        auto&           l = stim_list(daqListNumber);
        l.layout();
        if (l.fields.empty()) {
            throw std::runtime_error("Field types not set for DAQ list " + std::to_string(daqListNumber));
        }
        if (index >= l.fields.size()) {
            throw std::out_of_range("Invalid element index.");
        }
        encode_value(value, l.fields[index], m_params.big_endian, l.data.data() + l.field_offsets[index]);
        l.data_valid = true;
    }

    py::list getValues(std::uint16_t daqListNumber) {
        std::lock_guard lock(m_mutex);
        auto&           l = stim_list(daqListNumber);
        l.layout();
        if (l.fields.empty()) {
            throw std::runtime_error("Field types not set for DAQ list " + std::to_string(daqListNumber));
        }
        py::list result;
        for (std::size_t idx = 0; idx < l.fields.size(); ++idx) {
            result.append(decode_value(l.data.data() + l.field_offsets[idx], l.fields[idx], m_params.big_endian));
        }
        return result;
    }

    // ---- Transmission. ----

    /*
     * Transmit all ODTs of a STIM list (one DTO per ODT).
     * `dto_ctr` overrides the list's own DTO CTR (only used if the list has the DTO_CTR mode bit).
     */
    void trigger(std::uint16_t daqListNumber, std::optional<std::uint8_t> dto_ctr = std::nullopt, std::uint64_t timestamp = 0) {
        std::vector<std::vector<std::uint8_t>> frames;
        {
            std::lock_guard lock(m_mutex);
            build_frames(daqListNumber, stim_list(daqListNumber), dto_ctr, timestamp, frames);
        }
        transmit(frames);
    }

    // Transmit all running STIM lists bound to an event channel.
    void triggerEvent(std::uint16_t eventChannel, std::uint64_t timestamp = 0) {
        std::vector<std::vector<std::uint8_t>> frames;
        {
            std::lock_guard lock(m_mutex);
            for (auto& [number, list] : m_daq_lists) {
                if (list.is_stim() && list.running && list.event_channel_number == eventChannel) {
                    build_frames(number, list, std::nullopt, timestamp, frames);
                }
            }
        }
        transmit(frames);
    }

    void send(std::uint8_t pid, const std::vector<std::uint8_t>& payload) {
        if (!m_send_function) {
            throw std::runtime_error("No frame sender set (set_frame_sender).");
        }
        m_send_function.value()(FakeEnum(pid), payload);
    }

    // ---- Bypassing. ----

    /*
     * Register a bypass. `function` is called with one list of values per input DAQ list and returns the values for the
     * output STIM list (single output) or a sequence of value-sequences (multiple outputs).
     * `function=None` copies inputs[i] to outputs[i].
     * `delay` > 0 implements delayed bypassing (data of DAQ cycle n is stimulated in cycle n + delay); if `prime` is set the
     * STIM pipeline is pre-filled with the current STIM list contents.
     */
    void addBypass(
        const std::string& name, const std::vector<std::uint16_t>& inputs, const std::vector<std::uint16_t>& outputs,
        const py::object& function, std::size_t delay = 0, bool prime = true, const py::object& on_inconsistent = py::none()
    ) {
        if (inputs.empty() || outputs.empty()) {
            throw std::invalid_argument("A bypass needs at least one input DAQ list and one output STIM list.");
        }
        if (function.is_none() && inputs.size() != outputs.size()) {
            throw std::invalid_argument("A pass-through bypass needs as many outputs as inputs.");
        }
        if (!function.is_none() && !PyCallable_Check(function.ptr())) {
            throw std::invalid_argument("Bypass function is not callable.");
        }
        std::lock_guard lock(m_mutex);
        if (m_bypasses.contains(name)) {
            throw std::invalid_argument("Bypass '" + name + "' already exists.");
        }
        Bypass b;
        b.name            = name;
        b.inputs          = inputs;
        b.outputs         = outputs;
        b.function        = function;
        b.delay           = delay;
        b.prime           = prime;
        b.on_inconsistent = on_inconsistent;
        m_bypasses.emplace(name, std::move(b));
    }

    void removeBypass(const std::string& name) {
        std::lock_guard lock(m_mutex);
        m_bypasses.erase(name);
    }

    void clearBypasses() {
        std::lock_guard lock(m_mutex);
        m_bypasses.clear();
    }

    py::dict bypassStatistics(const std::string& name) {
        std::lock_guard lock(m_mutex);
        auto            it = m_bypasses.find(name);
        if (it == m_bypasses.end()) {
            throw std::out_of_range("Unknown bypass: " + name);
        }
        py::dict d;
        d["cycles"]     = it->second.cycles;
        d["overruns"]   = it->second.overruns;
        d["ctr_errors"] = it->second.ctr_errors;
        d["pending"]    = it->second.pending.size();
        return d;
    }

    /*
     * Feed decoded DAQ data into the bypasses. Call it from the DAQ policy (`on_daq_list`).
     * `dto_ctr` is the DTO CTR of the DAQ DTO, if known; otherwise a tool-internal cycle counter is used.
     */
    void feedDaq(std::uint16_t daqListNumber, const py::sequence& values, std::optional<std::uint8_t> dto_ctr = std::nullopt) {
        std::vector<Bypass*> affected;
        {
            std::lock_guard lock(m_mutex);
            for (auto& [name, b] : m_bypasses) {
                if (std::find(b.inputs.begin(), b.inputs.end(), daqListNumber) != b.inputs.end()) {
                    affected.push_back(&b);
                }
            }
        }
        for (auto* b : affected) {
            feed_bypass(*b, daqListNumber, values, dto_ctr);
        }
    }

    py::dict listInfo(std::uint16_t daqListNumber) {
        std::lock_guard lock(m_mutex);
        auto&           l = stim_list_any(daqListNumber);
        l.layout();
        py::dict d;
        d["mode"]       = l.mode;
        d["event"]      = l.event_channel_number;
        d["first_pid"]  = l.first_pid;
        d["running"]    = l.running;
        d["selected"]   = l.selected;
        d["stim"]       = l.is_stim();
        d["data_size"]  = l.data.size();
        d["triggers"]   = l.triggers;
        py::list odt_sizes;
        for (const auto& odt : l.odts) {
            odt_sizes.append(odt.size);
        }
        d["odt_sizes"] = odt_sizes;
        return d;
    }

   protected:

    StimList* find_list(std::uint16_t number) {
        auto it = m_daq_lists.find(number);
        return (it == m_daq_lists.end()) ? nullptr : &it->second;
    }

    StimList& stim_list_any(std::uint16_t number) {
        auto* l = find_list(number);
        if (!l) {
            throw std::out_of_range("Invalid DAQ list number: " + std::to_string(number));
        }
        return *l;
    }

    StimList& stim_list(std::uint16_t number) {
        auto& l = stim_list_any(number);
        if (!l.is_stim()) {
            throw std::invalid_argument("DAQ list " + std::to_string(number) + " is not a STIM list.");
        }
        return l;
    }

    bool valid_entry(std::uint16_t daqListNumber, std::uint16_t odtNumber, std::uint16_t odtEntryNumber) {
        auto* l = find_list(daqListNumber);
        return l && odtNumber < l->odts.size() && odtEntryNumber < l->odts[odtNumber].entries.size();
    }

    void set_values_locked(StimList& l, const py::sequence& values) {
        l.layout();
        if (l.fields.empty()) {
            throw std::runtime_error("Field types not set for this DAQ list.");
        }
        if (static_cast<std::size_t>(py::len(values)) != l.fields.size()) {
            throw std::invalid_argument(
                "Expected " + std::to_string(l.fields.size()) + " values, got " + std::to_string(py::len(values)) + "."
            );
        }
        // Encode into a scratch buffer first, so a bad value does not leave a half-written list behind.
        std::vector<std::uint8_t> scratch(l.data.size());
        for (std::size_t idx = 0; idx < l.fields.size(); ++idx) {
            encode_value(values[idx], l.fields[idx], m_params.big_endian, scratch.data() + l.field_offsets[idx]);
        }
        l.data       = std::move(scratch);
        l.data_valid = true;
    }

    void append_id_field(const StimList& l, std::uint16_t daq, std::size_t odt, std::vector<std::uint8_t>& frame) const {
        const auto id_field = static_cast<IdFieldType>(m_params.id_field);
        auto       lo       = static_cast<std::uint8_t>(daq & 0xFF);
        auto       hi       = static_cast<std::uint8_t>(daq >> 8);
        if (m_params.big_endian) {
            std::swap(lo, hi);
        }
        switch (id_field) {
            case IdFieldType::ABS_ODT_NUMBER: {
                const auto pid = l.first_pid + odt;
                if (pid > MAX_STIM_PID) {
                    throw std::runtime_error("STIM PID " + std::to_string(pid) + " out of range (0x00..0xBF).");
                }
                frame.push_back(static_cast<std::uint8_t>(pid));
                break;
            }
            case IdFieldType::REL_ODT_ABS_DAQ_BYTE:
                frame.push_back(static_cast<std::uint8_t>(odt));
                frame.push_back(static_cast<std::uint8_t>(daq));
                break;
            case IdFieldType::REL_ODT_ABS_DAQ_WORD:
                frame.push_back(static_cast<std::uint8_t>(odt));
                frame.push_back(lo);
                frame.push_back(hi);
                break;
            case IdFieldType::REL_ODT_ABS_DAQ_WORD_ALGN:
                frame.push_back(static_cast<std::uint8_t>(odt));
                frame.push_back(0);
                frame.push_back(lo);
                frame.push_back(hi);
                break;
        }
    }

    // Must be called with m_mutex held.
    void build_frames(
        std::uint16_t daq, StimList& l, std::optional<std::uint8_t> dto_ctr, std::uint64_t timestamp,
        std::vector<std::vector<std::uint8_t>>& frames
    ) {
        l.layout();
        if (!l.data_valid) {
            throw std::runtime_error("STIM list " + std::to_string(daq) + " has no data yet (bypassing startup, 4.3.3).");
        }
        const bool with_ctr = (l.mode & MODE_DTO_CTR) != 0;
        const bool with_ts  = (l.mode & MODE_TIMESTAMP) != 0 && m_params.timestamp_size > 0;
        std::uint8_t ctr    = 0;
        if (with_ctr) {
            ctr   = dto_ctr.value_or(l.ctr);
            l.ctr = static_cast<std::uint8_t>(ctr + 1);
        }
        for (std::size_t idx = 0; idx < l.odts.size(); ++idx) {
            const auto& odt        = l.odts[idx];
            const bool  first      = (idx == 0);
            const bool  has_extras = first && (with_ctr || with_ts);
            if (odt.size == 0 && !has_extras) {
                continue;
            }
            std::vector<std::uint8_t> frame;
            frame.reserve(odt.size + 8);
            append_id_field(l, daq, idx, frame);
            if (first && with_ctr) {
                frame.push_back(ctr);
            }
            if (first && with_ts) {
                std::uint8_t ts_bytes[8];
                put_bytes(ts_bytes, &timestamp, sizeof(timestamp), m_params.big_endian);
                if (m_params.big_endian) {
                    frame.insert(frame.end(), ts_bytes + 8 - m_params.timestamp_size, ts_bytes + 8);
                } else {
                    frame.insert(frame.end(), ts_bytes, ts_bytes + m_params.timestamp_size);
                }
            }
            frame.insert(frame.end(), l.data.begin() + odt.offset, l.data.begin() + odt.offset + odt.size);
            if (frame.size() > m_params.max_dto) {
                throw std::runtime_error(
                    "STIM DTO of list " + std::to_string(daq) + " (" + std::to_string(frame.size()) + " bytes) exceeds MAX_DTO."
                );
            }
            frames.push_back(std::move(frame));
        }
        l.triggers++;
    }

    void wait_us(std::uint64_t us) {
        if (us == 0) {
            return;
        }
        py::gil_scoped_release release;
        const auto             deadline = std::chrono::steady_clock::now() + std::chrono::microseconds(us);
        if (us > 2000) {
            std::this_thread::sleep_for(std::chrono::microseconds(us - 1000));
        }
        while (std::chrono::steady_clock::now() < deadline) {
        }
    }

    void transmit(const std::vector<std::vector<std::uint8_t>>& frames) {
        const std::uint64_t separation = static_cast<std::uint64_t>(m_params.min_st_stim) * 100ULL;
        bool                first      = true;
        for (const auto& frame : frames) {
            if (!first) {
                wait_us(separation);
            }
            first = false;
            send(frame.front(), std::vector<std::uint8_t>(frame.begin() + 1, frame.end()));
        }
    }

    static void reset_bypass(Bypass& b) {
        b.values.clear();
        b.received.clear();
        b.pending.clear();
        b.primed         = false;
        b.internal_ctr   = 0;
        b.last_input_ctr = std::nullopt;
    }

    void emit(Bypass& b, std::uint8_t ctr, const std::vector<py::object>& outputs) {
        for (std::size_t idx = 0; idx < b.outputs.size(); ++idx) {
            setValues(b.outputs[idx], py::reinterpret_borrow<py::sequence>(outputs[idx]));
            trigger(b.outputs[idx], ctr);
        }
    }

    void feed_bypass(Bypass& b, std::uint16_t daq, const py::sequence& values, std::optional<std::uint8_t> dto_ctr) {
        if (b.received.contains(daq)) {
            // The next cycle started before the previous one completed.
            b.overruns++;
            b.received.clear();
            b.values.clear();
        }
        b.values[daq] = py::list(values);
        if (daq == b.inputs.front()) {
            if (dto_ctr) {
                if (b.last_input_ctr && static_cast<std::uint8_t>(*b.last_input_ctr + 1) != *dto_ctr) {
                    b.ctr_errors++;
                    if (!b.on_inconsistent.is_none()) {
                        b.on_inconsistent(b.name, static_cast<std::uint8_t>(*b.last_input_ctr + 1), *dto_ctr);
                    }
                }
                b.last_input_ctr = dto_ctr;
                b.current_ctr    = *dto_ctr;
            } else {
                b.current_ctr = b.internal_ctr;
            }
        }
        b.received.insert(daq);
        if (b.received.size() < b.inputs.size()) {
            return;
        }

        // Complete cycle.
        std::vector<py::object> outputs;
        if (b.function.is_none()) {
            for (auto l : b.inputs) {
                outputs.push_back(b.values.at(l));
            }
        } else {
            py::list args;
            for (auto l : b.inputs) {
                args.append(b.values.at(l));
            }
            py::object result = b.function(*args);
            if (b.outputs.size() == 1) {
                outputs.push_back(result);
            } else {
                py::sequence seq = py::reinterpret_borrow<py::sequence>(result);
                if (static_cast<std::size_t>(py::len(seq)) != b.outputs.size()) {
                    throw std::invalid_argument("Bypass function must return one value sequence per output list.");
                }
                for (std::size_t i = 0; i < b.outputs.size(); ++i) {
                    outputs.push_back(seq[i]);
                }
            }
        }
        const std::uint8_t ctr = b.current_ctr;
        b.received.clear();
        b.values.clear();
        b.cycles++;
        b.internal_ctr = static_cast<std::uint8_t>(b.internal_ctr + 1);

        if (!b.primed) {
            b.primed = true;
            if (b.delay > 0 && b.prime) {
                // Pre-fill the pipeline for the cycles whose STIM data cannot be derived from DAQ data yet.
                for (std::size_t i = 0; i < b.delay; ++i) {
                    for (auto out : b.outputs) {
                        trigger(out, static_cast<std::uint8_t>(ctr + i));
                    }
                }
            }
        }
        b.pending.emplace_back(ctr, std::move(outputs));
        while (b.pending.size() > b.delay) {
            auto [pending_ctr, pending_values] = std::move(b.pending.front());
            b.pending.pop_front();
            // The ECU checks the DTO CTR against the counter of the cycle in which the data is stimulated.
            emit(b, static_cast<std::uint8_t>(pending_ctr + b.delay), pending_values);
        }
    }

   private:

    bool                                              m_activate;
    StimParameters                                    m_params{};
    mutable std::mutex                                m_mutex;
    std::map<std::uint16_t, StimList>                 m_daq_lists{};
    std::optional<std::tuple<std::uint16_t, std::uint16_t, std::uint16_t>> m_daq_ptr{ std::nullopt };
    std::map<std::uint16_t, DaqEventInfo>             m_daq_event_info{};
    std::map<std::uint16_t, DtoCtrEvent>              m_dto_ctr_events{};
    std::map<std::string, Bypass>                     m_bypasses{};
    std::optional<feed_function_t>                    m_feed_function{ std::nullopt };
    std::optional<send_function_t>                    m_send_function{ std::nullopt };
};

#endif  // __STIM_HPP
