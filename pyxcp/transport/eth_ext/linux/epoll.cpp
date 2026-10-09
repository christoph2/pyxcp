#include "epoll.hpp"

#include <array>
#include <cerrno>
#include <system_error>

#include <sys/socket.h>

namespace {
constexpr std::size_t MAX_EVENTS = 16;
constexpr int EPOLL_TIMEOUT_MS = 100;

[[noreturn]] void throw_system_error(const char* operation) {
    throw std::system_error(errno, std::generic_category(), operation);
}
}  // namespace

Epoll::Epoll(IoCallbacks callbacks, std::uint16_t, std::optional<std::uint16_t>) : m_callbacks(std::move(callbacks)) {
    m_epoll_fd = ::epoll_create1(EPOLL_CLOEXEC);
    if (m_epoll_fd == -1) {
        throw_system_error("epoll_create1");
    }

    m_wakeup_fd = ::eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC);
    if (m_wakeup_fd == -1) {
        const int error = errno;
        ::close(m_epoll_fd);
        m_epoll_fd = -1;
        throw std::system_error(error, std::generic_category(), "eventfd");
    }

    epoll_event event{};
    event.events = EPOLLIN;
    event.data.ptr = nullptr;
    if (::epoll_ctl(m_epoll_fd, EPOLL_CTL_ADD, m_wakeup_fd, &event) == -1) {
        const int error = errno;
        ::close(m_wakeup_fd);
        ::close(m_epoll_fd);
        m_wakeup_fd = -1;
        m_epoll_fd = -1;
        throw std::system_error(error, std::generic_category(), "epoll_ctl(eventfd)");
    }

    m_worker = std::jthread([this] { workerThreadMain(); });
}

Epoll::~Epoll() {
    postQuitMessage();
    if (m_worker.joinable()) {
        m_worker.join();
    }
    if (m_wakeup_fd != -1) {
        ::close(m_wakeup_fd);
    }
    if (m_epoll_fd != -1) {
        ::close(m_epoll_fd);
    }
}

void Epoll::registerSocket(AsyncClientSocket& socket) {
    epoll_event event{};
    event.events = EPOLLIN | EPOLLERR | EPOLLHUP | EPOLLRDHUP;
    event.data.ptr = &socket;
    if (::epoll_ctl(m_epoll_fd, EPOLL_CTL_ADD, socket.getHandle(), &event) == -1) {
        throw_system_error("epoll_ctl(socket)");
    }
}

void Epoll::postUserMessage(MessageCode messageCode, void* data) const {
    {
        std::lock_guard lock(m_messages_mutex);
        m_messages.push_back(UserMessage{messageCode, data});
    }
    wake();
}

void Epoll::postQuitMessage() const {
    postUserMessage(MessageCode::QUIT);
}

HANDLE Epoll::getHandle() const {
    return m_epoll_fd;
}

void Epoll::wake() const noexcept {
    const std::uint64_t value = 1;
    if (::write(m_wakeup_fd, &value, sizeof(value)) == -1 && errno != EAGAIN) {
        m_stopping.store(true);
    }
}

void Epoll::drainWakeup() {
    std::uint64_t value;
    while (::read(m_wakeup_fd, &value, sizeof(value)) == -1 && errno == EINTR) {
    }
    processUserMessages();
}

void Epoll::processUserMessages() {
    std::deque<UserMessage> messages;
    {
        std::lock_guard lock(m_messages_mutex);
        messages.swap(m_messages);
    }
    for (const auto& message : messages) {
        if (message.code == MessageCode::QUIT) {
            m_stopping.store(true);
        } else if (message.code == MessageCode::TIMEOUT && m_callbacks.on_timeout) {
            try {
                m_callbacks.on_timeout();
            } catch (...) {
            }
        }
    }
}

void Epoll::workerThreadMain() {
    std::array<epoll_event, MAX_EVENTS> events{};
    while (!m_stopping.load()) {
        const int count = ::epoll_wait(m_epoll_fd, events.data(), static_cast<int>(events.size()), EPOLL_TIMEOUT_MS);
        if (count == -1) {
            if (errno == EINTR) {
                continue;
            }
            reportError(nullptr, IoType::IO_READ, errno);
            break;
        }
        for (int index = 0; index < count && !m_stopping.load(); ++index) {
            auto* socket = static_cast<AsyncClientSocket*>(events[static_cast<std::size_t>(index)].data.ptr);
            if (socket == nullptr) {
                drainWakeup();
            } else {
                processSocketEvent(*socket, events[static_cast<std::size_t>(index)].events);
            }
        }
    }
}

void Epoll::processSocketEvent(AsyncClientSocket& socket, std::uint32_t events) {
    if ((events & EPOLLIN) != 0) {
        std::array<char, 65536> buffer{};
        for (;;) {
            sockaddr_storage peer{};
            socklen_t peer_length = sizeof(peer);
            int received;
            try {
                if (socket.getSocketType() == SOCK_DGRAM) {
                    received = socket.receiveFrom(buffer.data(), buffer.size(), reinterpret_cast<sockaddr*>(&peer), &peer_length);
                } else {
                    received = socket.receive(buffer.data(), buffer.size());
                }
            } catch (const std::system_error& error) {
                const int code = error.code().value();
                if (code == EAGAIN || code == EWOULDBLOCK) {
                    break;
                }
                reportError(&socket, IoType::IO_READ, code);
                if (socket.getSocketType() == SOCK_STREAM && m_callbacks.on_disconnect) {
                    try {
                        m_callbacks.on_disconnect(socket);
                    } catch (...) {
                    }
                }
                ::epoll_ctl(m_epoll_fd, EPOLL_CTL_DEL, socket.getHandle(), nullptr);
                return;
            }
            if (received == 0 && socket.getSocketType() == SOCK_STREAM) {
                if (m_callbacks.on_disconnect) {
                    try {
                        m_callbacks.on_disconnect(socket);
                    } catch (...) {
                    }
                }
                ::epoll_ctl(m_epoll_fd, EPOLL_CTL_DEL, socket.getHandle(), nullptr);
                return;
            }
            if (m_callbacks.on_receive) {
                try {
                    const sockaddr* address = socket.getSocketType() == SOCK_DGRAM ? reinterpret_cast<sockaddr*>(&peer) : nullptr;
                    m_callbacks.on_receive(socket, buffer.data(), static_cast<std::size_t>(received), address);
                } catch (...) {
                }
            }
            if (socket.getSocketType() == SOCK_STREAM && static_cast<std::size_t>(received) < buffer.size()) {
                break;
            }
        }
    }

    if ((events & (EPOLLERR | EPOLLHUP | EPOLLRDHUP)) != 0) {
        int error = 0;
        socklen_t length = sizeof(error);
        if (::getsockopt(socket.getHandle(), SOL_SOCKET, SO_ERROR, &error, &length) == -1) {
            error = errno;
        }
        if (error != 0) {
            reportError(&socket, IoType::IO_READ, error);
        }
        if (socket.getSocketType() == SOCK_STREAM && m_callbacks.on_disconnect) {
            try {
                m_callbacks.on_disconnect(socket);
            } catch (...) {
            }
        }
        ::epoll_ctl(m_epoll_fd, EPOLL_CTL_DEL, socket.getHandle(), nullptr);
    }
}

void Epoll::reportError(AsyncClientSocket* socket, IoType operation, int error) const noexcept {
    if (!m_callbacks.on_error) {
        return;
    }
    try {
        m_callbacks.on_error(socket, operation, static_cast<unsigned long>(error));
    } catch (...) {
    }
}
