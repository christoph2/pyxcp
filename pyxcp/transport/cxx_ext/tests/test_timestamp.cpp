
#include "timestamp.hpp"
#include "utils.hpp"

#include <iomanip>
#include <iostream>

using std::cout;
using std::endl;
using namespace std;


int main(void)
{
    auto ts = Timestamp();
    double previous = 0.0;
    double current = 0.0;

    cout << fixed;

    for (uint16_t idx = 0; idx < 100; ++idx) {
        current = ts.get();
        cout << "#" << setw(3) << setfill('0') << idx + 1 << " " << current << " diff: " << current -previous << endl;
        Sleep(100);
        previous = current;
    }
}
