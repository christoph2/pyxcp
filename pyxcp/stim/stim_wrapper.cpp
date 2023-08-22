#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <mutex>

namespace py = pybind11;
using namespace py::literals;

#pragma warning(disable: 4251 4273)

#include "stim.hpp"


PYBIND11_MODULE(stim, m) {
	
	m.def("get_writer_lock", &get_writer_lock, py::return_value_policy::reference);
	m.def("get_policy_lock", &get_policy_lock, py::return_value_policy::reference);
	
	py::class_<DaqEventInfo>(m, "DaqEventInfo")
		.def(py::init<const std::string&, std::int8_t, std::size_t, std::size_t, std::size_t, std::string_view, bool, bool, bool>())
	;

    py::class_<Stim>(m, "Stim")
        .def(py::init<>())
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
		
		.def("set_policy_feeder", [](Stim& self, const py::function& callback) { 
			self.set_policy_feeder(callback); 
		})
		
		.def("set_frame_sender", [](Stim& self, const py::function& callback) { 
			self.set_frame_sender(callback); 
		})
		
	;
	
	py::class_<Mutex> (m, "Mutex")
		.def("__enter__", [&] (Mutex& self) { 
			self.lock(); 
		})
		.def("__exit__",
		 [&] (Mutex& self, const std::optional<pybind11::type>& exc_type, const std::optional<pybind11::object>& exc_value, const std::optional<pybind11::object>& traceback) { 
			self.unlock(); 
		 })
    ;
}
