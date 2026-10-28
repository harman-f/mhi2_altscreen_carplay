# SEAT/CUPRA MU1409 ViewArea calibration

Target: CUPRA Ateca, MHI2_ER_SEG11_P4708_1 / MU1409, fitted Continental 790-family
cockpit. Values are calibration observations from the adapted receiver, not
panel resolution measurements or a universally qualified SEAT profile.

| Index | Menu label | Outer ViewArea | SafeArea | Origin |
|---|---|---|---|---|
| 0 | Wide | 1010 x 376 | 708 x 244 | 151,56 |
| 1 | Full | 1010 x 376 | 482 x 244 | 264,56 |
| 2 | Center | 1010 x 376 | 256 x 244 | 377,56 |

Wide preserved visible directions and ETA in Waze. Switching Full and Center
eventually changed the view, but ETA/directions disappeared or were obscured by
OEM gauge artwork; returning to Wide restored them. These reduced rectangles
are useful reproducible candidates, not accepted final framing. App behavior
and the physical OEM dial layout are independent observations.

The earlier 708 x 264 SafeArea was shortened to height 244 while preserving
origin 151,56 to move lower information farther inside the visible map region.
SafeArea describes where the phone should place active content; it is not
pixel padding, resampling or a remedy for every apparent zoom effect.

The explicit pure-C helper `alt111_profile_seat_mu1409_views` supplies the table
to a target adapter without changing global defaults. It accepts only an
existing valid 1010 x 376 Type-111 profile and commits atomically after bounds
validation. Transport identity, advertised physical size, features and frame
rate remain unchanged. Callers must reconcile the candidate with their existing
canonical settings authority; do not run this as a competing settings store or
silently override later user geometry. No production loader/menu integration or
SEAT installer is introduced by this calibration helper.

View switching also required adjacentViewAreas in updateViewArea, already
present in public upstream. A zero callback status or empty response dictionary
alone did not establish a visible layout change. Keep stored/requested/phone
acknowledged/visible states distinct.

Host regression links the actual profile helper and validator; it checks all
three rectangles, unchanged identity/transport fields, wrong-canvas rejection,
invalid-profile rejection without partial mutation and unchanged default profile.
Vehicle acceptance still needs each navigation provider, information placement,
physical layouts and restart/reconnect checks independently.

No scaling zoomFactor change, menu patch or wheel mapping is included here.
