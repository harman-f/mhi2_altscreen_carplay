#ifndef ALT111_TCP_NODELAY_H
#define ALT111_TCP_NODELAY_H

#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>

/* Only the GEN2 -> local renderer TCP socket. Never touch iPhone or MOST.
 * Read-back makes A/B logs report the actual socket option rather than merely
 * a successful setsockopt(2) call.
 */
static int alt111_tcp_nodelay_apply(int fd, int enabled)
{
    int requested = enabled ? 1 : 0;
    int observed = -1;
    socklen_t len = (socklen_t)sizeof(observed);
    if (setsockopt(fd, IPPROTO_TCP, TCP_NODELAY,
                   (const void *)&requested, (socklen_t)sizeof(requested)) != 0)
        return -1;
    if (getsockopt(fd, IPPROTO_TCP, TCP_NODELAY, (void *)&observed, &len) != 0)
        return -1;
    if (len != (socklen_t)sizeof(observed) || (!!observed) != requested) {
        errno = EIO;
        return -1;
    }
    return 0;
}

#endif /* ALT111_TCP_NODELAY_H */
