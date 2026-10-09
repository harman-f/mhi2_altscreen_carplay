# 06. QNX ownership and recovery — wireless transport scope only

The early native wireless bootstrap prototype uses QNX Resource Manager callbacks, a native Bluetooth process/service owner and an optional volatile startup wrapper. These observations apply to iAP/RFCOMM ownership, not to any cockpit/video transport.

## Key engineering boundaries

- QNX Resource Manager IO handlers, `select`/`io_notify`, read/write backpressure and dispatch/thread lifetime must agree on endpoint readiness.
- RX/TX native callback quiescence, generation invalidation and per-connection bounded queues are required on close and fast reconnect.
- Teardown must avoid calling into an unloaded native servicegraph object, closing the wrong borrowed descriptor, double releasing a completion-backed buffer or leaving a stale process lock.
- The earlier source candidate was independently **BLOCKED even though CI was green** due to control/teardown concerns. A later corrected exact build received limited conditional review for a narrowly managed diagnostic run only; it is not a production deployment or proven first connection.
- Temporary state, process identity checks and stock restoration are target/build-specific. None of the archived historical launcher scripts should be distributed as a generally safe vehicle-install recipe.

No build should be started on a real head unit without matching the target firmware components, safe management access and a known rollback plan. This research package contains no vehicle-side installer, preload binary, shell patcher or operational activation instructions.

Publicly documented QNX concepts: [QNX resource manager overview](https://qnx.com/developers/docs/6.4.0/neutrino/prog/resmgr.html) and [Resource Manager IO function table](https://qdn.qnx.com/developers/docs/7.1/com.qnx.doc.neutrino.lib_ref/topic/r/resmgr_io_funcs_t.html). These general manuals do not validate the MU1440-specific internal servicegraph ABI.
