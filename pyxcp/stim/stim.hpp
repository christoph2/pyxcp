
#if !defined(__STIM_HPP)
    #define __STIM_HPP

    #include <Avrt.h>
    #include <Windows.h>

    #include <algorithm>
    #include <cstdint>
    #include <functional>
    #include <iostream>
    #include <map>
    #include <mutex>
    #include <numeric>
    #include <optional>
    #include <queue>
    #include <set>
    #include <tuple>
    #include <vector>

    #include "scheduler.hpp"

constexpr double TMR_RESOLUTION = 1.0 / 1000.0;  // Timer resolution is one millisecond.

class Timer {
   public:

    Timer() {
        QueryPerformanceFrequency(&m_ticks_per_sec);
        QueryPerformanceCounter(&m_starting_time);
    }

    /*
     * Returns the number of µ-seconds since the timer was started.
     */
    std::uint64_t elapsed() const {
        LARGE_INTEGER now;
        LARGE_INTEGER ela;

        QueryPerformanceCounter(&now);
        ela.QuadPart = now.QuadPart - m_starting_time.QuadPart;
        ela.QuadPart /= (m_ticks_per_sec.QuadPart / 1000000UL);
        return ela.QuadPart;
    }

   private:

    LARGE_INTEGER m_ticks_per_sec;
    LARGE_INTEGER m_starting_time;
};

template<typename T>
class TsQueue {
   public:

    TsQueue() = default;

    TsQueue(const TsQueue& other) noexcept {
        std::scoped_lock lock(other.m_mtx);
        m_queue = other.m_queue;
    }

    void put(T value) noexcept {
        std::scoped_lock lock(m_mtx);
        m_queue.push(value);
        m_cond.notify_one();
    }

    std::shared_ptr<T> get() noexcept {
        std::unique_lock lock(m_mtx);
        m_cond.wait(lock, [this] { return !m_queue.empty(); });
        std::shared_ptr<T> result(std::make_shared<T>(m_queue.front()));
        m_queue.pop();
        return result;
    }

    bool empty() const noexcept {
        std::scoped_lock lock(m_mtx);
        return m_queue.empty();
    }

   private:

    mutable std::mutex      m_mtx;
    std::queue<T>           m_queue;
    std::condition_variable m_cond;
};

struct Mutex {
    ~Mutex() {
    }

    void lock() {
        m_mtx.lock();
    }

    void unlock() {
        m_mtx.unlock();
    }

    std::mutex m_mtx{};
};

Mutex& get_writer_lock();
Mutex& get_policy_lock();

constexpr std::uint8_t MIN_STIM_PID = 0x00;
constexpr std::uint8_t MAX_STIM_PID = 0xBF;

struct DAQListType {};

///// From BlueParrot.

using XcpDaq_ODTEntryIntegerType = std::uint16_t;
using XcpDaq_ODTIntegerType      = std::uint16_t;

typedef enum tagXcpDaq_DirectionType {
    XCP_DIRECTION_NONE,
    XCP_DIRECTION_DAQ,
    XCP_DIRECTION_STIM,
    XCP_DIRECTION_DAQ_STIM
} XcpDaq_DirectionType;

//////////////// C++ style ////////////////

struct OdtEntryType {
    void clear() {
        address           = 0;
        address_extension = 0;
        bitOffset         = 0;
        entry_size        = 0;
    }

    std::uint32_t address;
    std::uint16_t address_extension;
    std::uint16_t bitOffset;
    std::uint32_t entry_size;
};

struct OdtType {
    XcpDaq_ODTEntryIntegerType numOdtEntries;
    std::uint16_t              firstOdtEntry;

    void clear() {
        m_entries.resize(0);
    }

    void resize(std::uint16_t n) {
        m_entries.resize(n);
    }

    std::vector<OdtEntryType> m_entries;
};

struct DynamicListType {
    void clear() {
        numOdts              = 0;
        firstOdt             = 0;
        mode                 = 0;
        prescaler            = 0;
        counter              = 0;
        event_channel_number = 0;
        priority             = 0;
        m_odts.resize(0);
    }

    void resize(std::size_t n) {
        m_odts.resize(n);
    }

    XcpDaq_ODTIntegerType numOdts;
    std::uint16_t         firstOdt;
    std::uint16_t         mode;

    std::uint16_t prescaler;
    std::uint16_t event_channel_number;
    std::uint16_t counter;
    std::uint16_t priority;

    std::vector<OdtType> m_odts{};
};

//////////////// C++ style ////////////////

typedef struct tagXcpDaq_ListConfigurationType {
    XcpDaq_ODTIntegerType numOdts;
    std::uint16_t         firstOdt;
} XcpDaq_ListConfigurationType;

typedef struct tagXcpDaq_ListStateType {
    std::uint16_t mode;
    #if XCP_DAQ_ENABLE_PRESCALER == XCP_ON
    std::uint16_t prescaler;
    std::uint16_t counter;
    #endif /* XCP_DAQ_ENABLE_PRESCALER */
} XcpDaq_ListStateType;

typedef enum tagXcpDaq_EntityKindType {
    XCP_ENTITY_UNUSED,
    XCP_ENTITY_DAQ_LIST,
    XCP_ENTITY_ODT,
    XCP_ENTITY_ODT_ENTRY
} XcpDaq_EntityKindType;

typedef struct tagXcpDaq_EventType {
    std::uint8_t const * const name;
    std::uint8_t               nameLen;
    std::uint8_t               properties;
    std::uint8_t               timeunit;
    std::uint8_t               cycle;
    /* unit8_t priority; */
} XcpDaq_EventType;

typedef struct tagXcpDaq_MessageType {
    std::uint8_t         dlc;
    std::uint8_t const * data;
} XcpDaq_MessageType;

/////

struct StimParameters {
    std::byte max_dto;
};

struct DaqEventInfo {
    explicit DaqEventInfo(
        /*std::string_view*/ const std::string& name, std::int8_t unit_exp, std::size_t cycle, std::size_t maxDaqList,
        std::size_t priority, std::string_view consistency, bool daq, bool stim, bool packed
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
            std::cout << "\tTMR_TMP: " << m_cycle_time << std::endl;
        }

        std::cout << "Event: " << m_name << " Zaikel: " << m_cycle_time << "ms - periodic? " << m_periodic << std::endl;
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

enum class EventChannelTimeUnit : std::uint8_t {
    EVENT_CHANNEL_TIME_UNIT_1NS   = 0,
    EVENT_CHANNEL_TIME_UNIT_10NS  = 1,
    EVENT_CHANNEL_TIME_UNIT_100NS = 2,
    EVENT_CHANNEL_TIME_UNIT_1US   = 3,
    EVENT_CHANNEL_TIME_UNIT_10US  = 4,
    EVENT_CHANNEL_TIME_UNIT_100US = 5,
    EVENT_CHANNEL_TIME_UNIT_1MS   = 6,
    EVENT_CHANNEL_TIME_UNIT_10MS  = 7,
    EVENT_CHANNEL_TIME_UNIT_100MS = 8,
    EVENT_CHANNEL_TIME_UNIT_1S    = 9,
    EVENT_CHANNEL_TIME_UNIT_1PS   = 10,
    EVENT_CHANNEL_TIME_UNIT_10PS  = 11,
    EVENT_CHANNEL_TIME_UNIT_100PS = 12,
};

enum class DAQ_TIMESTAMP_UNIT_TO_EXP : std::int8_t {
    DAQ_TIMESTAMP_UNIT_1PS   = -12,
    DAQ_TIMESTAMP_UNIT_10PS  = -11,
    DAQ_TIMESTAMP_UNIT_100PS = -10,
    DAQ_TIMESTAMP_UNIT_1NS   = -9,
    DAQ_TIMESTAMP_UNIT_10NS  = -8,
    DAQ_TIMESTAMP_UNIT_100NS = -7,
    DAQ_TIMESTAMP_UNIT_1US   = -6,
    DAQ_TIMESTAMP_UNIT_10US  = -5,
    DAQ_TIMESTAMP_UNIT_100US = -4,
    DAQ_TIMESTAMP_UNIT_1MS   = -3,
    DAQ_TIMESTAMP_UNIT_10MS  = -2,
    DAQ_TIMESTAMP_UNIT_100MS = -1,
    DAQ_TIMESTAMP_UNIT_1S    = 0,
};

void sched_init();  // TODO: Incl.

class Stim {
   public:

    const std::uint8_t DIRECTION_STIM = 0x02;
    using event_info_t                = std::vector<DaqEventInfo>;
    using feed_function_t             = std::function<void(std::size_t, std::size_t, float, std::vector<std::uint8_t>)>;
    using send_function_t             = std::function<void(std::vector<std::uint8_t>)>;

    explicit Stim() {
        if (timeBeginPeriod(100) == TIMERR_NOERROR) {
            std::cout << "timeBeginPeriod() OK!!!" << std::endl;
        } else {
            std::cout << "timeBeginPeriod() failed!!!" << std::endl;
        }

        DWORD task_index = 0UL;

        auto xxx = AvSetMmThreadCharacteristics("Pro Audio", &task_index);
        std::cout << "AvSetMmThreadCharacteristics() " << xxx << ":" << task_index << std::endl;

        auto start = timeGetTime();
        m_scheduler.start_thread();
        // Sleep(1650);
        // std::cout << "Elapsed: " << timeGetTime() - start;
    }

    void setParameters(const StimParameters& params) {
        m_params = params;
    }

    void setDaqEventInfo(const event_info_t& daq_event_info) {
        m_daq_event_info = daq_event_info;
        std::size_t idx  = 0;

        for (const auto& event : daq_event_info) {
            if (event.m_stim) {
                m_stim_events.emplace(idx);
                std::cout << "\tSTIM: " << event.m_name << ":" << idx << std::endl;
            }
            idx++;
        }
    }

    void setDaqPtr(std::uint16_t daqListNumber, std::uint16_t odtNumber, std::uint16_t odtEntryNumber) {
        if (!validateEntryNumber(daqListNumber, odtNumber, odtEntryNumber)) {
            return;
        }
        m_daq_ptr = { daqListNumber, odtNumber, odtEntryNumber };
        std::cout << "SET_DAQ_PTR " << daqListNumber << ":" << odtNumber << ":" << odtEntryNumber << std::endl;
    }

    void clearDaqList(std::uint16_t daqListNumber) {
        if (!validateEntryNumber(daqListNumber)) {
            return;
        }
        auto entry = m_daq_lists[daqListNumber];
        std::cout << "CLEAR_DAQ_LIST " << daqListNumber << std::endl;
        entry.clear();
    }

    void writeDaq(std::uint16_t bitOffset, std::uint16_t entrySize, std::uint16_t addressExt, std::uint32_t address) {
        auto [d, o, e] = m_daq_ptr;
        auto entry     = m_daq_lists[d].m_odts[o].m_entries[e];

        std::cout << "WRITE_DAQ " << bitOffset << ":" << entrySize << ":" << addressExt << ":" << address << std::endl;

        entry.bitOffset         = bitOffset;
        entry.address           = address;
        entry.address_extension = addressExt;
        entry.entry_size        = entrySize;

        std::cout << "\tBO: " << entry.bitOffset << std::endl;
        std::cout << "\tES: " << entry.entry_size << std::endl;
        std::cout << "\tAD: " << entry.address << std::endl;
        std::cout << "\tAE: " << entry.address_extension << std::endl;
    }

    void setDaqListMode(
        std::uint16_t mode, std::uint16_t daqListNumber, std::uint16_t eventChannelNumber, std::uint16_t prescaler,
        std::uint16_t priority
    ) {
        if (!validateEntryNumber(daqListNumber)) {
            return;
        }
        auto entry      = m_daq_lists[daqListNumber];
        entry.mode      = mode;
        entry.prescaler = prescaler;
        // The use of a prescaler is only used for DAQ lists with DIRECTION = DAQ.

        entry.priority             = priority;
        entry.event_channel_number = eventChannelNumber;

        auto& event = m_daq_event_info[eventChannelNumber];
        event.m_daq_lists.emplace(daqListNumber);

        std::cout << "SET_DAQ_LIST_MODE: " << mode << ":" << daqListNumber << ":" << eventChannelNumber << ":" << prescaler << ":"
                  << priority << std::endl;
        if ((mode & DIRECTION_STIM) == DIRECTION_STIM) {
            std::cout << "\tSTIM-MODE!!!\n";
            // TODO: Calculate timebase on the fly.

            std::cout << "\t\tEvent: " << event.m_name << " ==> " << event.m_cycle_time << " - " << event.m_periodic << std::endl;
            calculate_scheduler_period(event.m_cycle_time);
        }
    }

    void startStopDaqList(std::uint16_t mode, std::uint16_t daqListNumber) {
        if (!validateEntryNumber(daqListNumber)) {
            return;
        }
        std::cout << "START_STOP_DAQ_LIST " << mode << ":" << daqListNumber << std::endl;
    }

    void startStopSynch(std::uint16_t mode) {
    }

    void writeDaqMultiple(/* const std::vector<DaqElement>&*/ std::uint16_t daqElements) {
    }

    void dtoCtrProperties(
        std::uint16_t modifier, std::uint16_t eventChannel, std::uint16_t relatedEventChannel, std::uint16_t mode
    ) {
    }

    void setDaqPackedMode(
        std::uint16_t, std::uint16_t daqListNumber, std::uint16_t daqPackedMode, std::uint16_t dpmTimestampMode = 0,
        std::uint16_t dpmSampleCount = 0
    ) {
        if (!validateEntryNumber(daqListNumber)) {
            return;
        }
        // PACKED_MODE
    }

    void clear() {
        m_daq_lists.clear();
        m_daq_event_info.clear();
        m_stim_events.clear();
    }

    void freeDaq() {
        std::cout << "FREE_DAQ\n";
        clear();
    }

    void allocDaq(std::uint16_t daqCount) {
        m_daq_lists.resize(daqCount);
        std::cout << "ALLOC_DAQ " << daqCount << std::endl;
        std::for_each(m_daq_lists.cbegin(), m_daq_lists.cend(), [](auto elem) { elem.clear(); });
    }

    void allocOdt(std::uint16_t daqListNumber, std::uint16_t odtCount) {
        if (!validateEntryNumber(daqListNumber)) {
            return;
        }
        std::cout << "ALLOC_ODT " << daqListNumber << ":" << odtCount << std::endl;
        m_daq_lists[daqListNumber].resize(odtCount);
    }

    void allocOdtEntry(std::uint16_t daqListNumber, std::uint16_t odtNumber, std::uint16_t odtEntriesCount) {
        if (!validateEntryNumber(daqListNumber, odtNumber)) {
            return;
        }
        std::cout << "ALLOC_ODT_ENTRY " << daqListNumber << ":" << odtNumber << ":" << odtEntriesCount << std::endl;
        m_daq_lists[daqListNumber].m_odts[odtNumber].resize(odtEntriesCount);
    }

    void set_policy_feeder(const feed_function_t& fun) {
        m_feed_function = fun;
    }

    void set_frame_sender(const send_function_t& fun) {
        m_send_function = fun;
    }

    void send(const std::vector<std::uint8_t> frame) {
        if (m_send_function) {
            std::scoped_lock _{ get_writer_lock() };
            m_send_function.value()(frame);
        }
    }

   protected:

    void calculate_scheduler_period(std::size_t value) {
        if (!m_scheduler_period) {
            *m_scheduler_period = value;
        }
        if (!m_scheduler_max_value) {
            *m_scheduler_max_value = value;
        }
        std::cout << "SCHED_Value: " << value << std::endl;
        *m_scheduler_period    = std::gcd(*m_scheduler_period, value);
        *m_scheduler_max_value = std::lcm(*m_scheduler_max_value, value);
        std::cout << "SCHED_Period: " << *m_scheduler_period << " max: " << *m_scheduler_max_value << std::endl;
    }

    bool validateEntryNumber(
        std::uint16_t daqListNumber, std::optional<std::uint16_t> odtNumber = std::nullopt,
        std::optional<std::uint16_t> odtEntryNumber = std::nullopt
    ) const {
        if (daqListNumber >= std::size(m_daq_lists)) {
            return false;
        }
        if (odtNumber) {
            auto entry = m_daq_lists[daqListNumber];
            if (*odtNumber >= std::size(entry.m_odts)) {
                return false;
            }
        }
        if (odtEntryNumber) {
            auto entry = m_daq_lists[daqListNumber].m_odts[*odtNumber];
            if (*odtEntryNumber >= std::size(entry.m_entries)) {
                return false;
            }
        }
        std::cout << "\tOK, number is valid!!!\n";
        return true;
    }

   private:

    StimParameters                                          m_params{};
    std::vector<DynamicListType>                            m_daq_lists{};
    std::tuple<std::uint16_t, std::uint16_t, std::uint16_t> m_daq_ptr;
    std::optional<std::size_t>                              m_scheduler_period{ std::nullopt };
    std::optional<std::size_t>                              m_scheduler_max_value{ std::nullopt };
    event_info_t                                            m_daq_event_info;
    // std::map<std::uint16_t, std::vector<std::uint16_t>> m_event_mapping{};
    std::set<std::size_t>          m_stim_events{};
    std::optional<feed_function_t> m_feed_function{ std::nullopt };
    std::optional<send_function_t> m_send_function{ std::nullopt };
    Scheduler                      m_scheduler{};
};

#endif  // __STIM_HPP
