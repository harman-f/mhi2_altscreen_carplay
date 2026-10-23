# Scroll indicator artwork provenance

These four first-party project assets are uniform RGBA rectangles created for the menu's owned scroll indicator. No OEM or third-party image pixels, skin records, logos, or backgrounds are included. The artwork uses simple fill colors; its color choices were informed by visual observations of scrollbar contrast on the target UI.

Each file is 8 × 32 pixels, RGBA, with one uniform color:

| File | RGBA | SHA-256 |
| --- | --- | --- |
| `mibr_scroll_thumb.png` | `(120, 250, 174, 255)` | `3f883283a5af35a789ce76c3f414a3b030250bbf5a3d8b76421120d80e39cbee` |
| `mibr_scroll_thumb_v2.png` | `(200, 245, 10, 255)` | `6d34382b9744264121871e8b092f1ab025619ee028b1f5ca30ffc030fe62f8f4` |
| `mibr_scroll_track.png` | `(120, 250, 174, 70)` | `f33c96eada17e1573a81032c5301dc9e0c9e5320ad37be3bc2dd97386f6b27d4` |
| `mibr_scroll_track_v2.png` | `(255, 250, 240, 235)` | `8b2f0d77dd89432e3faa043d0b0e1566d939366d42a6d3b2f8964645cd13f93b` |

The Java module refers to these as separate external PNGs under the target's MIBR icon directory; the JAR build does not bundle or install them. They are licensed as project-authored material under this repository's GPL-3.0-or-later license.
