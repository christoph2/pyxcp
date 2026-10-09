#include <pybind11/pybind11.h>

#include <algorithm>
#include <atomic>
#include <cctype>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>

#include <netinet/tcp.h>

#include "asynchiofactory.hpp"
#include "eth_io_backend.hpp"
#include "socket.hpp"

namespace py = pybind11;

namespace {

[[noreturn]] void raise_os_error(const std::system_error& error) {
    PyErr_SetObject(PyExc_OSError, py::make_tuple(error.code().value(), error.what()).ptr());
    throw py::error_already_set();
}

}  // namespace

class KqueueBackend : public EthIoBackend {
   public:
    explicit KqueueBackend(py::object eth) : EthIoBackend(std::move(eth)) {}

    void setup(const EthConfig& config) override {
        m_config = config;
        const bool use_tcp = config.use_tcp();
        std::string host = config.m_host;
        std::transform(host.begin(), host.end(), host.begin(), [](unsigned char value) {
            return static_cast<char>(std::tolower(value));
        });
        if (config.m_ipv6 && host == "localhost") {
            host = "::1";
        }

        const int family = config.m_ipv6 ? AF_INET6 : AF_INET;
        const int socktype = use_tcp ? SOCK_STREAM : SOCK_DGRAM;
        const int protocol = use_tcp ? IPPROTO_TCP : IPPROTO_UDP;
        if (!SocketAddress::resolve(host.c_str(), config.m_port, m_peer, family, socktype, protocol, 0)) {
            const std::string message = "XCPonEth - Failed to resolve address " + host + ":" + std::to_string(config.m_port);
            m_logger.attr("critical")(message);
            throw std::runtime_error(message);
        }

        try {
            m_socket = std::make_unique<AsyncClientSocket>(family, socktype, protocol);
            m_socket->setOption(SOL_SOCKET, SO_REUSEADDR, 1);
            if (use_tcp && config.m_use_tcp_no_delay) {
                m_socket->setOption(IPPROTO_TCP, TCP_NODELAY, 1);
            }
            if (config.m_ptp_timestamping) {
                m_logger.attr("warning")("PTP hardware timestamping is not supported by the kqueue backend.");
            }
            if (config.m_bind_to.has_value()) {
                const auto& [address, port] = *config.m_bind_to;
                m_socket->bind(address, port);
            }
        } catch (const std::system_error& error) {
            raise_os_error(error);
        }
        m_status.store(0);
        m_closing.store(false);
    }

    void connect() override {
        if (m_status.load() != 0) {
            return;
        }
        if (!m_socket) {
            throw std::runtime_error("XCPonEth - kqueue backend: connect() called before setup().");
        }
        try {
            m_socket->connect(m_peer);
        } catch (const std::system_error& error) {
            raise_os_error(error);
        }
        m_feed_frame = m_eth.attr("_eth_receiver").attr("feed_frame");
        m_timestamp = m_eth.attr("timestamp");
        m_status.store(1);
        m_logger.attr("info")("XCPonEth - Connected to: " + describe(m_peer) + " [" +
                              std::string(m_config.use_tcp() ? "TCP" : "UDP") + " / kqueue]");
    }

    void send(std::string_view frame) override {
        if (!m_socket || m_status.load() == 0) {
            raise_os_error(std::system_error(ENOTCONN, std::generic_category(), "XCPonEth - kqueue backend is not connected"));
        }
        try {
            const int sent = m_socket->send(frame.data(), frame.size());
            if (static_cast<std::size_t>(sent) != frame.size()) {
                throw std::system_error(EIO, std::generic_category(), "XCPonEth - partial frame send");
            }
        } catch (const std::system_error& error) {
            raise_os_error(error);
        }
    }

    void close_connection() override {
        m_closing.store(true);
        m_status.store(0);
        stop_listening();
        if (m_socket) {
            m_socket->close();
            m_socket.reset();
        }
    }

    void start_listening() override {
        if (!m_socket || m_io) {
            return;
        }
        IoCallbacks callbacks;
        callbacks.on_receive = [this](AsyncClientSocket&, const char* data, std::size_t length, const sockaddr*) {
            on_receive(data, length);
        };
        callbacks.on_disconnect = [this](AsyncClientSocket&) { m_status.store(0); };
        callbacks.on_error = [this](AsyncClientSocket*, IoType operation, unsigned long error) { on_error(operation, error); };
        try {
            m_io = createAsyncIoService(std::move(callbacks));
            m_io->registerSocket(*m_socket);
        } catch (const std::system_error& error) {
            m_io.reset();
            raise_os_error(error);
        }
    }

    void stop_listening() override {
        if (m_io) {
            py::gil_scoped_release release;
            m_io.reset();
        }
    }

    void listen() {
        py::object close_event = m_eth.attr("closeEvent");
        while (!m_closing.load() && !close_event.attr("is_set")().cast<bool>()) {
            close_event.attr("wait")(0.1);
        }
    }

    int get_status() const override { return m_status.load(); }
    void set_status(int value) override { m_status.store(value); }

    bool invalid_socket() const override {
        return !m_socket || m_socket->getHandle() == INVALID_NATIVE_HANDLE;
    }

   private:
    static std::string describe(const SocketAddress& address) {
        char host[NI_MAXHOST]{};
        char service[NI_MAXSERV]{};
        if (::getnameinfo(address.data(), address.length(), host, sizeof(host), service, sizeof(service),
                          NI_NUMERICHOST | NI_NUMERICSERV) != 0) {
            return "<unknown>";
        }
        return std::string(host) + ":" + service;
    }

    void on_receive(const char* data, std::size_t length) {
        py::gil_scoped_acquire gil;
        if (m_closing.load()) {
            return;
        }
        try {
            m_feed_frame(py::bytes(data, length), m_timestamp.attr("value"));
        } catch (py::error_already_set& error) {
            m_logger.attr("error")(std::string("XCPonEth - kqueue receive handler failed: ") + error.what());
        }
    }

    void on_error(IoType operation, unsigned long error) {
        if (m_closing.load()) {
            return;
        }
        if (m_config.use_tcp()) {
            m_status.store(0);
        }
        py::gil_scoped_acquire gil;
        m_logger.attr("error")("XCPonEth - kqueue I/O error (" +
                               std::string(operation == IoType::IO_WRITE ? "write" : "read") + "): " +
                               std::to_string(error));
    }

    EthConfig m_config;
    std::unique_ptr<AsyncClientSocket> m_socket;
    std::unique_ptr<IAsyncIoService> m_io;
    SocketAddress m_peer;
    py::object m_feed_frame;
    py::object m_timestamp;
    std::atomic<int> m_status{0};
    std::atomic<bool> m_closing{false};
};

PYBIND11_MODULE(eth_ext, m) {
    m.doc() = "kqueue based Ethernet I/O backend (macOS/FreeBSD).";
    py::module_::import("pyxcp.transport.transport_ext");

    py::class_<KqueueBackend, EthIoBackend>(m, "KqueueBackend")
        .def(py::init<py::object>(), py::arg("eth"))
        .def("listen", &KqueueBackend::listen)
        .def_property("status", &KqueueBackend::get_status, &KqueueBackend::set_status)
        .def_property_readonly("invalid_socket", &KqueueBackend::invalid_socket);
}
