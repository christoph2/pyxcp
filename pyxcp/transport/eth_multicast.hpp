#if !defined(__ETH_MULTICAST_HPP)
#define __ETH_MULTICAST_HPP

#if defined(_WIN32) || defined(_WIN64)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <cerrno>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

#include <cstdint>
#include <stdexcept>
#include <string>
#include <system_error>

#include <pybind11/pybind11.h>

class EthMulticastSender {
   public:

    EthMulticastSender() = default;
    EthMulticastSender(const EthMulticastSender&) = delete;
    EthMulticastSender& operator=(const EthMulticastSender&) = delete;

    ~EthMulticastSender() {
        close_socket();
    }

    static std::uint16_t validate_cluster_id(pybind11::handle value) {
        return validate_unsigned(value, 0xFFFF, "cluster_id");
    }

    static std::uint8_t validate_counter(pybind11::handle value) {
        return static_cast<std::uint8_t>(validate_unsigned(value, 0xFF, "counter"));
    }

    static std::string address(std::uint16_t cluster_id) {
        return "239.255." + std::to_string(cluster_id >> 8) + "." + std::to_string(cluster_id & 0xFF);
    }

    static pybind11::bytes build_packet(pybind11::object& framing, std::uint16_t cluster_id, std::uint8_t counter) {
        return framing.attr("prepare_request")(0xF2, 0xFA, cluster_id & 0xFF, cluster_id >> 8, counter).cast<pybind11::bytes>();
    }

    bool enabled() const noexcept {
        return m_socket != invalid_socket;
    }

    void enable() {
        if (enabled()) {
            return;
        }

        const socket_handle socket = ::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (socket == invalid_socket) {
            throw_socket_error(last_socket_error(), "Failed to create XCP multicast socket");
        }

        const int ttl = 2;
#if defined(_WIN32) || defined(_WIN64)
        const int result = setsockopt(socket, IPPROTO_IP, IP_MULTICAST_TTL, reinterpret_cast<const char*>(&ttl), sizeof(ttl));
#else
        const int result = setsockopt(socket, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof(ttl));
#endif
        if (result == socket_error) {
            const int error = last_socket_error();
            close_handle(socket);
            throw_socket_error(error, "Failed to set XCP multicast TTL");
        }
        m_socket = socket;
    }

    void disable() {
        close_socket();
    }

    void send(pybind11::object& framing, std::uint16_t cluster_id, std::uint8_t counter, std::uint16_t port) {
        if (!enabled()) {
            throw std::runtime_error("Multicast socket not available");
        }

        const pybind11::bytes packet = build_packet(framing, cluster_id, counter);
        const std::string data = packet;
        sockaddr_in destination{};
        destination.sin_family = AF_INET;
        destination.sin_port = htons(port);
        const std::uint32_t address_value =
            (239U << 24) | (255U << 16) | static_cast<std::uint32_t>(cluster_id);
        destination.sin_addr.s_addr = htonl(address_value);

#if defined(_WIN32) || defined(_WIN64)
        const int result = sendto(
            m_socket, data.data(), static_cast<int>(data.size()), 0, reinterpret_cast<const sockaddr*>(&destination),
            static_cast<int>(sizeof(destination))
        );
#else
        const auto result = sendto(
            m_socket, data.data(), data.size(), 0, reinterpret_cast<const sockaddr*>(&destination),
            static_cast<socklen_t>(sizeof(destination))
        );
#endif
        if (result == socket_error) {
            throw_socket_error(last_socket_error(), "Failed to send XCP multicast packet");
        }
    }

   private:
#if defined(_WIN32) || defined(_WIN64)
    using socket_handle = SOCKET;
    static constexpr socket_handle invalid_socket = INVALID_SOCKET;
    static constexpr int socket_error = SOCKET_ERROR;

    static int last_socket_error() {
        return WSAGetLastError();
    }

    static void close_handle(socket_handle socket) {
        closesocket(socket);
    }
#else
    using socket_handle = int;
    static constexpr socket_handle invalid_socket = -1;
    static constexpr int socket_error = -1;

    static int last_socket_error() {
        return errno;
    }

    static void close_handle(socket_handle socket) {
        ::close(socket);
    }
#endif

    static std::uint16_t validate_unsigned(pybind11::handle value, std::uint16_t max_value, const char* name) {
        if (!PyLong_Check(value.ptr()) || PyBool_Check(value.ptr())) {
            throw pybind11::value_error(std::string(name) + " must be an integer in the range 0.." + std::to_string(max_value));
        }
        const long long integer = PyLong_AsLongLong(value.ptr());
        if (PyErr_Occurred()) {
            PyErr_Clear();
            throw pybind11::value_error(std::string(name) + " must be an integer in the range 0.." + std::to_string(max_value));
        }
        if (integer < 0 || integer > max_value) {
            throw pybind11::value_error(std::string(name) + " must be an integer in the range 0.." + std::to_string(max_value));
        }
        return static_cast<std::uint16_t>(integer);
    }

    static void throw_socket_error(int error, const char* message) {
#if defined(_WIN32) || defined(_WIN64)
        throw std::system_error(error, std::system_category(), message);
#else
        throw std::system_error(error, std::generic_category(), message);
#endif
    }

    void close_socket() noexcept {
        if (enabled()) {
            const socket_handle socket = m_socket;
            m_socket = invalid_socket;
            close_handle(socket);
        }
    }

    socket_handle m_socket{invalid_socket};
};

#endif  // __ETH_MULTICAST_HPP
