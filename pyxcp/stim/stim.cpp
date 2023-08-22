
#pragma comment(lib, "Winmm.lib")
#pragma comment(lib, "Avrt.lib")

#include "stim.hpp"

void make_dto() {

}

void init() {


}

static Mutex writer_lock{};
static Mutex policy_lock{};

Mutex& get_writer_lock() {
    return writer_lock;
}

Mutex& get_policy_lock() {
    return policy_lock;
}
