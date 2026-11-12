# MIB-Konfigurator P0.9.5 – Drei geometrische Optimierungsläufe aus dem Zahlenraster
Stand: 12. November 2026. Referenzfotos: **IMG_2319(1).jpeg** (Wide), **IMG_2320(1).jpeg** (Center), **IMG_2321(1).jpeg** (Voll). Kalibrierung: 1010×376 SVG-Einheiten, 100er-X- und 50er-Y-Zahlenraster in den echten Fotos.

## Messmethode und Genauigkeit
Aus mehreren eindeutig beschrifteten Grid-Schnittpunkten der perspektivisch aufgenommenen Fahrzeugfotos wurden horizontale/vertikale Rastermaßstäbe näherungsweise bestimmt. Dann wurden die äußersten geometrischen OEM-Kanten (Trapez-Seams, Full-Unterkanten, Dial-Ränder) auf das Raster zurückgerechnet. Einzelne Werte können je nach Projektionsfehler des Fotos um etwa **±20 SVG-Einheiten** abweichen; dies ist keine homographische oder fahrzeugseitige Pixel-/BAP-Messung.

## Optimierung 1/3 – Wide und Voll
- **Wide:** Clip oben von x=284/723 auf **188/830**, unten von 331/685 auf **272/738** (Höhe 37–329). Sidepanel-Füllungen, schräge Linien und Kartenhintergrund auf dieselben Kanten abgestimmt. Die native Panel-Innendarstellung wurde in das neue freie Seitenmodul verschoben.
- **Voll:** Untere Clip-Schultern auf y=261 und Fußpunkte auf **x=273/737, y=350** gebracht, Sidecut-Pfade und Konturlinien folgen derselben Geometrie.

## Optimierung 2/3 – Center
- Die beiden Rundinstrumente aus den Referenzfotos etwas größer und weiter nach außen: effektive Mittelpunkte x=225/785, Radius **167,48** statt x=253/757, Radius 158.
- Zugehörige Lane-/Pfeil-/Distanzgruppen rechts erhalten exakt dieselbe Transformation, OEM Top/Bottom-Overlays bleiben unverändert gemeinsam.
- Die freie Kartenfläche x=393–615 bleibt damit zwischen den Zifferblättern (Grenzen x≈392.48 und 617.52).

## Optimierung 3/3 – Masken, Regression und Abnahme
- Im Safe-Area-Editor übernehmen die blockierten Center-Kreise jetzt die Transformation ihrer tatsächlichen Instrumentengruppen. Wide- und Voll-Masken sind weiterhin exakte Kopien ihrer gerade angezeigten Panel-/Unterkanten-Pfade.
- Prüft mit `test-p05.cjs`, `test-p09-visual.cjs` in Chrome Desktop/iPhone-Größe und `build-shared-oem-overlays.cjs --check`. P0.9.5 ist eine separate HTML-Snapshot-Datei, die P0.9.4 nicht überschreibt.
- **Weder Profile und Safe-Area-Werte noch `mibr-project/1`, `MIBR_MENU/1`, SD-Export oder Fahrzeug-Runtime wurden verändert.**

## Quantitative Raster-Anker (ungefähre SVG-Einheiten)
| View | Messpunkte | Vorher: mittlerer absoluter Ankerfehler | Nachher |
|---|---|---:|---:|
| Wide | Top links/rechts und Bottom links/rechts | 82,0 | 3,0 |
| Voll | Schultern, untere Endpunkte, zwei Y-Lagen | 17,8 | 2,2 |
| Center | Kreismitten links/rechts und zwei Außenradien | 18,8 | <0,1 |

**Wichtig:** Die Zahlen bewerten lediglich die Abweichung zu den **aus Fotos geschätzten** Kalibrierankern. Sie sind keine objektive Fehlerkennzahl für die wirkliche Display- bzw. OEM-Elementgeometrie. Nach der visuellen Safari-Abnahme können diese Näherungsanker weiter verbessert werden.
