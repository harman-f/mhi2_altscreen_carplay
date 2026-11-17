# MIB-Konfigurator – Anforderungen Konfigurations-Export (Entwurf 2026-11-17)

Status: **Entwurf**. Grundsatz von Owner bestätigt (2026-11-17): lokal eine Projektdatei, auf der SD-Karte Unit-Dateien im bestehenden Format. Mit **[OFFEN]** markierte Punkte warten auf Owner-Entscheidung; der jeweils genannte Vorschlag gilt bis dahin als Planungsannahme.

Bezug: Stand der Fahrzeugseite = Beta r13c (Profil-Schicht `MIBR_NAV_VIEW_PROFILES/3`, Broker als einziger Schreiber). Formate: [MENU_FILE_FORMAT.md](MENU_FILE_FORMAT.md), [MIBR_PROJECT_FORMAT.md](MIBR_PROJECT_FORMAT.md).

## 1. Dateien

### 1.1 Lokal (PC)

- **A1** Eine Projektdatei `mibr-project.json` (`mibr-project/1`) enthält **alle** Einstellungen: Fahrzeug, Menü, Ansichtsprofile, Safe Areas, Navigations-/CarPlay-Optionen, Tasten, Systemoptionen.
- **A2** Laden/Speichern: Datei-Import/-Download; in Chrome/Edge zusätzlich Arbeitsordner mit automatischem Speichern/Laden (vorhanden seit P0.9.10).

### 1.2 SD-Karte (Übertragung ins Auto)

Der Export schreibt in das gewählte SD-Stammverzeichnis (oder ein ZIP mit derselben Struktur):

| SD-Datei | Format | Inhalt | Ziel auf der Unit |
| --- | --- | --- | --- |
| `/mibr-menu/mibr-menu.txt` | `MIBR_MENU/1` + CRC32 (vorhanden) | Menüaufbau, Labels, Sichtbarkeit | `config/menu/layout.conf` |
| `/mibr-config/view-profiles.conf` | `MIBR_NAV_VIEW_PROFILES/3` + CRC32 | Ansichten, Zoom, Übergang, Safe Areas, Navigation/Pfeile, CarPlay-Nav-Optionen (s. 2) | `config/cockpit/view-profiles.conf` |
| `/mibr-config/keys.conf` | `MIBR_KEYS/1` + CRC32 (neu) | Tastenbelegung, Raddrehen-Zoom | eigene Nutzerdatei neben `config/platform/defaults.conf` (s. 3.3) |
| `/mibr-config/options.conf` | `MIBR_OPTIONS/1` + CRC32 (neu) | Sprache, Expertenmodus, SD-Log, Skalierung | bestehende Einzeldateien über bestehende Broker-SETs |
| `/mibr-config/mibr-project.json` | `mibr-project/1` | Kopie der Projektdatei, nur zum Zurückladen in den Editor | wird von der Unit ignoriert |

- **S1** Alle Unit-Dateien tragen dieselbe Zeile `export.id=<UTC-Zeitstempel>-<8 hex>`. Die Unit warnt beim Laden, wenn bereits geladene Dateien eine andere `export.id` haben.
- **S2** Jede Datei: UTF-8, `\n`, letzte Zeile `crc32=<8 hex>` über alle vorherigen Zeilen, max. 16384 Byte. Unbekannte Schlüssel lehnt die Unit nicht ab, sie werden ignoriert und protokolliert.
- **S3** Export nur für freigegebene Hardware (heute Škoda/MU1440/AID10); Prüffehler im Editor verhindern den Export.
- **S4** Der Editor kann jede der SD-Dateien auch einzeln wieder einlesen (Fallback, falls die Projektkopie fehlt).

## 2. Zuordnung der Einstellungen

| Einstellung | Editor heute | SD-Datei | Unit wertet heute aus | Arbeit |
| --- | --- | --- | --- | --- |
| Menüaufbau | ja | mibr-menu.txt | ja | – |
| Nav: Quelle, Anzeige, Textzeile, Unten, Spuren, Seitenstraßen (`global.*`) | ja | view-profiles.conf | ja | – |
| Safe Area je Ansicht | ja | view-profiles.conf | ja | – |
| Zoom je Ansicht, Übergang (`global.transition.*`) | ja | view-profiles.conf | ja | – |
| Nacht-Karte (`nav_night`) | nein | view-profiles.conf `global.navNight` | ja (Einzeldatei) | Editor + Profil-Schlüssel |
| CarPlay-Navigation an/aus (`carplay_nav`) | nein | view-profiles.conf `global.carplayNav` | ja (Einzeldatei) | Editor + Profil-Schlüssel |
| ETA, Tempolimit, Kompass, Manöver, Kartenart | ETA/Manöver/Kartenart je Ansicht; Tempolimit/Kompass fehlen | view-profiles.conf `global.carplay.*` | ja, aber aus Registry (persistent gesperrt) | GEN2 liest künftig aus dem Profil, Registry als Rückfall |
| Native-Optionen je Ansicht (`native.*`), `guidance.*` je Ansicht, `view.*.mode` | ja | view-profiles.conf (durchgereicht) | **nein** | s. E3 |
| Tastenbelegung (`key.*`), Raddrehen-Zoom (`zoom.*`) | nein | keys.conf | ja (Boot) | Editor + Import |
| Sprache, Expertenmodus, SD-Log, Skalierung | nein | options.conf | ja | Editor + Import |
| Kalibrierbild, Demo-Route, aktuelle Ansicht | – | nicht exportiert (Laufzeitzustand) | – | – |
| Kill-Switch, Feature-Flags, Single-Writer | – | nicht exportiert (Installer/Operator) | – | – |

## 3. Fahrzeugseite

- **U1 Import-Befehle im Broker** nach dem Muster von `MENU_LOAD` (fester SD-Pfad, Prüfung vorab, Stage + rename, Readback):
  - `VIEW_PROFILE_LOAD`: prüft Kopf, CRC, Wertebereiche; übernimmt nur bekannte Schlüssel plus durchgereichte Editor-Schlüssel; zählt `unit.revision` hoch; legt `.lastgood` an. GEN2/Java lesen das Profil danach selbst neu (kein Neustart).
  - `KEYMAP_LOAD`: s. 3.3.
  - `OPTIONS_LOAD`: setzt jeden Wert über den vorhandenen Einzel-SET (gleiche Prüfungen wie im Menü); kein neues Speicherformat.
- **U2 Menü:** unter „Erweitert“ ein Eintrag „Konfiguration laden“, der Menü, Profil, Tasten und Optionen in dieser Reihenfolge lädt und das Ergebnis je Datei anzeigt (geladen / fehlt / abgelehnt mit Grund). **[OFFEN E1]**
- **U3 Fehlerverhalten:** Eine abgelehnte Datei ändert nichts; bereits erfolgreich geladene Dateien bleiben. Keine Teilübernahme innerhalb einer Datei.
- **3.3 Tasten:** `KEYMAP_LOAD` schreibt nur `key.*`/`zoom.*` in eine Nutzerdatei (z. B. `config/platform/keys-user.conf`); Leser nehmen Nutzerwert vor Installer-Wert. Erlaubt sind nur Tasten aus einer festen Liste (Lenkrad 4/40, 4/41, 4/44, 4/46, 4/47, 4/50, 4/53; Menü 13/78 usw.). Kaputte oder fehlende Datei = Installer-Werte. Wirksam nach Neustart, solange key40d nur beim Boot liest. **[OFFEN E2]**
- **U4 GEN2:** CarPlay-Nav-Optionen (`global.carplay.showETA|showSpeedLimit|showCompass|maneuverLayout|surface`) aus dem Profil lesen, Registry nur als Rückfall.
- **U5 QNX-Regeln:** Jedes neue Unit-Skript besteht das bestehende QNX-Gate (`tools/check_mu1440_target_shell.py`).

## 4. Editor

- **E-1** Neue Felder: Nacht-Karte, CarPlay-Navigation, Tempolimit, Kompass, Tasten (Auswahl aus fester Liste), Sprache, Expertenmodus, SD-Log, Skalierung.
- **E-2** „Auf SD-Karte exportieren“ schreibt alle Dateien aus 1.2 gemeinsam; Statusanzeige je Datei.
- **E-3** Einstellungen ohne Wirkung auf der Unit werden als „noch ohne Wirkung im Fahrzeug“ gekennzeichnet bzw. ausgegraut.

## 5. Offene Owner-Entscheidungen

| Nr. | Frage | Vorschlag |
| --- | --- | --- |
| E1 | Ein Menüeintrag „Konfiguration laden“ für alles oder getrennte Einträge? | Ein Eintrag für alles, Ergebnis je Datei anzeigen |
| E2 | Tastenbelegung im Editor änderbar oder nur Anzeige? | Änderbar, nur aus fester Liste, Rückfall auf Installer-Werte |
| E3 | Native-/Guidance-Optionen je Ansicht ohne Unit-Wirkung: mitspeichern oder weglassen? | Mitspeichern (vorwärtskompatibel), im Editor als „noch ohne Wirkung“ ausgrauen |
| E4 | ETA, Manöver, Kartenart global oder je Ansicht? | Vorerst global; je Ansicht später (mehr GEN2-Arbeit) |
| E5 | Reihenfolge | Erst r13c-Fahrzeugtest abschließen, dann U1/U4, dann Editor-Export |
