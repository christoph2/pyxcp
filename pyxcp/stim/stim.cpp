
#pragma comment(lib, "Winmm.lib")
#pragma comment(lib, "Avrt.lib")

#include "stim.hpp"

void make_dto() {

}

void init() {


}

Mutex _writer_lock{};

const Mutex& get_writer_lock() {
    return _writer_lock;
}
