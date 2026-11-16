# MIB Atlas — comparison-first ordering and emulator host OS display

**UI review date:** 2026-11-16. **Scope:** documentation/site UX only. No new evidence, capability scores, firmware modifications or emulator compatibility assertions.

## CarPlay & Android Auto tab hierarchy

The user's agreed ordering is:
1. **Main 56-entry × 22-attribute comparison matrix first** at the top of the CarPlay & Android Auto tab.
2. **MIB1 High/MHIG context** under the comparison, explicitly author-reported without a public repository or inferred stream-111 success; not falsely counted as a 57th scored profile.
3. **Repository technical catalog** of the same 56 entries.
4. **OEM/factory HUD integration** last, still in the **same CarPlay & Android Auto tab**. Distinct from the aftermarket HUD section in Miscellaneous.

This is a DOM rearrangement of the existing four sections without moving cross-tab information or changing the search/sort/navigation implementation.

## Emulator Host OS evidence

The existing emulator matrix retains its **14** source leads and detailed original host remarks. Each row now displays separate small labels (Windows, Linux, macOS or unverified), and a **Host OS** filter is added to the toolbar with exact multi-host matching.

- Iscle: Linux and macOS (Apple Silicon reported tested), plus Windows **via WSL only**, not native Windows.
- Карась: uses iscle-derived Linux/macOS/Windows-WSL arrangements as community-reported, **not independently demonstrated native support**.
- omonob: Windows with WSL as reported.
- OneB1t: Windows for **ODIS diagnostics**; the related QEMU emulator's host remains **unknown**. Both labels are shown, with a distinction in the text.
- Remaining ten research leads: host OS not reported/confirmed; **unknown**, not inferred from Intel CPU, QEMU name, screenshot or the vehicle QNX guest.

The Host OS filter offers Linux, macOS, Windows (WSL), Windows (ODIS/tools only), and not stated/unverified. It uses an exact token comparison so multi-host entries appear correctly in each supported OS grouping while the other nine source-table filters preserve their previous equality semantics. Native Windows headunit emulation is **not claimed**.

## Release invariants

56 curated rows and cards, 22 original attributes, nine tab panels, nine searchable source matrices, 14 emulator rows, OEM HUD's five source entries, 38 lineage relationships and four diagrams, V3.0 Wireless release, feedback issue #187, anchors and local dark/light mode all remain unchanged.
