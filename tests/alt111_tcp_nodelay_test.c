/* Host-side smoke test for the socket option used by GEN2 A/B mode.
 * cc -std=c99 -Wall -Wextra -Werror -Isrc/native/altscreen111-gen2/include \
 *   tests/alt111_tcp_nodelay_test.c -o /tmp/alt111_tcp_nodelay_test
 * /tmp/alt111_tcp_nodelay_test
 */
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <arpa/inet.h>
#include "alt111_tcp_nodelay.h"

static int observed_nodelay(int fd)
{
    int value = -1;
    socklen_t len = (socklen_t)sizeof(value);
    assert(getsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &value, &len) == 0);
    assert(len == sizeof(value));
    return value != 0;
}

int main(void)
{
    int server, client, accepted;
    struct sockaddr_in addr;
    socklen_t addrlen = (socklen_t)sizeof(addr);
    server = socket(AF_INET, SOCK_STREAM, 0);
    assert(server >= 0);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    assert(bind(server, (struct sockaddr *)&addr, sizeof(addr)) == 0);
    assert(getsockname(server, (struct sockaddr *)&addr, &addrlen) == 0);
    assert(listen(server, 1) == 0);
    client = socket(AF_INET, SOCK_STREAM, 0);
    assert(client >= 0);
    assert(connect(client, (struct sockaddr *)&addr, sizeof(addr)) == 0);
    accepted = accept(server, NULL, NULL);
    assert(accepted >= 0);
    assert(alt111_tcp_nodelay_apply(accepted, 0) == 0);
    assert(observed_nodelay(accepted) == 0);
    assert(alt111_tcp_nodelay_apply(accepted, 1) == 0);
    assert(observed_nodelay(accepted) == 1);
    assert(alt111_tcp_nodelay_apply(accepted, 0) == 0);
    assert(observed_nodelay(accepted) == 0);
    close(accepted);
    close(client);
    close(server);
    puts("TCP_NODELAY off/on/off passed");
    return 0;
}
