static void rx_push(struct mhi2_rfcomm_provider *p,
                    const uint8_t *src, size_t length)
{
    size_t first;

    first = RX_CAPACITY - p->rx_tail;
    if (first > length) {
        first = length;
    }
    memcpy(p->rx + p->rx_tail, src, first);
    if (length > first) {
        memcpy(p->rx, src + first, length - first);
    }
    p->rx_tail = (p->rx_tail + length) % RX_CAPACITY;
    p->rx_count += length;
}

size_t mhi2_rfcomm_provider_rx_pending(struct mhi2_rfcomm_provider *p)
{
    size_t result;

    if (p == NULL) {
        return 0;
    }
    pthread_mutex_lock(&p->lock);
    result = p->rx_count;
    pthread_mutex_unlock(&p->lock);
    return result;
}

size_t mhi2_rfcomm_provider_read_rx(struct mhi2_rfcomm_provider *p,
                                    void *dst, size_t length)
{
    size_t n;
    size_t first;

    if (p == NULL || dst == NULL || length == 0) {
        return 0;
    }

    pthread_mutex_lock(&p->lock);
    if (!p->session_ready || p->stopping) {
        pthread_mutex_unlock(&p->lock);
        return 0;
    }
    n = length < p->rx_count ? length : p->rx_count;
    first = RX_CAPACITY - p->rx_head;
    if (first > n) {
        first = n;
    }
    memcpy(dst, p->rx + p->rx_head, first);
    if (n > first) {
        memcpy((uint8_t *)dst + first, p->rx, n - first);
    }
    p->rx_head = (p->rx_head + n) % RX_CAPACITY;
    p->rx_count -= n;
    pthread_mutex_unlock(&p->lock);
    return n;
}

static struct tx_packet *packet_alloc(struct mhi2_rfcomm_provider *p,
                                      const uint8_t *src, size_t length)
{
    struct tx_packet *pkt;

    pkt = (struct tx_packet *)calloc(1, sizeof(*pkt));
    if (pkt == NULL) {
        return NULL;
    }

    pkt->length = length;
    memcpy(pkt->data, src, length);
    put_target_ptr(pkt->raw + 0x08, pkt->data);
    put_u16(pkt->raw + 0x0c, (uint16_t)length);
    put_target_ptr(pkt->raw + 0x14, p);
    return pkt;
}

size_t mhi2_rfcomm_provider_queue_tx(struct mhi2_rfcomm_provider *p,
                                     const void *src, size_t length)
{
    const uint8_t *cursor = (const uint8_t *)src;
    size_t accepted = 0;
    uint64_t generation;

    if (p == NULL || (src == NULL && length != 0)) {
        return 0;
    }

    /* One write belongs to one session, including every MTU-sized chunk. */
    pthread_mutex_lock(&p->lock);
    generation = p->generation;
    pthread_mutex_unlock(&p->lock);

    while (accepted < length) {
        struct tx_packet *pkt;
        size_t chunk = length - accepted;

        if (chunk > MHI2_IAP_RFCOMM_MTU) {
            chunk = MHI2_IAP_RFCOMM_MTU;
        }

        pthread_mutex_lock(&p->lock);
        if (!p->started || p->stopping || !p->session_ready ||
            p->generation != generation ||
            p->tx_queued >= TX_QUEUE_LIMIT) {
            pthread_mutex_unlock(&p->lock);
            break;
        }
        pthread_mutex_unlock(&p->lock);

        pkt = packet_alloc(p, cursor + accepted, chunk);
        if (pkt == NULL) {
            break;
        }
        pkt->generation = generation;

        pthread_mutex_lock(&p->lock);
        if (!p->started || p->stopping || !p->session_ready ||
            p->generation != generation ||
            p->tx_queued >= TX_QUEUE_LIMIT) {
            pthread_mutex_unlock(&p->lock);
            free(pkt);
            break;
        }
        if (p->tx_tail != NULL) {
            p->tx_tail->next = pkt;
        } else {
            p->tx_head = pkt;
        }
        p->tx_tail = pkt;
        p->tx_queued++;
        pthread_mutex_unlock(&p->lock);

        accepted += chunk;
    }

    if (accepted != 0) {
        kick_tx(p);
    }
    return accepted;
}

static struct tx_packet *packet_from_raw(void *raw)
{
    struct tx_packet *pkt;
    size_t offset = (size_t)&((struct tx_packet *)0)->raw;
    pkt = (struct tx_packet *)((uint8_t *)raw - offset);
    return pkt;
}

/* Only the worker calls the SDK. IO/callback threads merely wake it. */
static void kick_tx(struct mhi2_rfcomm_provider *p)
{
    pthread_mutex_lock(&p->lock);
    p->tx_wake = 1;
    pthread_cond_broadcast(&p->cond);
    pthread_mutex_unlock(&p->lock);
}

static void pump_tx_once(struct mhi2_rfcomm_provider *p)
{
    struct tx_packet *pkt;
    unsigned capacity;
    int rc;
    int free_now = 0;
    int valid;

    pthread_mutex_lock(&p->lock);
    if (!p->started || p->stopping || !p->session_ready ||
        p->tx_inflight != NULL || p->tx_head == NULL) {
        pthread_mutex_unlock(&p->lock);
        return;
    }

    pkt = p->tx_head;
    p->tx_head = pkt->next;
    if (p->tx_head == NULL) {
        p->tx_tail = NULL;
    }
    p->tx_queued--;
    pkt->next = NULL;
    pkt->in_call = 1;
    p->tx_inflight = pkt;
    p->stack_calls++;
    pthread_mutex_unlock(&p->lock);

    /* Reservation pins packet/provider while capacity may synchronously
     * close the session. Admission refuses another peer until it drains. */
    capacity = p->stack.tx_capacity(p->stack_opaque, p->descriptor);
    pthread_mutex_lock(&p->lock);
    valid = p->started && !p->stopping && p->session_ready &&
            pkt->generation == p->generation;
    if (valid && capacity < pkt->length) {
        p->tx_inflight = NULL;
        pkt->in_call = 0;
        pkt->next = p->tx_head;
        p->tx_head = pkt;
        if (p->tx_tail == NULL) p->tx_tail = pkt;
        p->tx_queued++;
        p->stack_calls--;
        pthread_cond_broadcast(&p->cond);
        pthread_mutex_unlock(&p->lock);
        return; /* A later credit/control event wakes the worker. */
    }
    pthread_mutex_unlock(&p->lock);
    rc = valid ? p->stack.send(p->stack_opaque, p->descriptor, pkt->raw) : 0;

    pthread_mutex_lock(&p->lock);
    pkt->in_call = 0;
    p->stack_calls--;
    if (rc != RF_RC_QUEUED || pkt->event_done) {
        if (p->tx_inflight == pkt) {
            p->tx_inflight = NULL;
        }
        free_now = 1;
        p->tx_wake = 1;
        pthread_cond_broadcast(&p->cond);
    }
    pthread_mutex_unlock(&p->lock);

    if (free_now) {
        free(pkt);
    }
}

static void *tx_thread_main(void *opaque)
{
    struct mhi2_rfcomm_provider *p = opaque;
    pthread_mutex_lock(&p->lock);
    for (;;) {
        while (!p->tx_stop && !p->tx_wake)
            pthread_cond_wait(&p->cond, &p->lock);
        if (p->tx_stop) break;
        p->tx_wake = 0;
        pthread_mutex_unlock(&p->lock);
        pump_tx_once(p);
        pthread_mutex_lock(&p->lock);
        pthread_cond_broadcast(&p->cond);
    }
    pthread_mutex_unlock(&p->lock);
    return NULL;
}
