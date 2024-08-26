
#include <pybind11/functional.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>

#include "rekorder.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

PYBIND11_MAKE_OPAQUE(ValueHolder);

class PyDaqOnlinePolicy : public DaqOnlinePolicy {
   public:

    using DaqOnlinePolicy::DaqOnlinePolicy;

    void on_daq_list(
        std::uint16_t daq_list_num, std::uint64_t timestamp0, std::uint64_t timestamp1,
        const std::vector<measurement_value_t>& measurement
    ) override {
        PYBIND11_OVERRIDE_PURE(void, DaqOnlinePolicy, on_daq_list, daq_list_num, timestamp0, timestamp1, measurement);
    }

    void initialize() override {
        PYBIND11_OVERRIDE(void, DaqOnlinePolicy, initialize);
    }

    void finalize() override {
        PYBIND11_OVERRIDE(void, DaqOnlinePolicy, finalize);
    }
};

class PyDaqRecorderPolicy : public DaqRecorderPolicy {
   public:

    using DaqRecorderPolicy::DaqRecorderPolicy;

    void initialize() override {
        PYBIND11_OVERRIDE(void, DaqRecorderPolicy, initialize);
    }

    void finalize() override {
        PYBIND11_OVERRIDE(void, DaqRecorderPolicy, finalize);
    }
};

class PyXcpLogFileDecoder : public XcpLogFileDecoder {
   public:

    using XcpLogFileDecoder::XcpLogFileDecoder;

    void on_daq_list(
        std::uint16_t daq_list_num, std::uint64_t timestamp0, std::uint64_t timestamp1,
        const std::vector<measurement_value_t>& measurement
    ) override {
        PYBIND11_OVERRIDE_PURE(void, XcpLogFileDecoder, on_daq_list, daq_list_num, timestamp0, timestamp1, measurement);
    }

    void initialize() override {
        PYBIND11_OVERRIDE(void, XcpLogFileDecoder, initialize);
    }

    void finalize() override {
        PYBIND11_OVERRIDE(void, XcpLogFileDecoder, finalize);
    }
};

PYBIND11_MODULE(rekorder, m) {
    m.doc() = "XCP raw frame recorder.";
    m.def("data_types", get_data_types);

    py::class_<FileHeaderType>(m, "FileHeaderType")
        .def(py::init<std::uint16_t, std::uint16_t, std::uint16_t, std::uint32_t, std::uint32_t, std::uint32_t, std::uint32_t>())
        .def("__repr__", [](const FileHeaderType& self) {
            std::stringstream ss;
            ss << "FileHeaderType(" << std::endl;
            ss << "    hdr_size=" << self.hdr_size << "," << std::endl;
            ss << "    version=" << self.version << "," << std::endl;
            ss << "    options=" << self.options << "," << std::endl;
            ss << "    num_containers=" << self.num_containers << "," << std::endl;
            ss << "    record_count=" << self.record_count << "," << std::endl;
            ss << "    size_compressed=" << self.size_compressed << "," << std::endl;
            ss << "    size_uncompressed=" << self.size_uncompressed << "," << std::endl;
            ss << "    compression_ratio="
               << (double)((std::uint64_t)(((double)self.size_uncompressed / (double)self.size_compressed * 100.0) + 0.5)) / 100.0
               << std::endl;
            ss << ")" << std::endl;
            return ss.str();
        });

    py::class_<Deserializer>(m, "Deserializer").def(py::init<const std::string&>()).def("run", &Deserializer::run);

    py::class_<XcpLogFileReader>(m, "_PyXcpLogFileReader")
        .def(py::init<const std::string&>())
        .def("next_block", &XcpLogFileReader::next_block)
        .def("reset", &XcpLogFileReader::reset)
        .def("get_header_as_tuple", &XcpLogFileReader::get_header_as_tuple)
        .def("get_metadata", [](const XcpLogFileReader& self) { return py::bytes(self.get_metadata()); });

    py::class_<XcpLogFileWriter>(m, "_PyXcpLogFileWriter")
        .def(
            py::init<const std::string&, std::uint32_t, std::uint32_t, std::string_view>(), py::arg("filename"),
            py::arg("prealloc"), py::arg("chunk_size"), py::arg("metadata") = ""
        )
        .def("finalize", &XcpLogFileWriter::finalize)
        .def("add_frame", &XcpLogFileWriter::add_frame);

    py::class_<MeasurementParameters>(m, "MeasurementParameters")
        .def(py::init<
             std::uint8_t, std::uint8_t, bool, bool, bool, bool, double, std::uint8_t, std::uint16_t, const TimestampInfo&,
             const std::vector<DaqList>&, const std::vector<std::uint16_t>&>())
        .def("dumps", [](const MeasurementParameters& self) { return py::bytes(self.dumps()); })
        .def(
            "__repr__",
            [](const MeasurementParameters& self) {
                std::stringstream ss;
                ss << "MeasurementParameters(";
                ss << "byte_order=\"" << byte_order_to_string(self.m_byte_order) << "\", ";
                ss << "id_field_size=" << static_cast<std::uint16_t>(self.m_id_field_size) << ", ";
                ss << "timestamps_supported=" << bool_to_string(self.m_timestamps_supported) << ", ";
                ss << "ts_fixed=" << bool_to_string(self.m_ts_fixed) << ", ";
                ss << "prescaler_supported=" << bool_to_string(self.m_prescaler_supported) << ", ";
                ss << "selectable_timestamps=" << bool_to_string(self.m_selectable_timestamps) << ", ";
                ss << "ts_scale_factor=" << self.m_ts_scale_factor << ", ";
                ss << "ts_size=" << static_cast<std::uint16_t>(self.m_ts_size) << ", ";
                ss << "min_daq=" << static_cast<std::uint16_t>(self.m_min_daq) << ", ";
                ss << "timestamp_info=" << self.get_timestamp_info().to_string() << ", ";
                ss << "daq_lists=[\n";
                for (const auto& dl : self.m_daq_lists) {
                    ss << dl.to_string() << ",\n";
                }
                ss << "],\n";
                ss << "first_pids=[";
                for (auto fp : self.m_first_pids) {
                    ss << fp << ", ";
                }
                ss << "]";
                return ss.str();
            }
        )
        .def_property_readonly("byte_order", &MeasurementParameters::get_byte_order)
        .def_property_readonly("id_field_size", &MeasurementParameters::get_id_field_size)
        .def_property_readonly("timestamps_supported", &MeasurementParameters::get_timestamps_supported)
        .def_property_readonly("ts_fixed", &MeasurementParameters::get_ts_fixed)
        .def_property_readonly("prescaler_supported", &MeasurementParameters::get_prescaler_supported)
        .def_property_readonly("selectable_timestamps", &MeasurementParameters::get_selectable_timestamps)
        .def_property_readonly("ts_scale_factor", &MeasurementParameters::get_ts_scale_factor)
        .def_property_readonly("ts_size", &MeasurementParameters::get_ts_size)
        .def_property_readonly("min_daq", &MeasurementParameters::get_min_daq)
        .def_property_readonly("timestamp_info", &MeasurementParameters::get_timestamp_info)
        .def_property_readonly("daq_lists", &MeasurementParameters::get_daq_lists)
        .def_property_readonly("first_pids", &MeasurementParameters::get_first_pids)
        .def_property_readonly("timestamp_info", &MeasurementParameters::get_timestamp_info);

    py::class_<DaqRecorderPolicy, PyDaqRecorderPolicy>(m, "DaqRecorderPolicy", py::dynamic_attr())
        .def(py::init<>())
        .def("create_writer", &DaqRecorderPolicy::create_writer)
        .def("feed", &DaqRecorderPolicy::feed)
        .def("set_parameters", &DaqRecorderPolicy::set_parameters)
        .def("initialize", &DaqRecorderPolicy::initialize)
        .def("finalize", &DaqRecorderPolicy::finalize);

    py::class_<DaqOnlinePolicy, PyDaqOnlinePolicy>(m, "DaqOnlinePolicy", py::dynamic_attr())
        .def(py::init<>())
        .def("on_daq_list", &DaqOnlinePolicy::on_daq_list)
        .def("feed", &DaqOnlinePolicy::feed)
        .def("finalize", &DaqOnlinePolicy::finalize)
        .def("set_parameters", &DaqOnlinePolicy::set_parameters)
        .def("initialize", &DaqOnlinePolicy::initialize);

    py::class_<XcpLogFileDecoder, PyXcpLogFileDecoder>(m, "XcpLogFileDecoder", py::dynamic_attr())
        .def(py::init<const std::string&>())
        .def("run", &XcpLogFileDecoder::run)
        .def("on_daq_list", &XcpLogFileDecoder::on_daq_list)
        .def_property_readonly("parameters", &XcpLogFileDecoder::get_parameters)
        .def_property_readonly("daq_lists", &XcpLogFileDecoder::get_daq_lists)
        .def("get_header", &XcpLogFileDecoder::get_header)
        .def("initialize", &XcpLogFileDecoder::initialize)
        .def("finalize", &XcpLogFileDecoder::finalize);

    py::class_<ValueHolder>(m, "ValueHolder")
        //.def(py::init<const ValueHolder&>())
        .def(py::init<const std::any&>())
        .def_property_readonly("value", &ValueHolder::get_value);
}
