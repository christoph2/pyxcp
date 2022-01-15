#!/bin/bash
clang++ -std=c++17 -O3 -ggdb -Wall -Wextra -Weffc++ -DLZ4_DEBUG=1 -DSTANDALONE_REKORDER=0 `python3.7-config --includes` `pybind11-config --includes` lz4.c rekorder.cpp -o rekorder
