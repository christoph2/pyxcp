#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <mutex>

namespace py = pybind11;
using namespace py::literals;

#if defined(_MSC_VER)
    #pragma warning(disable: 4251 4273)
#endif

#include "stim.hpp"

PYBIND11_MODULE(stim, m) {
    py::class_<DaqEventInfo>(m, "DaqEventInfo")
        .def(py::init<const std::string&, std::int8_t, std::size_t, std::size_t, std::size_t, std::string_view, bool, bool, bool>()
        );

    py::class_<Stim>(m, "Stim")
        .def(py::init<bool>())
        .def("setDaqEventInfo", &Stim::setDaqEventInfo)
        .def("clear", &Stim::clear)
        .def("freeDaq", &Stim::freeDaq)
        .def("allocDaq", &Stim::allocDaq)
        .def("allocOdt", &Stim::allocOdt)
        .def("allocOdtEntry", &Stim::allocOdtEntry)
        .def("setDaqPtr", &Stim::setDaqPtr)
        .def("clearDaqList", &Stim::clearDaqList)
        .def("writeDaq", &Stim::writeDaq)
        .def("setDaqListMode", &Stim::setDaqListMode)
        .def("startStopDaqList", &Stim::startStopDaqList)
        .def("startStopSynch", &Stim::startStopSynch)

        .def("set_first_pid", &Stim::set_first_pid)
        .def("set_policy_feeder", [](Stim& self, const py::function& callback) { self.set_policy_feeder(callback); })
        .def("set_frame_sender", [](Stim& self, const py::function& callback) { self.set_frame_sender(callback); });

    py::class_<FakeEnum>(m, "FakeEnum")
        .def(py::init<std::uint8_t>())
        .def_property_readonly("name", &FakeEnum::get_name)
        .def_property_readonly("value", &FakeEnum::get_value)
        .def("bit_length", &FakeEnum::bit_length)
        .def("to_bytes", &FakeEnum::to_bytes)
        .def("__int__", [](const FakeEnum& self) { return self.get_value(); });
    ;
}
