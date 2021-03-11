
#include "socket.hpp"
#include "eth.hpp"

#include <iomanip>
#include <iostream>

using std::cout;
using std::endl;
using std::setw;
using std::internal;
using std::fixed;
using std::setfill;

using namespace std;


int main(void)
{
    auto iocp = IOCP();
    auto sock = Socket(&iocp);
}

