
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
#if 0
        std::string go(int n_times) override {
            PYBIND11_OVERRIDE_PURE(
                std::string, /* Return type */
                Animal,      /* Parent class */
                go,          /* Name of function in C++ (must match Python name) */
                n_times      /* Argument(s) */
            );
        }
#endif
        void do_it() {
            FrameVector const& res = next();
        }
};



PYBIND11_MODULE(rekorder, m) {
    m.doc() = "pybind11 example plugin";
    m.def("add", &add, "A function which adds two numbers",
	py::arg("i") = 1, py::arg("j") = 2
    );
    py::class_<PyXcpLogFileReader>(m, "XcpLogFileReader")
        .def(py::init<const std::string &>())
        .def("do_it",  &PyXcpLogFileReader::do_it)
//        .def("next",  &XcpLogFileReader::next, py::return_value_policy::move)
    ;
}

