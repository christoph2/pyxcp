

#include <pybind11/chrono.h>
#include <pybind11/functional.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>

#include "eth_framing.hpp"
#include "eth_io_backend.hpp"
#include "eth_multicast.hpp"
#include "framing.hpp"
#include "sxi_framing.hpp"
#include "transport_ext.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

[[noreturn]] static void raise_os_error(const std::system_error& error) {
    PyErr_SetObject(PyExc_OSError, py::make_tuple(error.code().value(), error.what()).ptr());
    throw py::error_already_set();
}

using SxiFrLBCN  = SxiReceiver< SxiHeaderFormat::LenByte, SxiChecksumType::None>;
using SxiFrLBC8  = SxiReceiver< SxiHeaderFormat::LenByte, SxiChecksumType::Sum8>;
using SxiFrLBC16 = SxiReceiver< SxiHeaderFormat::LenByte, SxiChecksumType::Sum16>;

using SxiFrLCBCN  = SxiReceiver< SxiHeaderFormat::LenCtrByte, SxiChecksumType::None>;
using SxiFrLCBC8  = SxiReceiver< SxiHeaderFormat::LenCtrByte, SxiChecksumType::Sum8>;
using SxiFrLCBC16 = SxiReceiver< SxiHeaderFormat::LenCtrByte, SxiChecksumType::Sum16>;

using SxiFrLFBCN  = SxiReceiver< SxiHeaderFormat::LenFillByte, SxiChecksumType::None>;
using SxiFrLFBC8  = SxiReceiver< SxiHeaderFormat::LenFillByte, SxiChecksumType::Sum8>;
using SxiFrLFBC16 = SxiReceiver< SxiHeaderFormat::LenFillByte, SxiChecksumType::Sum16>;

using SxiFrLWCN  = SxiReceiver< SxiHeaderFormat::LenWord, SxiChecksumType::None>;
using SxiFrLWC8  = SxiReceiver< SxiHeaderFormat::LenWord, SxiChecksumType::Sum8>;
using SxiFrLWC16 = SxiReceiver< SxiHeaderFormat::LenWord, SxiChecksumType::Sum16>;

using SxiFrLCWCN  = SxiReceiver< SxiHeaderFormat::LenCtrWord, SxiChecksumType::None>;
using SxiFrLCWC8  = SxiReceiver< SxiHeaderFormat::LenCtrWord, SxiChecksumType::Sum8>;
using SxiFrLCWC16 = SxiReceiver< SxiHeaderFormat::LenCtrWord, SxiChecksumType::Sum16>;

using SxiFrLFWCN  = SxiReceiver< SxiHeaderFormat::LenFillWord, SxiChecksumType::None>;
using SxiFrLFWC8  = SxiReceiver< SxiHeaderFormat::LenFillWord, SxiChecksumType::Sum8>;
using SxiFrLFWC16 = SxiReceiver< SxiHeaderFormat::LenFillWord, SxiChecksumType::Sum16>;

class PyFrameAcquisitionPolicy : public FrameAcquisitionPolicy {
   public:

    using FrameAcquisitionPolicy::FrameAcquisitionPolicy;

    void feed(FrameCategory frame_category, std::uint32_t counter, std::uint64_t timestamp, const payload_t &payload) override {
        PYBIND11_OVERRIDE_PURE(void, FrameAcquisitionPolicy, feed, frame_category, counter, timestamp, payload);
    }

    void finalize() override {
        PYBIND11_OVERRIDE_PURE(void, FrameAcquisitionPolicy, finalize);
    }
};

class PyEthIoBackend : public EthIoBackend {
   public:

    using EthIoBackend::EthIoBackend;

    void setup(const EthConfig& eth_config) override { PYBIND11_OVERRIDE_PURE(void, EthIoBackend, setup, eth_config); }

    void connect() override { PYBIND11_OVERRIDE_PURE(void, EthIoBackend, connect); }

    void send(std::string_view frame) override {
        py::gil_scoped_acquire gil;
        py::function override = py::get_override(static_cast<const EthIoBackend *>(this), "send");
        if (!override) {
            py::pybind11_fail("Tried to call pure virtual function \"EthIoBackend::send\"");
        }
        override(py::bytes(frame.data(), frame.size()));
    }

    void close_connection() override { PYBIND11_OVERRIDE_PURE(void, EthIoBackend, close_connection); }

    void start_listening() override { PYBIND11_OVERRIDE_PURE(void, EthIoBackend, start_listening); }

    void stop_listening() override { PYBIND11_OVERRIDE_PURE(void, EthIoBackend, stop_listening); }

    // Python subclasses implement these as properties, so they are resolved as attributes.
    int get_status() const override {
        py::gil_scoped_acquire gil;
        return py::cast(static_cast<const EthIoBackend *>(this)).attr("status").cast<int>();
    }

    void set_status(int value) override {
        py::gil_scoped_acquire gil;
        py::cast(static_cast<const EthIoBackend *>(this)).attr("status") = value;
    }

    bool invalid_socket() const override {
        py::gil_scoped_acquire gil;
        return py::cast(static_cast<const EthIoBackend *>(this)).attr("invalid_socket").cast<bool>();
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
        .value("STIM", FrameCategory::STIM);

    py::enum_<FramingError>(m, "FramingError")
        .value("TruncatedHeader", FramingError::TruncatedHeader)
        .value("TruncatedPayload", FramingError::TruncatedPayload)
        .value("PayloadTooLarge", FramingError::PayloadTooLarge);

    py::enum_<EthProtocol>(m, "EthProtocol")
        .value("UDP", EthProtocol::UDP)
        .value("TCP", EthProtocol::TCP);

    // No `status` / `invalid_socket` properties on the base: Python subclasses define them, native ones bind their own.
    py::class_<EthIoBackend, PyEthIoBackend> eth_io_backend(m, "EthIoBackend", py::dynamic_attr());
    eth_io_backend.def(py::init<py::object>(), py::arg("eth"))
        .def_readwrite("eth", &EthIoBackend::m_eth)
        .def_readwrite("logger", &EthIoBackend::m_logger)
        .def_readwrite("sock", &EthIoBackend::m_sock)
        .def("setup", &EthIoBackend::setup)
        .def("connect", &EthIoBackend::connect)
        .def("send", &EthIoBackend::send, py::arg("frame"))
        .def("close_connection", &EthIoBackend::close_connection)
        .def("start_listening", &EthIoBackend::start_listening)
        .def("stop_listening", &EthIoBackend::stop_listening);
    // True if the backend can be used on this platform/build; checked by create_eth_backend().
    eth_io_backend.attr("available") = true;

    py::class_<EthMulticastSender>(m, "EthMulticastSender")
        .def(py::init<>())
        .def_static("address", [](py::object cluster_id) {
            return EthMulticastSender::address(EthMulticastSender::validate_cluster_id(cluster_id));
        }, py::arg("cluster_id"))
        .def_static("validate_counter", [](py::object counter) {
            return EthMulticastSender::validate_counter(counter);
        }, py::arg("counter"))
        .def_static("build_packet", [](py::object framing, py::object cluster_id, py::object counter) {
            const auto cluster = EthMulticastSender::validate_cluster_id(cluster_id);
            const auto sequence = EthMulticastSender::validate_counter(counter);
            return EthMulticastSender::build_packet(framing, cluster, sequence);
        }, py::arg("framing"), py::arg("cluster_id"), py::arg("counter"))
        .def_property_readonly("enabled", &EthMulticastSender::enabled)
        .def("enable", [](EthMulticastSender& self) {
            try {
                self.enable();
            } catch (const std::system_error& error) {
                raise_os_error(error);
            }
        })
        .def("disable", &EthMulticastSender::disable)
        .def("send", [](EthMulticastSender& self, py::object framing, py::object cluster_id, py::object counter,
                        std::uint16_t port) {
            const auto cluster = EthMulticastSender::validate_cluster_id(cluster_id);
            const auto sequence = EthMulticastSender::validate_counter(counter);
            try {
                self.send(framing, cluster, sequence, port);
            } catch (const std::system_error& error) {
                raise_os_error(error);
            }
        }, py::arg("framing"), py::arg("cluster_id"), py::arg("counter"), py::arg("port"));

    py::class_<FrameAcquisitionPolicy, PyFrameAcquisitionPolicy>(m, "FrameAcquisitionPolicy", py::dynamic_attr())
        .def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t> &>(), py::arg("filtered_out") = std::nullopt)
        .def("feed", &FrameAcquisitionPolicy::feed)
        .def("finalize", &FrameAcquisitionPolicy::finalize)
        .def_property_readonly("filtered_out", &FrameAcquisitionPolicy::get_filtered_out);

    py::class_<LegacyFrameAcquisitionPolicy>(m, "LegacyFrameAcquisitionPolicy", py::dynamic_attr())
        .def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t> &>(), py::arg("filtered_out") = std::nullopt)
        .def("feed", &FrameAcquisitionPolicy::feed)
        .def("finalize", &FrameAcquisitionPolicy::finalize)
        .def_property_readonly("reqQueue", &LegacyFrameAcquisitionPolicy::get_req_queue)
        .def_property_readonly("resQueue", &LegacyFrameAcquisitionPolicy::get_res_queue)
        .def_property_readonly("daqQueue", &LegacyFrameAcquisitionPolicy::get_daq_queue)
        .def_property_readonly("evQueue", &LegacyFrameAcquisitionPolicy::get_ev_queue)
        .def_property_readonly("servQueue", &LegacyFrameAcquisitionPolicy::get_serv_queue)
        .def_property_readonly("metaQueue", &LegacyFrameAcquisitionPolicy::get_meta_queue)
        .def_property_readonly("errorQueue", &LegacyFrameAcquisitionPolicy::get_error_queue)
        .def_property_readonly("stimQueue", &LegacyFrameAcquisitionPolicy::get_stim_queue);

    py::class_<NoOpPolicy>(m, "NoOpPolicy", py::dynamic_attr())
        .def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t> &>(), py::arg("filtered_out") = std::nullopt)
        .def("feed", &FrameAcquisitionPolicy::feed)
        .def("finalize", &FrameAcquisitionPolicy::finalize);

    py::class_<StdoutPolicy>(m, "StdoutPolicy", py::dynamic_attr())
        .def(py::init<const std::optional<FrameAcquisitionPolicy::filter_t> &>(), py::arg("filtered_out") = std::nullopt)
        .def("feed", &FrameAcquisitionPolicy::feed)
        .def("finalize", &FrameAcquisitionPolicy::finalize);

    py::class_<FrameRecorderPolicy>(m, "FrameRecorderPolicy", py::dynamic_attr())
        .def(
            py::init<const std::string &, const std::optional<FrameAcquisitionPolicy::filter_t> &, uint32_t, uint32_t>(),
            py::arg("file_name"), py::arg("filtered_out") = std::nullopt, py::arg("prealloc") = 10UL, py::arg("chunk_size") = 1
        )
        .def("feed", &FrameAcquisitionPolicy::feed)
        .def("finalize", &FrameAcquisitionPolicy::finalize);
    // Transport layer type enum
    py::enum_<XcpTransportLayerType>(m, "XcpTransportLayerType")
        .value("CAN", XcpTransportLayerType::CAN)
        .value("ETH", XcpTransportLayerType::ETH)
        .value("SXI", XcpTransportLayerType::SXI)
        .value("USB", XcpTransportLayerType::USB);

    // XCP checksum type enum
    py::enum_<ChecksumType>(m, "ChecksumType")
        .value("NO_CHECKSUM", ChecksumType::NO_CHECKSUM)
        .value("BYTE_CHECKSUM", ChecksumType::BYTE_CHECKSUM)
        .value("WORD_CHECKSUM", ChecksumType::WORD_CHECKSUM);

    // XCPonEth Configuration Values.
    py::class_<EthConfig>(m, "EthConfig")
        .def(py::init<>())
        .def_property("host", [](const EthConfig &self) { return self.m_host; }, [](EthConfig &self, const std::string& host) { self.m_host = host;})
        .def_property("port", [](const EthConfig &self) { return self.m_port; }, [](EthConfig &self, uint16_t port) { self.m_port = port; })
        .def_property("protocol", [](const EthConfig &self) { return self.m_protocol; }, [](EthConfig &self, EthProtocol protocol) { self.m_protocol = protocol; })
        .def_property_readonly("use_tcp", [](const EthConfig &self) { return self.use_tcp(); })
        .def_property("ipv6", [](const EthConfig &self) { return self.m_ipv6; }, [](EthConfig &self, bool ipv6) { self.m_ipv6 = ipv6; })
        .def_property("use_tcp_no_delay", [](const EthConfig &self) { return self.m_use_tcp_no_delay; }, [](EthConfig &self, bool use_tcp_no_delay) { self.m_use_tcp_no_delay = use_tcp_no_delay; })
        .def_property("ptp_timestamping", [](const EthConfig &self) { return self.m_ptp_timestamping; }, [](EthConfig &self, bool ptp_timestamping) { self.m_ptp_timestamping = ptp_timestamping; })
        .def_property("bind_to", [](const EthConfig &self) { return self.m_bind_to; }, [](EthConfig &self, const std::optional<std::tuple<std::string, std::uint16_t>> &bind_to) { self.m_bind_to = bind_to; })
        .def_property("multicast_enabled", [](const EthConfig &self) { return self.m_multicast_enabled; }, [](EthConfig &self, bool multicast_enabled) { self.m_multicast_enabled = multicast_enabled; })
        .def_property("iocp_buffer_size", [](const EthConfig &self) { return self.m_iocp_buffer_size; }, [](EthConfig &self, const std::optional<std::uint16_t> &iocp_buffer_size) { self.m_iocp_buffer_size = iocp_buffer_size; })
        .def_property("iocp_receive_queue_depth", [](const EthConfig &self) { return self.m_iocp_receive_queue_depth; }, [](EthConfig &self, const std::optional<std::uint16_t> &iocp_receive_queue_depth) { self.m_iocp_receive_queue_depth = iocp_receive_queue_depth; })
        .def("__repr__", [](const EthConfig &e) {
            return "<EthConfig host='" + e.m_host + "' port=" + std::to_string(e.m_port) + " protocol=" + std::to_string(static_cast<int>(e.m_protocol)) + " ipv6=" + (e.m_ipv6 ? "true" : "false") + " use_tcp_no_delay=" + (e.m_use_tcp_no_delay ? "true" : "false") + " multicast_enabled=" + (e.m_multicast_enabled ? "true" : "false") + ">";
        });

    // XCP framing configuration and helper
    py::class_<XcpFramingConfig>(m, "XcpFramingConfig")
        .def(py::init<>())
        .def(
            py::init<XcpTransportLayerType, std::uint8_t, std::uint8_t, std::uint8_t, bool, ChecksumType>(),
            "transport_layer_type"_a, "header_len"_a, "header_ctr"_a, "header_fill"_a, "tail_fill"_a = false,
            "tail_cs"_a = ChecksumType::NO_CHECKSUM
        )
        .def_property_readonly("transport_layer_type", [](const XcpFramingConfig &self) { return self.transport_layer_type; })
        .def_property_readonly("header_len", [](const XcpFramingConfig &self) { return self.header_len; })
        .def_property_readonly("header_ctr", [](const XcpFramingConfig &self) { return self.header_ctr; })
        .def_property_readonly("header_fill", [](const XcpFramingConfig &self) { return self.header_fill; })
        .def_property_readonly("tail_fill", [](const XcpFramingConfig &self) { return self.tail_fill; })
        .def_property_readonly("tail_cs", [](const XcpFramingConfig &self) { return self.tail_cs; });

    py::class_<XcpFraming>(m, "XcpFraming")
        .def(py::init<const XcpFramingConfig &>())
        .def(
            "prepare_request",
            [](XcpFraming &self, std::uint32_t cmd, py::bytes data) {
                std::string          s = data;
                std::vector<uint8_t> data_vec(s.begin(), s.end());
                return self.prepare_request(cmd, data_vec);
            },
            "cmd"_a, "data"_a
        )
        .def(
            "prepare_request",
            [](XcpFraming &self, std::uint32_t cmd, py::args data) {
                std::vector<uint8_t> data_vec;
                for (auto item : data) {
                    data_vec.push_back(py::cast<uint8_t>(item));
                }
                return self.prepare_request(cmd, data_vec);
            },
            "cmd"_a
        )
        .def("unpack_header", &XcpFraming::unpack_header, py::arg("data"), py::arg("initial_offset") = 0)
        .def("verify_checksum", &XcpFraming::verify_checksum)
        .def_property("counter_send", &XcpFraming::get_counter_send, &XcpFraming::set_counter_send)
        .def_property_readonly("header_size", &XcpFraming::get_header_size);

#define PYBIND11_SXI_RECEIVER(name)                                                                                                \
    py::class_<name>(m, #name)                                                                                                     \
        .def(                                                                                                                      \
            py::init([](std::function<void(py::bytes, uint16_t, uint16_t)> dispatch_handler) {                                     \
                return new name([dispatch_handler](const std::vector<uint8_t> &payload, uint16_t length, uint16_t counter) {       \
                    py::gil_scoped_acquire acquire;                                                                                \
                    dispatch_handler(py::bytes(reinterpret_cast<const char *>(payload.data()), payload.size()), length, counter);  \
                });                                                                                                                \
            }),                                                                                                                    \
            py::arg("dispatch_handler")                                                                                            \
        )                                                                                                                          \
        .def(                                                                                                                      \
            "feed_bytes",                                                                                                          \
            [](name &self, const py::bytes &data) {                                                                                \
                std::string s = data;                                                                                              \
                self.feed_bytes(s);                                                                                                \
            },                                                                                                                     \
            py::arg("data")                                                                                                        \
        );

    PYBIND11_SXI_RECEIVER(SxiFrLBCN)
    PYBIND11_SXI_RECEIVER(SxiFrLBC8)
    PYBIND11_SXI_RECEIVER(SxiFrLBC16)
    PYBIND11_SXI_RECEIVER(SxiFrLCBCN)
    PYBIND11_SXI_RECEIVER(SxiFrLCBC8)
    PYBIND11_SXI_RECEIVER(SxiFrLCBC16)
    PYBIND11_SXI_RECEIVER(SxiFrLFBCN)
    PYBIND11_SXI_RECEIVER(SxiFrLFBC8)
    PYBIND11_SXI_RECEIVER(SxiFrLFBC16)
    PYBIND11_SXI_RECEIVER(SxiFrLWCN)
    PYBIND11_SXI_RECEIVER(SxiFrLWC8)
    PYBIND11_SXI_RECEIVER(SxiFrLWC16)
    PYBIND11_SXI_RECEIVER(SxiFrLCWCN)
    PYBIND11_SXI_RECEIVER(SxiFrLCWC8)
    PYBIND11_SXI_RECEIVER(SxiFrLCWC16)
    PYBIND11_SXI_RECEIVER(SxiFrLFWCN)
    PYBIND11_SXI_RECEIVER(SxiFrLFWC8)
    PYBIND11_SXI_RECEIVER(SxiFrLFWC16)

    py::class_<EthReceiver>(m, "EthReceiver")
        .def(
            py::init([](
                EthProtocol proto,
                std::function<void(py::bytes, uint16_t, uint16_t, uint64_t)> dispatch_handler,
                std::function<void(FramingError, std::size_t)> error_handler,
                std::size_t max_payload_size) {
                    EthReceiver::dispatch_t dispatch = [dispatch_handler](EthReceiver::payload_t payload, uint16_t counter, uint64_t timestamp) {
                        py::gil_scoped_acquire acquire;

                        dispatch_handler(
                            py::bytes(reinterpret_cast<const char *>(payload.data()), payload.size()),
                            static_cast<uint16_t>(payload.size()), counter, timestamp
                        );
                    };
                    EthReceiver::error_handler_t on_error = [error_handler](FramingError error, std::size_t offset) {
                        py::gil_scoped_acquire acquire;
                        error_handler(error, offset);
                    };
                    return std::make_unique<EthReceiver>(proto, std::move(dispatch), std::move(on_error), max_payload_size);
                }
            ), py::arg("proto"), py::arg("dispatch_handler"), py::arg("error_handler"), py::arg("max_payload_size") = 0xFFFF
        )
        .def("feed_frame", [](EthReceiver & self, py::bytes data, uint64_t timestamp) {
                char       *buffer = nullptr;
                py::ssize_t size   = 0;

                if (PYBIND11_BYTES_AS_STRING_AND_SIZE(data.ptr(), &buffer, &size)) {
                    throw py::error_already_set();
                }

                return self.feed_frame(
                    std::span<const uint8_t>(reinterpret_cast<const uint8_t *>(buffer), static_cast<std::size_t>(size)), timestamp
                );
            },
            py::arg("data"), py::arg("timestamp") = 0
        )
    ;
}
