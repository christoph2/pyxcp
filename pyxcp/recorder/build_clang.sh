#!/bin/bash
clang++ -std=c++20 -O0 -fvectorize -Rpass=loop-vectorize -ggdb -Wall -Wextra -Weffc++ -lpthread -DLZ4_DEBUG=1 -DSTANDALONE_REKORDER=1 lz4.cpp rekorder.cpp -o rekorder
