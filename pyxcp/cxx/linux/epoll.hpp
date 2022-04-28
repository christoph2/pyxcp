#if !defined(__EPOLL_HPP)
#define __EPOLL_HPP

#include <memory>
#include <vector>

#include <unistd.h>
#include <pthread.h>
#include <sys/epoll.h>

#include "socket.hpp"
#include "iasyncioservice.hpp"

void *  WorkerThread(void * param);

enum class EventType {
    SOCKET,
    TIMEOUT
};

struct EventRecord {
    EventType event_type;
    union {
        Socket const * socket;
        TimeoutTimer const * timeout_timer;
    } obj;
};

class Epoll : public IAsyncIoService {
public:
    Epoll(size_t numProcessors = 1, size_t multiplier = 1) {
        int ret;

        m_epoll_fd = ::epoll_create(42);
        ret = pthread_create(&m_worker_thread, nullptr, &WorkerThread, reinterpret_cast<void*>(this));
        if (ret != 0) {
            OsErrorExit("Epoll:Epoll() -- Create worker thread");
        }
    }

    ~Epoll() {
        ::close(m_epoll_fd);
    }

    void registerSocket(Socket& socket) {

        registerHandle(socket.getHandle(), reinterpret_cast<void const*>(&socket), EventType::SOCKET);
        registerHandle(socket.getTimeout().getHandle(), reinterpret_cast<void const*>(&socket.getTimeout()), EventType::TIMEOUT);
        printf("S: %d T: %d\n", socket.getHandle(), socket.getTimeout().getHandle());
    }

    void postUserMessage(MessageCode messageCode, void * data = nullptr) const {}
    void postQuitMessage() const {}

    HANDLE getHandle() const {
        return m_epoll_fd;
    }

protected:

    void registerHandle(HANDLE handle, void const * data_ptr, EventType event_type) {

        struct epoll_event event;
        auto event_record = std::make_shared<EventRecord>();
        m_events.emplace_back(event_record);

        event_record->event_type = event_type;
        if (event_type == EventType::SOCKET) {
            event_record->obj.socket = reinterpret_cast<Socket const*>(data_ptr);
        } else if (event_type == EventType::TIMEOUT) {
            event_record->obj.timeout_timer = static_cast<TimeoutTimer const*>(data_ptr);
        }
        event.data.ptr = event_record.get();
        event.events = EPOLLIN;
        if (::epoll_ctl(m_epoll_fd, EPOLL_CTL_ADD, handle, &event) == -1) {
            OsErrorExit("Epoll::registerHandle()");
        }
    }

private:
    int m_epoll_fd;
    pthread_t m_worker_thread;
    std::vector<std::shared_ptr<EventRecord>> m_events;
};


#endif // __EPOLL_HPP
