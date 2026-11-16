#!/usr/bin/env python3
"""Validate the public, self-contained MIB Atlas; no third-party dependencies."""
from html.parser import HTMLParser
from pathlib import Path
import sys

TABS = ("overview", "comparison", "wireless", "emulators", "integrations", "perk", "roadmap", "misc", "research")
FEATURES = ("cpmap", "aamap", "mirror", "card", "rgi", "arrows", "lanes", "hud", "handoff", "cover", "media", "progress", "calls", "spatial", "zoom", "views", "siri", "touchpad", "vehicle", "wireless", "recovery", "installer")

class AtlasParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.fragments = []
        self.rows = []
        self.cards = []
        self.panel_names = []
        self.radios = []
        self.labels = []
        self.links = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a":
            href = a.get("href", "")
            self.links.append(href)
            if href.startswith("#"):
                self.fragments.append(href[1:])
        classes = (a.get("class") or "").split()
        if tag == "tr" and "data-row" in classes:
            self.rows.append(a)
        if tag == "article" and "repo-card" in classes:
            self.cards.append(a)
        if tag == "div" and "atlas-tab-pane" in classes:
            self.panel_names.append(a.get("data-atlas-tab"))
        if tag == "input" and a.get("name") == "atlas-topical-view":
            self.radios.append(a)
        if tag == "label" and a.get("role") == "tab":
            self.labels.append(a)

def audit(path: Path) -> None:
    data = path.read_text(encoding="utf-8")
    parser = AtlasParser()
    parser.feed(data)
    errors = []
    ids = set(parser.ids)
    if len(ids) != len(parser.ids):
        errors.append("duplicate HTML ids")
    missing = sorted(set(parser.fragments) - ids)
    if missing:
        errors.append("broken internal href anchors: " + ", ".join(missing[:20]))
    if len(parser.rows) != 58 or len(parser.cards) != 58:
        errors.append(f"expected exactly 58 repository rows and 58 cards, got {len(parser.rows)} rows and {len(parser.cards)} cards")
    row_ids = {x.get("data-id") for x in parser.rows}
    card_ids = {x.get("id", "")[5:] for x in parser.cards}
    if row_ids != card_ids:
        errors.append(f"row/profile mismatch: {sorted(row_ids ^ card_ids)}")
    for idx, row in enumerate(parser.rows):
        miss = [k for k in FEATURES if "data-" + k not in row]
        if miss:
            errors.append(f"row {idx} lacks original feature keys: {miss}")
    if len(FEATURES) != 22:
        errors.append("original comparison feature count changed")
    if set(parser.panel_names) != set(TABS) or len(parser.panel_names) != len(TABS):
        errors.append(f"incorrect tab panels: {parser.panel_names}")
    if {i.get("id") for i in parser.radios} != {"atlas-tab-" + t for t in TABS}:
        errors.append("tab radio input set does not match panels")
    if {l.get("for") for l in parser.labels} != {"atlas-tab-" + t for t in TABS}:
        errors.append("tab label set does not match panels")
    if sum("checked" in x for x in parser.radios) != 1:
        errors.append("exactly one topic radio must be checked")
    for t in TABS:
        if f"#atlas-tab-{t}:checked ~ main #atlas-panel-{t}" not in data:
            errors.append(f"missing CSS-only tab activation rule for {t}")
    for required in ("id=\"wireless-update\"", "id=\"emulator-overview\"", "id=\"integrations-overview\"", "id=\"perk-overview\"", "id=\"community-repository-leads\"", "id=\"community-roadmap-20261116\"", "id=\"matrix\"", "id=\"lineage\"", "id=\"timeline\""):
        if required not in data:
            errors.append("missing section: " + required)
    if any(s in data.lower() for s in ("messages11.html", "messages10.html", "t.me/c/")):
        errors.append("private/community raw source marker found in public HTML")
    if "14 emulator and lab leads" not in data or "25 selected development claims and releases" not in data:
        errors.append("missing annotated community research inventory")
    if "Host operating system" not in data or "Telegram author / dates" not in data:
        errors.append("missing emulator host/guest provenance columns")
    for marker in ('<title>MIB Atlas', 'id="mib1-retrofit"', 'data-atlas-filter-table="native"', 'data-atlas-filter-table="emulators"', 'data-atlas-filter-table="ha-tools"', 'data-atlas-filter-table="contitool"', 'data-atlas-filter-table="roadmap"', 'data-atlas-filter-table="misc"', 'data-atlas-filter-table="lineage"', 'id="atlas-theme-toggle"'):
        if marker not in data:
            errors.append("MIB Atlas required feature missing: "+marker)
    for marker in ('58-ENTRY SCORE BASELINE 04 NOV 2026', 'SOURCE REVIEW 16 NOV 2026'):
        if marker not in data:
            errors.append("Missing evidence date boundary: "+marker)
    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {len(parser.rows)} rows × {len(FEATURES)} features, {len(parser.cards)} profiles, {len(TABS)} tab panels, {len(ids)} distinct IDs, {len(parser.fragments)} internal anchors; privacy markers absent")

if __name__ == "__main__":
    audit(Path(sys.argv[1] if len(sys.argv) > 1 else "docs/index.html"))
