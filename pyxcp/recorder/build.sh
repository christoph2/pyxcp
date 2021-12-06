#!/bin/bash
clang++ -std=c++17 -O3 -Wall -Wextra -Weffc++ -DLZ4_DEBUG=20 lz4.c rekorder.cpp -o rekorder

