# P0.9.2 – Navigationspfeil und OEM-Footer-Symbole

Stand 12. November 2026. Basis P0.9.1 (Draft-PR #167).

## Korrekturen

- **Wide-Abbiegepfeil:** Die alte weiße Pfeilkontur verwendete eine von der grünen Form abweichende SVG-Kurve. Nun zeichnet ein einziger geschlossener Pfad mit `fill=url(#w-turn)` und weißem `stroke` beide gleichzeitig; kein Offset zwischen Kontur und Grünfläche.
- **Rotes Symbol:** Die generische Strichfigur wurde durch einen bewusst erkennbaren, sitzenden Insassen mit diagonaler Schulter-/Gurtlinie, Sitzkontur und Gurtschloss ersetzt. Das Symbol heißt `<view>-seatbelt-warning`.
- **Gelbes Symbol:** Die zuvor separaten Dach-/Chevron-Dreiecke werden durch zwei perspektivisch verlaufende Straßenränder **plus gestrichelte Mittellinie** ersetzt (`<view>-yellow-road-guidance`).
- Die beiden Footer-Symbole werden weiterhin **aus einer gemeinsamen Quelle** (`build-shared-oem-overlays.cjs`) für Center, Wide und Voll generiert. Alle drei haben gleiche Abmessungen und Positionen.
- **P0.9.2 Abnahme:** `mibr-menu-editor-nav-views-p092.html`, separat von der unveränderten P0.9.1 Abnahme-Snapshot-Datei.

## Abgrenzung und Tests

Nur Editor-Visualisierung, keine QNX-/BAP-Laufzeitänderung. OEM-Fotos dienen als optische Referenz, nicht als Funktionsbeleg. Bestehende Projekt-, View-, Safe-Area- und SD-Menüformate bleiben unverändert. Tests prüfen SVG-Quelle/Inline-Identität, drei Shared-Symbole, Single-Path-Wide-Pfeil, Desktop-/Mobile-Chromium, bisherigen Menüeditor und Exporte. PR bleibt Draft bis zur manuellen iPhone-Safari-Abnahme.
