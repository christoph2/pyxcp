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
        .def(py::init<const std::string&, std::int8_t, std::size_t, std::size_t, std::size_t, std::string_view, bool, bool, bool>(),
        "name"_a, "type_code"_a, "cycle"_a, "max_daq_lists"_a, "priority"_a, "consistency"_a, "daq_supported"_a,
        "stim_supported"_a, "packed_supported"_a
        );

    py::class_<StimParameters>(m, "StimParameters")
        .def(py::init<>())
        .def_readwrite("id_field", &StimParameters::id_field)
        .def_readwrite("timestamp_size", &StimParameters::timestamp_size)
        .def_readwrite("max_dto", &StimParameters::max_dto)
        .def_readwrite("min_st_stim", &StimParameters::min_st_stim)
        .def_readwrite("min_daq", &StimParameters::min_daq)
        .def_readwrite("big_endian", &StimParameters::big_endian);

    py::class_<DtoCtrEvent>(m, "DtoCtrEvent")
        .def(py::init<>())
        .def_readwrite("related_event_channel", &DtoCtrEvent::related_event_channel)
        .def_readwrite("daq_mode", &DtoCtrEvent::daq_mode)
        .def_readwrite("stim_mode", &DtoCtrEvent::stim_mode)
        .def_readwrite("event_counter_present", &DtoCtrEvent::event_counter_present)
        .def_readwrite("stim_counter_copy_present", &DtoCtrEvent::stim_counter_copy_present);

    py::class_<Stim>(m, "Stim")
        .def(py::init<bool>(), "activate"_a = true)
        .def_static("enableHighResolutionTimer", &Stim::enableHighResolutionTimer)
        .def("activate", &Stim::activate)
        .def_property_readonly("active", &Stim::isActive)
        .def("setParameters", &Stim::setParameters)
        .def("getParameters", &Stim::getParameters)
        .def("setDaqEventInfo", &Stim::setDaqEventInfo)
        .def("clear", &Stim::clear)
        .def("freeDaq", &Stim::freeDaq)
        .def("allocDaq", &Stim::allocDaq)
        .def("allocOdt", &Stim::allocOdt)
        .def("allocOdtEntry", &Stim::allocOdtEntry)
        .def("setDaqPtr", &Stim::setDaqPtr)
        .def("clearDaqList", &Stim::clearDaqList)
        .def("writeDaq", &Stim::writeDaq)
        .def("writeDaqMultiple", &Stim::writeDaqMultiple)
        .def("setDaqListMode", &Stim::setDaqListMode)
        .def("startStopDaqList", &Stim::startStopDaqList)
        .def("startStopSynch", &Stim::startStopSynch)
        .def("dtoCtrProperties", &Stim::dtoCtrProperties)
        .def("setDtoCtrEvent", &Stim::setDtoCtrEvent)
        .def("getDtoCtrEvent", &Stim::getDtoCtrEvent)
        .def(
            "setDaqPackedMode",
            [](Stim& self, std::uint16_t daq_list_number, std::uint16_t daq_packed_mode, std::uint16_t dpm_timestamp_mode,
               std::uint16_t dpm_sample_count) {
                self.setDaqPackedMode(0, daq_list_number, daq_packed_mode, dpm_timestamp_mode, dpm_sample_count);
            },
            "daq_list_number"_a, "daq_packed_mode"_a, "dpm_timestamp_mode"_a = 0, "dpm_sample_count"_a = 0
        )
        .def("set_first_pid", &Stim::set_first_pid)
        .def("set_policy_feeder", [](Stim& self, const py::function& callback) { self.set_policy_feeder(callback); })
        .def("set_frame_sender", [](Stim& self, const py::function& callback) { self.set_frame_sender(callback); })

        .def("setFieldTypes", &Stim::setFieldTypes, "daq_list_number"_a, "types"_a)
        .def("dataSize", &Stim::dataSize)
        .def("setData", &Stim::setData, "daq_list_number"_a, "data"_a)
        .def("setOdtData", &Stim::setOdtData, "daq_list_number"_a, "odt_number"_a, "data"_a)
        .def("getData", &Stim::getData)
        .def("setValues", &Stim::setValues, "daq_list_number"_a, "values"_a)
        .def("setValue", &Stim::setValue, "daq_list_number"_a, "index"_a, "value"_a)
        .def("getValues", &Stim::getValues)
        .def("trigger", &Stim::trigger, "daq_list_number"_a, "dto_ctr"_a = std::nullopt, "timestamp"_a = 0)
        .def("triggerEvent", &Stim::triggerEvent, "event_channel"_a, "timestamp"_a = 0)
        .def("send", &Stim::send)
        .def("listInfo", &Stim::listInfo)

        .def("addBypass", &Stim::addBypass, "name"_a, "inputs"_a, "outputs"_a, "function"_a = py::none(), "delay"_a = 0,
             "prime"_a = true, "on_inconsistent"_a = py::none())
        .def("removeBypass", &Stim::removeBypass)
        .def("clearBypasses", &Stim::clearBypasses)
        .def("bypassStatistics", &Stim::bypassStatistics)
        .def("feedDaq", &Stim::feedDaq, "daq_list_number"_a, "values"_a, "dto_ctr"_a = std::nullopt);

    py::class_<FakeEnum>(m, "FakeEnum")
        .def(py::init<std::uint8_t>())
        .def_property_readonly("name", &FakeEnum::get_name)
        .def_property_readonly("value", &FakeEnum::get_value)
        .def("bit_length", &FakeEnum::bit_length)
        .def("to_bytes", &FakeEnum::to_bytes)
        .def("__int__", [](const FakeEnum& self) { return self.get_value(); })
        .def("__index__", [](const FakeEnum& self) { return self.get_value(); });
}
