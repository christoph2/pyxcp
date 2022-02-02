#!/bin/bash
clang++ -std=c++17 -O3 -fvectorize -Rpass=loop-vectorize -ggdb -Wall -Wextra -Weffc++ -DLZ4_DEBUG=1 -DSTANDALONE_REKORDER=1 `python3.7-config --includes` `pybind11-config --includes` lz4.cpp rekorder.cpp -o rekorder
