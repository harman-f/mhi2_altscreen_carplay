"""Generate Classic111 descriptor metadata and the MU1440 menu overlay.

The canonical registry is the only source for setting descriptors and choice
domains. The menu JSON is UI metadata only; it has no values, defaults, or
persistence behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "settings/registry.json"
MENU_SOURCE = Path(__file__).with_name("menu-definition.json")
DEFAULT_OUT_DIR = Path("build/oem-menu-generated")

# R57 menu: six registry settings directly on the main list, three submenus.
# The Views submenu has broker-backed virtual rows that are not registry keys.
# navigation.url is hidden from the HMI only; it stays in the 48-key registry
# and in the native MIBR/3 scope=ui projection.
EXPECTED_ROOT = (
    "viewarea.selected", "navigation.surface",
    "navigation.ETA", "navigation.speedLimit", "navigation.compass",
    "navigation.maneuver",
)
# CarPlay in the cockpit, frame rate and source version are nested under Advanced.
# under Erweitert, Diagnose reached from Erweitert, Profil hidden in the HMI.
EXPECTED_VISIBLE = {
    "views": set(),
    "advanced": {"carplay.enabled", "maxFPS", "sourceVersion"},
    "diagnostics": set(),
    "version": set(),
}
EXPECTED_GROUPS = ("views", "advanced", "diagnostics", "version")
# Exact native MIBR/3 SNAPSHOT scope=ui row order (row_count=11, the native UI projection).
EXPECTED_NATIVE_UI = (
    "carplay.enabled", "viewarea.selected", "navigation.surface",
    "navigation.ETA", "navigation.speedLimit", "navigation.compass",
    "navigation.maneuver", "navigation.url", "preset.id", "maxFPS", "sourceVersion",
)
EXPECTED_VISIBLE_COUNT = 9
ALLOWED_TOP_FIELDS = {"schema", "target", "title", "root", "sections",
                      "native_ui_keys", "labels"}
LANGUAGES = {"de", "en"}
ALLOWED_SECTION_FIELDS = {"id", "label", "keys"}


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_FIELD: " + key)
        result[key] = value
    return result


def java_string(value):
    return json.dumps(value, ensure_ascii=True)


def array(name, values):
    return " public static final String[] " + name + "={\n  " + ",\n  ".join(
        map(java_string, values)
    ) + "\n };\n"


def widget_kind(setting):
    """Presentation-only kind; never changes canonical validation."""
    key = setting["key"]
    if setting["read_only"] or key == "display.uuid" or (
        "min" in setting and setting.get("min") == setting.get("max")
    ):
        return "STATUS"
    if setting.get("allowed") == ["yes", "no", "user"]:
        return "TRISTATE"
    if key in ("navigation.url", "sourceVersion", "presentation.suggested_urls"):
        return "CHOICE_PENDING_CANONICAL_VALIDATOR"
    if setting["type"] == "enum" or key in (
        "viewarea.selected", "viewareas.initial"
    ) or key.endswith(".adjacent"):
        return "CHOICE"
    if key in (
        "carplay.enabled", "keyframe.showui", "keyframe.gap_recovery",
        "keyframe.latency_recovery",
    ):
        return "TOGGLE"
    if key.startswith("viewarea.") or key.startswith("viewareas."):
        return "BOUNDED_BATCH_NUMBER"
    if setting["type"] == "integer":
        return "BOUNDED_NUMBER"
    return "STATUS"


def validate_menu(menu, keys):
    if not isinstance(menu, dict) or set(menu) != ALLOWED_TOP_FIELDS:
        raise ValueError("MENU_FIELDS_INVALID")
    if type(menu["schema"]) is not int or menu["schema"] != 3:
        raise ValueError("MENU_SCHEMA_INVALID")
    if menu["target"] != "MU1440_SSM_5458":
        raise ValueError("MENU_TARGET_INVALID")
    if not valid_text(menu["title"]):
        raise ValueError("MENU_TITLE_INVALID")

    root = menu["root"]
    if not isinstance(root, list) or tuple(root) != EXPECTED_ROOT:
        raise ValueError("MENU_ROOT_POLICY_INVALID")
    sections = menu["sections"]
    if not isinstance(sections, list) or len(sections) != len(EXPECTED_GROUPS):
        raise ValueError("MENU_GROUP_COUNT_INVALID")
    ids = []
    assigned = []
    for key in root:
        if key not in keys:
            raise ValueError("MENU_UNKNOWN_KEY: " + str(key))
        if key in assigned:
            raise ValueError("MENU_DUPLICATE_KEY: " + key)
        assigned.append(key)
    for section in sections:
        if not isinstance(section, dict) or set(section) != ALLOWED_SECTION_FIELDS:
            raise ValueError("MENU_SECTION_FIELDS_INVALID")
        section_id = section["id"]
        if not isinstance(section_id, str) or section_id in ids:
            raise ValueError("MENU_GROUP_DUPLICATE_OR_INVALID")
        if not valid_text(section["label"]):
            raise ValueError("MENU_GROUP_LABEL_INVALID")
        section_keys = section["keys"]
        if not isinstance(section_keys, list):
            raise ValueError("MENU_GROUP_KEYS_INVALID")
        ids.append(section_id)
        for key in section_keys:
            if not isinstance(key, str) or key not in keys:
                raise ValueError("MENU_UNKNOWN_KEY: " + str(key))
            if key in assigned:
                raise ValueError("MENU_DUPLICATE_KEY: " + key)
            assigned.append(key)

    if tuple(ids) != EXPECTED_GROUPS:
        raise ValueError("MENU_GROUP_SET_OR_ORDER_INVALID")
    if not isinstance(menu["labels"], dict):
        raise ValueError("MENU_LABELS_INVALID")
    label_keys = set(menu["labels"])
    if label_keys != keys:
        raise ValueError("MENU_LABEL_KEY_SET_INVALID")
    if any(not valid_text(label) for label in menu["labels"].values()):
        raise ValueError("MENU_LABEL_VALUE_INVALID")

    for section in sections:
        actual = set(section["keys"])
        if actual != EXPECTED_VISIBLE[section["id"]]:
            raise ValueError("MENU_VISIBILITY_POLICY_INVALID: " + section["id"])
    if len(assigned) != EXPECTED_VISIBLE_COUNT:
        raise ValueError("MENU_VISIBLE_COUNT_INVALID")
    native = menu["native_ui_keys"]
    if not isinstance(native, list) or tuple(native) != EXPECTED_NATIVE_UI:
        raise ValueError("MENU_NATIVE_UI_PROJECTION_INVALID")
    if not set(assigned) <= set(native):
        raise ValueError("MENU_VISIBLE_NOT_IN_NATIVE_PROJECTION")


def valid_text(value):
    """A UI text is a language map with exactly de and en (fallback chain: current -> en)."""
    return (isinstance(value, dict) and set(value) == LANGUAGES and
            all(valid_label(value[lang]) for lang in sorted(LANGUAGES)))


def valid_label(value):
    return (isinstance(value, str) and 0 < len(value) <= 80 and
            all(ord(c) >= 32 and ord(c) != 127 and not 0xD800 <= ord(c) <= 0xDFFF for c in value))


def load_inputs(registry_path, menu_path):
    raw = registry_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    schema = json.loads(raw)
    settings = schema.get("settings")
    if (schema.get("schema") != 2 or not isinstance(settings, list) or
            len(settings) != 48 or
            len({s.get("key") for s in settings if isinstance(s, dict)}) != 48):
        raise ValueError("REGISTRY_SCHEMA_OR_COUNT_CHANGED")
    keys = {setting["key"] for setting in settings}
    menu = json.loads(menu_path.read_text(encoding="utf-8"),
                      object_pairs_hook=reject_duplicate_pairs)
    validate_menu(menu, keys)
    return digest, settings, menu


def render_catalog(settings, menu):
    # Preserve the canonical descriptor order used by the existing generated
    # class. UI group order lives only in MibrMenuDefinition.
    order = {"normal": 0, "advanced": 1, "developer": 2}
    settings = sorted(
        settings,
        key=lambda setting: (
            order[setting["hmi"]],
            0 if setting["key"] == "navigation.url" else 1,
        ),
    )
    visible_by_key = {key: "root" for key in menu["root"]}
    visible_by_key.update({
        key: section["id"]
        for section in menu["sections"]
        for key in section["keys"]
    })
    out = [
        "/* Generated from the canonical registry supplied to this build.",
        " * UI metadata only. Never used to resolve effective values or write files. */\n",
        "package de.mibr.hmi;\npublic final class MibrSettingsCatalog {\n",
        " private MibrSettingsCatalog() {}\n",
    ]
    out.append(array("KEYS", [setting["key"] for setting in settings]))
    for lang in ("de", "en"):
        out.append(array("LABELS_" + lang.upper(),
                         [menu["labels"][setting["key"]][lang] for setting in settings]))
    out.append(" public static String label(int index){return MibrI18n.german()?LABELS_DE[index]:LABELS_EN[index];}\n")
    out.append(array("GROUPS", [setting["hmi"] for setting in settings]))
    out.append(array("APPLY", [setting["apply"] for setting in settings]))
    out.append(array("KINDS", [setting["type"] for setting in settings]))
    out.append(array("CHOICES", ["|".join(setting.get("allowed", [])) for setting in settings]))
    out.append(" public static final boolean[] READ_ONLY={\n  " +
               ", ".join("true" if setting["read_only"] or
                         setting["key"] == "display.uuid" else "false"
                         for setting in settings) + "\n };\n")
    out.append(array("UI_KINDS", [widget_kind(setting) for setting in settings]))
    out.append(array("UI_SECTIONS", [visible_by_key.get(setting["key"], "hidden")
                                      for setting in settings]))
    out.append("}\n")
    return "".join(out)


def render_menu(menu):
    sections = menu["sections"]
    out = [
        "/* Generated from menu-definition.json schema 3. UI navigation metadata only. */\n",
        "package de.mibr.hmi;\npublic final class MibrMenuDefinition {\n",
        " private MibrMenuDefinition() {}\n",
        " public static final String TITLE_DE=" + java_string(menu["title"]["de"]) + ";\n",
        " public static final String TITLE_EN=" + java_string(menu["title"]["en"]) + ";\n",
        " public static String title(){return MibrI18n.german()?TITLE_DE:TITLE_EN;}\n",
        array("ROOT_KEYS", menu["root"]),
        array("GROUP_IDS", [section["id"] for section in sections]),
        array("GROUP_NAMES_DE", [section["label"]["de"] for section in sections]),
        array("GROUP_NAMES_EN", [section["label"]["en"] for section in sections]),
        " public static String[] groupNames(){return MibrI18n.german()?GROUP_NAMES_DE:GROUP_NAMES_EN;}\n",
        " public static final String[][] GROUP_KEYS={\n  " +
        ",\n  ".join("{" + ", ".join(map(java_string, section["keys"])) + "}"
                       for section in sections) + "\n };\n",
        " /** Every HMI-visible key: main list first, then submenus in order. */\n",
        array("VISIBLE_KEYS", menu["root"] + [key for section in sections
                                              for key in section["keys"]]),
        " /** Exact native MIBR/3 SNAPSHOT scope=ui row order; includes HMI-hidden keys. */\n",
        array("NATIVE_UI_KEYS", menu["native_ui_keys"]),
        "}\n",
    ]
    return "".join(out)


def normalized_text(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="compare generated Java sources without writing")
    parser.add_argument("--menu", type=Path, default=MENU_SOURCE,
                        help="UI menu overlay JSON")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help="directory for generated Java sources")
    parser.add_argument("--registry", type=Path, default=SOURCE,
                        help="pinned canonical registry snapshot (test override)")
    args = parser.parse_args(argv)

    try:
        digest, settings, menu = load_inputs(args.registry, args.menu)
        outputs = {
            "MibrSettingsCatalog.java": render_catalog(settings, menu),
            "MibrMenuDefinition.java": render_menu(menu),
        }
        if args.check:
            mismatches = [name for name, expected in outputs.items()
                          if not (args.out_dir / name).is_file() or
                          normalized_text(args.out_dir / name) != expected]
            if mismatches:
                raise ValueError("GENERATED_SOURCE_MISMATCH: " + ",".join(mismatches))
            print("MIBR_CATALOG_CHECK=PASS keys=48 registry=" + digest)
            return 0
        args.out_dir.mkdir(parents=True, exist_ok=True)
        for name, source in outputs.items():
            (args.out_dir / name).write_text(source, encoding="utf-8", newline="\n")
        print("MIBR_CATALOG_GENERATED keys=48 registry=" + digest)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
