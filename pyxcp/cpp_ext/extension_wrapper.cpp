
#include <pybind11/chrono.h>
#include <pybind11/functional.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>

#include "mcobject.hpp"
#include "bin.hpp"
#include "daqlist.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

PYBIND11_MODULE(cpp_ext, m) {
    m.doc() = "C++ extensions for pyXCP.";

    py::class_<McObject>(m, "McObject")
        .def(py::init<std::string_view, std::uint32_t, std::uint8_t, std::uint16_t, const std::string&, const std::vector<McObject>&>()
            ,"name"_a, "address"_a, "ext"_a, "length"_a, "data_type"_a="", "components"_a=std::vector<McObject>()
             )
        .def_property("name", &McObject::get_name, &McObject::set_name)
        .def_property("address", &McObject::get_address, &McObject::set_address)
        .def_property("ext", &McObject::get_ext, &McObject::set_ext)
        .def_property("length", &McObject::get_length, &McObject::set_length)
        .def_property("data_type", &McObject::get_data_type, &McObject::set_data_type)

        .def("add_component", &McObject::add_component, "component"_a)
         .def("__repr__", [](const McObject& self) {
           return to_string(self);
        })
    ;

    py::class_<Bin>(m, "Bin")
        .def(py::init<std::uint16_t>(), "size"_a)
        .def_property("size", &Bin::get_size, &Bin::set_size)
        .def_property("residual_capacity", &Bin::get_residual_capacity, &Bin::set_residual_capacity)
        .def_property("entries", &Bin::get_entries, nullptr)
        .def("append", &Bin::append)

        .def("__repr__", [](const Bin& self) {
            return to_string(self);
        })

        .def("__eq__", [](const Bin& self, const Bin& other) {
            return self == other;
        })

        .def("__len__", [](const Bin& self) {
            return std::size(self.get_entries());
        })
    ;

    py::class_<DaqList>(m, "DaqList")
        .def(py::init<std::uint16_t, bool, const std::vector<DaqList::daq_list_initialzer_t>&>(),
             "event_num"_a, "enable_timestamps"_a, "measurements"_a)
        .def_property("event_num", &DaqList::get_event_num, nullptr)
        .def_property("enable_timestamps", &DaqList::get_enable_timestamps, nullptr)
        .def_property("measurements", &DaqList::get_measurements, nullptr)
        .def_property("measurements_opt", &DaqList::get_measurements_opt, &DaqList::set_measurements_opt)
        .def_property("header_names", &DaqList::get_header_names, nullptr)
        .def_property("odt_count", &DaqList::get_odt_count, nullptr)
        .def_property("total_entries", &DaqList::get_total_entries, nullptr)
        .def_property("total_length", &DaqList::get_total_length, nullptr)
    ;

}
