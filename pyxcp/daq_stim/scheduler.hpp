

#ifndef STIM_SCHEDULER_HPP
#define STIM_SCHEDULER_HPP

#if !defined(_CRT_SECURE_NO_WARNINGS)
    #define _CRT_SECURE_NO_WARNINGS (1)
#endif

#include <stdio.h>

#if defined(_WIN32)
    #include <windows.h>

    #include <thread>

VOID CALLBACK TimerRoutine(PVOID lpParam, BOOLEAN TimerOrWaitFired);

struct Scheduler {
    Scheduler()  = default;
    ~Scheduler() = default;

    bool start_thread() noexcept {
        if (timer_thread.joinable()) {
            return false;
        }

        m_TimerQueue = CreateTimerQueue();
        if (NULL == m_TimerQueue) {
            printf("CreateTimerQueue failed (%d)\n", GetLastError());
            return false;
        }

        // Set a timer to call the timer routine in 10 seconds.
        if (!CreateTimerQueueTimer(&m_timer, m_TimerQueue, (WAITORTIMERCALLBACK)TimerRoutine, nullptr, 1, 500, 0)) {
            printf("CreateTimerQueueTimer failed (%d)\n", GetLastError());
            return false;
        }

        stop_timer_thread_flag = false;
        timer_thread           = std::jthread([this]() {
            while (!stop_timer_thread_flag) {
                printf("ENTER SLEEP loop!!!\n");
                SleepEx(INFINITE, TRUE);
                stop_timer_thread_flag = TRUE;
            }
        });
        return true;
    }

    bool stop_thread() noexcept {
        if (!timer_thread.joinable()) {
            return false;
        }
        stop_timer_thread_flag = true;
        // my_queue.put(std::nullopt);
        timer_thread.join();
        return true;
    }

    std::jthread timer_thread{};
    bool         stop_timer_thread_flag{};
    HANDLE       m_timer{};
    HANDLE       m_TimerQueue;
};
#else

struct Scheduler {
    Scheduler()  = default;
    ~Scheduler() = default;
};

#endif

#endif  // STIM_SCHEDULER_HPP
