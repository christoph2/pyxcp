#!/bin/bash
g++ -std=c++20 -O3 -ffast-math -ftree-vectorize -ftree-vectorizer-verbose=9 -fcoroutines -ggdb -Wall -Wextra -Weffc++ -DLZ4_DEBUG=1 -DSTANDALONE_REKORDER=1 -I/usr/local/include/python3.7m -I/usr/local/include/python3.7m -I/usr/local/include/python3.7m -I/home/pi/.local/lib/python3.7/site-packages/pybind11/include lz4.cpp rekorder.cpp -o rekorder
