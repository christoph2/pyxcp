
#include <cstdint>

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include "rekorder.hpp"

namespace py = pybind11;
using namespace pybind11::literals;


PYBIND11_MODULE(rekorder, m) {
    m.doc() = "XCP raw frame recorder.";
    py::class_<XcpLogFileReader>(m, "_PyXcpLogFileReader")
        .def(py::init<const std::string &>())
        .def("next_block", &XcpLogFileReader::next_block)
        .def("reset", &XcpLogFileReader::reset)
        .def("get_header_as_tuple", &XcpLogFileReader::get_header_as_tuple)
    ;
    py::class_<XcpLogFileWriter>(m, "_PyXcpLogFileWriter")
        .def(py::init<const std::string&, std::uint32_t, std::uint32_t>())
        .def("finalize",  &XcpLogFileWriter::finalize)
        .def("add_frame", &XcpLogFileWriter::add_frame)
    ;
}
