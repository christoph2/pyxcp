#include "kqueue.hpp"

#include <array>
#include <cerrno>
#include <cstdint>
#include <fcntl.h>
#include <system_error>
#include <utility>

#include <sys/socket.h>
#include <time.h>

namespace {
constexpr std::size_t MAX_EVENTS = 16;
constexpr long WAIT_TIMEOUT_MS = 100;

[[noreturn]] void throw_system_error(const char* operation) {
    throw std::system_error(errno, std::generic_category(), operation);
}

void set_pipe_flags(int fd) {
    const int statusFlags = ::fcntl(fd, F_GETFL, 0);
    if (statusFlags == -1 || ::fcntl(fd, F_SETFL, statusFlags | O_NONBLOCK) == -1 ||
        ::fcntl(fd, F_SETFD, FD_CLOEXEC) == -1) {
        throw_system_error("fcntl(wakeup pipe)");
    }
}
}  // namespace

Kqueue::Kqueue(IoCallbacks callbacks, std::uint16_t, std::optional<std::uint16_t>) : m_callbacks(std::move(callbacks)) {
    m_kqueue_fd = ::kqueue();
    if (m_kqueue_fd == -1) {
        throw_system_error("kqueue");
    }
    if (::pipe(m_wakeup_pipe) == -1) {
        const int error = errno;
        ::close(m_kqueue_fd);
        m_kqueue_fd = -1;
        throw std::system_error(error, std::generic_category(), "pipe(wakeup)");
    }

    try {
        set_pipe_flags(m_wakeup_pipe[0]);
        set_pipe_flags(m_wakeup_pipe[1]);
        struct kevent event;
        EV_SET(&event, static_cast<std::uintptr_t>(m_wakeup_pipe[0]), EVFILT_READ, EV_ADD | EV_ENABLE, 0, 0, nullptr);
        if (::kevent(m_kqueue_fd, &event, 1, nullptr, 0, nullptr) == -1) {
            throw_system_error("kevent(wakeup registration)");
        }
    } catch (...) {
        ::close(m_wakeup_pipe[0]);
        ::close(m_wakeup_pipe[1]);
        ::close(m_kqueue_fd);
        m_wakeup_pipe[0] = -1;
        m_wakeup_pipe[1] = -1;
        m_kqueue_fd = -1;
        throw;
    }

    m_worker = std::thread([this] { workerThreadMain(); });
}

Kqueue::~Kqueue() {
    postQuitMessage();
    if (m_worker.joinable()) {
        m_worker.join();
    }
    if (m_wakeup_pipe[0] != -1) {
        ::close(m_wakeup_pipe[0]);
        ::close(m_wakeup_pipe[1]);
    }
    if (m_kqueue_fd != -1) {
        ::close(m_kqueue_fd);
    }
}

void Kqueue::registerSocket(AsyncClientSocket& socket) {
    struct kevent event;
    EV_SET(&event, static_cast<std::uintptr_t>(socket.getHandle()), EVFILT_READ, EV_ADD | EV_ENABLE, 0, 0, &socket);
    if (::kevent(m_kqueue_fd, &event, 1, nullptr, 0, nullptr) == -1) {
        throw_system_error("kevent(socket registration)");
    }
}

void Kqueue::postUserMessage(MessageCode messageCode, void* data) const {
    {
        std::lock_guard lock(m_messages_mutex);
        m_messages.push_back(UserMessage{messageCode, data});
    }
    wake();
}

void Kqueue::postQuitMessage() const {
    postUserMessage(MessageCode::QUIT);
}

HANDLE Kqueue::getHandle() const {
    return m_kqueue_fd;
}

void Kqueue::wake() const noexcept {
    const char value = 1;
    while (::write(m_wakeup_pipe[1], &value, sizeof(value)) == -1) {
        if (errno == EINTR) {
            continue;
        }
        if (errno != EAGAIN) {
            m_stopping.store(true);
        }
        break;
    }
}

void Kqueue::drainWakeup() {
    std::array<char, 128> buffer{};
    while (::read(m_wakeup_pipe[0], buffer.data(), buffer.size()) > 0) {
    }
    processUserMessages();
}

void Kqueue::processUserMessages() {
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

void Kqueue::workerThreadMain() {
    std::array<struct kevent, MAX_EVENTS> events{};
    const struct timespec timeout{WAIT_TIMEOUT_MS / 1000, (WAIT_TIMEOUT_MS % 1000) * 1000000};
    while (!m_stopping.load()) {
        const int count = ::kevent(m_kqueue_fd, nullptr, 0, events.data(), static_cast<int>(events.size()), &timeout);
        if (count == -1) {
            if (errno == EINTR) {
                continue;
            }
            reportError(nullptr, IoType::IO_READ, errno);
            break;
        }
        for (int index = 0; index < count && !m_stopping.load(); ++index) {
            const auto& event = events[static_cast<std::size_t>(index)];
            if (event.ident == static_cast<std::uintptr_t>(m_wakeup_pipe[0])) {
                drainWakeup();
            } else if (event.udata != nullptr) {
                processSocketEvent(*static_cast<AsyncClientSocket*>(event.udata), event);
            }
        }
    }
}

void Kqueue::processSocketEvent(AsyncClientSocket& socket, const struct kevent& event) {
    if ((event.flags & EV_ERROR) != 0 && event.data != 0) {
        reportError(&socket, IoType::IO_READ, static_cast<int>(event.data));
        if (socket.getSocketType() == SOCK_STREAM && m_callbacks.on_disconnect) {
            try {
                m_callbacks.on_disconnect(socket);
            } catch (...) {
            }
        }
        unregisterSocket(socket);
        return;
    }

    bool disconnected = false;
    if (event.filter == EVFILT_READ) {
        std::array<char, 65536> buffer{};
        for (;;) {
            sockaddr_storage peer{};
            socklen_t peerLength = sizeof(peer);
            int received;
            try {
                if (socket.getSocketType() == SOCK_DGRAM) {
                    received = socket.receiveFrom(buffer.data(), buffer.size(), reinterpret_cast<sockaddr*>(&peer), &peerLength);
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
                unregisterSocket(socket);
                return;
            }

            if (received == 0 && socket.getSocketType() == SOCK_STREAM) {
                if (m_callbacks.on_disconnect) {
                    try {
                        m_callbacks.on_disconnect(socket);
                    } catch (...) {
                    }
                }
                unregisterSocket(socket);
                disconnected = true;
                break;
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

    if (!disconnected && (event.flags & EV_EOF) != 0) {
        if (event.data != 0) {
            reportError(&socket, IoType::IO_READ, static_cast<int>(event.data));
        }
        if (socket.getSocketType() == SOCK_STREAM && m_callbacks.on_disconnect) {
            try {
                m_callbacks.on_disconnect(socket);
            } catch (...) {
            }
        }
        unregisterSocket(socket);
    }
}

void Kqueue::unregisterSocket(AsyncClientSocket& socket) noexcept {
    struct kevent event;
    EV_SET(&event, static_cast<std::uintptr_t>(socket.getHandle()), EVFILT_READ, EV_DELETE, 0, 0, nullptr);
    ::kevent(m_kqueue_fd, &event, 1, nullptr, 0, nullptr);
}

void Kqueue::reportError(AsyncClientSocket* socket, IoType operation, int error) const noexcept {
    if (!m_callbacks.on_error) {
        return;
    }
    try {
        m_callbacks.on_error(socket, operation, static_cast<unsigned long>(error));
    } catch (...) {
    }
}
