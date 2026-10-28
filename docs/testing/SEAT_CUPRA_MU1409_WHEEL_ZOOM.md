# SEAT/CUPRA MU1409 right-wheel zoom

Scope: CUPRA Ateca, MHI2_ER_SEG11_P4708_1 / MU1409. Passive target observations
identified right-roller rotation as keyboard 4, encoder 40, signed detent +/-1,
extra 0, effective-validity 1, correlated with the native scale-associated record
within 40 ms. The short press separately appeared as KBD 4 / KEY 40 with
press/release states; do not treat that key event as rotation.

The existing public receive-only DebugSPI parser already recognizes the measured
tuple and requires a matching Tag56 record. This is empirical correlation,
not a decoded guarantee of OEM method identity or exclusive VC focus. No raw
capture or OEM Java is published here.

The target-adapted automatic bridge reported completed commands and the operator
visibly confirmed wheel zoom in Apple Maps and Google Maps. Waze did not visibly
respond. Phone command success alone does not demonstrate visible zoom.

The public source adds explicit opt-in `ALTSCREEN111_SEAT_WHEEL_ZOOM=1` for
that correlated observer. Without it the existing manual-arm behavior remains.
It requires the current authenticated/desired projection, matching video session,
a DIRECT marker and a healthy zoom session; dispatch still requires the existing
ready/shown/configured/primed predicates. Per-consumer/session/codec epochs clear
queued context, and timestamp freshness rejects pre-binding or stale detents.
A fresh correlated event is needed to establish each zoom intent. A failed
zoom command inhibits automatic eligibility until a new session resets policy.

This is a parallel observer. It does not suppress OEM navigation zoom, intercept
Back/volume/presses, change Java/DSI configuration, add a second AirPlay session,
or create a second video writer. The DIRECT marker is one runtime predicate,
not independent proof of actual visible ownership. No automatic mode is enabled
globally or by installation here; runtime selection must be explicitly qualified
for the fitted target and native listener availability.

The public-source integration is host/compile checked and is not the exact
older receiver used for the target confirmation. Qualification still requires
parked tests of both directions, native menu/Back/volume, route changes, DIRECT
to STOCK, consumer recovery and phone reconnect. Manual arm takes precedence;
do not use simultaneous manual and automatic test flows to establish acceptance.

Regression tests cover binding freshness, consumer/session change, revocation
and timestamp wrap, alongside existing real-parser tuple/correlation negatives
and the bounded zoom policy tests. Keep this steering-wheel semantic zoom
separate from the phone logical `zoomFactor` scaling setting.
