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
