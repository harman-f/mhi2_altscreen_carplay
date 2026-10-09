CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Werror -std=c99

SRC = src/wcp_probe.c
TEST = tests/test_wcp_probe.c
OBSERVER_SRC = endpoint-observer/mhi2_iap_endpoint_observer.c
A3_CREDENTIALS_SRC = a3-credentials/mhi2_wcp_a3_credentials.c
RUNTIME_IAP2_CONFIG_SRC = runtime-iap2-config/mhi2_wcp_iap2_runtime_config.c
RUNTIME_IAP2_CONFIG_TEST = tests/test_iap2_runtime_config.sh
SERVICEGRAPH_SRC = servicegraph-adapter/mhi2_iap_servicegraph_adapter.c
SERVICEGRAPH_TEST = tests/test_servicegraph_adapter.c
RFCOMM_PROVIDER_SRC = rfcomm-provider/mhi2_rfcomm_provider.c
RFCOMM_PROVIDER_TEST = tests/test_rfcomm_provider.c
B0_DISCOVERY_SRC = b0-discovery/mhi2_wcp_b0_discovery.c
OWNER_HOOK_SRC = btstack-owner-hook/mhi2_btstack_owner_hook.c

.PHONY: all test observer a3-credentials runtime-iap2-config servicegraph-adapter rfcomm-provider owner-hook b0-discovery clean qnx

all: test

build:
	mkdir -p build

build/test_wcp_probe: build $(SRC) $(TEST) src/wcp_probe.h
	$(CC) $(CFLAGS) -Isrc $(SRC) $(TEST) -o $@

build/mhi2-iap-endpoint-observer: build $(OBSERVER_SRC)
	$(CC) $(CFLAGS) -D_DEFAULT_SOURCE $(OBSERVER_SRC) -o $@

build/mhi2-wcp-a3-credentials: build $(A3_CREDENTIALS_SRC)
	$(CC) $(CFLAGS) -D_DEFAULT_SOURCE $(A3_CREDENTIALS_SRC) -o $@

build/mhi2-wcp-iap2-runtime-config: build $(RUNTIME_IAP2_CONFIG_SRC)
	$(CC) $(CFLAGS) -D_DEFAULT_SOURCE $(RUNTIME_IAP2_CONFIG_SRC) -o $@

build/test_servicegraph_adapter: build $(SERVICEGRAPH_SRC) $(SERVICEGRAPH_TEST) servicegraph-adapter/mhi2_iap_servicegraph_adapter.h
	$(CC) $(CFLAGS) -Iservicegraph-adapter $(SERVICEGRAPH_SRC) $(SERVICEGRAPH_TEST) -o $@

build/test_rfcomm_provider: build $(RFCOMM_PROVIDER_SRC) $(RFCOMM_PROVIDER_TEST) rfcomm-provider/mhi2_rfcomm_provider.h
	$(CC) $(CFLAGS) -pthread -Irfcomm-provider $(RFCOMM_PROVIDER_SRC) $(RFCOMM_PROVIDER_TEST) -o $@

build/libmhi2-iap-owner-hook.so: build $(OWNER_HOOK_SRC) $(SERVICEGRAPH_SRC) $(RFCOMM_PROVIDER_SRC) servicegraph-adapter/mhi2_iap_servicegraph_adapter.h rfcomm-provider/mhi2_rfcomm_provider.h
	$(CC) $(CFLAGS) -fPIC -shared -pthread -Iservicegraph-adapter -Irfcomm-provider $(OWNER_HOOK_SRC) $(SERVICEGRAPH_SRC) $(RFCOMM_PROVIDER_SRC) -ldl -o $@

build/mhi2-wcp-b0-discovery: build $(B0_DISCOVERY_SRC)
	$(CC) $(CFLAGS) -D_DEFAULT_SOURCE $(B0_DISCOVERY_SRC) -ldl -o $@

build/test_b0_state: build tests/test_b0_state.c $(B0_DISCOVERY_SRC)
	$(CC) $(CFLAGS) -D_DEFAULT_SOURCE tests/test_b0_state.c -ldl -o $@

build/qnx_ep_write.inc: build rfcomm-provider/mhi2_rfcomm_provider_qnx.inc
	awk '/^static int ep_io_write\(/ {copy=1} copy {print} copy && /^}/ {exit}' rfcomm-provider/mhi2_rfcomm_provider_qnx.inc > $@

build/test_qnx_write_length: build tests/test_qnx_write_length.c build/qnx_ep_write.inc
	$(CC) $(CFLAGS) tests/test_qnx_write_length.c -o $@

build/qnx_notify.inc: build rfcomm-provider/mhi2_rfcomm_provider_qnx.inc
	awk '/^#else/ {exit} /^static (int|void) (ep_io_notify|ep_io_close_dup|endpoint_rx_ready)\(/ {copy=1} copy {print} copy && /^}/ {copy=0}' rfcomm-provider/mhi2_rfcomm_provider_qnx.inc > $@

build/test_qnx_notify: build tests/test_qnx_notify.c build/qnx_notify.inc
	$(CC) $(CFLAGS) -pthread tests/test_qnx_notify.c -o $@

build/qnx_dispatch.inc: build rfcomm-provider/mhi2_rfcomm_provider_qnx.inc
	awk '/^#else/ {exit} /^static (int endpoint_publish_ready|void endpoint_remove_ready|void \*endpoint_thread_main)\(/ {copy=1} copy {print} copy && /^}/ {copy=0}' rfcomm-provider/mhi2_rfcomm_provider_qnx.inc > $@

build/test_qnx_dispatch: build tests/test_qnx_dispatch.c build/qnx_dispatch.inc
	$(CC) $(CFLAGS) -pthread tests/test_qnx_dispatch.c -o $@

test: build/test_wcp_probe build/test_servicegraph_adapter build/test_rfcomm_provider build/mhi2-iap-endpoint-observer build/mhi2-wcp-a3-credentials build/mhi2-wcp-iap2-runtime-config build/mhi2-wcp-b0-discovery build/test_b0_state build/test_qnx_write_length build/test_qnx_notify build/test_qnx_dispatch
	./build/test_wcp_probe
	./build/test_servicegraph_adapter
	./build/test_rfcomm_provider
	./build/test_b0_state build/test-b0.state
	./build/test_qnx_write_length
	./build/test_qnx_notify
	./build/test_qnx_dispatch
	./build/mhi2-wcp-a3-credentials --help >/dev/null
	./build/mhi2-wcp-iap2-runtime-config --help >/dev/null
	./$(RUNTIME_IAP2_CONFIG_TEST) ./build/mhi2-wcp-iap2-runtime-config
	sh -n a3-network-preflight/mhi2_wcp_a3_network_preflight.sh
	sh -n runtime-launcher/mhi2_wcp_mm_ipod_launch.sh
	sh -n runtime-launcher/mhi2_wcp_mm_ipod_stop.sh
	sh -n btstack-preload/mhi2_wcp_control_common.sh
	python3 tests/test_control_shell.py
	./runtime-launcher/mhi2_wcp_mm_ipod_launch.sh --help >/dev/null
	sh -n btstack-preload/mhi2_wcp_btstack_wrapper.sh
	sh -n btstack-preload/mhi2_wcp_btstack_overlay_up.sh
	sh -n btstack-preload/mhi2_wcp_btstack_overlay_down.sh
	sh -n btstack-preload/mhi2_wcp_btstack_cycle.sh
	sh tests/test_btstack_cycle_signal.sh
	./btstack-preload/mhi2_wcp_btstack_overlay_up.sh --help >/dev/null 2>&1 || test $? -eq 2
	./btstack-preload/mhi2_wcp_btstack_overlay_down.sh --help >/dev/null
	./build/mhi2-wcp-b0-discovery --help >/dev/null

observer: build/mhi2-iap-endpoint-observer

a3-credentials: build/mhi2-wcp-a3-credentials

runtime-iap2-config: build/mhi2-wcp-iap2-runtime-config

servicegraph-adapter: build/test_servicegraph_adapter

rfcomm-provider: build/test_rfcomm_provider

owner-hook: build/libmhi2-iap-owner-hook.so

b0-discovery: build/mhi2-wcp-b0-discovery

qnx: build
	arm-unknown-nto-qnx6.5.0eabi-gcc $(CFLAGS) -D_QNX_SOURCE -Isrc -c $(SRC) -o build/wcp_probe.qnx.o
	arm-unknown-nto-qnx6.5.0eabi-gcc $(CFLAGS) -D_QNX_SOURCE $(OBSERVER_SRC) -o build/mhi2-iap-endpoint-observer.qnx
	arm-unknown-nto-qnx6.5.0eabi-gcc $(CFLAGS) -D_QNX_SOURCE $(RUNTIME_IAP2_CONFIG_SRC) -o build/mhi2-wcp-iap2-runtime-config.qnx
	arm-unknown-nto-qnx6.5.0eabi-gcc $(CFLAGS) -D_QNX_SOURCE $(B0_DISCOVERY_SRC) -o build/mhi2-wcp-b0-discovery.qnx

clean:
	rm -rf build
