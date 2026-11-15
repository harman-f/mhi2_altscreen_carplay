# P0.9.8 – View-Profile Format /3

Basis P0.9.7, 16.11.2026. Keine Änderungen an Cockpit-SVGs, Safe-Area-Koordinaten oder Menüformat.

## Änderungen
1. Schema `mibr.nav-view-profiles/3` (`version: 3`), `.conf`-Kennung `MIBR_NAV_VIEW_PROFILES/3` und `version=3`. Import von v1 und v2 (JSON und `.conf`) hebt auf v3 an, indem Standardwerte ergänzt werden. Gespeicherte v2-Browserdaten werden beim Laden migriert.
2. Neu pro View `geometry.zoom` (`inherit`, `70`, `85`, `100`, `125`, `150`; Standard `inherit`, String). `.conf`: `view.<id>.geometry.zoom=`. Wird für jede View ausgegeben, auch im Modus `inherit`.
3. Neu global `transition`: `enabled` (Standard aus), `mode` (`cycle`/`panels`), `gap_ms` (100..3000, 500), `min_interval_ms` (500..60000, 3000). `.conf`: `global.transition.enabled=1|0`, `.mode`, `.gap_ms`, `.min_interval_ms`.
4. Unbekannte `.conf`-Schlüssel landen in `meta.extra` und werden sortiert vor `crc32` unverändert zurückgeschrieben. CRC32 weiterhin über alle Zeilen vor der `crc32`-Zeile.
5. UI: Gruppe „Bildgeometrie“ mit Auswahl „Zoom (Stream 111)“ und Hinweis (DE/EN) in den View-Einstellungen; Gruppe „Übergang“ (Checkbox, Modus, zwei ms-Felder mit Validierung, ungültige Werte werden nicht gespeichert) unter „Gemeinsame Vorgaben“. Alle neuen Texte über das vorhandene Wörterbuch DE/EN.
6. Kopieren und Zurücksetzen von Profilen lassen `geometry` unverändert (wie `safeArea`).
7. Versionslabel P0.9.8; eigenständige Kopie `mibr-menu-editor-nav-views-p098.html`.

## Nicht enthalten
Der Fahrzeug-Loader für `/mnt/app/root/mibr/config/cockpit/view-profiles.conf` (SD-Transport `/mibr-config/view-profiles.conf`) ist für r13 geplant und noch nicht vorhanden. Der Editor schreibt nichts automatisch dorthin.

## Tests
`test-p05.cjs` prüft v2 nach v3 (JSON, `.conf`, localStorage), v1-`.conf`, `.conf`-Rundlauf mit Geometrie, Übergang und unbekannten Schlüsseln, CRC32, Ablehnung ungültiger Zoom-, `gap_ms`-, `min_interval_ms`-, Modus- und `enabled`-Werte sowie Kopieren/Zurücksetzen ohne Geometrieverlust.
