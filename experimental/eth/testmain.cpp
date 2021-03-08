
#include "copi.hpp"

#include <iostream>

using namespace std;


struct ParamType {
    DWORD id;
    COPI::CQueue<int> * q;
};

DWORD producer(LPVOID param);
DWORD worker(LPVOID param);

DWORD producer(LPVOID param)
{
    ExitThread(0);
}

DWORD worker(LPVOID param)
{
    ParamType * p = reinterpret_cast<ParamType*>(param);

    //cout << "Starting Thread#" << p->id << " &" << p->q << endl;
    p->q->put(p->id * 2);
    ExitThread(0);
}

void testQueue();

#define NUM_WORKERS 8

static HANDLE threads[NUM_WORKERS];

void testQueue()
{
    COPI::CQueue<int> q;
    int value;

    q.put(3);
    q.put(2);
    q.put(1);
    q.put(0);

    for (int i = 0; i < 4; ++i) {
        try  {
            q.get(&value, 500);
        } catch (COPI::TimeoutException) {
            cout << "TIME'D OUT " << endl;
        }
        cout << "Popped value: " << value << endl;
    }
}

class Person
{
int age;
char* pName;

public:
    Person(): pName(0),age(0) {}
    Person(char* pName, int age): pName(pName), age(age) {}
    ~Person() {}

    void Display()
    {
        printf("Name = %s Age = %d \n", pName, age);
    }
    void Shout()
    {
        printf("Ooooooooooooooooo");
    }
};

int main()
{
    COPI::CQueue<int> q(0);
    DWORD thid;
    int value;
    bool res;
    COPI::CAddress addr;

#if 0
    int kung_foo = 4711;
    int * foo_ptr = new int;
    foo_ptr = &kung_foo;
    COPI::CSharedPointer<int> sp(foo_ptr);

    cout << "sp value is: " << *sp << endl;
    {
        COPI::CSharedPointer<int> sp2(sp);
        cout << "sp2 value is: " << *sp2 << endl;

    }

    //COPI::CRefCounter cnt;
    //COPI::CRefCounter cnt2(23);
    //COPI::CRefCounter cnt3(&cnt2);
#endif // 0

    COPI::CSharedPointer<Person> p(new Person("Scott", 25));
    p->Display();
    {
        COPI::CSharedPointer<Person> q = p;
        q->Display();
        // Destructor of q will be called here..

        COPI::CSharedPointer<Person> r;
        r = p;
        r->Display();
        // Destructor of r will be called here..
    }
    p->Display();

    for (int idx = 0; idx < NUM_WORKERS; ++idx) {
        ParamType * param = new ParamType;
        param->q = &q;
        param->id = idx;
        threads[idx] = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)worker, param, 0, &thid);
    }
    for (int idx = 0; idx < NUM_WORKERS; ++idx) {
        res = q.get(&value, 1500);
        if (res) {
            cout << "Popped value: " << value << endl;
        } else {
            cout << "TIME'D OUT " << endl;
        }
    }
    WaitForMultipleObjects(NUM_WORKERS, threads, TRUE, INFINITE);

    for (int idx = 0; idx < NUM_WORKERS; ++idx) {
        CloseHandle(threads[idx]);
    }


    //return 1;

    //testQueue();

    COPI::CWSock ws = COPI::CWSock();
    COPI::IOCP iocp = COPI::IOCP();
    COPI::CSystemInformation si = COPI::CSystemInformation();
    COPI::CSocket sock = COPI::CSocket(&iocp);

    //if (!sock.getaddrinfo(PF_INET, SOCK_STREAM, 0, NULL, 5555, addr)) {
    if (!sock.getaddrinfo(PF_INET, SOCK_STREAM, 0, "localhost", 50007, addr)) {
        cout << "getaddrinfo() failed." << endl;
    } else {
        //sock.bind(addr);
        if (!sock.connect(addr)) {
            cout << "connect() failed." << endl;
        }
        char * msg = "Hello IOCP world!!!";
        sock.write(msg, ::strlen(msg));
    }

//    Sleep(2000);
#if 0
    __except(EXCEPTION_EXECUTE_HANDLER)
    {
        cout << "Cauth Exc: " << GetExceptionCode() << endl;
    }
#endif


#if 0
    //IOCP::OpenConnection("www.microsoft.com", 80, PF_UNSPEC);
    //IOCP::OpenConnection("::1", 990, PF_UNSPEC);

    CIOCP::Socket sock = CIOCP::Socket(&iocp, AF_INET, SOCK_STREAM, IPPROTO_TCP);
    sock.setOption(SO_REUSEADDR, &enable, sizeof(int));
    //sock.Connect("www.google.com", 80, AF_INET);
    //sock.Connect("localhost", 50007, AF_INET);
    sock.connect("localhost", 990, AF_INET);

    ph.handle = sock.getHandle();
    ph.handleType = CIOCP::HANDLE_SOCKET;

    iocp.registerHandle(&ph);

    //DWORD error = GetLastError();
    //cout << "Error: " << error << endl;
    cout << "Socket Handle: " << sock.getHandle() << endl;

    CIOCP::Lock * lock = new CIOCP::win::CriticalSection();
    lock->acquire();
    lock->release();
    delete lock;
#endif // 0
}
