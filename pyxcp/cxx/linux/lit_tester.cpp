
#include <iostream>
#include <chrono>

#include <cstdint>

using namespace std::literals;
using namespace std;


int main()
{
//    cout << static_cast<unsignedI>(23ms) << endl;
    auto d1 = 250ns;

    std::chrono::nanoseconds d2 = 1us;
    std::cout << "250ns = " << d1.count() << " nanoseconds\n" << "1us = " << d2.count() << " nanoseconds\n";

}
