/*
 * IOCP based implementation of the EthIoBackend interface (Windows only).
 *
 * The overlapped sockets / completion port live in this directory; this file glues them to
 * pyxcp.transport.eth.Eth: received datagrams / stream chunks are handed (together with a
 * receive timestamp) to ``eth._eth_receiver.feed_frame()`` straight from the IOCP worker thread,
 * so no extra Python reader thread is needed.
 */

#include <pybind11/pybind11.h>

#include <algorithm>
#include <atomic>
#include <cctype>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <variant>
#include <thread>

#include "asynchiofactory.hpp"
#include "eth_io_backend.hpp"
#include "socket.hpp"
#include "concurrent_queue.hpp"

namespace py = pybind11;

namespace {

[[noreturn]] void raiseOsError(int code, const std::string & what) {
    PyErr_SetObject(PyExc_OSError, py::make_tuple(code, what).ptr());
    throw py::error_already_set();
}

}   // namespace

enum class MessageTypeCode : std::uint8_t {
    RECEIVED,
    IO_ERROR,
    TIMEOUT,
};

struct Message {
    MessageTypeCode type;
    IoType operation;
    std::variant<std::string, std::uint32_t, std::monostate> payload;
};

class IocpBackend : public EthIoBackend {
   public:

    explicit IocpBackend(py::object eth) : EthIoBackend(std::move(eth)) {
    }

    ~IocpBackend() override {
        shutdown();
    }

    void setup(const EthConfig& eth_config) override {
        try {
            doSetup(eth_config);
        } catch (const std::system_error & ex) {
            raiseOsError(ex.code().value(), ex.what());
        }
    }

    void connect() override {
        try {
            doConnect();
        } catch (const std::system_error & ex) {
            raiseOsError(ex.code().value(), ex.what());
        }
    }

    void send(std::string_view frame) override {
        if (!m_socket || !m_io) {
            raiseOsError(WSAENOTCONN, "XCPonEth - IOCP backend is not connected");
        }
        if (const int rc = m_socket->write(frame.data(), frame.size()); rc != 0) {
            raiseOsError(rc, "XCPonEth - send failed");
        }
    }

    void close_connection() override {
        shutdown();
    }

    void start_listening() override {
        if (!m_listener_thread.joinable()) {
            m_listener_thread = std::jthread([this]() {
                while (!m_listener_stop_flag.load()) {
                    Message msg;
                    if (m_messages.dequeue(msg, 100)) {
                        if ((msg.type == MessageTypeCode::RECEIVED) && (std::holds_alternative<std::string>(msg.payload))) {
                            onReceive(std::get<std::string>(msg.payload).data(), std::get<std::string>(msg.payload).size());
                        } else if (msg.type == MessageTypeCode::IO_ERROR) {
                            // printf("Listener thread: received error: %s\n", msg.error_message.c_str());
                        }
                    } else {
                        std::this_thread::yield();
                    }
                }
            });
        }
    }

    void stop_listening() override {
        if (m_listener_thread.joinable()) {
            // m_logger.attr("info")("Stop listening requested");
            m_listener_stop_flag.store(true);
            m_listener_thread.join();
            // m_logger.attr("info")("OK, listener stopped!");
        } else {
            // // m_logger.attr("info")("Listener thread not running / already stopped.");
        }

    }

    void listen() {
        py::object close_event = m_eth.attr("closeEvent");
        while (!m_closing.load() && !close_event.attr("is_set")().cast<bool>()) {
            close_event.attr("wait")(0.1);
        }
    }

    int get_status() const override {
        return m_status.load();
    }

    void set_status(int value) override {
        m_status.store(value);
    }

    bool invalid_socket() const override {
        return !m_socket || m_socket->getHandle() == INVALID_SOCKET;
    }

   private:

    void doSetup(const EthConfig& eth_config) {
        m_eth_config = eth_config;
        const bool ipv6 = eth_config.m_ipv6;
        const bool use_tcp = eth_config.use_tcp();
        std::string host = eth_config.m_host;
        const int port = eth_config.m_port;

        std::string lowered(host);
        std::transform(lowered.begin(), lowered.end(), lowered.begin(), [](unsigned char c) { return std::tolower(c); });
        if (ipv6 && lowered == "localhost") {
            host = "::1";
        }

        const int family = ipv6 ? PF_INET6 : PF_INET;
        const int socktype = use_tcp ? SOCK_STREAM : SOCK_DGRAM;
        const int protocol = use_tcp ? IPPROTO_TCP : IPPROTO_UDP;

        bool resolved = false;
        {
            py::gil_scoped_release release;
            resolved = SocketAddress::resolve(host.c_str(), port, m_peer, family, socktype, protocol, 0);
        }
        if (!resolved) {
            const std::string msg = "XCPonEth - Failed to resolve address " + host + ":" + std::to_string(port);
            m_logger.attr("critical")(msg);
            throw std::runtime_error(msg);
        }

        m_status.store(0);
        m_closing.store(false);
        m_socket = std::make_unique<AsyncClientSocket>(family, socktype, protocol);
        m_socket->setOption(SOL_SOCKET, SO_REUSEADDR, 1);
        if (use_tcp && m_eth_config.m_use_tcp_no_delay) {
            m_socket->setOption(IPPROTO_TCP, TCP_NODELAY, 1);
        }
        if (m_eth_config.m_ptp_timestamping) {
            m_logger.attr("warning")("PTP hardware timestamping is not supported by the IOCP backend.");
        }

        if (m_eth_config.m_bind_to.has_value()) {
            const auto & [address, bind_port] = *m_eth_config.m_bind_to;
            try {
                m_socket->bind(address, static_cast<std::uint16_t>(bind_port));
            } catch (const std::system_error & ex) {
                const std::string msg = "XCPonEth - Failed to bind socket to given address " + address + ":" + std::to_string(bind_port) +
                                        ": " + ex.what();
                m_logger.attr("critical")(msg);
                throw std::runtime_error(msg);
            }
        }
    }

    void doConnect() {
        if (m_status.load() != 0) {
            return;
        }
        if (!m_socket) {
            throw std::runtime_error("XCPonEth - IOCP backend: connect() called without a usable socket (closed or setup() missing).");
        }
        {
            py::gil_scoped_release release;
            m_socket->connect(m_peer);
        }
        m_socket->setPeerAddress(m_peer);

        m_feed_frame = m_eth.attr("_eth_receiver").attr("feed_frame");
        m_timestamp = m_eth.attr("timestamp");
        m_stream = m_socket->getSocketType() == SOCK_STREAM;

        IoCallbacks callbacks;
        callbacks.on_receive = [this](AsyncClientSocket &, const char * data, std::size_t length, const sockaddr *) {
            m_messages.enqueue(Message{MessageTypeCode::RECEIVED, IoType::IO_READ, std::string(data, length)});
        };
        callbacks.on_disconnect = [this](AsyncClientSocket &) { m_status.store(0); };
        callbacks.on_error = [this](AsyncClientSocket *, IoType operation, unsigned long error) { onError(operation, error); };
        {
            py::gil_scoped_release release;
            m_io = createAsyncIoService(std::move(callbacks), m_eth_config.m_iocp_receive_queue_depth.value_or(64), m_eth_config.m_iocp_buffer_size);
            m_io->registerSocket(*m_socket);
        }
        m_status.store(1);
        std::string proto_str = m_stream ? "TCP" : "UDP";
        m_logger.attr("info")("XCPonEth - Connected to: " + describe(m_peer) + " [" + proto_str + " / experimental]");
        m_logger.attr("info")("XCPonEth - IOCP receive queue depth: " +         std::to_string(m_eth_config.m_iocp_receive_queue_depth.value_or(64)) +
                    ", buffer size: " +
                    (m_eth_config.m_iocp_buffer_size ? std::to_string(*m_eth_config.m_iocp_buffer_size) : std::string("default")));
    }

    static std::string describe(const SocketAddress & address) {
        char host[NI_MAXHOST] = {0};
        char service[NI_MAXSERV] = {0};
        if (::getnameinfo(address.data(), address.length(), host, sizeof(host), service, sizeof(service), NI_NUMERICHOST | NI_NUMERICSERV) != 0) {
            return "<unknown>";
        }
        return std::string(host) + ":" + service;
    }

    void onReceive(const char * data, std::size_t length) {
        py::gil_scoped_acquire gil;
        if (m_closing.load()) {
            return;
        }
        try {
            m_feed_frame(py::bytes(data, length), m_timestamp.attr("value"));
        } catch (py::error_already_set & ex) {
            m_logger.attr("error")(std::string("XCPonEth - IOCP receive handler failed: ") + ex.what());
        }
    }

    void onError(IoType operation, unsigned long error) {
        if (m_closing.load() || error == ERROR_OPERATION_ABORTED) {
            return;
        }
        if (m_stream) {
            m_status.store(0);
        }
        py::gil_scoped_acquire gil;
        try {
            m_logger.attr("error")(
                "XCPonEth - IOCP I/O error (" + std::string(operation == IoType::IO_WRITE ? "write" : "read") + "): Windows error " +
                std::to_string(error)
            );
        } catch (py::error_already_set &) {
        }
    }

    void shutdown() {
        m_closing.store(true);
        m_status.store(0);
        if (m_socket) {
            m_socket->close();
        }
        if (m_io) {
            py::gil_scoped_release release;
            m_io.reset();
        }
        m_socket.reset();
        stop_listening();
    }

    std::jthread m_listener_thread;
    std::atomic<bool> m_listener_stop_flag{false};
    SPSCQueue<Message> m_messages = SPSCQueue<Message> {};
    EthConfig m_eth_config;
    std::unique_ptr<AsyncClientSocket> m_socket;
    std::unique_ptr<IAsyncIoService> m_io;
    SocketAddress m_peer;
    py::object m_feed_frame;
    py::object m_timestamp;
    bool m_stream{false};
    std::atomic<int> m_status{0};
    std::atomic<bool> m_closing{false};
};

PYBIND11_MODULE(eth_ext, m) {
    m.doc() = "IOCP based Ethernet I/O backend (Windows).";

    // The EthIoBackend base class is registered by transport_ext.
    py::module_::import("pyxcp.transport.transport_ext");

    py::class_<IocpBackend, EthIoBackend>(m, "IocpBackend")
        .def(py::init<py::object>(), py::arg("eth"))
        .def("listen", &IocpBackend::listen)
        .def_property("status", &IocpBackend::get_status, &IocpBackend::set_status)
        .def_property_readonly("invalid_socket", &IocpBackend::invalid_socket);
};
