#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
import socket
import time
import sys

import numpy as np

RS = np.random.RandomState(23)
LE_WORD_STRUCT = struct.Struct("<H")

##
## Basic Configuration.
##
HOST = "localhost"
PORT = 56789
TOTAL_BYTES = 250 * 1024 * 1024
MIN_MSG_LEN = 128
MAX_MSG_LEN = 16384

##
## Performance Relevant Configuration.
##
NO_DELAY = True
SOCKET_SNDBUF = 4096 * 4
SOCKET_RCVBUF = 4096 * 12
RCV_RCVBUF    = 4096 * 1

def client():
    payload = 0
    so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    so.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1 if NO_DELAY else 0)
    so.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_SNDBUF)
    so.connect((HOST, PORT))
    total_length = 0
    counter = 0
    while total_length < TOTAL_BYTES:
        msg_len = RS.randint(MIN_MSG_LEN, MAX_MSG_LEN)
        msg = bytearray(msg_len)
        msg[0 : 2] = LE_WORD_STRUCT.pack(msg_len)
        msg[2 : 4] = LE_WORD_STRUCT.pack(counter % 0x10000)
        so.send(msg)
        total_length += msg_len
        counter += 1
    so.close()

def server_recv():
    so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    so.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_RCVBUF)
    so.bind(("localhost", PORT))
    so.listen(1)
    conn, addr = so.accept()
    print("Connected by {}//{}".format(*addr))
    start = time.clock()
    finished = False
    received = False
    buffer = bytearray()
    total_length = 0
    while not finished:
        offset = 0
        msg_length = 0
        state = 0
        received = False
        bytes_to_read = 2
        while not received:
            data = conn.recv(bytes_to_read)
            if not data:
                finished = True
                break
            buffer += data
            offset += len(data)
            if offset >= 2 and state == 0:
                msg_length = LE_WORD_STRUCT.unpack(buffer[0 : 2])[0]
                state = 1
                if msg_length <= 0:
                    sys.exit(1)
                bytes_to_read = msg_length - 2
            else:
                if offset == msg_length:
                    received = True
                else:
                    bytes_to_read = msg_length - offset
                    if bytes_to_read <= 0:
                        print("BTR?:", bytes_to_read)
                        sys.exit(1)
        total_length += offset
        if total_length >= TOTAL_BYTES:
            finished = True
    conn.close()
    elapsed_time = time.clock() - start
    print("Elapsed time: {:.2f}s - throughput: {:.2f} MB/s".format(elapsed_time, (total_length / elapsed_time) / (1024 * 1024)))

def run(args = []):
    if len(args) == 1 and args[0] == "c":
        start = time.clock()
        client()
        print("Elapsed time: {:.2f}".format(time.clock() - start))
    else:
        server_recv()

