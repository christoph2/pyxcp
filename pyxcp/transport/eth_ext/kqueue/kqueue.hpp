#if !defined(__KQUEUE_HPP)
#define __KQUEUE_HPP

#include <atomic>
#include <cstdint>
#include <deque>
#include <mutex>
#include <optional>
#include <thread>

#include <sys/event.h>
#include <unistd.h>

#include "iasyncioservice.hpp"
#include "socket.hpp"

class Kqueue : public IAsyncIoService {
   public:
    explicit Kqueue(IoCallbacks callbacks = {}, std::uint16_t = 64, std::optional<std::uint16_t> = std::nullopt);
    ~Kqueue() override;

    Kqueue(const Kqueue&) = delete;
    Kqueue& operator=(const Kqueue&) = delete;

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
    void processSocketEvent(AsyncClientSocket& socket, const struct kevent& event);
    void reportError(AsyncClientSocket* socket, IoType operation, int error) const noexcept;
    void wake() const noexcept;
    void drainWakeup();
    void processUserMessages();
    void unregisterSocket(AsyncClientSocket& socket) noexcept;

    int m_kqueue_fd{-1};
    int m_wakeup_pipe[2]{-1, -1};
    IoCallbacks m_callbacks;
    mutable std::atomic<bool> m_stopping{false};
    mutable std::mutex m_messages_mutex;
    mutable std::deque<UserMessage> m_messages;
    std::thread m_worker;
};

#endif  // __KQUEUE_HPP
