#!/usr/bin/env python3
"""Patch two caller-supplied OEM source files in a private build directory.

The inputs are not distributed. Each patch is guarded by exact unique anchors,
read as data from modules/profiles/<id>/hmi/oem-anchors.json; source drift fails
closed instead of producing a partial replacement.
"""
import argparse
import json
from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise ValueError(label + "_ANCHOR_COUNT=" + str(count))
    return text.replace(old, new, 1)


DEFAULT_PROFILE = "skoda-mu1440-p4526"
PROFILES_DIR = Path(__file__).resolve().parents[2] / "profiles"
_CACHE = {}


def load_anchors(profile=DEFAULT_PROFILE, profiles_dir=None):
    """Anchor set (data) of one profile: modules/profiles/<id>/hmi/oem-anchors.json.

    A profile may reuse another profile's anchors with "anchors_from".
    """
    base = Path(profiles_dir) if profiles_dir else PROFILES_DIR
    key = (str(base), profile)
    if key in _CACHE:
        return _CACHE[key]
    seen = []
    name = profile
    while True:
        if name in seen or "/" in name or "\\" in name or name.startswith("."):
            raise ValueError("PROFILE_ANCHORS_INVALID=" + name)
        seen.append(name)
        path = base / name / "hmi" / "oem-anchors.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ValueError("PROFILE_ANCHORS_MISSING=" + name)
        if "anchors_from" not in data:
            break
        name = data["anchors_from"]
    _CACHE[key] = data
    return data


def apply_anchor_set(text, spec, already_patched_label):
    """Apply guarded exact-anchor edits; every anchor must occur exactly once."""
    for marker in spec["already_patched_markers"]:
        if marker in text:
            raise ValueError(already_patched_label)
    for edit in spec["edits"]:
        text = replace_once(text, edit["old"], edit["new"], edit["label"])
    return text


def patch_activator(text, anchors=None):
    anchors = anchors or load_anchors()
    return apply_anchor_set(text, anchors["activator"], "ACTIVATOR_ALREADY_PATCHED")


def patch_widget_factory(text, anchors=None):
    anchors = anchors or load_anchors()
    return apply_anchor_set(text, anchors["widget_factory"], "WIDGET_FACTORY_ALREADY_PATCHED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activator", required=True, type=Path,
                        help="local source for the target CIO Activator")
    parser.add_argument("--widget-factory", required=True, type=Path,
                        help="local source for the target WidgetFactoryImpl")
    parser.add_argument("--out-dir", required=True, type=Path,
                        help="private generated-source directory")
    parser.add_argument("--profile", default=DEFAULT_PROFILE,
                        help="profile id whose hmi/oem-anchors.json is applied")
    args = parser.parse_args()
    try:
        anchors = load_anchors(args.profile)
        activator = args.activator.read_text(encoding="utf-8").replace("\r\n", "\n")
        widget = args.widget_factory.read_text(encoding="utf-8").replace("\r\n", "\n")
        activator = patch_activator(activator, anchors)
        widget = patch_widget_factory(widget, anchors)
        a_path = args.out_dir / "de/vw/mib/cio/internal/Activator.java"
        w_path = args.out_dir / "generated/de/vw/mib/global/view/internal/WidgetFactoryImpl.java"
        a_path.parent.mkdir(parents=True, exist_ok=True)
        w_path.parent.mkdir(parents=True, exist_ok=True)
        a_path.write_text(activator, encoding="utf-8", newline="\n")
        w_path.write_text(widget, encoding="utf-8", newline="\n")
        print(anchors.get("pass_label", "OEM_SOURCE_PATCH") + "=PASS inputs=2 outputs=private-build-only")
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
