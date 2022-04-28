#if !defined(__EXCEPTIONS_HPP)
#define __EXCEPTIONS_HPP

#include <exception>


struct OSException : public std::exception {
    const char * what () const throw() {
        return "OS Exception";
    }
};

struct TimeoutException : public std::exception {
    const char * what () const throw() {
        return "Timeout Exception";
    }
};

struct CapacityExhaustedException : public std::exception {
    const char * what () const throw() {
        return "Capacity Exhausted Exception";
    }
};

struct InvalidObjectException : public std::exception {
    const char * what () const throw() {
        return "Invalid Object Exception";
    }
};
#endif // __EXCEPTIONS_HPP
