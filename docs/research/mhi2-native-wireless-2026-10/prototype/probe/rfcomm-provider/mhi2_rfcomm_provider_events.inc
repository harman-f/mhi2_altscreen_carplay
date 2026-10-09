static void complete_tx(struct mhi2_rfcomm_provider *p, void *raw, uint16_t status)
{
    struct tx_packet *pkt = NULL;
    int free_now = 0;
    int kick = 0;

    if (raw != NULL) {
        pkt = packet_from_raw(raw);
    }

    pthread_mutex_lock(&p->lock);
    if (pkt != NULL && p->tx_inflight == pkt) {
        pkt->event_done = 1;
        if (!pkt->in_call) {
            p->tx_inflight = NULL;
            free_now = 1;
            kick = 1;
            pthread_cond_broadcast(&p->cond);
        }
    }
    pthread_mutex_unlock(&p->lock);

    if (status != 0 && status != RF_TX_CANCELLED) {
        fprintf(stderr,
            "MHI2_RFCOMM_PROVIDER tx_complete status=0x%04x\n",
            (unsigned)status);
    }
    if (free_now) {
        free(pkt);
    }
    if (kick) {
        kick_tx(p);
    }
}

static void handle_event_body(struct mhi2_rfcomm_provider *p,
                                       const void *event_record)
{
    const uint8_t *event = (const uint8_t *)event_record;
    unsigned id;
    int accept_now = 0;
    int reject_now = 0;
    int add_credit = 0;
    int force_disconnect = 0;

    if (p == NULL || event == NULL) {
        return;
    }

    id = event[0];

    if (id == RF_EVENT_INBOUND) {
        pthread_mutex_lock(&p->lock);
        if (p->started && p->sdp_published && !p->stopping &&
            !p->connected && !p->pending_accept &&
            p->tx_inflight == NULL && p->stack_calls == 0) {
            p->pending_accept = 1;
            p->generation++;
            p->stack_calls++;
            accept_now = 1;
        } else if (p->registered && !p->pending_accept &&
                   p->stack_calls == 0 && p->tx_inflight == NULL) {
            p->stack_calls++;
            reject_now = 1;
        }
        pthread_mutex_unlock(&p->lock);

        if (accept_now) {
            int rc = p->stack.accept(p->stack_opaque, p->descriptor, 1);
            pthread_mutex_lock(&p->lock);
            if (rc != 0 && rc != RF_RC_QUEUED) p->pending_accept = 0;
            p->stack_calls--;
            pthread_cond_broadcast(&p->cond);
            pthread_mutex_unlock(&p->lock);
        } else if (reject_now) {
            (void)p->stack.accept(p->stack_opaque, p->descriptor, 0);
            pthread_mutex_lock(&p->lock);
            p->stack_calls--;
            pthread_cond_broadcast(&p->cond);
            pthread_mutex_unlock(&p->lock);
        }
        return;
    }

    if (id == RF_EVENT_ESTABLISHED) {
        void *remote = get_target_ptr(event + 0x0c);
        uint16_t status = get_u16(event + 0x02);

        pthread_mutex_lock(&p->lock);
        if (status == 0) {
            p->connected = 1;
            p->session_ready = p->pending_accept && p->started &&
                               !p->stopping && p->tx_inflight == NULL;
            if (p->session_ready && remote != NULL) {
                memcpy(p->peer_mac, (const uint8_t *)remote + 0x0d,
                       sizeof(p->peer_mac));
            }
            if (!p->session_ready) {
                p->stack_calls++;
                force_disconnect = 1;
            }
        }
        p->pending_accept = 0;
        pthread_cond_broadcast(&p->cond);
        pthread_mutex_unlock(&p->lock);
        if (force_disconnect) {
            (void)p->stack.disconnect(p->stack_opaque, p->descriptor);
            pthread_mutex_lock(&p->lock);
            p->stack_calls--;
            pthread_cond_broadcast(&p->cond);
            pthread_mutex_unlock(&p->lock);
        }
        endpoint_rx_ready(p);
        return;
    }

    if (id == RF_EVENT_CONTROL) {
        kick_tx(p);
        return;
    }

    if (id == RF_EVENT_CLOSED) {
        struct tx_packet *queued;
        pthread_mutex_lock(&p->lock);
        p->connected = 0;
        p->session_ready = 0;
        p->pending_accept = 0;
        p->generation++;
        p->rx_head = p->rx_tail = p->rx_count = 0;
        queued = p->tx_head;
        p->tx_head = p->tx_tail = NULL;
        p->tx_queued = 0;
        /* tx_inflight remains pinned until its native completion/cancel. */
        memset(p->peer_mac, 0, sizeof(p->peer_mac));
        pthread_cond_broadcast(&p->cond);
        pthread_mutex_unlock(&p->lock);
        free_tx_list(queued);
        endpoint_rx_ready(p);
        return;
    }

    if (id == RF_EVENT_RX) {
        uint16_t length = get_u16(event + 0x08);
        const uint8_t *payload =
            (const uint8_t *)get_target_ptr(event + 0x0c);

        if (payload == NULL || length == 0) {
            return;
        }

        pthread_mutex_lock(&p->lock);
        if (p->session_ready && !p->stopping &&
            (size_t)length <= RX_CAPACITY - p->rx_count) {
            rx_push(p, payload, length);
            add_credit = 1;
        } else if (p->connected) {
            force_disconnect = 1;
        }
        if (add_credit || force_disconnect) p->stack_calls++;
        pthread_mutex_unlock(&p->lock);

        if (add_credit) {
            endpoint_rx_ready(p);
            (void)p->stack.add_credit(p->stack_opaque, p->descriptor, 1);
        } else if (force_disconnect) {
            fprintf(stderr,
                "MHI2_RFCOMM_PROVIDER rx_overflow=disconnect length=%u\n",
                (unsigned)length);
            (void)p->stack.disconnect(p->stack_opaque, p->descriptor);
        }
        if (add_credit || force_disconnect) {
            pthread_mutex_lock(&p->lock);
            p->stack_calls--;
            pthread_cond_broadcast(&p->cond);
            pthread_mutex_unlock(&p->lock);
        }
        return;
    }

    if (id == RF_EVENT_TX_DONE) {
        complete_tx(p, get_target_ptr(event + 0x0c), get_u16(event + 0x02));
    }
}

void mhi2_rfcomm_provider_handle_event(struct mhi2_rfcomm_provider *p,
                                       const void *event_record)
{
    if (p == NULL || event_record == NULL) return;
    pthread_mutex_lock(&p->lock);
    p->callbacks_active++;
    pthread_mutex_unlock(&p->lock);
    handle_event_body(p, event_record);
    pthread_mutex_lock(&p->lock);
    p->callbacks_active--;
    pthread_cond_broadcast(&p->cond);
    pthread_mutex_unlock(&p->lock);
}

uint8_t mhi2_rfcomm_provider_channel(const struct mhi2_rfcomm_provider *p)
{
    return p != NULL ? p->channel : 0;
}

int mhi2_rfcomm_provider_is_started(const struct mhi2_rfcomm_provider *p)
{
    int result = 0;
    if (p != NULL) {
        pthread_mutex_lock((pthread_mutex_t *)&p->lock);
        result = p->started && !p->stopping;
        pthread_mutex_unlock((pthread_mutex_t *)&p->lock);
    }
    return result;
}

int mhi2_rfcomm_provider_is_connected(const struct mhi2_rfcomm_provider *p)
{
    int result = 0;
    if (p != NULL) {
        pthread_mutex_lock((pthread_mutex_t *)&p->lock);
        result = p->session_ready && !p->stopping;
        pthread_mutex_unlock((pthread_mutex_t *)&p->lock);
    }
    return result;
}

const char *mhi2_rfcomm_provider_endpoint_path(
    const struct mhi2_rfcomm_provider *p)
{
    return p != NULL ? p->endpoint_path : NULL;
}
