/*
 * MU1440 Wireless CarPlay B0 discovery sidecar.
 *
 * Purpose:
 *   Bridge A3 (iPhone joined the target AP) to the first B0 session-plane
 *   observation by browsing _carplay-ctrl._tcp through the stock
 *   libdns_sd.so.1 already present on MU1440.
 *
 * Safety / scope:
 *   - does not modify WLAN configuration;
 *   - does not pair, authenticate or open a CarPlayControl session;
 *   - does not publish mDNS services;
 *   - only browses/resolves and records observed metadata.
 *
 * Build target: QNX 6.5 ARMv7 (also host-buildable for ABI/tests).
 */

#include <arpa/inet.h>
#include <ctype.h>
#include <dlfcn.h>
#include <errno.h>
#include <net/if.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 1024
#endif

typedef struct _DNSServiceRef_t *DNSServiceRef;
typedef uint32_t DNSServiceFlags;
typedef int32_t DNSServiceErrorType;
typedef uint32_t DNSServiceProtocol;

enum {
    DNS_FLAG_MORE_COMING = 0x1u,
    DNS_FLAG_ADD = 0x2u,
    DNS_PROTO_IPV4 = 0x1u,
    DNS_PROTO_IPV6 = 0x2u
};

typedef void (*DNSServiceBrowseReply)(
    DNSServiceRef,
    DNSServiceFlags,
    uint32_t,
    DNSServiceErrorType,
    const char *,
    const char *,
    const char *,
    void *);

typedef void (*DNSServiceResolveReply)(
    DNSServiceRef,
    DNSServiceFlags,
    uint32_t,
    DNSServiceErrorType,
    const char *,
    const char *,
    uint16_t,
    uint16_t,
    const unsigned char *,
    void *);

typedef void (*DNSServiceGetAddrInfoReply)(
    DNSServiceRef,
    DNSServiceFlags,
    uint32_t,
    DNSServiceErrorType,
    const char *,
    const struct sockaddr *,
    uint32_t,
    void *);

typedef DNSServiceErrorType (*PFN_DNSServiceBrowse)(
    DNSServiceRef *,
    DNSServiceFlags,
    uint32_t,
    const char *,
    const char *,
    DNSServiceBrowseReply,
    void *);

typedef DNSServiceErrorType (*PFN_DNSServiceResolve)(
    DNSServiceRef *,
    DNSServiceFlags,
    uint32_t,
    const char *,
    const char *,
    const char *,
    DNSServiceResolveReply,
    void *);

typedef DNSServiceErrorType (*PFN_DNSServiceGetAddrInfo)(
    DNSServiceRef *,
    DNSServiceFlags,
    uint32_t,
    DNSServiceProtocol,
    const char *,
    DNSServiceGetAddrInfoReply,
    void *);

typedef int (*PFN_DNSServiceRefSockFD)(DNSServiceRef);
typedef DNSServiceErrorType (*PFN_DNSServiceProcessResult)(DNSServiceRef);
typedef void (*PFN_DNSServiceRefDeallocate)(DNSServiceRef);

struct dns_api {
    void *handle;
    PFN_DNSServiceBrowse browse;
    PFN_DNSServiceResolve resolve;
    PFN_DNSServiceGetAddrInfo get_addr_info;
    PFN_DNSServiceRefSockFD sockfd;
    PFN_DNSServiceProcessResult process;
    PFN_DNSServiceRefDeallocate deallocate;
};

struct b0_state {
    struct dns_api api;

    DNSServiceRef browse_ref;
    DNSServiceRef resolve_ref;
    DNSServiceRef addr_ref;

    char ifname[IFNAMSIZ];
    uint32_t ifindex;
    char regtype[128];
    char management_ifname[IFNAMSIZ];
    int watch_management;
    int management_present;

    char expected_bt_mac[32];
    int has_expected_bt_mac;
    int txt_mac_match;

    char service_name[256];
    char service_domain[256];
    char host_target[256];
    uint16_t port;
    char address[INET6_ADDRSTRLEN];

    char state_path[PATH_MAX];
    unsigned timeout_sec;

    int discovered;
    int resolved;
    int got_addr;
    int fatal_error;
};

static volatile sig_atomic_t g_stop = 0;

static void on_signal(int sig)
{
    (void)sig;
    g_stop = 1;
}

static void usage(const char *argv0)
{
    fprintf(stderr,
        "usage: %s [--interface uap0] [--service _carplay-ctrl._tcp]\n"
        "          [--expected-bt-mac AA:BB:CC:DD:EE:FF]\n"
        "          [--state /tmp/mhi2-wcp-b0.state] [--timeout SEC]\n",
        argv0);
}

static int copy_str(char *dst, size_t dst_size, const char *src)
{
    size_t n;

    if (dst == NULL || dst_size == 0 || src == NULL) {
        return -1;
    }

    n = strlen(src);
    if (n >= dst_size) {
        return -1;
    }

    memcpy(dst, src, n + 1);
    return 0;
}

static int ci_equal_char(char a, char b)
{
    return tolower((unsigned char)a) == tolower((unsigned char)b);
}

static int contains_ci(const char *haystack, const char *needle)
{
    size_t i;
    size_t j;
    size_t hlen;
    size_t nlen;

    if (haystack == NULL || needle == NULL) {
        return 0;
    }

    hlen = strlen(haystack);
    nlen = strlen(needle);
    if (nlen == 0 || nlen > hlen) {
        return 0;
    }

    for (i = 0; i + nlen <= hlen; ++i) {
        for (j = 0; j < nlen; ++j) {
            if (!ci_equal_char(haystack[i + j], needle[j])) {
                break;
            }
        }
        if (j == nlen) {
            return 1;
        }
    }

    return 0;
}

static int normalize_mac(const char *src, char out[13])
{
    size_t n = 0;
    const unsigned char *p = (const unsigned char *)src;

    if (src == NULL) {
        return -1;
    }

    while (*p != '\0') {
        if (isxdigit(*p)) {
            if (n >= 12) {
                return -1;
            }
            out[n++] = (char)toupper(*p);
        } else if (*p != ':' && *p != '-' && *p != '.') {
            return -1;
        }
        ++p;
    }

    if (n != 12) {
        return -1;
    }

    out[12] = '\0';
    return 0;
}

static int text_contains_normalized_mac(const char *text, const char mac12[13])
{
    char compact[1024];
    size_t n = 0;
    const unsigned char *p = (const unsigned char *)text;

    while (*p != '\0' && n + 1 < sizeof(compact)) {
        if (isxdigit(*p)) {
            compact[n++] = (char)toupper(*p);
        } else {
            compact[n++] = ' ';
        }
        ++p;
    }
    compact[n] = '\0';

    return contains_ci(compact, mac12);
}

static void write_state_file(const struct b0_state *s, const char *phase)
{
    char tmp_path[PATH_MAX + 8];
    FILE *fp;

    if (s->state_path[0] == '\0') {
        return;
    }

    if (snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", s->state_path)
            >= (int)sizeof(tmp_path)) {
        return;
    }

    fp = fopen(tmp_path, "w");
    if (fp == NULL) {
        fprintf(stderr, "B0_STATE_ERROR path=%s errno=%d\n",
            tmp_path, errno);
        return;
    }

    fprintf(fp, "phase=%s\n", phase != NULL ? phase : "unknown");
    fprintf(fp, "interface=%s\n", s->ifname);
    fprintf(fp, "ifindex=%u\n", (unsigned)s->ifindex);
    fprintf(fp, "regtype=%s\n", s->regtype);
    fprintf(fp, "service_name=%s\n", s->service_name);
    fprintf(fp, "domain=%s\n", s->service_domain);
    fprintf(fp, "host=%s\n", s->host_target);
    fprintf(fp, "port=%u\n", (unsigned)s->port);
    fprintf(fp, "address=%s\n", s->address);
    fprintf(fp, "expected_bt_mac=%s\n",
        s->has_expected_bt_mac ? s->expected_bt_mac : "");
    fprintf(fp, "txt_bt_mac_match=%d\n", s->txt_mac_match ? 1 : 0);
    fprintf(fp, "discovered=%d\n", s->discovered ? 1 : 0);
    fprintf(fp, "resolved=%d\n", s->resolved ? 1 : 0);
    fprintf(fp, "got_addr=%d\n", s->got_addr ? 1 : 0);

    if (fclose(fp) != 0) {
        unlink(tmp_path);
        return;
    }

    if (rename(tmp_path, s->state_path) != 0) {
        fprintf(stderr, "B0_STATE_ERROR rename=%s errno=%d\n",
            s->state_path, errno);
        unlink(tmp_path);
    }
}

static void print_txt(struct b0_state *s,
    const unsigned char *txt, uint16_t txt_len)
{
    size_t off = 0;
    unsigned item = 0;
    char mac12[13];

    printf("B0_TXT_RAW len=%u hex=", (unsigned)txt_len);
    for (off = 0; off < txt_len; ++off) {
        printf("%02x", (unsigned)txt[off]);
    }
    printf("\n");

    off = 0;
    while (off < txt_len) {
        unsigned len = txt[off++];
        char buf[512];
        unsigned i;
        unsigned copy_len;

        if (off + len > txt_len) {
            printf("B0_TXT_ERROR offset=%u length=%u remaining=%u\n",
                (unsigned)(off - 1), len, (unsigned)(txt_len - off));
            break;
        }

        copy_len = len < sizeof(buf) - 1 ? len : (unsigned)sizeof(buf) - 1;
        for (i = 0; i < copy_len; ++i) {
            unsigned char ch = txt[off + i];
            buf[i] = isprint(ch) ? (char)ch : '.';
        }
        buf[copy_len] = '\0';

        printf("B0_TXT_ITEM index=%u len=%u text=%s\n",
            item, len, buf);

        if (s->has_expected_bt_mac
                && normalize_mac(s->expected_bt_mac, mac12) == 0
                && text_contains_normalized_mac(buf, mac12)) {
            s->txt_mac_match = 1;
            printf("B0_IDENTITY_MATCH source=txt expected_bt_mac=%s\n",
                s->expected_bt_mac);
        }

        off += len;
        ++item;
    }
}

static int sockaddr_to_text(const struct sockaddr *sa,
    char *out, size_t out_size)
{
    const void *addr;

    if (sa == NULL || out == NULL || out_size == 0) {
        return -1;
    }

    if (sa->sa_family == AF_INET) {
        addr = &((const struct sockaddr_in *)sa)->sin_addr;
        return inet_ntop(AF_INET, addr, out, out_size) != NULL ? 0 : -1;
    }

    if (sa->sa_family == AF_INET6) {
        addr = &((const struct sockaddr_in6 *)sa)->sin6_addr;
        return inet_ntop(AF_INET6, addr, out, out_size) != NULL ? 0 : -1;
    }

    return -1;
}

static void addr_reply(DNSServiceRef sd_ref,
    DNSServiceFlags flags,
    uint32_t ifindex,
    DNSServiceErrorType error,
    const char *hostname,
    const struct sockaddr *address,
    uint32_t ttl,
    void *context)
{
    struct b0_state *s = (struct b0_state *)context;
    char addrbuf[INET6_ADDRSTRLEN];

    (void)sd_ref;
    (void)flags;

    if (error != 0) {
        fprintf(stderr,
            "B0_ADDR_ERROR error=%d ifindex=%u host=%s\n",
            (int)error, (unsigned)ifindex,
            hostname != NULL ? hostname : "");
        s->fatal_error = 1;
        return;
    }

    if (sockaddr_to_text(address, addrbuf, sizeof(addrbuf)) != 0) {
        fprintf(stderr,
            "B0_ADDR_ERROR reason=unsupported_address_family ifindex=%u\n",
            (unsigned)ifindex);
        return;
    }

    (void)copy_str(s->address, sizeof(s->address), addrbuf);
    s->got_addr = 1;

    printf("B0_ADDR ifindex=%u host=%s address=%s ttl=%u\n",
        (unsigned)ifindex,
        hostname != NULL ? hostname : "",
        addrbuf,
        (unsigned)ttl);
    write_state_file(s, "addr");
}

static void resolve_reply(DNSServiceRef sd_ref,
    DNSServiceFlags flags,
    uint32_t ifindex,
    DNSServiceErrorType error,
    const char *fullname,
    const char *hosttarget,
    uint16_t port,
    uint16_t txt_len,
    const unsigned char *txt_record,
    void *context)
{
    struct b0_state *s = (struct b0_state *)context;
    DNSServiceErrorType rc;

    (void)sd_ref;
    (void)flags;

    if (error != 0) {
        fprintf(stderr,
            "B0_RESOLVE_ERROR error=%d ifindex=%u fullname=%s\n",
            (int)error, (unsigned)ifindex,
            fullname != NULL ? fullname : "");
        s->fatal_error = 1;
        return;
    }

    s->resolved = 1;
    (void)copy_str(s->host_target, sizeof(s->host_target),
        hosttarget != NULL ? hosttarget : "");
    s->port = ntohs(port);

    printf("B0_RESOLVE ifindex=%u fullname=%s host=%s port=%u txt_len=%u\n",
        (unsigned)ifindex,
        fullname != NULL ? fullname : "",
        hosttarget != NULL ? hosttarget : "",
        (unsigned)s->port,
        (unsigned)txt_len);

    if (txt_record != NULL && txt_len != 0) {
        print_txt(s, txt_record, txt_len);
    }

    write_state_file(s, "resolved");

    if (s->addr_ref != NULL || hosttarget == NULL || *hosttarget == '\0') {
        return;
    }

    rc = s->api.get_addr_info(
        &s->addr_ref,
        0,
        ifindex,
        DNS_PROTO_IPV4 | DNS_PROTO_IPV6,
        hosttarget,
        addr_reply,
        s);

    if (rc != 0) {
        fprintf(stderr,
            "B0_ADDR_START_ERROR error=%d host=%s\n",
            (int)rc, hosttarget);
        s->fatal_error = 1;
    }
}

static void browse_reply(DNSServiceRef sd_ref,
    DNSServiceFlags flags,
    uint32_t ifindex,
    DNSServiceErrorType error,
    const char *service_name,
    const char *regtype,
    const char *reply_domain,
    void *context)
{
    struct b0_state *s = (struct b0_state *)context;
    DNSServiceErrorType rc;

    (void)sd_ref;

    if (error != 0) {
        fprintf(stderr,
            "B0_BROWSE_ERROR error=%d ifindex=%u\n",
            (int)error, (unsigned)ifindex);
        s->fatal_error = 1;
        return;
    }

    if ((flags & DNS_FLAG_ADD) == 0) {
        printf("B0_REMOVE ifindex=%u service=%s regtype=%s domain=%s\n",
            (unsigned)ifindex,
            service_name != NULL ? service_name : "",
            regtype != NULL ? regtype : "",
            reply_domain != NULL ? reply_domain : "");
        return;
    }

    printf("B0_DISCOVER ifindex=%u service=%s regtype=%s domain=%s more=%u\n",
        (unsigned)ifindex,
        service_name != NULL ? service_name : "",
        regtype != NULL ? regtype : "",
        reply_domain != NULL ? reply_domain : "",
        (unsigned)((flags & DNS_FLAG_MORE_COMING) != 0));

    if (s->resolve_ref != NULL) {
        return;
    }

    s->discovered = 1;
    (void)copy_str(s->service_name, sizeof(s->service_name),
        service_name != NULL ? service_name : "");
    (void)copy_str(s->service_domain, sizeof(s->service_domain),
        reply_domain != NULL ? reply_domain : "");
    write_state_file(s, "discovered");

    rc = s->api.resolve(
        &s->resolve_ref,
        0,
        ifindex,
        service_name,
        regtype,
        reply_domain,
        resolve_reply,
        s);

    if (rc != 0) {
        fprintf(stderr,
            "B0_RESOLVE_START_ERROR error=%d service=%s\n",
            (int)rc, service_name != NULL ? service_name : "");
        s->fatal_error = 1;
    }
}

static int load_symbol(void *handle, const char *name, void **out)
{
    const char *err;

    dlerror();
    *out = dlsym(handle, name);
    err = dlerror();
    if (err != NULL || *out == NULL) {
        fprintf(stderr, "B0_DLSYM_ERROR symbol=%s error=%s\n",
            name, err != NULL ? err : "not found");
        return -1;
    }

    return 0;
}

static int load_dns_api(struct dns_api *api)
{
    const char *candidates[] = {
        "libdns_sd.so.1",
        "libdns_sd.so",
        NULL
    };
    size_t i;

    memset(api, 0, sizeof(*api));

    for (i = 0; candidates[i] != NULL; ++i) {
        api->handle = dlopen(candidates[i], RTLD_NOW | RTLD_LOCAL);
        if (api->handle != NULL) {
            printf("B0_DNS_LIBRARY path=%s\n", candidates[i]);
            break;
        }
    }

    if (api->handle == NULL) {
        fprintf(stderr, "B0_DLOPEN_ERROR libdns_sd error=%s\n",
            dlerror() != NULL ? dlerror() : "not found");
        return -1;
    }

#define LOAD_API(field, symbol) \
    do { \
        void *p = NULL; \
        if (load_symbol(api->handle, symbol, &p) != 0) return -1; \
        memcpy(&api->field, &p, sizeof(api->field)); \
    } while (0)

    LOAD_API(browse, "DNSServiceBrowse");
    LOAD_API(resolve, "DNSServiceResolve");
    LOAD_API(get_addr_info, "DNSServiceGetAddrInfo");
    LOAD_API(sockfd, "DNSServiceRefSockFD");
    LOAD_API(process, "DNSServiceProcessResult");
    LOAD_API(deallocate, "DNSServiceRefDeallocate");

#undef LOAD_API
    return 0;
}

static void unload_dns_api(struct dns_api *api)
{
    if (api->handle != NULL) {
        dlclose(api->handle);
        api->handle = NULL;
    }
}

static int wait_for_interface(const char *ifname,
    unsigned timeout_sec, uint32_t *ifindex)
{
    time_t start = time(NULL);

    for (;;) {
        unsigned idx = if_nametoindex(ifname);
        if (idx != 0) {
            *ifindex = (uint32_t)idx;
            return 0;
        }

        if ((unsigned)(time(NULL) - start) >= timeout_sec) {
            return -1;
        }

        sleep(1);
    }
}

static void poll_management_interface(struct b0_state *s)
{
    int present;

    if (!s->watch_management) {
        return;
    }

    present = if_nametoindex(s->management_ifname) != 0;
    if (present != s->management_present) {
        s->management_present = present;
        printf("B0_MGMT interface=%s present=%d\n",
            s->management_ifname, present);
        write_state_file(s, present ? "management-up" : "management-down");
    }
}

static int process_ref(struct b0_state *s,
    DNSServiceRef ref, fd_set *readfds)
{
    int fd;
    DNSServiceErrorType rc;

    if (ref == NULL) {
        return 0;
    }

    fd = s->api.sockfd(ref);
    if (fd < 0 || !FD_ISSET(fd, readfds)) {
        return 0;
    }

    rc = s->api.process(ref);
    if (rc != 0) {
        fprintf(stderr, "B0_PROCESS_ERROR fd=%d error=%d\n",
            fd, (int)rc);
        return -1;
    }

    return 0;
}

static int run_loop(struct b0_state *s)
{
    time_t start = time(NULL);

    while (!g_stop && !s->fatal_error && !s->got_addr) {
        fd_set readfds;
        struct timeval tv;
        int maxfd = -1;
        int refs[3];
        size_t i;
        DNSServiceRef dsrefs[3];

        dsrefs[0] = s->browse_ref;
        dsrefs[1] = s->resolve_ref;
        dsrefs[2] = s->addr_ref;

        FD_ZERO(&readfds);

        for (i = 0; i < 3; ++i) {
            refs[i] = -1;
            if (dsrefs[i] != NULL) {
                refs[i] = s->api.sockfd(dsrefs[i]);
                if (refs[i] >= 0) {
                    FD_SET(refs[i], &readfds);
                    if (refs[i] > maxfd) {
                        maxfd = refs[i];
                    }
                }
            }
        }

        if (maxfd < 0) {
            fprintf(stderr, "B0_ERROR no_active_dns_fds\n");
            return -1;
        }

        tv.tv_sec = 1;
        tv.tv_usec = 0;

        if (select(maxfd + 1, &readfds, NULL, NULL, &tv) < 0) {
            if (errno == EINTR) {
                continue;
            }
            fprintf(stderr, "B0_SELECT_ERROR errno=%d\n", errno);
            return -1;
        }

        for (i = 0; i < 3; ++i) {
            if (process_ref(s, dsrefs[i], &readfds) != 0) {
                return -1;
            }
        }

        poll_management_interface(s);

        if ((unsigned)(time(NULL) - start) >= s->timeout_sec) {
            fprintf(stderr,
                "B0_TIMEOUT seconds=%u discovered=%d resolved=%d addr=%d\n",
                s->timeout_sec, s->discovered, s->resolved, s->got_addr);
            return 2;
        }
    }

    return s->fatal_error ? -1 : 0;
}

static void cleanup(struct b0_state *s)
{
    if (s->addr_ref != NULL) {
        s->api.deallocate(s->addr_ref);
        s->addr_ref = NULL;
    }
    if (s->resolve_ref != NULL) {
        s->api.deallocate(s->resolve_ref);
        s->resolve_ref = NULL;
    }
    if (s->browse_ref != NULL) {
        s->api.deallocate(s->browse_ref);
        s->browse_ref = NULL;
    }
    unload_dns_api(&s->api);
}

int main(int argc, char **argv)
{
    struct b0_state s;
    int i;
    DNSServiceErrorType rc;
    unsigned interface_wait_sec = 60;
    int result;

    memset(&s, 0, sizeof(s));
    (void)copy_str(s.ifname, sizeof(s.ifname), "uap0");
    (void)copy_str(s.regtype, sizeof(s.regtype), "_carplay-ctrl._tcp");
    (void)copy_str(s.management_ifname, sizeof(s.management_ifname), "mlan0");
    s.watch_management = 1;
    (void)copy_str(s.state_path, sizeof(s.state_path),
        "/tmp/mhi2-wcp-b0.state");
    s.timeout_sec = 120;

    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--interface") == 0 && i + 1 < argc) {
            if (copy_str(s.ifname, sizeof(s.ifname), argv[++i]) != 0) {
                fprintf(stderr, "invalid interface name\n");
                return 64;
            }
        } else if (strcmp(argv[i], "--service") == 0 && i + 1 < argc) {
            if (copy_str(s.regtype, sizeof(s.regtype), argv[++i]) != 0) {
                fprintf(stderr, "invalid service type\n");
                return 64;
            }
        } else if (strcmp(argv[i], "--expected-bt-mac") == 0
                && i + 1 < argc) {
            char mac12[13];
            if (copy_str(s.expected_bt_mac, sizeof(s.expected_bt_mac),
                    argv[++i]) != 0
                    || normalize_mac(s.expected_bt_mac, mac12) != 0) {
                fprintf(stderr, "invalid Bluetooth MAC\n");
                return 64;
            }
            s.has_expected_bt_mac = 1;
        } else if (strcmp(argv[i], "--management-interface") == 0
                && i + 1 < argc) {
            if (copy_str(s.management_ifname, sizeof(s.management_ifname),
                    argv[++i]) != 0) {
                fprintf(stderr, "invalid management interface name\n");
                return 64;
            }
            s.watch_management = 1;
        } else if (strcmp(argv[i], "--no-management-watch") == 0) {
            s.watch_management = 0;
        } else if (strcmp(argv[i], "--state") == 0 && i + 1 < argc) {
            if (copy_str(s.state_path, sizeof(s.state_path), argv[++i]) != 0) {
                fprintf(stderr, "invalid state path\n");
                return 64;
            }
        } else if (strcmp(argv[i], "--timeout") == 0 && i + 1 < argc) {
            unsigned long value = strtoul(argv[++i], NULL, 10);
            if (value == 0 || value > 3600) {
                fprintf(stderr, "invalid timeout\n");
                return 64;
            }
            s.timeout_sec = (unsigned)value;
        } else if (strcmp(argv[i], "--interface-wait") == 0
                && i + 1 < argc) {
            unsigned long value = strtoul(argv[++i], NULL, 10);
            if (value > 3600) {
                fprintf(stderr, "invalid interface wait\n");
                return 64;
            }
            interface_wait_sec = (unsigned)value;
        } else if (strcmp(argv[i], "--no-state") == 0) {
            s.state_path[0] = '\0';
        } else if (strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 64;
        }
    }

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    printf("B0_START interface=%s service=%s timeout=%u expected_bt_mac=%s\n",
        s.ifname, s.regtype, s.timeout_sec,
        s.has_expected_bt_mac ? s.expected_bt_mac : "");

    if (wait_for_interface(s.ifname, interface_wait_sec, &s.ifindex) != 0) {
        fprintf(stderr,
            "B0_INTERFACE_TIMEOUT interface=%s seconds=%u\n",
            s.ifname, interface_wait_sec);
        return 3;
    }

    printf("B0_INTERFACE interface=%s ifindex=%u\n",
        s.ifname, (unsigned)s.ifindex);
    write_state_file(&s, "interface");

    if (load_dns_api(&s.api) != 0) {
        cleanup(&s);
        return 4;
    }

    rc = s.api.browse(
        &s.browse_ref,
        0,
        s.ifindex,
        s.regtype,
        NULL,
        browse_reply,
        &s);

    if (rc != 0) {
        fprintf(stderr,
            "B0_BROWSE_START_ERROR error=%d interface=%s ifindex=%u\n",
            (int)rc, s.ifname, (unsigned)s.ifindex);
        cleanup(&s);
        return 5;
    }

    write_state_file(&s, "browsing");
    result = run_loop(&s);

    if (result == 0 && s.got_addr) {
        printf(
            "B0_READY service=%s host=%s port=%u address=%s txt_bt_mac_match=%d\n",
            s.service_name,
            s.host_target,
            (unsigned)s.port,
            s.address,
            s.txt_mac_match);
        write_state_file(&s, "ready");
    }

    cleanup(&s);
    return result;
}
