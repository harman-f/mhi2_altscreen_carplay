static struct mhi2_rfcomm_provider *
provider_alloc(const struct mhi2_rfcomm_stack_ops *ops, void *opaque,
               int target_mode)
{
    struct mhi2_rfcomm_provider *p;
    pthread_condattr_t cond_attr;

    if (ops == NULL || ops->register_server == NULL ||
        ops->publish_sdp == NULL || ops->accept == NULL ||
        ops->add_credit == NULL || ops->tx_capacity == NULL ||
        ops->send == NULL || ops->disconnect == NULL ||
        ops->deregister_server == NULL || ops->remove_sdp == NULL) {
        errno = EINVAL;
        return NULL;
    }

    p = (struct mhi2_rfcomm_provider *)calloc(1, sizeof(*p));
    if (p == NULL) {
        return NULL;
    }

    p->stack = *ops;
    p->stack_opaque = opaque;
    p->target_mode = target_mode;
    p->channel = 0;
    (void)snprintf(p->endpoint_path, sizeof(p->endpoint_path), "%s",
                   MHI2_IAP_ENDPOINT_DEFAULT);

#ifdef __QNXNTO__
    p->ep_attach_id = -1;
#endif

    if (pthread_mutex_init(&p->lock, NULL) != 0) {
        free(p);
        errno = ENOMEM;
        return NULL;
    }
    if (pthread_mutex_init(&p->lifecycle_lock, NULL) != 0) {
        pthread_mutex_destroy(&p->lock);
        free(p);
        errno = ENOMEM;
        return NULL;
    }
    if (pthread_condattr_init(&cond_attr) != 0) {
        pthread_mutex_destroy(&p->lifecycle_lock);
        pthread_mutex_destroy(&p->lock);
        free(p);
        errno = ENOMEM;
        return NULL;
    }
    if (pthread_condattr_setclock(&cond_attr, CLOCK_MONOTONIC) != 0 ||
        pthread_cond_init(&p->cond, &cond_attr) != 0) {
        pthread_condattr_destroy(&cond_attr);
        pthread_mutex_destroy(&p->lifecycle_lock);
        pthread_mutex_destroy(&p->lock);
        free(p);
        errno = ENOMEM;
        return NULL;
    }

    pthread_condattr_destroy(&cond_attr);
    prepare_descriptor(p);
    prepare_sdp(p);
    return p;
}

struct mhi2_rfcomm_provider *mhi2_rfcomm_provider_create_target(void)
{
    struct mhi2_rfcomm_provider *p;

    if (g_target_provider != NULL) {
        errno = EBUSY;
        return NULL;
    }

    p = provider_alloc(&g_target_ops, NULL, 1);
    if (p != NULL) {
        g_target_provider = p;
    }
    return p;
}

struct mhi2_rfcomm_provider *
mhi2_rfcomm_provider_create_test(const struct mhi2_rfcomm_stack_ops *ops,
                                 void *opaque)
{
    return provider_alloc(ops, opaque, 0);
}

static void target_callback(void *descriptor, void *event_record)
{
    struct mhi2_rfcomm_provider *p = g_target_provider;

    if (p == NULL || descriptor != p->descriptor || event_record == NULL) {
        return;
    }
    mhi2_rfcomm_provider_handle_event(p, event_record);
}

static void prepare_descriptor(struct mhi2_rfcomm_provider *p)
{
    void (*cb)(void *, void *) = target_callback;

    memset(p->descriptor, 0, sizeof(p->descriptor));
    /*
     * Exact generic MU1440 descriptor fields:
     *   +0x08 callback
     *   +0x0c requested MTU
     *   +0x0e priority
     * Old MU1433 iAP constructor used MTU 0x13ab and priority 0.
     */
    put_target_ptr(p->descriptor + 0x08, (const void *)(uintptr_t)cb);
    put_u16(p->descriptor + 0x0c, (uint16_t)MHI2_IAP_RFCOMM_MTU);
    p->descriptor[0x0e] = 0;
}

static void prepare_sdp(struct mhi2_rfcomm_provider *p)
{
    static const uint8_t service_class[19] = {
        0x35, 0x11, 0x1c, 0x00, 0x00, 0x00, 0x00, 0xde, 0xca, 0xfa,
        0xde, 0xde, 0xca, 0xde, 0xaf, 0xde, 0xca, 0xca, 0xff
    };
    static const uint8_t protocol[14] = {
        0x35, 0x0c, 0x35, 0x03, 0x19, 0x01, 0x00,
        0x35, 0x05, 0x19, 0x00, 0x03, 0x08, 0x00
    };

    memcpy(p->sdp_service_class, service_class, sizeof(service_class));
    memcpy(p->sdp_protocol, protocol, sizeof(protocol));
    memset(p->sdp_attrs, 0, sizeof(p->sdp_attrs));
    memset(p->sdp_record, 0, sizeof(p->sdp_record));

    /* Exact old iAP SDP attributes: 0x0001 len 0x13, 0x0004 len 0x0e. */
    put_u16(p->sdp_attrs + 0x00, 0x0001u);
    put_u16(p->sdp_attrs + 0x02, (uint16_t)sizeof(p->sdp_service_class));
    put_target_ptr(p->sdp_attrs + 0x04, p->sdp_service_class);

    put_u16(p->sdp_attrs + 0x0c, 0x0004u);
    put_u16(p->sdp_attrs + 0x0e, (uint16_t)sizeof(p->sdp_protocol));
    put_target_ptr(p->sdp_attrs + 0x10, p->sdp_protocol);

    /* Generic target record: attr count +0x08, attr pointer +0x0c, handle +0x14. */
    p->sdp_record[0x08] = 2;
    put_target_ptr(p->sdp_record + 0x0c, p->sdp_attrs);
    put_u32(p->sdp_record + 0x14, 0);
}

static void free_tx_list(struct tx_packet *head)
{
    while (head != NULL) {
        struct tx_packet *next = head->next;
        free(head);
        head = next;
    }
}

static void reset_queues(struct mhi2_rfcomm_provider *p)
{
    struct tx_packet *head;

    pthread_mutex_lock(&p->lock);
    p->rx_head = 0;
    p->rx_tail = 0;
    p->rx_count = 0;
    head = p->tx_head;
    p->tx_head = NULL;
    p->tx_tail = NULL;
    p->tx_queued = 0;
    pthread_mutex_unlock(&p->lock);

    free_tx_list(head);
}
