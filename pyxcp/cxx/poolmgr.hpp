#if !defined(__POOLMGR_H)
#define __POOLMGR_H

#include "pool.hpp"
#include "periodata.hpp"

/*
 *
 * PoolManager holds various resource pools.
 *
 *
 */

class PoolManager {
public:
    using IodPool_t = Pool<PerIoData, 64>;

    PoolManager() = default;
    ~PoolManager() = default;

    IodPool_t& get_iod() const {
        return m_iod_pool;
    }

private:

    static IodPool_t m_iod_pool;
};


#endif // __POOLMGR_H
