cmake_minimum_required(VERSION 3.12)
project(eth_booster VERSION 0.1.0 LANGUAGES CXX)

set(BUILD_SHARED_LIBS false)

set(BASE_DIR "../../cxx")

if(WIN32)
    set(_PS "win")
elseif(UNIX)
    set(_PS "linux")
endif(WIN32)


add_library(eth
    ${BASE_DIR}/utils.cpp
)
if(WIN32)
    set(ADD_LIBS ws2_32)
elseif(UNIX)
    set(ADD_LIBS pthread rt)
endif(WIN32)

target_compile_features(eth PRIVATE cxx_std_14)
target_include_directories(eth PUBLIC ${BASE_DIR} ${BASE_DIR}/${_PS})

add_executable(test_timestamp tests/test_timestamp.cpp)
target_include_directories(
    test_timestamp PUBLIC
    ${eth_booster_SOURCE_DIR}
    ${eth_booster_SOURCE_DIR}/${_PS}
)
target_link_libraries(test_timestamp eth)


add_executable(test_pool tests/test_pool.cpp)
target_include_directories(
    test_pool PUBLIC
    ${eth_booster_SOURCE_DIR}
    ${eth_booster_SOURCE_DIR}/${_PS}
)
target_link_libraries(test_pool eth)

add_executable(blocking_client ${BASE_DIR}/blocking_socket.cpp  ${BASE_DIR}/blocking_client.cpp)
target_include_directories(
    blocking_client PUBLIC
    ${eth_booster_SOURCE_DIR}
#    ${eth_booster_SOURCE_DIR}/${_PS}
)
target_link_libraries(blocking_client eth ${ADD_LIBS})

