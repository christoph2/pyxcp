

#include <pybind11/chrono.h>
#include <pybind11/functional.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>

#include "transport_ext.hpp"


namespace py = pybind11;
using namespace pybind11::literals;


class PyFrameAcquisitionPolicy : public FrameAcquisitionPolicy {
   public:

    using FrameAcquisitionPolicy::FrameAcquisitionPolicy;

    void feed(
        FrameCategory frame_category, std::uint32_t counter, std::uint64_t timestamp, const payload_t& payload
    ) override {
        PYBIND11_OVERRIDE_PURE(void, FrameAcquisitionPolicy, feed, frame_category, counter, timestamp, payload);
    }


    void finalize() override {
        PYBIND11_OVERRIDE_PURE(void, FrameAcquisitionPolicy, finalize);
    }
};


PYBIND11_MODULE(transport_ext, m) {
    m.doc() = "pyXCP transport-layer base classes.";

	py::enum_<FrameCategory>(m, "FrameCategory")
		.value("METADATA", FrameCategory::META)
		.value("CMD", FrameCategory::CMD)
		.value("RESPONSE", FrameCategory::RES)
		.value("ERROR", FrameCategory::ERR)
		.value("EVENT", FrameCategory::EV)
		.value("SERV", FrameCategory::SERV)
		.value("DAQ", FrameCategory::DAQ)
		.value("STIM", FrameCategory::STIM)
	;

	py::class_<FrameAcquisitionPolicy, PyFrameAcquisitionPolicy>(m, "FrameAcquisitionPolicy", py::dynamic_attr())
		.def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t>&>(), py::arg("filtered_out") = std::nullopt)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
		.def_property_readonly("filtered_out", &FrameAcquisitionPolicy::get_filtered_out)
	;

	py::class_<LegacyFrameAcquisitionPolicy>(m, "LegacyFrameAcquisitionPolicy", py::dynamic_attr())
		.def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t>&>(), py::arg("filtered_out") = std::nullopt)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
		.def_property_readonly("reqQueue", &LegacyFrameAcquisitionPolicy::get_req_queue)
		.def_property_readonly("resQueue", &LegacyFrameAcquisitionPolicy::get_res_queue)
		.def_property_readonly("daqQueue", &LegacyFrameAcquisitionPolicy::get_daq_queue)
		.def_property_readonly("evQueue", &LegacyFrameAcquisitionPolicy::get_ev_queue)
		.def_property_readonly("servQueue", &LegacyFrameAcquisitionPolicy::get_serv_queue)
		.def_property_readonly("metaQueue", &LegacyFrameAcquisitionPolicy::get_meta_queue)
		.def_property_readonly("errorQueue", &LegacyFrameAcquisitionPolicy::get_error_queue)
		.def_property_readonly("stimQueue", &LegacyFrameAcquisitionPolicy::get_stim_queue)
	;

	py::class_<NoOpPolicy>(m, "NoOpPolicy", py::dynamic_attr())
		.def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t>&>(), py::arg("filtered_out") = std::nullopt)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
	;

	py::class_<StdoutPolicy>(m, "StdoutPolicy", py::dynamic_attr())
		.def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t>&>(), py::arg("filtered_out") = std::nullopt)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
	;

	py::class_<FrameRecorderPolicy>(m, "FrameRecorderPolicy", py::dynamic_attr())
		.def(py::init<const std::string&, const std::optional<FrameAcquisitionPolicy::filter_t>&, uint32_t, uint32_t>(),
			py::arg("file_name"), py::arg("filtered_out") = std::nullopt, py::arg("prealloc") = 10UL, py::arg("chunk_size") = 1)
		.def("feed", &FrameAcquisitionPolicy::feed)
		.def("finalize", &FrameAcquisitionPolicy::finalize)
	;
}
