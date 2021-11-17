
#include <cstdio>

#include <thread>

#include "concurrent_queue.hpp"

auto queue = ConcurrentQueue<int> {};

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

    return 0;
}
