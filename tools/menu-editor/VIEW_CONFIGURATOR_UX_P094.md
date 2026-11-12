# P0.9.4 – Safe Area visual clarity (12.11.2026)

Basis: P0.9.3 und die drei neuen Safe-Area-Abnahmescreenshots (Voll, Wide, Center).

Die OEM-Gruppen werden in der richtigen View angezeigt. Die in der Referenz sichtbaren Gitter-Zahlen scheinen bei 80 % Deckkraft jedoch durch die Instrumente, Statusgruppen und Safe-Area-Markierungen hindurch. Der großflächige gelbe Hintergrund der bisher aktiven Safe Area ist zudem nicht klar von gelben OEM-Sperrzonen zu unterscheiden.

## Änderungen

- Die 100×50-Koordinatenbeschriftungen im Raster sind zu einer separaten SVG-Gruppe `#sa-grid-numbers` zusammengefasst. Bei aktivierter OEM-Vorschau sind sie standardmäßig verborgen, können aber über **Rasterzahlen anzeigen** wieder zugeschaltet werden. Ohne OEM-Overlays bleibt das Grid wie bisher vollständig sichtbar.
- 10/50/100-Rasterlinien bleiben in allen Modi unverändert, die Koordinaten können für Fotoabgleich weiterhin sichtbar geschaltet werden.
- Die konfigurierte Safe Area wird bei aktivem OEM-Assist als dünner türkiser Umriss mit nur 3,5 % Füllung markiert. Damit ist sie von gelben Statusbändern und roten Instrumenten/Panelmasken unterscheidbar. Ohne Assist bleibt die gelbe Ausgangsmarkierung unverändert.
- Deckkraft-Slider jetzt **20–100 %**; native OEM-Vorschau lässt sich vollständig deckend anzeigen.
- UI-Präferenzen allein unter `mibr-safe-oem-assist/1`. Keine Änderung von Safe-Area-Koordinaten, `mibr-project/1`, SD-/ZIP-Export oder Runtime.

Die Genauigkeit der Blockierungszonen bleibt wie in P0.9.3 eine vorsichtige Näherung aus den perspektivischen Fahrzeugfotos, keine automatische Sperrflächenberechnung.
