
#include <cstdint>

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include "rekorder.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

class _PyXcpLogFileReader : public XcpLogFileReader {
public:
    using XcpLogFileReader::XcpLogFileReader;

    auto py_get_header() -> py::tuple {
        auto hdr = get_header();
        return py::make_tuple(
            hdr.num_containers,
            hdr.record_count,
            hdr.size_uncompressed,
            hdr.size_compressed,
            (double)hdr.size_uncompressed / (double)hdr.size_compressed
        );
    }

};

class _PyXcpLogFileWriter : public XcpLogFileWriter {
public:
    using XcpLogFileWriter::XcpLogFileWriter;

};

PYBIND11_MODULE(rekorder, m) {
    m.doc() = "XCP raw frame recorder.";
    py::class_<_PyXcpLogFileReader>(m, "_PyXcpLogFileReader")
        .def(py::init<const std::string &>())
        //.def("next_block",  &_PyXcpLogFileReader::next, py::return_value_policy::move)
        .def("next",  &_PyXcpLogFileReader::next_block, py::return_value_policy::reference)
        .def("get_header",  &_PyXcpLogFileReader::py_get_header)
        .def("reset",  &_PyXcpLogFileReader::reset)
    ;
    py::class_<_PyXcpLogFileWriter>(m, "_PyXcpLogFileWriter")
        .def(py::init<const std::string&, std::uint32_t, std::uint32_t>())
        .def("finalize",  &_PyXcpLogFileWriter::finalize)
        .def("add_frame", &_PyXcpLogFileWriter::add_frame)
    ;
}
