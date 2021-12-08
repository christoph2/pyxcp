#!/bin/sh
clang++ -std=c++17 -O3 -ggdb -Wall -Wextra -Weffc++ -DLZ4_DEBUG=1 lz4.c rekorder.cpp -o rekorder
