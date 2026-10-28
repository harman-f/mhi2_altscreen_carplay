# SEAT/CUPRA MU1409: auxiliary scaling and queue recovery

Date: 25 October 2026. Target observation: CUPRA Ateca, MHI2_ER_SEG11_P4708_1 /
MU1409, fitted Continental 790-family cockpit. This is one target observation,
not qualification of every SEAT/CUPRA, cluster variant or iOS version.

## Auxiliary zoom percentage

A target-adapted receiver advertising numeric lowercase `zoomFactor=70` only
on the cloned Type-111 display produced a visibly improved map size, reported
by the vehicle operator as displaying correctly. The main display was unchanged.
The outer advertisement and reported VideoConfig remained 1010 x 376; advertised
physical dimensions stayed 200 x 74. This was original H.264 forwarding and TS
remuxing, with no decode/resize/encode stage or newly added black padding.

The phone software version was not recorded. Exact on-cluster pixel scaling
and a universal 70-percent shrink were not measured. SafeArea remains a separate
content-placement mechanism; this observation does not resolve reduced-layout
ETA/direction visibility or prove a SEAT-versus-Skoda hardware cause.

The public receiver provides opt-in `ALTSCREEN111_ZOOM_FACTOR=70` in the
receiver process environment. It emits numeric `zoomFactor` only on the
auxiliary clone. Unset, empty or zero leaves the existing advertisement intact;
there is no default change for Skoda, VW or SEAT. Other integer values from 70
through 150 are accepted for controlled research but are not vehicle-qualified
by this report. Malformed/out-of-range values and allocation failure use the
existing stock-info fallback. No menu setting or second settings store is added.

Set the environment before receiver startup and use a fresh CarPlay session.
This is a source integration point, not an instruction to edit production boot
files or an integrated SEAT installer. Restoring the previous receiver removes
the trial property; an existing connection may retain negotiated properties
until a new session. Check main-screen CarPlay separately.

## Queue overflow and OEM-map switching

After scaling was enabled on the adapted receiver, startup intermittently
alternated between Waze and OEM navigation before settling. The logs identify
the switching mechanism, but do not establish that the zoom property itself
caused overflow.

The older adapted core had a 16-AU / 4-MiB bounded queue. A full queue returned
`ALT111_RESTART_CONSUMER` (2), detached the consumer and closed its TCP stream.
The remux bridge ended cleanly, and the exclusive-owner supervisor returned to
STOCK before retrying. Bridge summaries showed no MOST write errors, timeouts
or pacing underflows in the inspected failed runs.

A narrow backport of the upstream soft-overflow principle preserved the consumer:
finish an AU whose payload has already started, discard only fully unsent AUs,
discard dependent pictures until a fresh complete IDR is available, and prefix
that recovery IDR with current SPS/PPS. The same serialized control worker asks
for a keyframe. Do not retain stale dependent pictures or truncate a partially
sent Annex-B AU. Real socket failures, changed codec, invalid AUs and teardown
retain their failure/fallback semantics.

Current public upstream already implements the fuller soft recovery, including
partial M1AU-header protection. Do not replace it with the older raw-Annex-B
backport or copy that target backport across framed transports. This contribution
adds byte-budget regression coverage alongside its existing count/partial-record
tests; it does not duplicate the recovery implementation or reduce queue limits.

## Observed acceptance and limits

Operator-supplied target output showed:
- Initial priming at 47.398 s, consumer generation 3.
- Overflow at 51.310 s: 16 queued AUs, 128879 queued bytes.
- Keyframe request at 51.316 s with the consumer retained.
- Re-priming at 51.457 s, still consumer generation 3.

This is about 147 ms from overflow to re-priming in the receiver log, not a
measured end-to-end display latency. The operator then reported that it appeared
to work. This supports one visible target recovery with improved scaling.
Repeated cold starts, unplug/reconnect, long drives and failure-path restoration
were not independently demonstrated after this combined change.

Host tests cover strict numeric metadata, unchanged primary/geometry, setter
failure, AU-count and byte-budget overload, partial payload/header preservation
and fresh-IDR resumption. Host and public-source build checks do not establish
that this exact newer public integration was executed on the SEAT vehicle.
The public receiver has newer transport/control features than the narrow tested
target receiver; this is not a universal ready-to-install SEAT binary.

Related: [SEAT/CUPRA collaboration](../porting/SEAT_CUPRA_MU1409_COLLABORATION.md).
