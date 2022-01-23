
#include <cstdio>

#include <thread>

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>

#include "concurrent_queue.hpp"

namespace py = pybind11;

auto queue = ConcurrentQueue<int> {};

using tuple_t =  std::tuple<uint16_t, uint16_t, double, py::bytes>;

auto frame_queue = ConcurrentQueue<tuple_t> {};

void worker(int num)
{
    printf("Entering #%u\n", num);
    for (int i = 0; i < 10; ++i) {
        queue.enqueue(num + i);
    }
}


int main(int ac, char const * av[])
{

    auto value = 0;
    auto frame = std::make_tuple(20, 1, 1.0045, "hello world!!!");
    uint16_t length, counter;
    double timestamp;
    py::bytes payload {};

    frame_queue.enqueue(frame);

    std::thread t0(worker, 10);
    std::thread t1(worker, 20);
    std::thread t2(worker, 30);
    std::thread t3(worker, 40);
    std::thread t4(worker, 50);

    for (auto i = 0; i < 100; ++i) {
        if (queue.dequeue(value, 1000)) {
            printf("%02u\n", value);
        } else {
            printf("TIME-OUT!!!\n");
            break;
        }
    }

    t4.join();
    t3.join();
    t2.join();
    t1.join();
    t0.join();

    tuple_t flonz;
    frame_queue.dequeue(flonz);
    //printf("%u %u %g\n", std::get<0>(flonz), std::get<1>(flonz), std::get<2>(flonz));

    std::tie(length, counter, timestamp, payload) = flonz;
    printf("%u %u %g\n", length, counter, timestamp);

    return 0;
}
