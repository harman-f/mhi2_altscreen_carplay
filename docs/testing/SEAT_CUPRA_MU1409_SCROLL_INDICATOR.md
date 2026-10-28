# SEAT/CUPRA MU1409 owned scroll indicator

The first adapted menu showed a project-owned green indicator. Later native
scrollbar lookup found zero native Scrollbar objects among 84 visited widgets.
Static firmware widget IDs therefore did not establish the live owned-page tree.

This change retains upstream native-widget discovery and its existing fallback.
The fallback gains duplicate protection and full detach cleanup on menu leave,
so re-entry does not accumulate images or adjustment listeners. The actual
indicator is exercised with host models for scrolling, clamping, resize,
fit-to-page hiding, duplicate attach, repeated detach and re-entry.

The optional Java property `mibr.hmi.scrollbar.theme=seat_red` selects
`mibr_scroll_thumb_seat_red.png` in the existing MibrIconState icon directory.
Without that explicit property, the existing artwork remains selected.
Generate the first-party 8 x 32 RGBA (220,35,55,255) rectangle on the workstation:
`python3 tools/generate_seat_scroll_thumb.py --out /chosen/output/mibr_scroll_thumb_seat_red.png`.
Deliver it through the target adapter’s existing owned-icon installation process.
The pale existing track is reused. No OEM pixels, widget IDs or menu positions
are copied into the contribution; no new input/drag controller is added.

The private target adaptation compiled against locally held SEAT APIs.
The red re-entry integration was prepared for vehicle testing; no confirmed
red-indicator vehicle acceptance has been supplied. Host models are not proof
of Java/J9 linkage or visual appearance on another skin. Exact target compilation,
appearance, Back/focus and re-entry remain acceptance checkpoints.

Run `python3 tests/test_owned_scroll_indicator.py` with JAVAC/JAVA pointing to
a workstation JDK. This change does not alter video, SafeArea, scaling or wheel zoom.
