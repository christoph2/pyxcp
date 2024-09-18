
cmake_minimum_required(VERSION 3.20...3.30)
project(pyxcp_extensions LANGUAGES C CXX)


if(POLICY CMP0135)
  cmake_policy(SET CMP0135 NEW)
endif()
cmake_policy(SET CMP0094 NEW)

find_package(Python3 COMPONENTS Interpreter Development)
find_package(pybind11 CONFIG)

SET(CMAKE_C_STANDARD 17)
set(CMAKE_CXX_STANDARD 23)

message( STATUS "Found pybind11 v${pybind11_VERSION} ${pybind11_VERSION_TYPE}: ${pybind11_INCLUDE_DIRS}")

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/dist")


SET(GCC_N_CLANG_BASE_OPTIONS "-std=c++23 -Wall -Wextra -Wpedantic -Warray-bounds -mtune=native -fexceptions")

SET(MSVC_BASE_OPTIONS "/W3 /permissive- /EHsc /bigobj /Zc:__cplusplus /std:c++latest")



if (CMAKE_BUILD_TYPE STREQUAL "Debug")
	if (MSVC)
		SET(MSVC_BASE_OPTIONS "${MSVC_BASE_OPTIONS}  /Od /fsanitize=address /Zi")
	else()
		SET(MSVC_BASE_OPTIONS "${MSVC_BASE_OPTIONS} -Og -g3 -ggdb --fno-omit-frame-pointer -fsanitize=address -fsanitize=undefined -fsanitize=bounds")	# -fsanitize=hwaddress
	endif()
else ()
	if (MSVC)
		SET(MSVC_BASE_OPTIONS "${MSVC_BASE_OPTIONS} /Ox")
	else()
		SET(MSVC_BASE_OPTIONS "${MSVC_BASE_OPTIONS} -O3 --fomit-frame-pointer")
	endif()
 endif ()


if (CMAKE_SYSTEM_NAME STREQUAL  "Darwin")
    set(ENV{MACOSX_DEPLOYMENT_TARGET}  "11.0")
	SET(GCC_N_CLANG_EXTRA_OPTIONS "-stdlib=libc++")
	message("Platform is Darwin")
elseif (CMAKE_SYSTEM_NAME STREQUAL  "Windows")
	message("Platform is WINDOWS")
	SET(MSVC_EXTRA_OPTIONS "")
elseif (CMAKE_SYSTEM_NAME STREQUAL  "Linux")
	SET(GCC_N_CLANG_EXTRA_OPTIONS "-fvisibility=hidden -g0") # -fcoroutines
	message("Platform is LINUX")
endif()


IF (CMAKE_C_COMPILER_ID STREQUAL "GNU")

ELSEIF (CMAKE_C_COMPILER_ID MATCHES "Clang")

ELSEIF (CMAKE_C_COMPILER_ID MATCHES "MSVC")

ELSE ()

ENDIF ()

IF (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")

ELSEIF (CMAKE_CXX_COMPILER_ID MATCHES "Clang")

ELSEIF (CMAKE_CXX_COMPILER_ID MATCHES "MSVC")

ELSE ()


ENDIF ()

message("Compiling C with: " ${CMAKE_C_COMPILER_ID})
message("Compiling Cpp with: " ${CMAKE_CXX_COMPILER_ID})

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(EXTENSION_INCS ${CMAKE_CURRENT_SOURCE_DIR}/pyxcp/cpp_ext)

pybind11_add_module(rekorder pyxcp/recorder/wrap.cpp pyxcp/recorder/lz4.c pyxcp/recorder/lz4hc.c)
pybind11_add_module(cpp_ext pyxcp/cpp_ext/extension_wrapper.cpp)
pybind11_add_module(stim pyxcp/daq_stim/stim_wrapper.cpp pyxcp/daq_stim/stim.cpp pyxcp/daq_stim/scheduler.cpp)

target_include_directories(rekorder PRIVATE ${EXTENSION_INCS} ${CMAKE_CURRENT_SOURCE_DIR}/pyxcp/recorder)
target_include_directories(cpp_ext PRIVATE ${EXTENSION_INCS})
target_include_directories(stim PRIVATE ${EXTENSION_INCS} ${CMAKE_CURRENT_SOURCE_DIR}/pyxcp/daq_stim)

target_compile_options(rekorder PUBLIC "-DEXTENSION_NAME=pyxcp.recorder.rekorder")
target_compile_options(cpp_ext PUBLIC "-DEXTENSION_NAME=pyxcp.cpp_ext.cpp_ext")
target_compile_options(stim PUBLIC "-DEXTENSION_NAME=pyxcp.daq_stim.stim")

add_executable(asamkeydll ${CMAKE_CURRENT_SOURCE_DIR}/pyxcp/asamkeydll.c)
if (CMAKE_SYSTEM_NAME STREQUAL  "Linux")
	target_link_libraries(asamkeydll PRIVATE dl)
endif()


if (CMAKE_SIZEOF_VOID_P EQUAL 8)
    # CMAKE_SYSTEM_NAME STREQUAL  "Windows"
endif()

IF (CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
	SET(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} ${GCC_N_CLANG_BASE_OPTIONS} ${GCC_N_CLANG_EXTRA_OPTIONS}")
	target_link_options(cpp_ext PUBLIC -flto=auto)
	target_link_options(stim PUBLIC -flto=auto)
	target_link_options(rekorder PUBLIC -flto=auto)
ELSEIF (CMAKE_C_COMPILER_ID MATCHES "MSVC")
	SET(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} ${MSVC_BASE_OPTIONS} ${MSVC_EXTRA_OPTIONS}")
ENDIF()

IF (CMAKE_SYSTEM_NAME STREQUAL  "Linux" AND CMAKE_CXX_COMPILER_ID MATCHES "Clang")
	# SET(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS}" -fuse-ld=lld)
ENDIF()

# target_include_directories(preprocessor PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/pya2l/extensions>)
# target_link_libraries(preprocessor pybind11::headers)
# set_target_properties(preprocessor PROPERTIES INTERPROCEDURAL_OPTIMIZATION ON CXX_VISIBILITY_PRESET ON VISIBILITY_INLINES_HIDDEN ON)

install(TARGETS rekorder LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/pyxcp/recorder)
install(TARGETS cpp_ext LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/pyxcp/cpp_ext)
install(TARGETS stim LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/pyxcp/daq_stim)
# install(TARGETS asamkeydll LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/pyxcp/)
