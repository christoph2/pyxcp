#!/bin/bash - 
#===============================================================================
#
#          FILE: build.sh
# 
#         USAGE: ./build.sh 
# 
#   DESCRIPTION: 
# 
#       OPTIONS: ---
#  REQUIREMENTS: ---
#          BUGS: ---
#         NOTES: ---
#        AUTHOR: Christoph Schueler (), cpu12.gems@googlemail.com
#  ORGANIZATION: 
#       CREATED: 05.12.2021 08:58:22
#      REVISION:  ---
#===============================================================================

set -o nounset                              # Treat unset variables as an error

clang++ -std=c++17 -O3 -Wall -Wextra -Weffc++ -DLZ4_DEBUG=20 lz4.c rekorder.cpp -o rekorder

