
#if !defined(__CONFIG_H)
#define __CONFIG_H
/*
 * Basic Options.
 */
#define PORT "56789"
#define HOST "localhost"
#define MIN_MSG_LEN     (128)
#define MAX_MSG_LEN     (16384)
#define TOTAL_BYTES     (250 * 1024 * 1024)

/*
 * Performance Relevant Options.
 */
#define NO_DELAY        (1)
#define SOCKET_SNDBUF   (4096 * 8)
#define SOCKET_RCVBUF   (4096 * 4)
#define RCV_RCVBUF      (4096 * 1)


#define SIZEOF_SHORT    (sizeof(unsigned short))

#endif // __CONFIG_H

