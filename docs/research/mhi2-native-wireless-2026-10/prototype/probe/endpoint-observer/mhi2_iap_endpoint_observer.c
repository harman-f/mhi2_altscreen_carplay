#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 1024
#endif

#define MAX_ENTRIES 8192
#define DEFAULT_SECONDS 60
#define DEFAULT_INTERVAL_MS 250
#define DEFAULT_DEPTH 3

struct entry {
    char path[PATH_MAX];
    mode_t mode;
    off_t size;
    time_t mtime;
    dev_t rdev;
};

struct snapshot {
    struct entry *items;
    size_t count;
    size_t capacity;
    int truncated;
};

static int entry_cmp(const void *a, const void *b)
{
    const struct entry *ea = (const struct entry *)a;
    const struct entry *eb = (const struct entry *)b;
    return strcmp(ea->path, eb->path);
}

static int add_entry(struct snapshot *snap, const char *path, const struct stat *st)
{
    struct entry *e;
    size_t n;

    if (!snap || !path || !st)
        return EINVAL;
    if (snap->count >= snap->capacity) {
        snap->truncated = 1;
        return ENOSPC;
    }

    n = strlen(path);
    if (n >= sizeof(snap->items[0].path))
        return ENAMETOOLONG;

    e = &snap->items[snap->count++];
    memcpy(e->path, path, n + 1);
    e->mode = st->st_mode;
    e->size = st->st_size;
    e->mtime = st->st_mtime;
    e->rdev = st->st_rdev;
    return 0;
}

static void scan_path(struct snapshot *snap, const char *path, unsigned depth)
{
    struct stat st;
    DIR *dir;
    struct dirent *de;

    if (lstat(path, &st) != 0)
        return;

    (void)add_entry(snap, path, &st);
    if (!S_ISDIR(st.st_mode) || depth == 0)
        return;

    dir = opendir(path);
    if (!dir)
        return;

    while ((de = readdir(dir)) != NULL) {
        char child[PATH_MAX];
        int n;

        if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0)
            continue;

        n = snprintf(child, sizeof(child), "%s/%s", path, de->d_name);
        if (n < 0 || (size_t)n >= sizeof(child))
            continue;

        scan_path(snap, child, depth - 1);
        if (snap->truncated)
            break;
    }
    closedir(dir);
}

static void collect_snapshot(struct snapshot *snap,
                             char **roots,
                             size_t root_count)
{
    size_t i;

    snap->count = 0;
    snap->truncated = 0;
    for (i = 0; i < root_count; ++i) {
        scan_path(snap, roots[i], DEFAULT_DEPTH);
        if (snap->truncated)
            break;
    }
    qsort(snap->items, snap->count, sizeof(snap->items[0]), entry_cmp);
}

static const char *kind(mode_t mode)
{
    if (S_ISDIR(mode)) return "dir";
    if (S_ISCHR(mode)) return "chr";
    if (S_ISBLK(mode)) return "blk";
    if (S_ISFIFO(mode)) return "fifo";
    if (S_ISSOCK(mode)) return "sock";
    if (S_ISREG(mode)) return "file";
#ifdef S_ISLNK
    if (S_ISLNK(mode)) return "link";
#endif
    return "other";
}

static void print_entry(const char *tag, const struct entry *e)
{
    printf("%s\t%s\tmode=%#lo\tsize=%lld\trdev=%llu\t%s\n",
           tag,
           kind(e->mode),
           (unsigned long)(e->mode & 07777),
           (long long)e->size,
           (unsigned long long)e->rdev,
           e->path);
}

static int metadata_changed(const struct entry *a, const struct entry *b)
{
    return a->mode != b->mode ||
           a->size != b->size ||
           a->mtime != b->mtime ||
           a->rdev != b->rdev;
}

static void diff_snapshots(const struct snapshot *before,
                           const struct snapshot *after)
{
    size_t i = 0;
    size_t j = 0;

    while (i < before->count || j < after->count) {
        if (i >= before->count) {
            print_entry("ADD", &after->items[j++]);
            continue;
        }
        if (j >= after->count) {
            print_entry("REMOVE", &before->items[i++]);
            continue;
        }

        {
            int cmp = strcmp(before->items[i].path, after->items[j].path);
            if (cmp < 0) {
                print_entry("REMOVE", &before->items[i++]);
            } else if (cmp > 0) {
                print_entry("ADD", &after->items[j++]);
            } else {
                if (metadata_changed(&before->items[i], &after->items[j]))
                    print_entry("CHANGE", &after->items[j]);
                ++i;
                ++j;
            }
        }
    }
}

static void sleep_ms(unsigned ms)
{
    struct timespec req;
    struct timespec rem;

    req.tv_sec = (time_t)(ms / 1000u);
    req.tv_nsec = (long)(ms % 1000u) * 1000000L;
    while (nanosleep(&req, &rem) != 0 && errno == EINTR)
        req = rem;
}

static unsigned parse_u(const char *s, unsigned fallback)
{
    char *end = NULL;
    unsigned long v;

    if (!s || !*s)
        return fallback;
    errno = 0;
    v = strtoul(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0' || v > 86400UL)
        return fallback;
    return (unsigned)v;
}

int main(int argc, char **argv)
{
    static char *default_roots[] = { "/dev", "/pps/services", "/dev/shmem" };
    unsigned seconds = DEFAULT_SECONDS;
    unsigned interval_ms = DEFAULT_INTERVAL_MS;
    char **roots = default_roots;
    size_t root_count = sizeof(default_roots) / sizeof(default_roots[0]);
    struct snapshot a;
    struct snapshot b;
    struct snapshot *before = &a;
    struct snapshot *after = &b;
    unsigned elapsed_ms = 0;

    if (argc > 1)
        seconds = parse_u(argv[1], DEFAULT_SECONDS);
    if (argc > 2)
        interval_ms = parse_u(argv[2], DEFAULT_INTERVAL_MS);
    if (interval_ms == 0)
        interval_ms = DEFAULT_INTERVAL_MS;
    if (argc > 3) {
        roots = &argv[3];
        root_count = (size_t)(argc - 3);
    }

    a.items = (struct entry *)calloc(MAX_ENTRIES, sizeof(struct entry));
    b.items = (struct entry *)calloc(MAX_ENTRIES, sizeof(struct entry));
    if (!a.items || !b.items) {
        fprintf(stderr, "allocation failed\n");
        free(a.items);
        free(b.items);
        return 2;
    }
    a.capacity = b.capacity = MAX_ENTRIES;

    fprintf(stderr,
            "MHI2 iAP endpoint observer: metadata-only; never opens device endpoints.\n"
            "watch=%us interval=%ums roots=%lu\n",
            seconds, interval_ms, (unsigned long)root_count);

    collect_snapshot(before, roots, root_count);
    if (before->truncated)
        fprintf(stderr, "warning: baseline snapshot truncated at %u entries\n", MAX_ENTRIES);

    while (elapsed_ms < seconds * 1000u) {
        struct snapshot *tmp;
        sleep_ms(interval_ms);
        elapsed_ms += interval_ms;
        collect_snapshot(after, roots, root_count);
        diff_snapshots(before, after);
        fflush(stdout);
        if (after->truncated)
            fprintf(stderr, "warning: snapshot truncated at %u entries\n", MAX_ENTRIES);
        tmp = before;
        before = after;
        after = tmp;
    }

    free(a.items);
    free(b.items);
    return 0;
}
