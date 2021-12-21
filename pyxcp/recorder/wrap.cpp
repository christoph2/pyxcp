
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "rekorder.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

int add(int i, int j) {
    return i + j;
}

class PyXcpLogFileReader : public XcpLogFileReader {
public:
    using XcpLogFileReader::XcpLogFileReader;

    void run() {

    }

    auto py_get_header() -> py::tuple {
        auto hdr = get_header();
        return py::make_tuple(
            hdr.record_count,
            hdr.size_uncompressed,
            hdr.size_compressed,
            (double)hdr.size_uncompressed / (double)hdr.size_compressed
        );
    }

#if 0
    std::string go(int n_times) override {
        PYBIND11_OVERRIDE_PURE(std::string, Animal, go, n_times);
    }

    std::string name() override {
        PYBIND11_OVERRIDE(std::string, Animal, name, );
    }
#endif
};


PYBIND11_MODULE(rekorder, m) {
    m.doc() = "pybind11 example plugin";
    m.def("add", &add, "A function which adds two numbers",
	py::arg("i") = 1, py::arg("j") = 2
    );
    py::class_<PyXcpLogFileReader>(m, "XcpLogFileReader")
        .def(py::init<const std::string &>())
//        .def("next",  &XcpLogFileReader::next)
        .def("get_header",  &PyXcpLogFileReader::py_get_header)
        .def("run",  &PyXcpLogFileReader::run)
    ;
}

