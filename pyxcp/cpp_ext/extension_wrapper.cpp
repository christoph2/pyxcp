
#include <pybind11/chrono.h>
#include <pybind11/functional.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <memory>

#include <cstdint>

#include "aligned_buffer.hpp"
#include "bin.hpp"
#include "daqlist.hpp"
#include "mcobject.hpp"
#include "framing.hpp"
#include "sxi_framing.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

class PyTimestampInfo : public TimestampInfo {
   public:

    using TimestampInfo::TimestampInfo;
};

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


PYBIND11_MODULE(cpp_ext, m) {
    m.doc() = "C++ extensions for pyXCP.";

    //m.def("sleep_ms", &sleep_ms, "milliseconds"_a);
    //m.def("sleep_ns", &sleep_ns, "nanoseconds"_a);

    py::class_<McObject>(m, "McObject")
        .def(
            py::init<
                std::string_view, std::uint32_t, std::uint8_t, std::uint16_t, const std::string&, const std::vector<McObject>&>(),
            "name"_a, "address"_a, "ext"_a, "length"_a, "data_type"_a = "", "components"_a = std::vector<McObject>()
        )
        .def_property("name", &McObject::get_name, &McObject::set_name)
        .def_property("address", &McObject::get_address, &McObject::set_address)
        .def_property("ext", &McObject::get_ext, &McObject::set_ext)
        .def_property("length", &McObject::get_length, &McObject::set_length)
        .def_property("data_type", &McObject::get_data_type, &McObject::set_data_type)
        .def_property_readonly("components", &McObject::get_components)

        .def("add_component", &McObject::add_component, "component"_a)
        .def("__eq__", [](const McObject& self, const McObject& other) { return self == other; })
        .def("__repr__", [](const McObject& self) { return to_string(self); })
        .def("__hash__", [](const McObject& self) { return self.get_hash(); })
        ;

    py::class_<Bin>(m, "Bin")
        .def(py::init<std::uint16_t>(), "size"_a)
        .def_property("size", &Bin::get_size, &Bin::set_size)
        .def_property("residual_capacity", &Bin::get_residual_capacity, &Bin::set_residual_capacity)
        .def_property("entries", &Bin::get_entries, nullptr)
        .def("append", &Bin::append)
        .def("__repr__", [](const Bin& self) { return to_string(self); })
        .def("__eq__", [](const Bin& self, const Bin& other) { return self == other; })
        .def("__len__", [](const Bin& self) { return std::size(self.get_entries()); });

    py::class_<DaqListBase, std::shared_ptr<DaqListBase>>(m, "DaqListBase")
        .def_property("name", &DaqListBase::get_name, nullptr)
        .def_property("event_num", &DaqListBase::get_event_num, &DaqListBase::set_event_num)
        .def_property("priority", &DaqListBase::get_priority, nullptr)
        .def_property("prescaler", &DaqListBase::get_prescaler, nullptr)
        .def_property("stim", &DaqListBase::get_stim, nullptr)
        .def_property("enable_timestamps", &DaqListBase::get_enable_timestamps, nullptr)
        .def_property("measurements_opt", &DaqListBase::get_measurements_opt, &DaqListBase::set_measurements_opt)
        .def_property("headers", &DaqListBase::get_headers, nullptr)
        .def_property("odt_count", &DaqListBase::get_odt_count, nullptr)
        .def_property("total_entries", &DaqListBase::get_total_entries, nullptr)
        .def_property("total_length", &DaqListBase::get_total_length, nullptr);

    py::class_<DaqList, DaqListBase, std::shared_ptr<DaqList>>(m, "DaqList")
        .def(
            py::init<std::string_view, std::uint16_t, bool, bool, const std::vector<DaqList::daq_list_initialzer_t>&,
            std::uint8_t, std::uint8_t>(), "name"_a, "event_num"_a, "stim"_a, "enable_timestamps"_a, "measurements"_a,
            "priority"_a=0, "prescaler"_a=1
        )
        .def("__repr__", [](const DaqList& self) { return self.to_string(); })
        .def_property("measurements", &DaqList::get_measurements, nullptr);

    py::class_<PredefinedDaqList, DaqListBase, std::shared_ptr<PredefinedDaqList>>(m, "PredefinedDaqList")
        .def(
            py::init<std::string_view, std::uint16_t, bool, bool, const PredefinedDaqList::predefined_daq_list_initializer_t&,
            std::uint8_t, std::uint8_t>(), "name"_a, "event_num"_a, "stim"_a, "enable_timestamps"_a, "odts"_a,
            "priority"_a=0, "prescaler"_a=1
        )
        .def("__repr__", [](const PredefinedDaqList& self) {
            try {
                return self.to_string();
            } catch (const std::exception& e) {
                return std::string("PredefinedDaqList(<repr error: ") + e.what() + ">)";
            } catch (...) {
                return std::string("PredefinedDaqList(<repr error: unknown>)");
            }
        })
		;

    py::enum_<TimestampType>(m, "TimestampType")
        .value("ABSOLUTE_TS", TimestampType::ABSOLUTE_TS)
        .value("RELATIVE_TS", TimestampType::RELATIVE_TS);

    py::class_<Timestamp>(m, "Timestamp")
        .def(py::init<TimestampType>(), "ts_type"_a)
        .def_property_readonly("absolute", &Timestamp::absolute)
        .def_property_readonly("relative", &Timestamp::relative)
        .def_property_readonly("value", &Timestamp::get_value)
        .def_property_readonly("initial_value", &Timestamp::get_initial_value);

    py::class_<TimestampInfo, PyTimestampInfo>(m, "TimestampInfo", py::dynamic_attr())
        .def(py::init<std::uint64_t>())
        .def(py::init<std::uint64_t, const std::string&, std::int16_t, std::int16_t>())

        .def_property_readonly("timestamp_ns", &TimestampInfo::get_timestamp_ns)
        .def_property("utc_offset", &TimestampInfo::get_utc_offset, &TimestampInfo::set_utc_offset)
        .def_property("dst_offset", &TimestampInfo::get_dst_offset, &TimestampInfo::set_dst_offset)
        .def_property("timezone", &TimestampInfo::get_timezone, &TimestampInfo::set_timezone);

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
        .def("prepare_request", [](XcpFraming &self, std::uint32_t cmd, py::args data) {
            std::vector<uint8_t> data_vec;
            for (auto item : data) {
                data_vec.push_back(py::cast<uint8_t>(item));
            }
            return self.prepare_request(cmd, data_vec);
        }, "cmd"_a)
        .def("unpack_header", &XcpFraming::unpack_header, py::arg("data"), py::arg("initial_offset") = 0)
        .def("verify_checksum", &XcpFraming::verify_checksum)
        .def_property_readonly("counter_send", &XcpFraming::get_counter_send)
        .def_property_readonly("header_size", &XcpFraming::get_header_size);

    // Aligned buffer utility
    py::class_<AlignedBuffer>(m, "AlignedBuffer")
        .def(py::init<std::size_t>(), py::arg("size") = 0xffff)
        .def("reset", &AlignedBuffer::reset)
        .def("append", &AlignedBuffer::append, py::arg("value"))
        .def("extend", py::overload_cast<const py::bytes&>(&AlignedBuffer::extend))
        .def("extend", py::overload_cast<const std::vector<std::uint8_t>&>(&AlignedBuffer::extend))
        .def("__len__", [](const AlignedBuffer& self) { return self.size(); })
        .def("__getitem__", [](const AlignedBuffer& self, py::object index) { return self.get_item(index); });

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
