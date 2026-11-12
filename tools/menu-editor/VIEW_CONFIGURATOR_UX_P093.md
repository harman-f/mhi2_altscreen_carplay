# P0.9.3 – Safe Area OEM Overlay Assist
Datum: 12.11.2026. Basis P0.9.2 / Draft-PR #168.

## Umsetzung
- Optionaler Schalter **OEM-Overlays anzeigen**, Standard AUS.
- Anzeigearten `Vorschau + Maske`, `Nur OEM-Vorschau`, `Nur Blockierungsmaske`; Deckkraft 20–80%.
- Die OEM-Vorschau **klont die tatsächlichen SVG-Ebenen** der Center/Wide/Voll-Ansichten aus dem laufenden View-Konfigurator (einschließlich gemeinsamer Top-/Bottom-Gruppen, Gurt- und Spur-Symbole). Keine neue Fahrzeug- oder Exportfunktion.
- Die Blockierungsmaske zeigt vier gemeinsame, anhand der realen Grid-Fotos angenäherte Statuszonen: (374,19,288,47), (386,70,238,35), (397,297,220,35), (368,332,304,38) im 1010×376-Raster.
- Zusätzlich Center: exakte Kreise aus beiden originalen Dial-SVG-Gruppen; Wide: die ersten zwei echten Seitenteil-Pfade; Voll: die ersten zwei Pfade der unteren Ausschnitte. Damit bleiben Masken an die bestehende View-Geometrie gekoppelt.
- Aktive View-Auswahl ist bereits seit P0.8 bidirektional zwischen Safe Area und View-Konfigurator synchronisiert. Kein zweiter, abweichender Sync-Zustand.
- Separate Browserpräferenz `mibr-safe-oem-assist/1`; **kein Feld in** `mibr-project/1`, `mibr.nav-view-profiles/2`, Safe-Area-Kanten, `MIBR_MENU/1` oder SD-Export.
- Alte P0.9.2-Abnahmedatei bleibt unverändert; neue selbstständige `mibr-menu-editor-nav-views-p093.html`.

## Kalibriergrenze
Die Fotos zeigen ein aufgespanntes Fahrzeug-Grid in perspektivischer Aufnahmeposition, keine orthogonale Pixelmessung. Oben/unten sind deshalb großzügige Annäherungen der belegten Bereiche, keine pixelgenauen BAP-Clipgrenzen. Rote/geometrische Flächen sind konservative Hinweise auf nicht oder nur teilweise nutzbare Kartengebiete; der orangefarbene Overlay-Block ist kein automatisch anwendbares Safe-Area-Profil.

## Regression
`test-p04.cjs`, `test-p05.cjs`, `build-shared-oem-overlays.cjs --check` und Desktop-/iPhone-Chromium `test-p09-visual.cjs` einschließlich Masken und 12 zusätzlichen Bildern. Echte Safari-Abnahme vor Merge. `main` und Fahrzeug-Runtime bleiben unverändert.
