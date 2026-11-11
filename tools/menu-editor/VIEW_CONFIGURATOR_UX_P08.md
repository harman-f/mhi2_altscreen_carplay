# View-Konfigurator P0.8 – Bedienlogik und Audit

## Ziel

Auf Basis der sechs Screenshots vom iPhone und der drei Cockpit-Fotos: nur die ausgewählte Ansicht darstellen, die Geometrie groß und vergleichbar halten und die Einstellungen als echte Eigenschaften dieses ausgewählten Views behandeln.

### Hauptfluss

1. **Aktive Cockpit-Ansicht**: Center, Wide oder Voll auswählen (zunächst die drei Ansichten mit Karten-/Navigationsinhalt).
2. **Einzige Live-Vorschau**: genau das ausgewählte Cockpit, groß über die Breite; Großansicht und Hintergrund nur für diese View.
3. **Einstellungen**: darunter auf breiten Displays zweispaltig, auf iPhone schmal einspaltig; CarPlay, native Navigation und Guidance.
4. **Profilverwaltung**: sekundär, aufklappbar direkt unter der Auswahl; dort globale Vorgaben, kopieren und zurücksetzen.

Die von der AID10 bekannte Zahl von insgesamt fünf Cockpit-Ansichten ist damit nicht aufgehoben. Die zusätzlichen Ansichten ohne Karte/Navigation werden **noch nicht** als unbestätigte Profile eingeführt.

## Behobene Fehler

- **Drei SVGs gleichzeitig:** P0.7 setzte ausschließlich `SVGElement.hidden`, das in Safari als nicht wirksames JavaScript-Feld auftreten kann. P0.8 setzt explizit sowohl ein `hidden`-DOM-Attribut als auch `style.display = block/none`; Initialzustand durch CSS abgesichert. Regressionstests prüfen jetzt das tatsächliche Display-Verhalten statt der Eigenschaft.
- **Nicht unterscheidbarer Vorschau-Hintergrund:** Die Center-Route blieb vorher zusätzlich im Grid-Modus eingeblendet. In P0.8 sind die Modi für alle Views gleich:
  - **Kalibrier-Grid:** Hilfslinien ohne Route;
  - **Neutral:** ruhige Grundfläche ohne Straßen oder Route;
  - **Schematische Karte:** stilisierte Straßen und Route.
  Diese Wahl verändert ausdrücklich **nur die Editor-Vorschau**, nicht die CarPlay-/Fahrzeug-Ausgabe.
- **Profilkopieren überschreibt Geometrie:** Die vorherige Implementierung übertrug die Safe Area des Quellviews auf das Ziel. P0.8 kopiert ausschließlich `carplay`, `native` und `guidance`, mit Bestätigung. Ziel-Safe-Area und editorseitiger Hintergrund bleiben erhalten.
- **Reset überschreibt Safe Area:** Zurücksetzen behält jetzt Safe Area und Vorschau-Hintergrund; nur fachliche CarPlay-/Navigationswerte werden auf Standard gesetzt.
- **Profilmodus wirkt wie Pflicht:** Neu angelegte Center-/Wide-/Voll-Profile sind standardmäßig `custom` (individuell); die vorhandene Vererbungsfunktion ist optional in der Profilverwaltung. **Bereits gespeicherte** `inherit`-Profile werden nicht still umgestellt: Die Auswahl ist weiterhin funktionsfähig und als solche erkennbar.

## Unterscheidung Editor und Fahrzeug

- `MIBR_MENU/1` bleibt die aktuelle native Menüdatei und wird ausschließlich von den bisherigen SD-Exportaktionen erstellt.
- `mibr-project/1` bündelt die Arbeit im Editor; die View-Profil-Daten einschließlich Safe Areas werden als experimentelles `mibr.nav-view-profiles/2` gehalten.
- Änderungen in der Cockpit-Live-Vorschau **ändern nicht** die native QNX-/BAP-/RGI-Darstellung. Die tatsächliche Schaltbarkeit einzelner OEM-Symbole ist weiterhin nachzuweisen.

## Weiter offen

- Neue Ansichtstypen außerhalb Center/Wide/Voll einführen, sobald die korrekten OEM-Zuordnungen bestätigt sind.
- Präzisere Verknüpfung von `nav_display`, `nav_line`, `nav_lanes` und echten BAP-Kanälen vor Fahrzeugexport von View-Profilen.
- Entscheidung, ob die Browser-Vorschau für App-Standard vs. CarPlay-Karte separate Visualisierungen braucht.
- Safe-Area-Reiter pro View mit dem gleichen, eindeutigen aktiven View-Kontext koppeln. Aktuell sind die Daten zwar gemeinsam gespeichert, aber die Auswahl in den beiden Modulen ist noch unabhängig.
- Manueller visueller iPhone-Safari-Test bleibt nötig; jsdom-Tests prüfen keine echten Schriftgrößen oder Safari-Rendering.

## Prüfungen

CI-Suite `test-p04.cjs` und `test-p05.cjs`: Menüeditor, View-Auswahl, sichtbares SVG, Hintergrund, Zielprofilkopie, Vererbung, sichere Geometrie, JSON-Speicherung, native Menüdatei mit CRC32, ZIP- und SD-Schreibpfad.

## P0.8-Folgeaudit: gemeinsamer aktiver View-Kontext (11.11.2026)

- View-Konfigurator und Safe-Area-Reiter verwenden dieselbe aktive Auswahl `center`/`wide`/`full` (im älteren Safe-Area-Speicher wird `full` weiterhin `voll` genannt). Auswahlwechsel aus einem der beiden Bereiche aktualisieren den anderen; die Geometrie wird **nicht** durch bloße Auswahl verändert.
- Ein separater `localStorage`-Schlüssel merkt sich die aktive Ansicht. Dies ist **kein** neues Feld in `mibr-project/1` oder `mibr.nav-view-profiles/2`. JSON-, .conf- und native Menü-Exporte bleiben unverändert.
- Eine direkte Aktion im View-Konfigurator öffnet den Safe-Area-Reiter für die aktive Ansicht.
- `Guidance-Mapping` ist standardmäßig eingeklappt und als experimentelle Dateninterpretation beschriftet. **Keine Schemafelder entfernt.** `carplay.eta`, `native.bottomEta` und `guidance.bottom` sowie Lane-Schalter können visuell ähnliche Ergebnisse haben, aber unterschiedliche Modellbedeutungen. Vor einer Zusammenlegung sind reale Runtime-/BAP-Belege nötig.
- Browser-Regressionen prüfen die Auswahl in beide Richtungen, den direkten Wechsel zur Safe Area und die Ein-SVG-Sichtbarkeit. Der visuelle iPhone-Safari-Test bleibt ausstehend.

### Noch nicht als Fahrzeugfunktion freigegeben

Die individuellen nativen Schalter repräsentieren Mock-up-Ebenen. Rechter Pfeil, obere Pfeile, Lane-Anzeige und Zeitfelder sind erst nach Runtime-/BAP-Nachweis als unabhängig programmierbar zu bezeichnen. Native SD-Ausgabe bleibt ausschließlich `MIBR_MENU/1`.
