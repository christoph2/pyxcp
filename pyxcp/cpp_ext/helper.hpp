
#if !defined(__HELPER_HPP)
#define __HELPER_HPP

#include <iostream>
#include <utility>

template<typename ...Args>
constexpr void DBG_PRINTN(Args&&... args) noexcept
{
    ((std::cout << std::forward<Args>(args) << " "), ...);
}


#endif // __HELPER_HPP
