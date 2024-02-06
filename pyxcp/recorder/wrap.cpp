
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include <cstdint>

#include "rekorder.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

class PyDAQParser : public DAQParser {
   public:

    using DAQParser::DAQParser;

    void on_daq_list(
        std::uint16_t daq_list_num, double timestamp0, double timestamp1, const std::vector<measurement_value_t> &measurement
    ) override {
        PYBIND11_OVERRIDE_PURE(void, DAQParser, on_daq_list, daq_list_num, timestamp0, timestamp1, measurement);
    }

    void Initialize() override {
        PYBIND11_OVERRIDE(void, DAQParser, Initialize);
    }

    void finalize() override {
        PYBIND11_OVERRIDE(void, DAQParser, finalize);
    }
};

PYBIND11_MODULE(rekorder, m) {
    m.doc() = "XCP raw frame recorder.";
    py::class_<XcpLogFileReader>(m, "_PyXcpLogFileReader")
        .def(py::init<const std::string &>())
        .def("next_block", &XcpLogFileReader::next_block)
        .def("reset", &XcpLogFileReader::reset)
        .def("get_header_as_tuple", &XcpLogFileReader::get_header_as_tuple);
    py::class_<XcpLogFileWriter>(m, "_PyXcpLogFileWriter")
        .def(py::init<const std::string &, std::uint32_t, std::uint32_t>())
        .def("finalize", &XcpLogFileWriter::finalize)
        .def("add_frame", &XcpLogFileWriter::add_frame);

    py::class_<MeasurementParameters>(m, "_MeasurementParameters")
        .def(py::init<
             std::uint8_t, std::uint8_t, bool, bool, bool, bool, double, std::uint8_t, std::uint16_t, const std::vector<DaqList> &>(
        ));

    py::class_<DAQParser, PyDAQParser>(m, "DAQParser", py::dynamic_attr())
        .def(py::init<>())
        .def("on_daq_list", &DAQParser::on_daq_list)
        .def("feed", &DAQParser::feed)
        .def("finalize", &DAQParser::finalize)
        .def("set_parameters", &DAQParser::set_parameters)
        .def("Initialize", &DAQParser::Initialize);
}
