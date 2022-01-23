
#include "memoryblock.hpp"
#include "pool.hpp"

#include <iostream>
#include <cassert>


typedef Pool<MemoryBlock<char, 64>, 8> Pool_t;

void acquire_memory_blocks(Pool_t& pool)
{
	for (int i = 0; i < 8; ++i) {
		auto obj = pool.acquire();
        pool.release(obj);
	}
	// Blocks should be released.
}

int main()
{
    Pool_t pool;

	acquire_memory_blocks(pool);

    auto p0 = pool.acquire();
    auto p1 = pool.acquire();
    auto p2 = pool.acquire();
    auto p3 = pool.acquire();
    auto p4 = pool.acquire();
    auto p5 = pool.acquire();
    auto p6 = pool.acquire();
    auto p7 = pool.acquire();
    try {
        auto p8 = pool.acquire(); // should throw CapacityExhaustedException.
    } catch(CapacityExhaustedException) {
        std::cout << "OK, caught CapacityExhaustedException as expected." << std::endl;
    }
}
