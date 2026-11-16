# Cluster geometry from calibration photos (Skoda MU1440)

Source: three photos (2026-11-15 23:21) of the cockpit showing the calibration clip (`modules/navigation/source/tools/make_calib_clip.py`, stream 111, 1010x376, every 100x50 cell labels its own top left corner).

- `rectify.py`: control points (stream grid point -> photo pixel) and homography per view; writes `rect_<view>.png` in stream coordinates (margin -160..1170 x -70..446, 2 px per stream px). Residual: full 2 photo px, wide/center exact (4 points).
- The rectified photos (cropped to 0..1010 x 0..376, 1:1 with stream pixels) are embedded in the HTML configurator `tools/menu-editor/`; this repository keeps no separate image files (publication audit).
- `cluster-geometry.json`: measured OEM chrome per view in stream pixels (accuracy about 3 px): top bar (translucent, clock tab down to y 48 for x 455..555), bottom bar y >= 334 (opaque), Voll bottom corners, Wide side panels (straight edges 162->231 and 847->777), Center dials (circles r 186 at x 182 / 822, y 186, fitted on the whole ring), plus the largest free rectangle per view.

Finding: the display shows the whole 1010x376 stream in every view; views only differ by the chrome drawn on top. The Skoda platform defaults (`skoda-mu1440.conf`) fit the free area in all three views; only the compiled fallbacks in `mibr_durable_switch.c` (used without platform defaults) overlap the Voll corners and the Wide side panels.
