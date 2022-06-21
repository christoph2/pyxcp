
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
        .def("next_record", &_PyXcpLogFileReader::next_record) //, py::return_value_policy::reference)
        .def("get_header", &_PyXcpLogFileReader::get_header)
#if 0
        .def("__iter__", [](std::vector<int>& v) {
            return py::make_iterator(v.begin(), v.end());
            }, py::keep_alive<0, 1>()
        )
#endif
    ;
    py::class_<_PyXcpLogFileWriter>(m, "_PyXcpLogFileWriter")
        .def(py::init<const std::string&, std::uint32_t, std::uint32_t>())
        .def("finalize",  &_PyXcpLogFileWriter::finalize)
        .def("add_frame", &_PyXcpLogFileWriter::add_frame)
    ;
}
