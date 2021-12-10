
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "rekorder.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

int add(int i, int j) {
    return i + j;
}


PYBIND11_MODULE(rekorder, m) {
    m.doc() = "pybind11 example plugin";
    m.def("add", &add, "A function which adds two numbers",
	py::arg("i") = 1, py::arg("j") = 2
    );
    py::class_<XcpLogFileReader>(m, "XcpLogFileReader")
        .def(py::init<const std::string &>())
        .def("next",  &XcpLogFileReader::next)
    ;
}

