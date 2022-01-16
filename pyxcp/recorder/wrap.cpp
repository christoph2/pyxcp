
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include "rekorder.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

int add(int i, int j) {
    return i + j;
}

template<typename T>
py::array_t<T> create_matrix(std::size_t width, std::size_t height)
{
    auto buffer = py::buffer_info{
        nullptr,
        sizeof(T),// itemsize
        py::format_descriptor<T>::format(),
        2, // ndim
        std::vector<std::size_t> {width, height},
        std::vector<std::size_t> {height * sizeof(T), sizeof(T)},
    };

    return py::array_t<T>(buffer);
}

class PyXcpLogFileReader : public XcpLogFileReader {
public:
    using XcpLogFileReader::XcpLogFileReader;

    py::array_t<float> run() {
        py::array_t<float> arr = create_matrix<float>(2, 2);

        return arr;
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
    m.doc() = "XCP raw frame recorder.";
    m.def("add", &add, "A function which adds two numbers",
	py::arg("i") = 1, py::arg("j") = 2
    );
    py::class_<PyXcpLogFileReader>(m, "XcpLogFileReader")
        .def(py::init<const std::string &>())
        //.def("next",  &PyXcpLogFileReader::next, py::return_value_policy::reference_internal)
        .def("next",  &PyXcpLogFileReader::next, py::return_value_policy::move)
        .def("get_header",  &PyXcpLogFileReader::py_get_header)
        .def("run",  &PyXcpLogFileReader::run)
    ;
}

