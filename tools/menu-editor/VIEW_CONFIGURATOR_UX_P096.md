# P0.9.6 – OEM Randanschlüsse und Vordergrund-Zahlenraster
Datum: 12.11.2026. Basis: P0.9.5 / Draft-PR #171.

## Problem / Fotovergleich
In der P0.9.5-Safe-Area-OEM-Vorschau sehen die seitlichen Instrument- und Trapezflächen wie isolierte Inseln aus. Vor allem links/rechts bleibt ein unterbrochener Bereich bis zum AID10-Rand. Statuszeilen oben/unten wirken teilweise ebenfalls nicht abgeschlossen. Bei 100% OEM-Deckkraft verschwinden die auf dem Kalibriergrid benötigten Zahlen hinter den undurchsichtigen OEM-Grafiken, insbesondere bei Wide und Center rechts. Die Originalfotos enthalten ein 100×50-Koordinatenraster als Messreferenz; diese Ziffern sind kein nativer UI-Inhalt.

## Änderung
- **Optische Cockpit-Einfassung** im Safe-Area-Editor über `#sa-oem-edge-shell`: eine gemeinsame dünne obere Status-Hinterlegung und eine untere Status-Hinterlegung, ergänzt durch zwei Randanschlüsse pro View. Wide schließt linkes/rechtes Seitenmodul bis x=0/x=1010 und unten y=376 an, Center schließt die äußeren Instrumentumfelder an, Voll die diagonalen unteren Ausschnitte. Diese blau-grauen Übergänge sind ausdrücklich **nur visuell** und werden **nicht** als Belegung oder automatische Safe-Area-Korrektur exportiert.
- **Rasterzahlen über OEM-Grafik**: Wenn `Rasterzahlen anzeigen` eingeschaltet ist, zeichnet `#sa-grid-foreground` kompakte 15px-Koordinaten mit dunkler Außenkontur *vor* den OEM-Gruppen. Das 10/50/100-Raster bleibt als Hintergrund sichtbar. Ohne Overlay bleiben die bisherigen großen 20px-Koordinaten unverändert; bei aktiviertem OEM und deaktiviertem Zahlenraster bleibt die Grafik sauber.
- **Keine erneute Skalierung** der Center-Instrumente, Wide-Trapez-Innenkanten oder Full-Kartenausschnitte: nur optische Randanbindung und bessere Vergleichbarkeit der Rasterzahlen.
- Die bisherige rote/gelbe Maskenlogik bleibt unverändert. Neue Einfassung ist ausdrücklich **keine verbindliche Sperrfläche**. Keine Änderung an Fahrzeug-Runtime, Safe-Area-Profilen, JSON-, CONF- oder SD-Export.
- **Abnahmeversion `mibr-menu-editor-nav-views-p096.html`** mit Versionshinweis P0.9.6; ältere Snapshots unverändert.

## Verifikation
`test-p04.cjs`, `test-p05.cjs`, `build-shared-oem-overlays.cjs --check`, und `test-p09-visual.cjs` mit Chrome Desktop (1440) sowie Mobile-Viewport (390). Neue Screenshots je View mit und ohne Vordergrund-Rasterzahlen. Die perspektivischen Originalfotos sind die visuelle Referenz, eine metrisch exakte OEM-BAP-Pixelabbildung liegt weiterhin nicht vor.
