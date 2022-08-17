#!/bin/sh
g++ -std=c++20 -O0 -ffast-math -ftree-vectorize -ftree-vectorizer-verbose=9 -fcoroutines -ggdb -Wall -Wextra -Weffc++ -DLZ4_DEBUG=1 -DSTANDALONE_REKORDER=1 lz4.cpp rekorder.cpp -o rekorder -lpthread
