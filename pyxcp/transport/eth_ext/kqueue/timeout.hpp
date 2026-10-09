#if !defined(__KQUEUE_TIMEOUT_HPP)
#define __KQUEUE_TIMEOUT_HPP

#include <cstdint>

class TimeoutTimer {
   public:
    explicit TimeoutTimer(std::uint64_t value) : m_millis(value) {}

    void arm() {}
    void disarm() {}
    int getHandle() const { return -1; }
    std::uint64_t getValue() const { return m_millis; }
    void setValue(std::uint64_t value) { m_millis = value; }

   private:
    std::uint64_t m_millis;
};

#endif  // __KQUEUE_TIMEOUT_HPP
