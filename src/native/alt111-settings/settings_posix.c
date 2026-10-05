/* SPDX-License-Identifier: GPL-3.0-or-later
 * Flat-file, shared-lock settings transactions. Persistent mutation is gated.
 * No media, routing, service restart or shell-command execution in this layer.
 */
#include "alt111_settings.h"
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int fail(char *out, size_t cap, const char *format, ...)
{
    va_list ap;
    if (out && cap) { va_start(ap, format); vsnprintf(out, cap, format, ap); va_end(ap); }
    return -1;
}

static int path_for(char *out, size_t cap, const char *root, const char *name)
{
    int n;
    if (!root || !name || root[0] != '/' || strchr(name, '/')) return -1;
    n = snprintf(out, cap, "%s/%s", root, name);
    return n < 0 || (size_t)n >= cap ? -1 : 0;
}

static const char *group_name(unsigned group)
{
    unsigned i;
    for (i = 0; i < ALTSET_COUNT; ++i)
        if (alt111_setting(i)->group == group) return alt111_setting(i)->basename;
    return NULL;
}

/* 1 means absent; every other read failure is invalid, not a fallback. */
static int read_file(const char *path, char *out, size_t cap, size_t *size)
{
    struct stat before, opened;
    size_t used = 0;
    int fd;
    if (lstat(path, &before)) return errno == ENOENT ? 1 : -1;
    if (!S_ISREG(before.st_mode) || before.st_size < 1 || (uint64_t)before.st_size >= cap) return -1;
    fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    if (fcntl(fd, F_SETFD, FD_CLOEXEC) || fstat(fd, &opened) ||
        !S_ISREG(opened.st_mode) || opened.st_dev != before.st_dev || opened.st_ino != before.st_ino) {
        close(fd); return -1;
    }
    while (used < cap) {
        ssize_t n = read(fd, out + used, cap - used);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { close(fd); return -1; }
        if (!n) break;
        used += (size_t)n;
    }
    if (close(fd) || used >= cap || used != (size_t)opened.st_size) return -1;
    out[used] = 0; *size = used;
    return 0;
}

static int replace_file(const char *path, const char *data, size_t size)
{
    char temp[640];
    int fd, n;
    size_t used = 0;
    n = snprintf(temp, sizeof(temp), "%s.new.%ld", path, (long)getpid());
    if (n < 0 || (size_t)n >= sizeof(temp)) return -1;
    /* No truncation of a pre-existing unowned temporary file. */
    fd = open(temp, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) return -1;
    while (used < size) {
        ssize_t wrote = write(fd, data + used, size - used);
        if (wrote < 0 && errno == EINTR) continue;
        if (wrote <= 0) { close(fd); unlink(temp); return -1; }
        used += (size_t)wrote;
    }
    /* /dev/shmem may not implement fsync. It is volatile by contract; other
     * failures and all future persistent failures must still be surfaced. */
    if (fsync(fd) && errno != ENOSYS) { close(fd); unlink(temp); return -1; }
    if (close(fd)) { unlink(temp); return -1; }
    if (rename(temp, path)) { unlink(temp); return -1; }
    return 0;
}

static int lock_settings(const struct alt111_settings_paths *paths, int write_lock,
                          char *error, size_t cap)
{
    char path[512];
    struct flock lk;
    struct stat st;
    int fd;
    if (!paths || path_for(path, sizeof(path), paths->temp, "mibr-alt111-settings.lock"))
        return fail(error, cap, "INVALID_VALUE settings_root");
    if (!lstat(path, &st) && !S_ISREG(st.st_mode)) return fail(error, cap, "INVALID_VALUE lock_file_type");
    fd = open(path, O_RDWR | O_CREAT, 0600);
    if (fd < 0) return fail(error, cap, "APPLY_FAILED lock_open");
    memset(&lk, 0, sizeof(lk)); lk.l_type = write_lock ? F_WRLCK : F_RDLCK; lk.l_whence = SEEK_SET;
    if (fstat(fd, &st) || !S_ISREG(st.st_mode) || fcntl(fd, F_SETFD, FD_CLOEXEC) ||
        fcntl(fd, F_SETLK, &lk)) { close(fd); return fail(error, cap, "BUSY settings_lock"); }
    return fd;
}

static int journal_path(const struct alt111_settings_paths *p, char out[512])
{
    return path_for(out, 512, p->temp, "mibr-alt111-settings.journal");
}

static int read_layer(const struct alt111_settings_paths *p, unsigned group,
                       char blob[2049], size_t *size, unsigned *layer,unsigned skip_temp)
{
    char path[512]; int rc;
    if(!skip_temp){
        if (path_for(path, sizeof(path), p->temp, group_name(group))) return -1;
        rc = read_file(path, blob, 2049, size);
        if (rc != 1) { *layer = ALT111_TEMP; return rc; }
    }
    if (path_for(path, sizeof(path), p->persistent, group_name(group))) return -1;
    rc = read_file(path, blob, 2049, size);
    *layer = rc == 1 ? ALT111_PROFILE : ALT111_PERSISTENT;
    return rc;
}

static uint64_t revision_of(const struct alt111_settings *s)
{
    uint64_t v = 14695981039346656037ull;
    unsigned i;
    /* Opaque content/layer revision for CAS and status, not a security hash. */
    for (i = 0; i < ALTSET_COUNT; ++i) {
        const unsigned char *p = (const unsigned char *)s->value[i];
        do { v = (v ^ *p) * 1099511628211ull; } while (*p++);
        v = (v ^ s->layer[i]) * 1099511628211ull;
    }
    return v ? v : 1;
}

static int load_selected_locked(const struct alt111_settings_paths *p,
                        struct alt111_settings *out, char *error, size_t cap,unsigned skip_temp)
{
    char blob[2049], journal[512], preset[192];
    size_t size = 0;
    unsigned group, layer = 0;
    int rc;
    if (journal_path(p, journal)) return fail(error, cap, "INVALID_VALUE journal_path");
    if (access(journal, F_OK) == 0) return fail(error, cap, "BUSY interrupted_transaction_reconcile_required");
    if (!alt111_settings_defaults(out, "mibr_legacy")) {
        group = alt111_setting(ALTSET_PRESET_ID)->group;
        rc = read_layer(p, group, blob, &size, &layer,skip_temp);
        if (rc < 0 || (rc == 0 && alt111_settings_parse_group(out, group, blob, size, layer, 0, error, cap)))
            return fail(error, cap, "INVALID_VALUE basename=%s layer=%u", group_name(group), layer);
        strcpy(preset, out->value[ALTSET_PRESET_ID]);
        if (alt111_settings_defaults(out, preset)) return fail(error, cap, "INVALID_VALUE preset");
    } else return fail(error, cap, "APPLY_FAILED defaults");
    for (group = 0; group < ALTSET_GROUP_COUNT; ++group) {
        rc = read_layer(p, group, blob, &size, &layer,skip_temp);
        if (rc < 0) return fail(error, cap, "INVALID_VALUE basename=%s layer=%u file_read_or_type", group_name(group), layer);
        if (rc == 1) continue;
        /* Exact old Free790 D2 file disabled the unrelated timer. Its known
         * profile policy was still every-20; do not interpret it as mode off. */
        if (group == alt111_setting(ALTSET_KEYFRAME_MODE)->group &&
            !strcmp(preset, "omonob790") &&
            !strcmp(blob, "enabled=0\nevent_delay_ms=250\nmin_gap_ms=1000\nwatchdog_ms=0\n")) {
            unsigned i;
            for (i = 0; i < ALTSET_COUNT; ++i) if (alt111_setting(i)->group == group) out->layer[i] = layer;
            continue;
        }
        if (alt111_settings_parse_group(out, group, blob, size, layer, 1, error, cap)) return -1;
    }
    if (alt111_settings_validate(out, error, cap)) return -1;
    out->revision = revision_of(out);
    return 0;
}

static int load_locked(const struct alt111_settings_paths *p,
                        struct alt111_settings *out,char *error,size_t cap)
{
    return load_selected_locked(p,out,error,cap,0u);
}

int alt111_settings_load(const struct alt111_settings_paths *p,
                         struct alt111_settings *out, char *error, size_t cap)
{
    int fd = lock_settings(p, 0, error, cap), rc;
    if (fd < 0) return -1;
    rc = load_locked(p, out, error, cap); close(fd); return rc;
}

static int backup_path(const struct alt111_settings_paths *p, unsigned group,
                        char out[512])
{
    char name[64];
    snprintf(name, sizeof(name), "mibr-alt111-settings.backup-%u", group);
    return path_for(out, 512, p->temp, name);
}

static int restore_locked(const struct alt111_settings_paths *p,
                           unsigned mask, unsigned absent, char hashes[][65],
                           char *error, size_t cap)
{
    unsigned group;
    char path[512], backup[512], blob[2049], journal[512];
    size_t size;
    char hash[65];
    /* Validate every backup before performing any restore mutation. */
    for (group = 0; group < ALTSET_GROUP_COUNT; ++group) {
        if (!(mask & (1u << group)) || (absent & (1u << group))) continue;
        if (backup_path(p, group, backup) || read_file(backup, blob, sizeof(blob), &size))
            return fail(error, cap, "ROLLBACK_FAILED missing_backup group=%u", group);
        mibr_sha256_bytes(blob, size, hash);
        if (strcmp(hash, hashes[group])) return fail(error, cap, "ROLLBACK_FAILED backup_hash group=%u", group);
    }
    for (group = 0; group < ALTSET_GROUP_COUNT; ++group) {
        if (!(mask & (1u << group))) continue;
        if (path_for(path, sizeof(path), p->temp, group_name(group)) || backup_path(p, group, backup))
            return fail(error, cap, "ROLLBACK_FAILED path");
        if (absent & (1u << group)) {
            if (unlink(path) && errno != ENOENT) return fail(error, cap, "ROLLBACK_FAILED absent group=%u", group);
        } else {
            if (read_file(backup, blob, sizeof(blob), &size) || replace_file(path, blob, size) ||
                read_file(path, blob, sizeof(blob), &size))
                return fail(error, cap, "ROLLBACK_FAILED group=%u", group);
            mibr_sha256_bytes(blob, size, hash);
            if (strcmp(hash, hashes[group])) return fail(error, cap, "ROLLBACK_FAILED restored_hash group=%u", group);
        }
    }
    if (journal_path(p, journal) || unlink(journal)) return fail(error, cap, "ROLLBACK_FAILED journal");
    return 0;
}

static int transaction_locked(const struct alt111_settings_paths *p,
                               struct alt111_settings *desired, unsigned mask,
                               unsigned clear_mask, struct alt111_settings *out,
                               char *error, size_t cap)
{
    char path[512], backup[512], journal[512], blob[2049], record[2049];
    char hashes[ALTSET_GROUP_COUNT][65];
    unsigned group, absent = 0;
    size_t size;
    int rc, length, used;
    memset(hashes, 0, sizeof(hashes));
    for (group = 0; group < ALTSET_GROUP_COUNT; ++group) {
        if (!(mask & (1u << group))) continue;
        if (path_for(path, sizeof(path), p->temp, group_name(group)) || backup_path(p, group, backup))
            return fail(error, cap, "APPLY_FAILED backup_path");
        rc = read_file(path, blob, sizeof(blob), &size);
        if (rc < 0) return fail(error, cap, "INVALID_VALUE backup group=%u", group);
        if (rc == 1) absent |= 1u << group;
        else {
            mibr_sha256_bytes(blob, size, hashes[group]);
            if (replace_file(backup, blob, size)) return fail(error, cap, "APPLY_FAILED backup group=%u", group);
        }
    }
    if (journal_path(p, journal)) return fail(error, cap, "APPLY_FAILED journal_path");
    used = snprintf(record, sizeof(record), "schema=1\nmask=%u\nabsent=%u\n", mask, absent);
    for (group = 0; group < ALTSET_GROUP_COUNT; ++group) {
        if (!(mask & (1u << group)) || (absent & (1u << group))) continue;
        length = snprintf(record + used, sizeof(record) - (size_t)used, "%u:%s\n", group, hashes[group]);
        if (length < 0 || (size_t)length >= sizeof(record) - (size_t)used) return fail(error, cap, "APPLY_FAILED journal_capacity");
        used += length;
    }
    if (replace_file(journal, record, (size_t)used)) return fail(error, cap, "APPLY_FAILED journal");
    for (group = 0; group < ALTSET_GROUP_COUNT; ++group) {
        if (!(mask & (1u << group))) continue;
        if (path_for(path, sizeof(path), p->temp, group_name(group))) goto rollback;
        if (clear_mask & (1u << group)) {
            if (unlink(path) && errno != ENOENT) goto rollback;
        } else {
            length = alt111_settings_render_group(desired, group, blob, sizeof(blob));
            if (length < 0 || replace_file(path, blob, (size_t)length)) goto rollback;
        }
    }
    /* The lock is the reader barrier. Removing the journal commits the batch;
     * a crash before removal means rollback at next explicit reconciliation. */
    if (unlink(journal)) goto rollback;
    if (load_locked(p, out, error, cap)) return fail(error, cap, "APPLY_FAILED committed_snapshot_read");
    return 0;
rollback:
    rc = restore_locked(p, mask, absent, hashes, error, cap);
    return rc ? -1 : fail(error, cap, "APPLY_FAILED rolled_back");
}

int alt111_settings_mutate(const struct alt111_settings_paths *p,
                           unsigned layer, const unsigned *ids,
                           const char *const *values, size_t count,
                           uint64_t expected, struct alt111_settings *out,
                           char *error, size_t cap)
{
    struct alt111_settings *desired;
    int fd, rc = -1;
    unsigned mask = 0, i, j;
    size_t total = 0;
    if (layer == ALT111_PERSISTENT) return fail(error, cap, "POLICY_BLOCKED persistent_backup_powerloss_gate");
    if (layer != ALT111_TEMP || !count || count > ALTSET_COUNT || !ids || !values)
        return fail(error, cap, "INVALID_VALUE batch");
    fd = lock_settings(p, 1, error, cap); if (fd < 0) return -1;
    desired = malloc(sizeof(*desired));
    if (!desired) { close(fd); return fail(error, cap, "APPLY_FAILED allocation"); }
    if (load_locked(p, desired, error, cap)) goto done;
    if (expected && desired->revision != expected) { fail(error, cap, "STALE_REVISION"); goto done; }
    for (i = 0; i < count; ++i) {
        if (ids[i] >= ALTSET_COUNT || !values[i]) { fail(error, cap, "INVALID_VALUE key"); goto done; }
        for (j = 0; j < i; ++j) if (ids[j] == ids[i]) { fail(error, cap, "INVALID_VALUE duplicate_batch_key"); goto done; }
        total += strlen(values[i]) + strlen(alt111_setting(ids[i])->key) + 2;
        if (total > ALT111_SETTING_BATCH_CAP || alt111_settings_set(desired, ids[i], values[i], layer)) {
            fail(error, cap, "INVALID_VALUE key=%s", alt111_setting(ids[i])->key); goto done;
        }
        mask |= 1u << alt111_setting(ids[i])->group;
    }
    if (alt111_settings_validate(desired, error, cap)) goto done;
    rc = transaction_locked(p, desired, mask, 0, out, error, cap);
done:
    free(desired); close(fd); return rc;
}

int alt111_settings_clear(const struct alt111_settings_paths *p,
                          unsigned layer, unsigned id, uint64_t expected,
                          struct alt111_settings *out, char *error, size_t cap)
{
    int fd, rc = -1;
    struct alt111_settings *desired;
    char path[512], blob[2049];
    size_t size;
    unsigned group;
    if (layer != ALT111_TEMP) return fail(error, cap, "POLICY_BLOCKED persistent_backup_powerloss_gate");
    if (id >= ALTSET_COUNT) return fail(error, cap, "INVALID_VALUE key");
    fd = lock_settings(p, 1, error, cap); if (fd < 0) return -1;
    desired = malloc(sizeof(*desired));
    if (!desired) { close(fd); return fail(error, cap, "APPLY_FAILED allocation"); }
    if (load_locked(p, desired, error, cap)) goto done;
    if (expected && desired->revision != expected) { fail(error, cap, "STALE_REVISION"); goto done; }
    group = alt111_setting(id)->group;
    /* Validate the complete post-clear snapshot before the first mutation. */
    if (group == alt111_setting(ALTSET_PRESET_ID)->group) {
        fail(error, cap, "INVALID_VALUE use_preset_transaction_for_profile"); goto done;
    }
    {
        struct alt111_settings defaults;
        unsigned i;
        if (alt111_settings_defaults(&defaults, desired->value[ALTSET_PRESET_ID])) goto done;
        for (i = 0; i < ALTSET_COUNT; ++i) if (alt111_setting(i)->group == group) {
            strcpy(desired->value[i], defaults.value[i]); desired->layer[i] = ALT111_PROFILE;
        }
    }
    if (path_for(path, sizeof(path), p->persistent, group_name(group))) goto done;
    rc = read_file(path, blob, sizeof(blob), &size);
    if (rc < 0 || (rc == 0 && alt111_settings_parse_group(desired, group, blob, size, ALT111_PERSISTENT, 1, error, cap))) {
        rc = fail(error, cap, "INVALID_VALUE post_clear_lower_layer"); goto done;
    }
    if (alt111_settings_validate(desired, error, cap)) { rc = -1; goto done; }
    rc = transaction_locked(p, desired, 1u << group, 1u << group, out, error, cap);
done:
    free(desired); close(fd); return rc;
}

int alt111_settings_reconcile(const struct alt111_settings_paths *p,
                              char *error, size_t cap)
{
    char path[512], blob[2049];
    size_t size;
    unsigned mask = 0, absent = 0;
    unsigned group, hash_mask = 0;
    char hashes[ALTSET_GROUP_COUNT][65];
    int fd = lock_settings(p, 1, error, cap), rc, consumed = 0;
    if (fd < 0) return -1;
    if (journal_path(p, path)) { close(fd); return fail(error, cap, "INVALID_VALUE journal_path"); }
    rc = read_file(path, blob, sizeof(blob), &size);
    if (rc == 1) { close(fd); if (error && cap) error[0] = 0; return 0; }
    memset(hashes, 0, sizeof(hashes));
    if (rc || sscanf(blob, "schema=1\nmask=%u\nabsent=%u\n%n", &mask, &absent, &consumed) != 2 ||
        !mask || mask >= (1u << ALTSET_GROUP_COUNT) || (absent & ~mask)) {
        close(fd); return fail(error, cap, "ROLLBACK_FAILED malformed_journal");
    }
    while (consumed < (int)size) {
        int n = 0;
        char hash[65];
        if (sscanf(blob + consumed, "%u:%64[0123456789abcdef]\n%n", &group, hash, &n) != 2 ||
            !n || strlen(hash) != 64 || group >= ALTSET_GROUP_COUNT ||
            (hash_mask & (1u << group)) || !(mask & (1u << group)) || (absent & (1u << group))) {
            close(fd); return fail(error, cap, "ROLLBACK_FAILED malformed_journal_hash");
        }
        strcpy(hashes[group], hash); hash_mask |= 1u << group; consumed += n;
    }
    if (hash_mask != (mask & ~absent)) { close(fd); return fail(error, cap, "ROLLBACK_FAILED incomplete_journal_hashes"); }
    rc = restore_locked(p, mask, absent, hashes, error, cap); close(fd); return rc;
}

int alt111_settings_clear_temp(const struct alt111_settings_paths *p,
                               uint64_t expected,struct alt111_settings *out,
                               char *error,size_t cap)
{
    struct alt111_settings *lower;
    int fd,rc=-1;
    unsigned all=(1u<<ALTSET_GROUP_COUNT)-1u;
    fd=lock_settings(p,1,error,cap);if(fd<0)return -1;
    lower=malloc(sizeof(*lower));
    if(!lower){close(fd);return fail(error,cap,"APPLY_FAILED allocation");}
    if(expected && (load_locked(p,lower,error,cap)||lower->revision!=expected)){
        fail(error,cap,"STALE_REVISION");goto done;
    }
    /* No mutation until the entire newly exposed lower layer is valid. */
    if(load_selected_locked(p,lower,error,cap,1u))goto done;
    rc=transaction_locked(p,lower,all,all,out,error,cap);
done:
    free(lower);close(fd);return rc;
}

int alt111_settings_preset(const struct alt111_settings_paths *p,
                           const char *preset, uint64_t expected,
                           struct alt111_settings *out, char *error, size_t cap)
{
    struct alt111_settings *desired;
    char journal[512];
    int fd, rc = -1;
    unsigned i;
    fd = lock_settings(p, 1, error, cap); if (fd < 0) return -1;
    desired = malloc(sizeof(*desired));
    if (!desired) { close(fd); return fail(error, cap, "APPLY_FAILED allocation"); }
    if (journal_path(p, journal) || access(journal, F_OK) == 0) {
        fail(error, cap, "BUSY interrupted_transaction_reconcile_required"); goto done;
    }
    if (expected && (load_locked(p, desired, error, cap) || desired->revision != expected)) {
        fail(error, cap, "STALE_REVISION"); goto done;
    }
    if (alt111_settings_defaults(desired, preset) || alt111_settings_validate(desired, error, cap)) {
        fail(error, cap, "INVALID_VALUE preset"); goto done;
    }
    for (i = 0; i < ALTSET_COUNT; ++i) desired->layer[i] = ALT111_TEMP;
    /* Explicit whole-profile replacement can migrate an old D2 group. Exact
     * pre-existing bytes/ABSENT are journaled, never silently reinterpreted. */
    rc = transaction_locked(p, desired, (1u << ALTSET_GROUP_COUNT) - 1u, 0, out, error, cap);
done:
    free(desired); close(fd); return rc;
}
