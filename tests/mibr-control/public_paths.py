"""Canonical paths for host tests in the curated public repository."""
from pathlib import Path
import json

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[1]
NATIVE = ROOT / "src/native/mibr-control"
DISPLAY_SCALING = ROOT / "src/native/display-scaling"
RUNTIME = ROOT / "runtime/mibr-control"
OEM_MENU = ROOT / "src/hmi/oem-menu"


def write_default_profile(path):
    """Create an isolated host-only profile from the public canonical registry."""
    registry = json.loads((ROOT / "settings/registry.json").read_text(encoding="utf-8"))
    rows = registry["settings"]
    path.write_text("".join(
        f"{row['key']}={row['default']['mibr_legacy']}\n" for row in rows
        if not row["read_only"]
    ), encoding="utf-8")
