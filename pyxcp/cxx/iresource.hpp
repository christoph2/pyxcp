#if !defined(__IRESOURCE_HPP)
#define __IRESOURCE_HPP

/*
 *
 * Interface for pool-able resources.
 *
 */
class IResource {
public:

    virtual ~IResource() = default;
    virtual void reset() = 0;

};

#endif // __IRESOURCE_HPP
