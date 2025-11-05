
#include <cstdint>

#include <bit>
#include <optional>
#include <iostream>
#include <map>
#include <set>
#include <tuple>
#include <vector>

#include "rekorder.hpp"

const std::map<FrameCategory, std::string> FrameCategoryName {
	{FrameCategory::META, "METADATA"},
	{FrameCategory::CMD, "CMD"},
	{FrameCategory::RES, "RESPONSE"},
	{FrameCategory::ERR, "ERROR"},
	{FrameCategory::EV, "EVENT"},
	{FrameCategory::SERV, "SERV"},
	{FrameCategory::DAQ, "DAQ"},
	{FrameCategory::STIM, "STIM"},
};

/*
    Base class for all frame acquisition policies.

    Parameters
    ---------
    filter_out: set or None
        A set of frame types to filter out.
        If None, all frame types are accepted for further processing.

        Example: (FrameType.REQUEST, FrameType.RESPONSE, FrameType.EVENT, FrameType.SERV)
                  ==> care only about DAQ frames.
*/
class FrameAcquisitionPolicy {
public:

	using payload_t = std::string;
	using filter_t = std::set<FrameCategory>;
	using frame_t = std::tuple<std::uint32_t, std::uint64_t, const payload_t>;


	FrameAcquisitionPolicy(const std::optional<filter_t>& filter_out) {
		if (!filter_out) {
			m_filter_out = filter_t{};
		} else {
			m_filter_out = filter_out;
		}
	}

	std::optional<filter_t> get_filtered_out() const {
		return m_filter_out;
	}

	FrameAcquisitionPolicy(const FrameAcquisitionPolicy&) = delete;
	FrameAcquisitionPolicy(FrameAcquisitionPolicy&&) = delete;
	FrameAcquisitionPolicy() = delete;

	virtual ~FrameAcquisitionPolicy() {}

	virtual void feed(FrameCategory frame_category, std::uint32_t counter, std::uint64_t timestamp, const payload_t& payload) = 0;

	virtual void finalize() = 0;

protected:

	std::optional<filter_t> m_filter_out;

};


/*
	No operation / do nothing policy.
*/
class NoOpPolicy : public FrameAcquisitionPolicy {
public:

	NoOpPolicy(const std::optional<filter_t>& filter_out) : FrameAcquisitionPolicy(filter_out) {}

	void feed(FrameCategory frame_category, std::uint32_t counter, std::uint64_t timestamp, const payload_t& payload) override {}

	void finalize() override {}
};


/*
	Dequeue based frame acquisition policy.

    Deprecated: Use only for compatibility reasons.
*/
class LegacyFrameAcquisitionPolicy : public FrameAcquisitionPolicy {
	public:

		using deque_t = TsQueue<frame_t>;

		LegacyFrameAcquisitionPolicy(const std::optional<filter_t>& filter_out) : FrameAcquisitionPolicy(filter_out) {

			m_queue_map[FrameCategory::CMD] = std::make_shared<deque_t>();
			m_queue_map[FrameCategory::RES] = std::make_shared<deque_t>();
			m_queue_map[FrameCategory::EV] = std::make_shared<deque_t>();
			m_queue_map[FrameCategory::SERV] = std::make_shared<deque_t>();
			m_queue_map[FrameCategory::DAQ] = std::make_shared<deque_t>();
			m_queue_map[FrameCategory::META] = std::make_shared<deque_t>();
			m_queue_map[FrameCategory::ERR] = std::make_shared<deque_t>();
			m_queue_map[FrameCategory::STIM] = std::make_shared<deque_t>();

		}

		LegacyFrameAcquisitionPolicy() = delete;
		LegacyFrameAcquisitionPolicy(const LegacyFrameAcquisitionPolicy&) = delete;
		LegacyFrameAcquisitionPolicy(LegacyFrameAcquisitionPolicy&&) = delete;

		void feed(FrameCategory frame_category, std::uint32_t counter, std::uint64_t timestamp, const payload_t& payload) override {
			if (m_filter_out && (!(*m_filter_out).contains(frame_category))) {
				m_queue_map[frame_category]->put({counter, timestamp, payload});
			}
		}

		std::shared_ptr<deque_t> get_req_queue() {
			return m_queue_map.at(FrameCategory::CMD);
		}

		std::shared_ptr<deque_t> get_res_queue() {
			return m_queue_map.at(FrameCategory::RES);
		}

		std::shared_ptr<deque_t> get_daq_queue() {
			return m_queue_map.at(FrameCategory::DAQ);
		}

		std::shared_ptr<deque_t> get_ev_queue() {
			return m_queue_map.at(FrameCategory::EV);
		}

		std::shared_ptr<deque_t> get_serv_queue() {
			return m_queue_map.at(FrameCategory::SERV);
		}

		std::shared_ptr<deque_t> get_meta_queue() {
			return m_queue_map.at(FrameCategory::META);
		}

		std::shared_ptr<deque_t> get_error_queue() {
			return m_queue_map.at(FrameCategory::ERR);
		}

		std::shared_ptr<deque_t> get_stim_queue() {
			return m_queue_map.at(FrameCategory::STIM);
		}

		void finalize() override {}

private:

	std::map<FrameCategory, std::shared_ptr<deque_t>> m_queue_map{};
};

std::string hex_bytes(std::string_view payload) {
	std::stringstream ss;

	for (auto ch: payload) {
		ss << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(static_cast<unsigned char>(ch))  << " ";
	}
	return ss.str();
}

/*
	Frame acquisition policy that prints frames to stdout.
*/
class StdoutPolicy : public FrameAcquisitionPolicy {
public:
	StdoutPolicy(const std::optional<filter_t>& filter_out) : FrameAcquisitionPolicy(filter_out) {}

	StdoutPolicy() = delete;
	StdoutPolicy(const StdoutPolicy&) = delete;
	StdoutPolicy(StdoutPolicy&&) = delete;

	void feed(FrameCategory frame_category, std::uint32_t counter, std::uint64_t timestamp, const payload_t& payload) override {
		if (m_filter_out && (!(*m_filter_out).contains(frame_category))) {
			std::cout << std::left << std::setw(8) << FrameCategoryName.at(frame_category) << " " << std::right <<
				std::setw(6) << counter << " " << std::setw(8) << timestamp << " [ " << std::left << hex_bytes(payload) << "]" << std::endl;
		}
	}

	void finalize() override { }

};

class FrameRecorderPolicy : public FrameAcquisitionPolicy {
public:

	FrameRecorderPolicy(const std::string& file_name, const std::optional<filter_t>& filter_out, uint32_t prealloc = 10UL, uint32_t chunk_size = 1) : FrameAcquisitionPolicy(filter_out) {
		m_writer = std::make_unique<XcpLogFileWriter>(file_name, prealloc, chunk_size);
	}

	FrameRecorderPolicy() = delete;
	FrameRecorderPolicy(const FrameRecorderPolicy&) = delete;
	FrameRecorderPolicy(FrameRecorderPolicy&&) = delete;

	void feed(FrameCategory frame_category, std::uint32_t counter, std::uint64_t timestamp, const payload_t& payload) override {
		if (m_filter_out && (!(*m_filter_out).contains(frame_category))) {
			m_writer->add_frame(static_cast<std::uint8_t>(frame_category), counter, timestamp, payload.size(), std::bit_cast<const char *>(payload.data()));
		}
	}

	void finalize() override {
		m_writer->finalize();
	}

private:
	std::unique_ptr<XcpLogFileWriter> m_writer;
};
