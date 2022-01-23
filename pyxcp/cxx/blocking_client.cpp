

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
    CAddress address;
    auto sock = Socket {PF_INET, SOCK_STREAM, IPPROTO_TCP};


    //sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "localhost", 50007, address, 0);
    sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "192.168.168.100", 50007, address, 0);
    sock.connect(address);

    //auto opt_val = sock.get_option(SO_REUSEADDR, SOL_SOCKET);
    auto opt_val = sock.get_option(SO_RCVBUF, SOL_SOCKET);
    printf("before: %u\n", opt_val);
    sock.set_option(SO_SNDBUF, SOL_SOCKET, 64 * 1024);
    sock.set_option(SO_RCVBUF, SOL_SOCKET, 64 * 1024);
    opt_val = sock.get_option(SO_RCVBUF, SOL_SOCKET);
    printf("after: %u\n", opt_val);


    sock.startReceiverThread();
    //sock.getaddrinfo(PF_INET, SOCK_STREAM, IPPROTO_TCP, "google.de", 80, address, 0);
    //printf("addr: %x", address.address);
//    sock.shutdownReceiverThread();
    sock.write(hellomsg);
    Sleep(2000);
}
