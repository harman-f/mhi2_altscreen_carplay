# MIB-Konfigurator – Projektdatei und SD-Export (P0.5)

## Projekt speichern oder SD exportieren?

Die globale Kopfzeile bietet drei getrennte Aktionen:

- **Projekt laden**: `mibr-project.json` öffnen und den gesamten Editorzustand wiederherstellen
- **Projekt speichern**: versioniertes, editierbares JSON-Projekt; Zielordner wird vom Browser festgelegt beziehungsweise vom Benutzer gewählt
- **Auf SD-Karte exportieren**: nur die derzeit mit Fahrzeug-Runtime belegte Datei `/mibr-menu/mibr-menu.txt`

Die automatische Browser-Sicherung unter `localStorage["mibr-project/1:autosave"]` ist keine Projektdatei. Sie ersetzt keine regelmäßige Dateisicherung. Der Editor darf nicht ohne ausdrückliche Freigabe in den Ordner der HTML-Datei oder auf die SD-Karte schreiben.

## Projektformat

`schema: "mibr-project/1"`, `version: 1`:

```json
{
  "schema": "mibr-project/1",
  "version": 1,
  "vehicle": {
    "brand": "skoda",
    "headUnit": "MU1440",
    "cluster": "AID10"
  },
  "menu": {
    "v": 2,
    "build": "v2",
    "brand": "skoda",
    "name": "",
    "rootDe": "",
    "rootEn": "",
    "tree": [],
    "unused": []
  },
  "viewProfiles": {
    "schema": "mibr.nav-view-profiles/2",
    "version": 2,
    "vehicle": {
      "brand": "skoda",
      "headUnit": "MU1440",
      "cluster": "AID10"
    },
    "global": {},
    "views": {
      "center": {},
      "wide": {},
      "full": {}
    },
    "meta": {"runtimeCompatible": false}
  }
}
```

Das Beispiel zeigt **nur die Struktur**, keine vollständige oder gültig installierbare Konfiguration: `menu.tree`, `viewProfiles.global` und die drei Views benötigen konkrete Werte. Ein echter Export enthält sie. Bei Import werden die drei Fahrzeugkontexte gegeneinander geprüft. Der Menüeditor verwendet sein bewährtes JSON-Modell mit den ursprünglichen IDs und Funktionen; die View-Profile enthalten die Safe Areas `{x,y,w,h}` (x/y Ursprung links oben, Pixel, in der derzeitigen Referenz `1010×376`).

### Migration und Quellformate

- Die vorhandenen Browser-Daten des Menü-Editors und der Nav-Views bleiben erhalten und werden beim ersten P0.5-Start in den gemeinsamen Projekt-Autospeicher übernommen.
- Bisherige Menüdateien `MIBR_MENU/1` mit CRC32 können weiterhin im Menü-Editor (erweiterte Dateiaktionen) gelesen werden.
- View-Profil-JSON und `.conf` v1/v2 bleiben als Einzelformate im erweiterten View-Bereich erhalten. P0.5 erweitert das interne v2-Profil um optionale, abschaltbare Center-HUD-Elemente und den nur für die Vorschau gedachten Kartenhintergrund.
- Es gibt keine automatische Installation von View-Profilen ins Fahrzeug.

## Ausgabe auf die SD-Karte

Die native Menüdatei ist bereits definiert und wird über **Erweitert → Menü laden** vom Fahrzeug eingelesen:

```text
SD-Karten-Stammverzeichnis/
└── mibr-menu/
    └── mibr-menu.txt
```

Die Datei wird im unveränderten `MIBR_MENU/1`-Format mit `catalog=2`, `brand=skoda`, Zeilenstruktur und CRC32 erstellt.

Der aktuelle SD-Export ist ausdrücklich für **Škoda / MU1440 / AID10** freigegeben. Andere Hardwarekombinationen werden bis zu einer belegten Kompatibilität abgewiesen. Menüfehler verhindern den Export.

**Direct-write:** In Chromium-basierten Browsern mit `showDirectoryPicker` wählt der Benutzer das **Stammverzeichnis der SD-Karte**; der Editor legt `mibr-menu/` bei Bedarf an. Bei bereits vorhandener Menüdatei fragt er nach, bevor er überschreibt.

**Fallback:** Ohne Verzeichniszugriff erstellt der Editor `mibr-sd-menu.zip`; es enthält **nur** `mibr-menu/mibr-menu.txt`. Das ZIP muss manuell in das Stammverzeichnis der SD-Karte entpackt werden.

**Nicht enthalten:** `mibr.nav-view-profiles/2` und Safe-Area-Konfigurationen besitzen derzeit **keinen nachgewiesenen fahrzeugseitigen Loader**. Es wird ausdrücklich kein fiktives Fahrzeugdateiformat oder Zielverzeichnis für sie behauptet.

## Qualitätssicherung

Die GitHub-Action `menu-editor-p04-smoke.yml` prüft mit jsdom und JSZip den bisherigen Menüeditor, vier Hauptreiter, das modulare Center-Mockup, View-/Safe-Area-Einstellungen, gemeinsame JSON-Autosicherung, den nativen CRC32-Menütext, den ZIP-Inhalt und den simulierten Schreibpfad unter `mibr-menu/mibr-menu.txt`.

Es handelt sich um einen Browser-Mock-up-Test, **nicht** um einen Fahrzeugtest. Änderungen an BAP-/RGI-Navigation oder Java-Native-Runtime werden hierdurch nicht implementiert.
