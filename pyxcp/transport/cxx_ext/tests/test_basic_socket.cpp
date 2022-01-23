

#include "eth.hpp"
#include "socket.hpp"
#include "asynchiofactory.hpp"

#include <iomanip>
#include <iostream>

using std::cout;
using std::endl;
using std::setw;
using std::internal;
using std::fixed;
using std::setfill;

using namespace std;

std::array<char, 15> hellomsg {"hello world!!!"};

Eth eth;

int main(void)
{

    CAddress address;
    auto asio = createAsyncIoService();
    auto sock = Socket {PF_INET, SOCK_STREAM, IPPROTO_TCP};

    //sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "localhost", 50007, address, 0);
    sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "192.168.168.100", 50007, address, 0);
    sock.connect(address);
    asio->registerSocket(sock);
    //sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "google.de", 80, address, 0);
    //printf("addr: %x", address.address);

    sock.write(hellomsg);
    Sleep(250);
}
