
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include <cstdint>

#include "rekorder.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

class PyDaqOnlinePolicy : public DaqOnlinePolicy {
   public:

    using DaqOnlinePolicy::DaqOnlinePolicy;

    void on_daq_list(
        std::uint16_t daq_list_num, double timestamp0, double timestamp1, const std::vector<measurement_value_t> &measurement
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


PYBIND11_MODULE(rekorder, m) {
    m.doc() = "XCP raw frame recorder."
    ;
   ///  m.def("create_measurement_parameters", &create_measurement_parameters);
    py::class_<Deserializer>(m, "Deserializer")
        .def(py::init<const std::string &>())
        .def("run", &Deserializer::run)
    ;

    py::class_<XcpLogFileReader>(m, "_PyXcpLogFileReader")
        .def(py::init<const std::string &>())
        .def("next_block", &XcpLogFileReader::next_block)
        .def("reset", &XcpLogFileReader::reset)
        .def("get_header_as_tuple", &XcpLogFileReader::get_header_as_tuple)
        .def("get_metadata",[](const XcpLogFileReader& self) {
            return py::bytes(self.get_metadata());
        })
        ;

    py::class_<XcpLogFileWriter>(m, "_PyXcpLogFileWriter")
        .def(py::init<const std::string &, std::uint32_t, std::uint32_t, std::string_view>(),
            py::arg("filename"), py::arg("prealloc"), py::arg("chunk_size"), py::arg("metadata")="")
        .def("finalize", &XcpLogFileWriter::finalize)
        .def("add_frame", &XcpLogFileWriter::add_frame)
    ;

    py::class_<MeasurementParameters>(m, "MeasurementParameters")
        .def(py::init<
             std::uint8_t, std::uint8_t, bool, bool, bool, bool, double, std::uint8_t, std::uint16_t, const std::vector<DaqList> &>(
        ))
        .def("dumps", [](const MeasurementParameters& self) {
            return py::bytes(self.dumps());
        })
        ;

    py::class_<DaqRecorderPolicy, PyDaqRecorderPolicy>(m, "DaqRecorderPolicy", py::dynamic_attr())
        .def(py::init<>())
        .def("create_writer", &DaqRecorderPolicy::create_writer)
        .def("feed", &DaqRecorderPolicy::feed)
        .def("set_parameters", &DaqRecorderPolicy::set_parameters)
        .def("initialize", &DaqRecorderPolicy::initialize)
        .def("finalize", &DaqRecorderPolicy::finalize)
        ;

    py::class_<DaqOnlinePolicy, PyDaqOnlinePolicy>(m, "DaqOnlinePolicy", py::dynamic_attr())
        .def(py::init<>())
        .def("on_daq_list", &DaqOnlinePolicy::on_daq_list)
        .def("feed", &DaqOnlinePolicy::feed)
        .def("finalize", &DaqOnlinePolicy::finalize)
        .def("set_parameters", &DaqOnlinePolicy::set_parameters)
        .def("initialize", &DaqOnlinePolicy::initialize);
}
