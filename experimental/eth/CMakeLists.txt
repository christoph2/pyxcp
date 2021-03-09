cmake_minimum_required(VERSION 3.12)
project(eth_booster VERSION 0.1.0 LANGUAGES CXX)

set(BUILD_SHARED_LIBS false)
#add_definitions("--std=c++14")

if(WIN32)
    set(_PS "win")
elseif(UNIX)
    set(_PS "linux")
endif(WIN32)


message(STATUS ${MY_INCLUDES})

if(WIN32)
    add_library(eth
        win/exceptions.cpp
        win/iocp.cpp
        win/socket.cpp
        win/timestamp.cpp
    )
elseif(UNIX)
    add_library(eth
        linux/timestamp.cpp
        linux/utils.cpp
    )
endif(WIN32)

target_include_directories(eth PUBLIC . ${_PS})
add_executable(test_timestamp tests/test_timestamp.cpp)
target_include_directories(
    test_timestamp PUBLIC
    ${eth_booster_SOURCE_DIR}
    ${eth_booster_SOURCE_DIR}/${_PS}
)
target_link_libraries(test_timestamp eth)

# ${CMAKE_CURRENT_SOURCE_DIR}
