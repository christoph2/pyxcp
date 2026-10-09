#if !defined(__EPOLL_HPP)
#define __EPOLL_HPP

#include <atomic>
#include <cstdint>
#include <deque>
#include <mutex>
#include <optional>
#include <thread>

#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <unistd.h>

#include "iasyncioservice.hpp"
#include "socket.hpp"

class Epoll : public IAsyncIoService {
   public:
    explicit Epoll(IoCallbacks callbacks = {}, std::uint16_t = 64, std::optional<std::uint16_t> = std::nullopt);
    ~Epoll() override;

    Epoll(const Epoll&) = delete;
    Epoll& operator=(const Epoll&) = delete;

    void registerSocket(AsyncClientSocket& socket) override;
    void postUserMessage(MessageCode messageCode, void* data = nullptr) const override;
    void postQuitMessage() const override;
    HANDLE getHandle() const override;

   private:
    struct UserMessage {
        MessageCode code;
        void* data;
    };

    void workerThreadMain();
    void processSocketEvent(AsyncClientSocket& socket, std::uint32_t events);
    void reportError(AsyncClientSocket* socket, IoType operation, int error) const noexcept;
    void wake() const noexcept;
    void drainWakeup();
    void processUserMessages();

    int m_epoll_fd{-1};
    int m_wakeup_fd{-1};
    IoCallbacks m_callbacks;
    mutable std::atomic<bool> m_stopping{false};
    mutable std::mutex m_messages_mutex;
    mutable std::deque<UserMessage> m_messages;
    std::jthread m_worker;
};

#endif  // __EPOLL_HPP
