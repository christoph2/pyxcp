

#include "blocking_socket.hpp"

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

int main(void)
{
    int opt;
    CAddress address;
    auto sock = Socket {PF_INET, SOCK_STREAM, IPPROTO_TCP};

    opt = 1;
    sock.option(SO_REUSEADDR, SOL_SOCKET, &opt);

    //sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "localhost", 50007, address, 0);
    sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "192.168.168.100", 50007, address, 0);
    sock.connect(address);
    //sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "google.de", 80, address, 0);
    //printf("addr: %x", address.address);

    sock.write(hellomsg);
    Sleep(250);
}

