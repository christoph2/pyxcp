

#include <pybind11/chrono.h>
#include <pybind11/functional.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>

#include "transport_ext.hpp"
#include "framing.hpp"
#include "sxi_framing.hpp"


namespace py = pybind11;
using namespace pybind11::literals;

using SxiFrLBCN   = SxiReceiver< SxiHeaderFormat::LenByte, SxiChecksumType::None>;
using SxiFrLBC8   = SxiReceiver< SxiHeaderFormat::LenByte, SxiChecksumType::Sum8>;
using SxiFrLBC16  = SxiReceiver< SxiHeaderFormat::LenByte, SxiChecksumType::Sum16>;

using SxiFrLCBCN  = SxiReceiver< SxiHeaderFormat::LenCtrByte, SxiChecksumType::None>;
using SxiFrLCBC8  = SxiReceiver< SxiHeaderFormat::LenCtrByte, SxiChecksumType::Sum8>;
using SxiFrLCBC16 = SxiReceiver< SxiHeaderFormat::LenCtrByte, SxiChecksumType::Sum16>;

using SxiFrLFBCN  = SxiReceiver< SxiHeaderFormat::LenFillByte, SxiChecksumType::None>;
using SxiFrLFBC8  = SxiReceiver< SxiHeaderFormat::LenFillByte, SxiChecksumType::Sum8>;
using SxiFrLFBC16 = SxiReceiver< SxiHeaderFormat::LenFillByte, SxiChecksumType::Sum16>;

using SxiFrLWCN   = SxiReceiver< SxiHeaderFormat::LenWord, SxiChecksumType::None>;
using SxiFrLWC8   = SxiReceiver< SxiHeaderFormat::LenWord, SxiChecksumType::Sum8>;
using SxiFrLWC16  = SxiReceiver< SxiHeaderFormat::LenWord, SxiChecksumType::Sum16>;

using SxiFrLCWCN  = SxiReceiver< SxiHeaderFormat::LenCtrWord, SxiChecksumType::None>;
using SxiFrLCWC8  = SxiReceiver< SxiHeaderFormat::LenCtrWord, SxiChecksumType::Sum8>;
using SxiFrLCWC16 = SxiReceiver< SxiHeaderFormat::LenCtrWord, SxiChecksumType::Sum16>;

using SxiFrLFWCN  = SxiReceiver< SxiHeaderFormat::LenFillWord, SxiChecksumType::None>;
using SxiFrLFWC8  = SxiReceiver< SxiHeaderFormat::LenFillWord, SxiChecksumType::Sum8>;
using SxiFrLFWC16 = SxiReceiver< SxiHeaderFormat::LenFillWord, SxiChecksumType::Sum16>;


class PyFrameAcquisitionPolicy : public FrameAcquisitionPolicy {
   public:

    using FrameAcquisitionPolicy::FrameAcquisitionPolicy;

    void feed(
        FrameCategory frame_category, std::uint32_t counter, std::uint64_t timestamp, const payload_t& payload
    ) override {
        PYBIND11_OVERRIDE_PURE(void, FrameAcquisitionPolicy, feed, frame_category, counter, timestamp, payload);
    }


    void finalize() override {
        PYBIND11_OVERRIDE_PURE(void, FrameAcquisitionPolicy, finalize);
    }
};


PYBIND11_MODULE(transport_ext, m) {
    m.doc() = "pyXCP transport-layer base classes.";

	py::enum_<FrameCategory>(m, "FrameCategory")
		.value("METADATA", FrameCategory::META)
		.value("CMD", FrameCategory::CMD)
		.value("RESPONSE", FrameCategory::RES)
		.value("ERROR", FrameCategory::ERR)
		.value("EVENT", FrameCategory::EV)
		.value("SERV", FrameCategory::SERV)
		.value("DAQ", FrameCategory::DAQ)
		.value("STIM", FrameCategory::STIM)
	;

	py::class_<FrameAcquisitionPolicy, PyFrameAcquisitionPolicy>(m, "FrameAcquisitionPolicy", py::dynamic_attr())
		.def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t>&>(), py::arg("filtered_out") = std::nullopt)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
		.def_property_readonly("filtered_out", &FrameAcquisitionPolicy::get_filtered_out)
	;

	py::class_<LegacyFrameAcquisitionPolicy>(m, "LegacyFrameAcquisitionPolicy", py::dynamic_attr())
		.def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t>&>(), py::arg("filtered_out") = std::nullopt)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
		.def_property_readonly("reqQueue", &LegacyFrameAcquisitionPolicy::get_req_queue)
		.def_property_readonly("resQueue", &LegacyFrameAcquisitionPolicy::get_res_queue)
		.def_property_readonly("daqQueue", &LegacyFrameAcquisitionPolicy::get_daq_queue)
		.def_property_readonly("evQueue", &LegacyFrameAcquisitionPolicy::get_ev_queue)
		.def_property_readonly("servQueue", &LegacyFrameAcquisitionPolicy::get_serv_queue)
		.def_property_readonly("metaQueue", &LegacyFrameAcquisitionPolicy::get_meta_queue)
		.def_property_readonly("errorQueue", &LegacyFrameAcquisitionPolicy::get_error_queue)
		.def_property_readonly("stimQueue", &LegacyFrameAcquisitionPolicy::get_stim_queue)
	;

	py::class_<NoOpPolicy>(m, "NoOpPolicy", py::dynamic_attr())
		.def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t>&>(), py::arg("filtered_out") = std::nullopt)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
	;

	py::class_<StdoutPolicy>(m, "StdoutPolicy", py::dynamic_attr())
		.def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t>&>(), py::arg("filtered_out") = std::nullopt)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
	;

	py::class_<FrameRecorderPolicy>(m, "FrameRecorderPolicy", py::dynamic_attr())
		.def(py::init<const std::string&, const std::optional<FrameAcquisitionPolicy::filter_t>&, uint32_t, uint32_t>(),
			py::arg("file_name"), py::arg("filtered_out") = std::nullopt, py::arg("prealloc") = 10UL, py::arg("chunk_size") = 1)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
	;
    // Transport layer type enum
    py::enum_<XcpTransportLayerType>(m, "XcpTransportLayerType")
        .value("CAN", XcpTransportLayerType::CAN)
        .value("ETH", XcpTransportLayerType::ETH)
        .value("SXI", XcpTransportLayerType::SXI)
        .value("USB", XcpTransportLayerType::USB);

    // XCP checksum type enum
    py::enum_<ChecksumType>(m, "ChecksumType")
        .value("NO_CHECKSUM", ChecksumType::NO_CHECKSUM)
        .value("BYTE_CHECKSUM", ChecksumType::BYTE_CHECKSUM)
        .value("WORD_CHECKSUM", ChecksumType::WORD_CHECKSUM);

    // XCP framing configuration and helper
    py::class_<XcpFramingConfig>(m, "XcpFramingConfig")
        .def(py::init<>())
        .def(py::init<XcpTransportLayerType, std::uint8_t, std::uint8_t, std::uint8_t, bool, ChecksumType>(),
            "transport_layer_type"_a, "header_len"_a, "header_ctr"_a, "header_fill"_a, "tail_fill"_a = false, "tail_cs"_a = ChecksumType::NO_CHECKSUM)
        .def_property_readonly("transport_layer_type", [](const XcpFramingConfig &self) { return self.transport_layer_type; })
        .def_property_readonly("header_len", [](const XcpFramingConfig &self) { return self.header_len; })
        .def_property_readonly("header_ctr", [](const XcpFramingConfig &self) { return self.header_ctr; })
        .def_property_readonly("header_fill", [](const XcpFramingConfig &self) { return self.header_fill; })
        .def_property_readonly("tail_fill", [](const XcpFramingConfig &self) { return self.tail_fill; })
        .def_property_readonly("tail_cs", [](const XcpFramingConfig &self) { return self.tail_cs; });

    py::class_<XcpFraming>(m, "XcpFraming")
        .def(py::init<const XcpFramingConfig&>())
        .def("prepare_request", [](XcpFraming &self, std::uint32_t cmd, py::bytes data) {
            std::string s = data;
            std::vector<uint8_t> data_vec(s.begin(), s.end());
            return self.prepare_request(cmd, data_vec);
        }, "cmd"_a, "data"_a)
        .def("prepare_request", [](XcpFraming &self, std::uint32_t cmd, py::args data) {
            std::vector<uint8_t> data_vec;
            for (auto item : data) {
                data_vec.push_back(py::cast<uint8_t>(item));
            }
            return self.prepare_request(cmd, data_vec);
        }, "cmd"_a)
        .def("unpack_header", &XcpFraming::unpack_header, py::arg("data"), py::arg("initial_offset") = 0)
        .def("verify_checksum", &XcpFraming::verify_checksum)
        .def_property("counter_send", &XcpFraming::get_counter_send, &XcpFraming::set_counter_send)
        .def_property_readonly("header_size", &XcpFraming::get_header_size);

    py::class_<SxiFrLBCN>(m, "SxiFrLBCN")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLBCN::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLBC8>(m, "SxiFrLBC8")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLBC8::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLBC16>(m, "SxiFrLBC16")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLBC16::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLCBCN>(m, "SxiFrLCBCN")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLCBCN::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLCBC8>(m, "SxiFrLCBC8")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLCBC8::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLCBC16>(m, "SxiFrLCBC16")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLCBC16::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLFBCN>(m, "SxiFrLFBCN")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLFBCN::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLFBC8>(m, "SxiFrLFBC8")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLFBC8::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLFBC16>(m, "SxiFrLFBC16")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLFBC16::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLWCN>(m, "SxiFrLWCN")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLWCN::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLWC8>(m, "SxiFrLWC8")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLWC8::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLWC16>(m, "SxiFrLWC16")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLWC16::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLCWCN>(m, "SxiFrLCWCN")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLCWCN::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLCWC8>(m, "SxiFrLCWC8")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLCWC8::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLCWC16>(m, "SxiFrLCWC16")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLCWC16::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLFWCN>(m, "SxiFrLFWCN")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLFWCN::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLFWC8>(m, "SxiFrLFWC8")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLFWC8::feed_bytes, py::arg("data"))
    ;

    py::class_<SxiFrLFWC16>(m, "SxiFrLFWC16")
        .def(py::init<std::function<void(const std::vector<uint8_t>&, uint16_t, uint16_t)>>(), py::arg("dispatch_handler"))
        .def("feed_bytes", &SxiFrLFWC16::feed_bytes, py::arg("data"))
    ;

}
