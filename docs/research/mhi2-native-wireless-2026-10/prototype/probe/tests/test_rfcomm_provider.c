#include "../rfcomm-provider/mhi2_rfcomm_provider.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct mock_stack {
    int register_calls;
    int publish_calls;
    int accept_calls;
    int last_accept;
    int credit_calls;
    int send_calls;
    int disconnect_calls;
    int deregister_calls;
    int remove_calls;
    int emit_close;
    struct mhi2_rfcomm_provider *provider;
};

static int mock_register(void *opaque, void *descriptor,
                         uint8_t *channel, unsigned credits)
{
    struct mock_stack *m = (struct mock_stack *)opaque;
    (void)descriptor;
    assert(credits == MHI2_IAP_RFCOMM_INITIAL_CREDITS);
    m->register_calls++;
    *channel = 23;
    return 0;
}

static int mock_publish(void *opaque, void *record)
{
    struct mock_stack *m = (struct mock_stack *)opaque;
    (void)record;
    m->publish_calls++;
    return 0;
}

static int mock_accept(void *opaque, void *descriptor, int accept)
{
    struct mock_stack *m = (struct mock_stack *)opaque;
    (void)descriptor;
    m->accept_calls++;
    m->last_accept = accept;
    return 2;
}

static int mock_credit(void *opaque, void *descriptor, unsigned credits)
{
    struct mock_stack *m = (struct mock_stack *)opaque;
    (void)descriptor;
    m->credit_calls += (int)credits;
    return 0;
}

static unsigned mock_capacity(void *opaque, void *descriptor)
{
    (void)opaque;
    (void)descriptor;
    return MHI2_IAP_RFCOMM_MTU;
}

static int mock_send(void *opaque, void *descriptor, void *packet)
{
    struct mock_stack *m = (struct mock_stack *)opaque;
    (void)descriptor;
    (void)packet;
    m->send_calls++;
    return 1;
}

static int mock_disconnect(void *opaque, void *descriptor)
{
    struct mock_stack *m = (struct mock_stack *)opaque;
    (void)descriptor;
    m->disconnect_calls++;
    if (m->emit_close) {
        uint8_t closed[16] = {4};
        mhi2_rfcomm_provider_handle_event(m->provider, closed);
    }
    return 2;
}

static int mock_deregister(void *opaque, void *descriptor, uint8_t *channel)
{
    struct mock_stack *m = (struct mock_stack *)opaque;
    (void)descriptor;
    (void)channel;
    m->deregister_calls++;
    return 0;
}

static int mock_remove(void *opaque, void *record)
{
    struct mock_stack *m = (struct mock_stack *)opaque;
    (void)record;
    m->remove_calls++;
    return 0;
}

int main(void)
{
    struct mock_stack mock;
    struct mhi2_rfcomm_stack_ops ops;
    struct mhi2_rfcomm_provider *provider;
    uint8_t inbound[16];

    memset(&mock, 0, sizeof(mock));
    memset(&ops, 0, sizeof(ops));
    ops.register_server = mock_register;
    ops.publish_sdp = mock_publish;
    ops.accept = mock_accept;
    ops.add_credit = mock_credit;
    ops.tx_capacity = mock_capacity;
    ops.send = mock_send;
    ops.disconnect = mock_disconnect;
    ops.deregister_server = mock_deregister;
    ops.remove_sdp = mock_remove;

    provider = mhi2_rfcomm_provider_create_test(&ops, &mock);
    assert(provider != NULL);
    mock.provider = provider;
    mock.emit_close = 1;
    assert(strcmp(mhi2_rfcomm_provider_endpoint_path(provider),
                  MHI2_IAP_ENDPOINT_DEFAULT) == 0);

    assert(mhi2_rfcomm_provider_start(provider) == 0);
    assert(mhi2_rfcomm_provider_is_started(provider));
    assert(mhi2_rfcomm_provider_channel(provider) == 23);
    assert(mock.register_calls == 1);
    assert(mock.publish_calls == 1);

    assert(mhi2_rfcomm_provider_start(provider) == 0);
    assert(mock.register_calls == 1);

    memset(inbound, 0, sizeof(inbound));
    inbound[0] = 1;
    mhi2_rfcomm_provider_handle_event(provider, inbound);
    assert(mock.accept_calls == 1);
    assert(mock.last_accept == 1);

    assert(mhi2_rfcomm_provider_stop(provider) == 0);
    assert(!mhi2_rfcomm_provider_is_started(provider));
    assert(mock.remove_calls == 1);
    assert(mock.deregister_calls == 1);
    assert(mock.disconnect_calls == 1);

    mhi2_rfcomm_provider_handle_event(provider, inbound);
    assert(mock.accept_calls == 1); /* No SDK call after deregistration. */

    mhi2_rfcomm_provider_destroy(provider);
    puts("rfcomm provider tests: ok");
    return 0;
}
