#ifdef __QNXNTO__

#include <sys/types.h>
#include <unistd.h>
#include <fcntl.h>

#define PROVIDER_READY_PATH "/tmp/mhi2-wcp-provider.ready"

static int endpoint_publish_ready(struct mhi2_rfcomm_provider *p)
{
    char path[96], text[128];
    int fd, n, saved, result = -1;
    pthread_mutex_lock(&p->lock);
    if (p->ep_ready != 1 || p->stopping || !p->started ||
        !p->registered || !p->sdp_published) {
        errno = EIO;
        goto out;
    }
    snprintf(path, sizeof(path), "%s.%ld", PROVIDER_READY_PATH, (long)getpid());
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd == -1) goto out;
    n = snprintf(text, sizeof(text), "pid=%ld\nchannel=%u\nregistered=1\nsdp=1\nendpoint=1\n",
                 (long)getpid(), (unsigned)p->channel);
    if (write(fd, text, (size_t)n) != n) {
        saved = errno;
        close(fd);
        unlink(path);
        errno = saved;
        goto out;
    }
    if (close(fd) == -1) { unlink(path); goto out; }
    if (rename(path, PROVIDER_READY_PATH) == -1) { unlink(path); goto out; }
    result = 0;
out:
    pthread_mutex_unlock(&p->lock);
    return result;
}

static void endpoint_remove_ready(struct mhi2_rfcomm_provider *p)
{
    FILE *f;
    long pid = -1;
    (void)p;
    f = fopen(PROVIDER_READY_PATH, "r");
    if (f == NULL) return;
    if (fscanf(f, "pid=%ld", &pid) != 1) pid = -1;
    fclose(f);
    if (pid == (long)getpid()) unlink(PROVIDER_READY_PATH);
}

static int ep_io_read(resmgr_context_t *ctp, io_read_t *msg,
                      RESMGR_OCB_T *ocb)
{
    struct mhi2_rfcomm_provider *p = g_endpoint_provider;
    size_t want;
    size_t n;
    int rc;

    if (p == NULL) {
        return ENODEV;
    }

    rc = iofunc_read_verify(ctp, msg, ocb, NULL);
    if (rc != EOK) {
        return rc;
    }

    want = msg->i.nbytes;
    if (want > sizeof(p->ep_readbuf)) {
        want = sizeof(p->ep_readbuf);
    }
    n = mhi2_rfcomm_provider_read_rx(p, p->ep_readbuf, want);
    _IO_SET_READ_NBYTES(ctp, n);

    if (n == 0) {
        return EOK;
    }

    SETIOV(ctp->iov, p->ep_readbuf, n);
    return _RESMGR_NPARTS(1);
}

static int ep_io_write(resmgr_context_t *ctp, io_write_t *msg,
                       RESMGR_OCB_T *ocb)
{
    struct mhi2_rfcomm_provider *p = g_endpoint_provider;
    uint8_t *buf;
    size_t requested;
    size_t accepted;
    ssize_t received;
    int rc;

    if (p == NULL) {
        return ENODEV;
    }

    rc = iofunc_write_verify(ctp, msg, ocb, NULL);
    if (rc != EOK) {
        return rc;
    }

    if (!mhi2_rfcomm_provider_is_connected(p)) {
        return ENOTCONN;
    }

    requested = msg->i.nbytes;
    if (requested == 0) {
        _IO_SET_WRITE_NBYTES(ctp, 0);
        return EOK;
    }

    buf = (uint8_t *)malloc(requested);
    if (buf == NULL) {
        return ENOMEM;
    }

    received = resmgr_msgread(ctp, buf, requested, sizeof(msg->i));
    if (received == -1) {
        free(buf);
        return errno;
    }

    if (received == 0) {
        free(buf);
        _IO_SET_WRITE_NBYTES(ctp, 0);
        return EOK;
    }
    /* Only initialized bytes belong to this write, including short reads. */
    accepted = mhi2_rfcomm_provider_queue_tx(p, buf, (size_t)received);
    free(buf);

    if (accepted == 0) {
        return EAGAIN;
    }

    _IO_SET_WRITE_NBYTES(ctp, accepted);
    return EOK;
}

static int ep_io_notify(resmgr_context_t *ctp, io_notify_t *msg,
                        RESMGR_OCB_T *ocb)
{
    struct mhi2_rfcomm_provider *p = g_endpoint_provider;
    int trigger = 0;
    int rc;

    (void)ocb;
    if (p == NULL) {
        return ENODEV;
    }
    /* Explicit counting attr lock also covers callers without the default
     * dispatch lock. RX trigger uses the same lock, closing check/arm race. */
    rc = iofunc_attr_lock(&p->ep_attr);
    if (rc != EOK) return rc;

    if (mhi2_rfcomm_provider_rx_pending(p) != 0 ||
        !mhi2_rfcomm_provider_is_connected(p)) {
        trigger |= _NOTIFY_COND_INPUT;
    }

    rc = iofunc_notify(ctp, msg, p->ep_notify, trigger, NULL, NULL);
    iofunc_attr_unlock(&p->ep_attr);
    return rc;
}

static int ep_io_close_dup(resmgr_context_t *ctp, io_close_t *msg,
                            RESMGR_OCB_T *ocb)
{
    struct mhi2_rfcomm_provider *p = g_endpoint_provider;
    int rc;
    if (p != NULL) {
        rc = iofunc_attr_lock(&p->ep_attr);
        if (rc != EOK) return rc;
        iofunc_notify_remove(ctp, p->ep_notify);
        iofunc_attr_unlock(&p->ep_attr);
    }
    return iofunc_close_dup_default(ctp, msg, ocb);
}

static void *endpoint_thread_main(void *opaque)
{
    struct mhi2_rfcomm_provider *p =
        (struct mhi2_rfcomm_provider *)opaque;
    dispatch_context_t *ctp;

    ctp = dispatch_context_alloc(p->ep_dispatch);

    pthread_mutex_lock(&p->lock);
    p->ep_ready = ctp != NULL ? 1 : -1;
    pthread_cond_broadcast(&p->cond);
    pthread_mutex_unlock(&p->lock);

    if (ctp == NULL) {
        return NULL;
    }

    for (;;) {
        dispatch_context_t *next;
        int stop;

        pthread_mutex_lock(&p->lock);
        stop = p->ep_stop;
        pthread_mutex_unlock(&p->lock);
        if (stop) {
            break;
        }

        next = dispatch_block(ctp);
        if (next == NULL) {
            /* On error QNX keeps the old context valid. Do not lose it.
             * On success QNX may reallocate it; only this thread owns it. */
            int saved = errno;
            pthread_mutex_lock(&p->lock);
            stop = p->ep_stop;
            pthread_mutex_unlock(&p->lock);
            if (stop) {
                break;
            }
            if (saved != EINTR) {
                endpoint_remove_ready(p);
                break;
            }
            continue;
        }
        ctp = next;
        if (ctp->message_context.rcvid == -1) continue; /* relative timeout */
        dispatch_handler(ctp);
    }

    dispatch_context_free(ctp);

    pthread_mutex_lock(&p->lock);
    p->ep_ready = -1;
    pthread_cond_broadcast(&p->cond);
    pthread_mutex_unlock(&p->lock);
    endpoint_remove_ready(p);
    return NULL;
}

static int endpoint_start(struct mhi2_rfcomm_provider *p)
{
    int rc;
    struct timespec timeout;

    if (!p->target_mode) {
        return 0;
    }

    if (g_endpoint_provider != NULL && g_endpoint_provider != p) {
        errno = EBUSY;
        return -1;
    }

    p->ep_dispatch = dispatch_create();
    if (p->ep_dispatch == NULL) {
        return -1;
    }

    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, &p->ep_connect,
                     _RESMGR_IO_NFUNCS, &p->ep_io);
    p->ep_io.read = ep_io_read;
    p->ep_io.write = ep_io_write;
    p->ep_io.notify = ep_io_notify;
    p->ep_io.close_dup = ep_io_close_dup;
    iofunc_attr_init(&p->ep_attr, S_IFCHR | 0600, NULL, NULL);
    IOFUNC_NOTIFY_INIT(p->ep_notify);

    p->ep_attach_id = resmgr_attach(p->ep_dispatch, NULL,
                                    p->endpoint_path, _FTYPE_ANY, 0,
                                    &p->ep_connect, &p->ep_io, &p->ep_attr);
    if (p->ep_attach_id == -1) {
        dispatch_destroy(p->ep_dispatch);
        p->ep_dispatch = NULL;
        return -1;
    }

    /* Bounded receive wait avoids passing a reallocatable dispatch context
     * across threads to dispatch_unblock(). No SDK calls or context pointers
     * are needed under the provider mutex during stop. */
    timeout.tv_sec = 1;
    timeout.tv_nsec = 0;
    if (dispatch_timeout(p->ep_dispatch, &timeout) == -1) {
        resmgr_detach(p->ep_dispatch, p->ep_attach_id, 0);
        p->ep_attach_id = -1;
        dispatch_destroy(p->ep_dispatch);
        p->ep_dispatch = NULL;
        return -1;
    }

    p->ep_stop = 0;
    p->ep_ready = 0;
    g_endpoint_provider = p;

    rc = pthread_create(&p->ep_thread, NULL, endpoint_thread_main, p);
    if (rc != 0) {
        g_endpoint_provider = NULL;
        resmgr_detach(p->ep_dispatch, p->ep_attach_id, 0);
        p->ep_attach_id = -1;
        dispatch_destroy(p->ep_dispatch);
        p->ep_dispatch = NULL;
        errno = rc;
        return -1;
    }
    p->ep_thread_started = 1;

    pthread_mutex_lock(&p->lock);
    while (p->ep_ready == 0) {
        (void)pthread_cond_wait(&p->cond, &p->lock);
    }
    rc = p->ep_ready;
    pthread_mutex_unlock(&p->lock);

    if (rc < 0) {
        endpoint_stop(p);
        errno = EIO;
        return -1;
    }
    return 0;
}

static void endpoint_stop(struct mhi2_rfcomm_provider *p)
{
    if (!p->target_mode || p->ep_dispatch == NULL) {
        return;
    }

    if (iofunc_attr_lock(&p->ep_attr) == EOK) {
        iofunc_notify_trigger(p->ep_notify, 1, IOFUNC_NOTIFY_INPUT);
        iofunc_attr_unlock(&p->ep_attr);
    }
    pthread_mutex_lock(&p->lock);
    p->ep_stop = 1;
    pthread_mutex_unlock(&p->lock);

    if (p->ep_thread_started) {
        (void)pthread_join(p->ep_thread, NULL);
        p->ep_thread_started = 0;
    }

    if (p->ep_attach_id != -1 && p->ep_dispatch != NULL) {
        (void)resmgr_detach(p->ep_dispatch, p->ep_attach_id, 0);
        p->ep_attach_id = -1;
    }
    if (iofunc_attr_lock(&p->ep_attr) == EOK) {
        iofunc_notify_remove(NULL, p->ep_notify);
        iofunc_attr_unlock(&p->ep_attr);
    }
    if (p->ep_dispatch != NULL) {
        dispatch_destroy(p->ep_dispatch);
        p->ep_dispatch = NULL;
    }

    p->ep_ready = 0;
    p->ep_stop = 0;
    if (g_endpoint_provider == p) {
        g_endpoint_provider = NULL;
    }
}

static void endpoint_rx_ready(struct mhi2_rfcomm_provider *p)
{
    if (p->target_mode && g_endpoint_provider == p) {
        if (iofunc_attr_lock(&p->ep_attr) != EOK) {
            pthread_mutex_lock(&p->lock);
            p->ep_ready = -1;
            pthread_mutex_unlock(&p->lock);
            endpoint_remove_ready(p);
            return;
        }
        iofunc_notify_trigger(p->ep_notify, 1, IOFUNC_NOTIFY_INPUT);
        iofunc_attr_unlock(&p->ep_attr);
    }
}

#else

static int endpoint_publish_ready(struct mhi2_rfcomm_provider *p)
{
    (void)p;
    return 0;
}

static void endpoint_remove_ready(struct mhi2_rfcomm_provider *p)
{
    (void)p;
}

static int endpoint_start(struct mhi2_rfcomm_provider *p)
{
    if (p->target_mode) {
        errno = ENOTSUP;
        return -1;
    }
    return 0;
}

static void endpoint_stop(struct mhi2_rfcomm_provider *p)
{
    (void)p;
}

static void endpoint_rx_ready(struct mhi2_rfcomm_provider *p)
{
    (void)p;
}

#endif
