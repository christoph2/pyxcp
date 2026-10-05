#if !defined(__ETH_IO_BACKEND_HPP)
#define __ETH_IO_BACKEND_HPP

#include <pybind11/pybind11.h>

#include <optional>
#include <string_view>
#include <utility>

#include "eth_config.hpp"

/*
 * Abstract low-level I/O strategy for pyxcp.transport.eth.Eth.
 *
 * A backend owns the physical connection (socket / IOCP handle / ...), sends raw frames and
 * pumps received bytes (plus a timestamp) into ``eth._eth_receiver.feed_frame()``.
 *
 * Backends may be implemented in Python (subclassing the bound class) or natively in C++.
 */
class EthIoBackend {
   public:

    explicit EthIoBackend(pybind11::object eth) : m_eth(std::move(eth)) {
        m_logger = m_eth.attr("logger");
    }

    virtual ~EthIoBackend() = default;

    // Resolve addresses and create the underlying socket(s)/handle(s). Called once before connect().
    virtual void setup(const EthConfig& eth_config) = 0;
    // Establish the connection and start receiving.
    virtual void connect() = 0;
    // Send a fully framed XCP PDU.
    virtual void send(std::string_view frame) = 0;
    // Tear down the connection; must be idempotent.
    virtual void close_connection() = 0;
    // Start background thread(s)/loop(s) required for receiving.
    virtual void start_listening() = 0;
    // Stop what start_listening() started; must return promptly.
    virtual void stop_listening() = 0;
    // 0: disconnected, 1: connected.
    virtual int get_status() const = 0;
    virtual void set_status(int value) = 0;
    // True if the underlying socket/handle is not usable anymore.
    virtual bool invalid_socket() const = 0;

    pybind11::object m_eth;
    pybind11::object m_logger;
    // Underlying Python socket for socket based backends, None otherwise.
    pybind11::object m_sock{pybind11::none()};
};

#endif  // __ETH_IO_BACKEND_HPP
