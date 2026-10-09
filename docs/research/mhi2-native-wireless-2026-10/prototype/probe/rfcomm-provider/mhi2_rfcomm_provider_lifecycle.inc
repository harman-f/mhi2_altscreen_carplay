static int provider_start_impl(struct mhi2_rfcomm_provider *p)
{
    int rc;

    if (p == NULL) {
        errno = EINVAL;
        return -1;
    }

    if (p->target_mode && !env_enabled("MHI2_IAP_RFCOMM_LAB")) {
        errno = EPERM;
        fprintf(stderr,
            "MHI2_RFCOMM_PROVIDER start=blocked reason=rfcomm_lab_gate\n");
        return -1;
    }

    pthread_mutex_lock(&p->lock);
    if (p->started && !p->stopping) {
        pthread_mutex_unlock(&p->lock);
        return 0;
    }
    if (p->stopping) {
        pthread_mutex_unlock(&p->lock);
        errno = EBUSY;
        return -1;
    }
    pthread_mutex_unlock(&p->lock);

    reset_queues(p);
    p->channel = 0;
    prepare_descriptor(p);
    prepare_sdp(p);

    rc = p->stack.register_server(p->stack_opaque, p->descriptor,
                                  &p->channel,
                                  MHI2_IAP_RFCOMM_INITIAL_CREDITS);
    if (rc != 0) {
        endpoint_stop(p);
        errno = EIO;
        return -1;
    }
    pthread_mutex_lock(&p->lock);
    p->registered = 1;
    pthread_mutex_unlock(&p->lock);

    p->sdp_protocol[sizeof(p->sdp_protocol) - 1] = p->channel;
    rc = p->stack.publish_sdp(p->stack_opaque, p->sdp_record);
    if (rc != 0) {
        errno = EIO;
        return -1; /* start wrapper attempts checked rollback, retaining busy storage */
    }
    pthread_mutex_lock(&p->lock);
    p->sdp_published = 1;
    pthread_mutex_unlock(&p->lock);

    pthread_mutex_lock(&p->lock);
    p->started = 1;
    p->stopping = 0;
    p->tx_stop = p->tx_wake = 0;
    pthread_mutex_unlock(&p->lock);
    rc = pthread_create(&p->tx_thread, NULL, tx_thread_main, p);
    if (rc != 0) { errno = rc; return -1; }
    p->tx_thread_started = 1;
    /* Attach only after native registration, SDP and TX worker succeed. */
    if (endpoint_start(p) != 0 || endpoint_publish_ready(p) != 0) return -1;

    fprintf(stderr,
        "MHI2_RFCOMM_PROVIDER start=ok channel=%u mtu=%u credits=%u endpoint=%s\n",
        (unsigned)p->channel, (unsigned)MHI2_IAP_RFCOMM_MTU,
        (unsigned)MHI2_IAP_RFCOMM_INITIAL_CREDITS, p->endpoint_path);
    return 0;
}

static int wait_for_quiescence(struct mhi2_rfcomm_provider *p)
{
    struct timespec deadline;
    int rc = 0;

    if (clock_gettime(CLOCK_MONOTONIC, &deadline) != 0) {
        return -1;
    }
    deadline.tv_sec += STOP_WAIT_SECONDS;

    pthread_mutex_lock(&p->lock);
    while (p->connected || p->pending_accept || p->tx_inflight != NULL ||
           p->stack_calls != 0 || p->callbacks_active != 0) {
        rc = pthread_cond_timedwait(&p->cond, &p->lock, &deadline);
        if (rc == ETIMEDOUT) {
            pthread_mutex_unlock(&p->lock);
            errno = EBUSY;
            return -1;
        }
        if (rc != 0) {
            pthread_mutex_unlock(&p->lock);
            errno = rc;
            return -1;
        }
    }
    pthread_mutex_unlock(&p->lock);
    return 0;
}

static int provider_stop_impl(struct mhi2_rfcomm_provider *p)
{
    int connected;
    int rc;

    if (p == NULL) {
        errno = EINVAL;
        return -1;
    }

    pthread_mutex_lock(&p->lock);
    if (!p->started && !p->stopping && !p->registered) {
        pthread_mutex_unlock(&p->lock);
        return 0;
    }
    p->stopping = 1;
    connected = p->connected || p->pending_accept;
    p->session_ready = 0;
    pthread_mutex_unlock(&p->lock);

    endpoint_remove_ready(p);

    /* Stop new discovery/acceptance before disturbing an active session. */
    if (p->sdp_published) {
        rc = p->stack.remove_sdp(p->stack_opaque, p->sdp_record);
        if (rc != 0 && rc != 1) {
            errno = EBUSY;
            return -1;
        }
        pthread_mutex_lock(&p->lock);
        p->sdp_published = 0;
        pthread_mutex_unlock(&p->lock);
    }

    if (connected) {
        rc = p->stack.disconnect(p->stack_opaque, p->descriptor);
        if (rc != RF_RC_QUEUED && rc != 0 && rc != 0x13) {
            errno = EBUSY;
            return -1;
        }
    }

    if (wait_for_quiescence(p) != 0) {
        fprintf(stderr,
            "MHI2_RFCOMM_PROVIDER stop=blocked reason=not_quiescent\n");
        return -1;
    }

    if (p->registered) {
        rc = p->stack.deregister_server(p->stack_opaque, p->descriptor,
                                        &p->channel);
        if (rc != 0 && rc != 1) {
            errno = EBUSY;
            return -1;
        }
        pthread_mutex_lock(&p->lock);
        p->registered = 0;
        pthread_mutex_unlock(&p->lock);
    }

    /* Successful native deregistration prevents new callbacks; drain already
     * entered callbacks before freeing dispatch/notification state. */
    if (wait_for_quiescence(p) != 0) return -1;
    pthread_mutex_lock(&p->lock);
    p->tx_stop = 1;
    pthread_cond_broadcast(&p->cond);
    pthread_mutex_unlock(&p->lock);
    if (p->tx_thread_started) {
        pthread_join(p->tx_thread, NULL);
        p->tx_thread_started = 0;
    }
    endpoint_stop(p);
    reset_queues(p);

    pthread_mutex_lock(&p->lock);
    p->started = 0;
    p->stopping = 0;
    p->connected = 0;
    memset(p->peer_mac, 0, sizeof(p->peer_mac));
    pthread_cond_broadcast(&p->cond);
    pthread_mutex_unlock(&p->lock);

    fprintf(stderr, "MHI2_RFCOMM_PROVIDER stop=ok\n");
    return 0;
}

int mhi2_rfcomm_provider_start(struct mhi2_rfcomm_provider *p)
{
    int rc;
    if (p == NULL) { errno = EINVAL; return -1; }
    pthread_mutex_lock(&p->lifecycle_lock);
    rc = provider_start_impl(p);
    if (rc != 0) {
        int saved = errno;
        (void)provider_stop_impl(p);
        errno = saved;
    }
    pthread_mutex_unlock(&p->lifecycle_lock);
    return rc;
}

int mhi2_rfcomm_provider_stop(struct mhi2_rfcomm_provider *p)
{
    int rc;
    if (p == NULL) { errno = EINVAL; return -1; }
    pthread_mutex_lock(&p->lifecycle_lock);
    rc = provider_stop_impl(p);
    pthread_mutex_unlock(&p->lifecycle_lock);
    return rc;
}

void mhi2_rfcomm_provider_destroy(struct mhi2_rfcomm_provider *p)
{
    if (p == NULL) {
        return;
    }

    if (mhi2_rfcomm_provider_stop(p) != 0) {
        /*
         * Fail closed: do not free callback-owned storage while the target
         * stack may still reference it.
         */
        fprintf(stderr,
            "MHI2_RFCOMM_PROVIDER destroy=blocked reason=provider_busy\n");
        return;
    }

    if (p == g_target_provider) {
        g_target_provider = NULL;
    }
    pthread_cond_destroy(&p->cond);
    pthread_mutex_destroy(&p->lifecycle_lock);
    pthread_mutex_destroy(&p->lock);
    free(p);
}
