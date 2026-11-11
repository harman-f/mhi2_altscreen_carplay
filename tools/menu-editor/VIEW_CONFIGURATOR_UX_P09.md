# View-Konfigurator P0.9 – optischer Feinschliff

Basis P0.8, Commit `fbec802`. Bewertung der vier zusätzlichen Screenshots vom 11.11.2026.

## Änderungen

- **Center:** zwei Rundinstrumente und Karte bleiben unverändert in der Grundform. Rechter grüner Abbiegepfeil auf 90 % verkleinert, die weiße Kontur folgt nun derselben Silhouette. Uhrzeit oben 28 → 25, Temperatur auf 16,5, untere Distanz/ETA 16,5 → 14,5; Fahrt-/Tripzeile etwas ruhiger.
- **Wide:** Uhrzeit 29 → 25, Status- und Straßenzeile sowie untere Navigation kleiner; rechter Pfeil 94 %, Distanz 21 → 19. Seitenmodule und zentraler Kartenraum nicht neu gezeichnet.
- **Voll:** `f-mainclip` verwendet für die untere linke/rechte Kartenkante dieselbe Kontur wie `full-lower-corners`. Die ursprünglichen versetzten Kanten fallen zusammen. Oberes und unteres Textbild wie die anderen Views vereinheitlicht.
- **Alle drei:** Seitliche Tick-Zahlen in eigene Spalten gelegt und vertikal exakt auf die markierten Striche bezogen. Die zwei gelben Fußleisten-Chevrons sind lediglich schematische Fixture-Grafik, ihre tatsächliche OEM-Bedeutung ist nicht geklärt; Größe und Gewicht vorsichtig reduziert.
- **Kartenbild `map/app/off`:** App-Standard und Aus haben unterscheidbare, ausdrücklich nur im Editor gezeigte Platzhalter. Kartenhintergrund (Kalibrier-Grid, Neutral, Schematische Karte) lässt sich nur im Kartenmodus auswählen und bleibt ansonsten pro View gespeichert.

## Nicht geändert

Keine zusätzliche reale App-Darstellung oder BAP-Simulation; keine Änderung der OEM-Runtime. Die Projektformate `mibr-project/1`, `mibr.nav-view-profiles/2` und `MIBR_MENU/1`, Safe Areas sowie native Exportpfade bleiben erhalten. Originaler Menü-Editor mit Drag-and-drop, Import/Export und bestehendem Browser-Autosave bleibt funktionsfähig.

## Prüfung

`test-p04.cjs` und `test-p05.cjs` einschließlich neuer Assertions für App/Off/Map je View, Textgrößen, Tick-Ausrichtung, gemeinsame Voll-Maskenkontur und exakte Übereinstimmung zwischen SVG-Dateien und Inline-SVGs. Visuelle Prüfung auf echtem iPhone/Safari bleibt Freigabegate. PR bleibt Draft; keine Änderung an `main`.

## Abschlussaudit der Manöverkarte

Im P0.8/P0.9-Ausgangsstand wurde `carplay.maneuver` mit den Ausprägungen `left`, `right`, `top` nur ein- oder ausgeblendet, die gewählte Position blieb unberücksichtigt. Der P0.9-Renderer verschiebt nun ausschließlich die **Editor-Vorschau** innerhalb des jeweiligen Cockpitbereichs. Die Positionen unterscheiden sich optisch und werden in Chromium bei Desktop- und iPhone-Abmessungen darauf geprüft, dass `top` oberhalb von `left` liegt, `left` links von `right` und die obere Karte den nativen Straßentext nicht überlagert. Das gespeicherte Format bleibt unverändert; kein Nachweis für fahrzeugseitige Positionierbarkeit.

## P0.9.1 – Gemeinsame OEM-Status-Overlays (11.11.2026)

Die echten AID10-Aufnahmen für Center, Wide und Voll zeigen dieselben oberen und unteren OEM-Statuspositionen. Zuvor waren Uhrzeit, Kompass, Temperatur, Entfernung, ETA und Fußleiste für alle drei Ansichten unabhängig mit abweichenden SVG-Werten modelliert. Diese Abweichungen waren im Vergleich zur Fotoreferenz sichtbar.

**Korrektur:** Eine einzige Quellimplementierung `build-shared-oem-overlays.cjs` erzeugt in Center/Wide/Voll dieselbe Geometrie für die Statusgruppen `top-status`, `top-text`, `bottom-info` und `footer`. Die fahrzeugspezifisch angezeigten Beispieldaten (200/300/100 m oben, 1.3/1.4/1.2 km und ETA unten) werden separat übergeben. Front-SVGs und Standalone-HTML werden synchronisiert und mit `--check` in CI auf Drifts überprüft.

**Shared Design-Referenz (SVG 1010 × 376):** Uhrzeit Mitte x=505/y=43 und 24px; W x=399; Temperatur x=640; Navigationsstraße x=505/y=93; untere Restdistanz x=437/y=319; ETA x=550/y=319; Trip x=387/y=353. Das Mock-up übernimmt bewusst nur die optische Nähe zur realen AID10-Anzeige, nicht die Aussage, dass OEM-BAP-Elemente unabhängig positionierbar sind.

Die gemeinsamen Footer-Statusicons sind exemplarische Vektorgrafiken und keine gesicherten Kanal-/Statussignale. Die Ansichten behalten ihre individuellen Tubes, Sidepanels, Karte, Clip-Masken und Safe Areas.

**Abnahme:** `mibr-menu-editor-nav-views-p091.html` ist eine identische, eigenständig nutzbare Kopie der kanonischen HTML-Datei mit sichtbarem P0.9.1-Versionshinweis. Vor Merge wird sie auf Desktop und Mobile Safari visuell geprüft. `main` und alle Runtime-Artefakte bleiben unverändert.
