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
    if len(parser.rows) != 56 or len(parser.cards) != 56:
        errors.append(f"expected exactly 56 curated repository rows and 56 cards (58 original baseline), got {len(parser.rows)} rows and {len(parser.cards)} cards")
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
    # Primary navigation stays globally visible, but the overview hero and
    # its four statistics must be scoped to the Overview panel only.
    nav_start, nav_end = data.find("<nav>"), data.find("</nav>")
    tabbar = data.find('<div class="atlas-tabs">')
    main_start = data.find("<main>")
    overview_start = data.find('<div class="atlas-tab-pane" data-atlas-tab="overview" id="atlas-panel-overview">')
    hero = data.find('<header id="top">')
    overview_contents = data.find('<section id="atlas-introduction"')
    comparison_start = data.find('<div class="atlas-tab-pane" data-atlas-tab="comparison"')
    if not (0 <= nav_start < nav_end < tabbar < main_start < overview_start < hero < overview_contents < comparison_start):
        errors.append("global tabs then Overview-only hero/stats before Overview content is required")
    overview_html = data[overview_start:comparison_start] if overview_start >= 0 and comparison_start > overview_start else ""
    if data.count('<header id="top">') != 1 or data.count('class="stats"') != 1 or overview_html.count('class="atlas-feedback-banner"') != 1:
        errors.append("one hero/stats grid and one overview-scoped feedback banner are required")
    # The separate lineage binary/provenance notice legitimately reuses the
    # feedback-banner visual style; it is not a duplicate overview hero.
    if 'nav .brand{font-size:16px!important' not in data:
        errors.append("compact MIB Atlas brand must remain at enlarged 16px")
    if 'position:sticky;top:62px;z-index:79' not in data:
        errors.append("sticky topic navigation must stack beneath the 62px header")
    if 'background:linear-gradient(135deg,#176960,#1a8173)' not in data:
        errors.append("active topic must be visibly highlighted")
    if 'font-size:14px;font-weight:760' not in data:
        errors.append("topic labels must retain enlarged visible typography")
    if "14 emulator and lab leads" not in data or "25 selected development claims and releases" not in data:
        errors.append("missing annotated community research inventory")
    # Comparison tab: primary comparison must precede the MIB1 context,
    # detailed source catalog and finally the factory HUD (not a new tab).
    comparison_order = ('id="matrix"', 'id="mib1-retrofit"', 'id="catalog"', 'id="oem-hud-overview"')
    offsets = [data.find(item) for item in comparison_order]
    if any(pos < 0 for pos in offsets) or offsets != sorted(offsets) or len(set(offsets)) != len(offsets):
        errors.append("comparison section order must be matrix, MIB1, catalog, then OEM HUD")
    if data.count('data-host-os="') != 14 or data.count('class="atlas-host-tags"') != 14:
        errors.append("all 14 emulator entries must expose visible host OS badges and filter tokens")
    if '<select class="atlas-filter-select" data-field="hostOs">' not in data or 'sel.dataset.field==="hostOs"' not in data:
        errors.append("emulator host OS selector must be wired to multi-host filter handling")
    for label in ('Windows · WSL', 'Windows · ODIS only', 'macOS', 'Linux', 'OS not stated'):
        if label not in data:
            errors.append("missing independently classified host environment: " + label)
    if "Host operating system" not in data or "Telegram author / date" not in data:
        errors.append("missing emulator host/guest provenance columns")
    for marker in ('<title>MIB Atlas', 'id="mib1-retrofit"', 'data-atlas-filter-table="native"', 'data-atlas-filter-table="emulators"', 'data-atlas-filter-table="ha-tools"', 'data-atlas-filter-table="contitool"', 'data-atlas-filter-table="roadmap"', 'data-atlas-filter-table="misc"', 'data-atlas-filter-table="lineage"', 'data-atlas-filter-table="oem-hud"', 'data-atlas-filter-table="aftermarket-hud"', 'id="atlas-theme-toggle"'):
        if marker not in data:
            errors.append("MIB Atlas required feature missing: "+marker)
    for marker in ('58-ENTRY SCORE BASELINE 04 NOV 2026', 'SOURCE REVIEW 27 NOV 2026'):
        if marker not in data:
            errors.append("Missing evidence date boundary: "+marker)
    # Interaction contract: all nine research matrices have actual search/filter/reset handlers.
    if data.count('data-atlas-filter-table="') != 9:
        errors.append("expected exactly nine filterable research matrices")
    if data.count('class="atlas-filter-search"') != 9:
        errors.append("every research matrix must have a search control")
    if data.count('class="atlas-filter-clear"') != 9:
        errors.append("every research matrix must have an active reset control")
    if "data-atlas-sort" not in data or 'root.querySelectorAll("[data-atlas-sort]")' not in data:
        errors.append("research table sorting must be connected to JavaScript")
    if 'dataset.theme=next' not in data or 'localStorage.setItem("cluster-atlas-theme",next)' not in data:
        errors.append("persistent light/dark toggle logic missing")
    if 'html[data-theme="light"]' not in data:
        errors.append("light theme stylesheet missing")
    nav = data[data.find("<nav>"):data.find("</nav>") + len("</nav>")]
    if 'href="#matrix"' in nav or 'href="#catalog"' in nav or 'href="#timeline"' in nav:
        errors.append("top navigation duplicates the topic tabs")
    if "**Gateway J533" in data:
        errors.append("raw Markdown emphasis inside public HTML")
    if 'MHI2Q_WiFi_CarPlay' not in data or 'perkthefox/mqb_contitool' not in data:
        errors.append("source-anchored native wireless or ContiTool evidence missing")
    # Native Wireless is evidenced by exact release + separately scoped GitHub user reports.
    # The historical baseline still dates to 4 Nov, but the latest source review is 27 Nov.
    if 'Wireless CarPlay Maps V3.2' not in data or 'data-search="omonob Wireless CarPlay Maps V3.2' not in data:
        errors.append("latest omonob V3.2 experimental release entry missing")
    if 'Škoda MU1440 790' not in data or 'MU1367 790/791' not in data:
        errors.append("native firmware/cluster exact profile list missing")
    if 'MU1440/791 unsupported' not in data or 'MU1433/MU1447 wired-only' not in data:
        errors.append("unsupported newer AID/other-MU native wireless boundary missing")
    if 'SD install had already been reported' not in data:
        errors.append("MU1367 V3.2 installation user report absent")
    if 'not a complete receiver implementation/build source release' not in data.lower():
        errors.append("missing explicit omonob complete source/build limitation")
    if 'issues/72' not in data or 'issues/73' not in data or 'iPhone 16 Pro Max' not in data:
        errors.append("MU1440 real-wireless no-VC and VC user field reports missing")
    if 'Exact cluster part number not supplied' not in data and 'Exact cluster part/790 suffix not specified' not in data:
        errors.append("MU1440 VC part-number uncertainty must be explicit")
    for issue in ('issues/70','issues/71','issues/75','issues/76','issues/79'):
        if issue not in data:
            errors.append("missing unresolved omonob field regression: "+issue)
    if 'MU1367-v1.6.7-e' not in data or 'v1.6.6-e was withdrawn' not in data:
        errors.append("latest tomasz MU1367 experimental 790 / withdrawn history missing")
    if 'MU1367-v1.6.1' not in data or 'AID 791' not in data:
        errors.append("vehicle-tested stable MU1367 downstream lineage missing")
    if 'chrzanowy MU1161/AID791 v1.9.0' not in data or 'ContiTool v2.2.1' not in data:
        errors.append("25 Nov nearby MHI2 AA and J533 tool updates missing")
    if 'CatPlay / CarPlay2Air V0.33.0' not in data:
        errors.append("open USB dongle project must remain in its Misc tab")
    if '27 Nov</b><span>Last source review' not in data:
        errors.append("latest source review date stale")
    for marker in ('ATLAS_REFRESH_2026-11-26.md', 'primaryInputDevice=0', 'HW301 v1178', 'issues/80', 'issues/119', 'issues/120', 'source review 27 Nov 2026'):
        if marker not in data:
            errors.append("26 Nov evidence missing: "+marker)
    for marker in ('VEHICLE_DATA_SURVEY_2026-11-27.md', '22 / 22', 'Victor-Unsullied/mib2-sports-gauges', 'ijord/EXLAP-mib2-atlas', 'Matze89x/ha-car-assistant', 'korhojoa/exlap-client'):
        if marker not in data:
            errors.append("27 Nov vehicle-data evidence missing: "+marker)
    if '7 / 7' not in data or data.count('data-search="tomasz-twardzicki MHI2 CarPlay Maps') != 1:
        errors.append("seven distinct native research/port entries required")
    if 'https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.2' not in data:
        errors.append("omonob latest release link missing")
    if 'MU1440 wireless still lacks hardware acceptance' in data or 'MU1440/790 have only offline V3.2 regression' in data:
        errors.append("stale 20 Nov MU1440 offline-only claim on current site")
    if 'issues/187' not in data or 'id="oem-hud-overview"' not in data or 'id="aftermarket-hud-overview"' not in data:
        errors.append("HUD taxonomy or feedback issue missing")
    if data.count('data-lineage-edge="1"') != 38 or data.count('class="atlas-lineage-svg"') != 4:
        errors.append("expanded static lineage graph and source evidence table missing")
    if 'GitHub fork' not in data or 'Code adaptation' not in data or 'Design reference' not in data or 'Pinned component' not in data:
        errors.append("lineage must distinguish ancestry from design and pinned dependencies")
    for hidden in ('repo-new-maxim-smirnov-mhi2-carplay-cluster', 'repo-new-mr-mibonk-mhi2-android-auto-cluster-map'):
        if hidden in parser.ids:
            errors.append("unchanged/behind-only fork remains in active catalog: " + hidden)
    if 'id="misc-overview"' not in data:
        errors.append("external dongles and HUD must have a separate Misc tab")
    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {len(parser.rows)} curated rows (58 source baseline) × {len(FEATURES)} features, {len(parser.cards)} profiles, {len(TABS)} tabs, nine filterable research matrices, {len(ids)} distinct IDs and {len(parser.fragments)} working internal anchors")

if __name__ == "__main__":
    audit(Path(sys.argv[1] if len(sys.argv) > 1 else "docs/index.html"))
