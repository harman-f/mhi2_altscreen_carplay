#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic assembler for the MU1440-only modular package ZIP.

Inputs: a directory of native build outputs (mu1440-source/, gen2/,
direct-ts-remux/, support-tools/ ...), the repository modules at a git commit,
and optionally an installer directory and a menu JAR built elsewhere.
Output: ``MIBR-CarPlay/`` ZIP laid out per docs/build/PACKAGE_LAYOUT.md for the
single MU1440 profile. Rebuilding from identical inputs yields identical bytes.

Host-only. Contains no OEM bytes; the menu JAR and the installer are supplied
from outside or the package is marked incomplete and not installable.
"""
import argparse
import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import source_defaults_inventory as inv  # noqa: E402

PREFIX = "MIBR-CarPlay/"
PROFILE = "skoda-mu1440-p4526"
MODULES = ["carplay", "broker", "menu", "navigation"]
# package.json scope field; names kept in one place so they can be aligned with
# tools/validate_modular_package.py.
SCOPE_FIELD = "scope"
SCOPE_VALUE = "single-profile"
COMPLETE_FIELD = "complete"
INSTALLABLE_FIELD = "installable"
MISSING_FIELD = "missing_inputs"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
SCRIPT_SUFFIXES = {".sh", ".ksh"}
APP = "/mnt/app/root/altscreen-u2"
MIBR_V3 = "/mnt/app/root/mibr-v3"
ESO_LIB = "/mnt/app/eso/lib"
README = "INSTALLATION-README.md"
MATRIX = "docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md"


class AssembleError(Exception):
    pass


class MissingInput(AssembleError):
    def __init__(self, items):
        self.items = list(items)
        super().__init__("MISSING_INPUT: " + "; ".join(self.items))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def mode_for(path, data):
    if data[:4] == b"\x7fELF" or Path(path).suffix in SCRIPT_SUFFIXES:
        return 0o755
    return 0o644


# (package path, [native candidates relative to the input dir], payload targets)
NATIVE = [
    ("common/carplay/bin/libaltscreen111.so",
     ["gen2/libaltscreen111.so", "mu1440-source/libaltscreen111.so"],
     [ESO_LIB + "/libmibr_carplay111.so", APP + "/bin/libaltscreen111.so"]),
    ("common/carplay/bin/alt111-settings", ["mu1440-source/alt111-settings"],
     [APP + "/bin/alt111-settings"]),
    ("common/carplay/bin/direct-ts-parity", ["mu1440-source/direct-ts-parity"],
     [APP + "/bin/direct-ts-parity"]),
    ("common/carplay/bin/parity-session", ["mu1440-source/parity-session"],
     [APP + "/bin/parity-session"]),
    ("common/carplay/bin/direct-ts-remux", ["direct-ts-remux/direct-ts-remux"],
     [APP + "/bin/direct-ts-remux"]),
    ("common/carplay/bin/libmibr_isotx2_gate.so", ["mu1440-source/libmibr_isotx2_gate.so"],
     [ESO_LIB + "/libmibr_isotx2_gate.so"]),
    ("common/carplay/bin/libmibr_isotx2_guard.so", ["mu1440-source/libmibr_isotx2_guard.so"],
     [ESO_LIB + "/libmibr_isotx2_guard.so"]),
    ("common/broker/bin/mibr-v3-service",
     ["mu1440-source/mibr-control/mibr-v3-service-QNX65-ARMv7-NOT-INSTALL-READY"],
     [MIBR_V3 + "/bin/mibr-v3-service"]),
    ("common/broker/bin/mibrctl-v3",
     ["mu1440-source/mibr-control/mibrctl-v3-QNX65-ARMv7-NOT-INSTALL-READY"],
     [MIBR_V3 + "/bin/mibrctl-v3"]),
    ("common/broker/bin/mibr-v3-genkey",
     ["mu1440-source/mibr-control/mibr-v3-genkey-QNX65-ARMv7-NOT-INSTALL-READY"],
     [MIBR_V3 + "/bin/mibr-v3-genkey"]),
    ("common/broker/bin/mibr-key40d",
     ["mu1440-source/mibr-control/mibr-key40d-QNX65-ARMv7-NOT-INSTALL-READY"],
     [MIBR_V3 + "/bin/mibr-key40d"]),
    ("installer/bin/sha256sum", ["support-tools/sha256sum"], []),
    ("installer/bin/tee", ["support-tools/tee"], []),
]

BROKER_SCRIPTS = ("mibr-engine.ksh", "mibr-menu.ksh", "mibr-v3-boot.ksh",
                  "mibr-view.ksh", "mibr-watch.ksh")
CARPLAY_RUNTIME = ("auto-direct", "parity", "isotx2-gate")
SCROLL = ("mibr_scroll_thumb.png", "mibr_scroll_thumb_v2.png",
          "mibr_scroll_track.png", "mibr_scroll_track_v2.png")
SUPPORT_JARS = ("artifacts/mu1440/navignore/vehicle-tested-2026-09-27/MIBR-NavIgnore.jar",
                "artifacts/mu1440/most20fps/vehicle-tested-2026-09-29/MIBR-Most20FPS.jar")
EDITOR = ("mibr-menu-editor.html", "MENU_FILE_FORMAT.md", "function-catalog.json",
          "standard-menu.txt")


# ---------------------------------------------------------------- generators
def registry_data(repo):
    registry = inv.registry_inventory(json.loads(inv.read(repo, inv.REGISTRY)))
    broker = inv.broker_inventory(inv.read(repo, inv.BROKER_C), inv.read(repo, inv.BROKER_H))
    return registry, broker


def md_cell(value):
    return str(value).replace("|", "\\|")


def render_matrix(repo, menu_text):
    registry, broker = registry_data(repo)
    menu = inv.menu_inventory(menu_text, json.loads(inv.read(repo, inv.CATALOG)),
                              registry, broker)
    presets = registry["carplay_presets"]
    out = ["# Default configuration matrix", "",
           "Generated from `settings/registry.json`, the broker durable-switch table and the "
           "staged standard menu by `tools/release/build_mu1440_modular.py`. Do not edit by hand.",
           "", "These are **source-defined defaults**. They are not an effective unit state and "
           "not evidence of completed vehicle tests. Persisted overrides on a unit take "
           "precedence in the order: " + " > ".join(registry["layer_order"]) + ".", "",
           "## CarPlay registry (%d settings)" % len(registry["settings"]), "",
           "| Key | Storage file | Field | Type | Apply | " + " | ".join(presets) + " |",
           "|---|---|---|---|---|" + "---|" * len(presets)]
    for s in registry["settings"]:
        out.append("| %s | %s | %s | %s | %s | %s |" % (
            md_cell(s["key"]), md_cell(s["current_basename"]), md_cell(s["field"] or "-"),
            md_cell(s["data_type"]), md_cell(s["apply"]),
            " | ".join("`%s`" % md_cell(s["defaults_by_carplay_preset"][p]) for p in presets)))
    out += ["", "## Broker durable switches (%d)" % len(broker["switches"]), "",
            "Storage root `%s`; platform override `%s`." % (broker["current_root"],
                                                          broker["platform_override"]), "",
            "| Capability | Allowed | Compiled default | File |", "|---|---|---|---|"]
    for s in broker["switches"]:
        out.append("| %s | %s | `%s` | `%s` |" % (
            md_cell(s["key"]), md_cell("|".join(s["allowed"]) if s["allowed"] else "rectangle"),
            md_cell(s["compiled_default"]), md_cell(s["current_path"])))
    out += ["", "## Menu (brand `%s`, %d layout entries)" % (menu["brand_hint"], menu["layout_entries"]),
            "", "Menu presence, actions and aliases are not default values.", "",
            "Menu entries bound directly to CarPlay registry keys: %d. Bound to broker "
            "switches: %d." % (len(menu["direct_carplay_bindings"]), len(menu["direct_broker_bindings"])),
            "", "Menu-only entries (no direct registry key):", ""]
    out += ["- `%s`" % e for e in menu["other_menu_ids_no_direct_registry_key"]]
    return "\n".join(out) + "\n"


def default_of(registry, key, preset=None):
    for s in registry["settings"]:
        if s["key"] == key:
            d = s["defaults_by_carplay_preset"]
            return "/".join(dict.fromkeys(d.values())) if preset is None else d[preset]
    raise AssembleError("registry key missing: " + key)


def render_readme(repo, menu_text, complete):
    registry, broker = registry_data(repo)
    menu = inv.menu_inventory(menu_text, json.loads(inv.read(repo, inv.CATALOG)),
                              registry, broker)
    sw = {s["key"]: s["compiled_default"] for s in broker["switches"]}
    presets = ", ".join(registry["carplay_presets"])
    rows = [
        ("CarPlay video", "enabled `%s`, max FPS `%s` (per preset), source version `%s`" % (
            default_of(registry, "carplay.enabled"), default_of(registry, "maxFPS"),
            default_of(registry, "sourceVersion"))),
        ("Phone-route arrows", "broker `carplay_nav` = `%s`" % sw.get("carplay_nav", "n/a")),
        ("Arrow source / placement", "source `%s`, display `%s`, nav line `%s`, night `%s`" % (
            sw.get("nav_source", "n/a"), sw.get("nav_display", "n/a"),
            sw.get("nav_line", "n/a"), sw.get("nav_night", "n/a"))),
        ("View / presentation", "view areas `%s` (per preset), URL `%s`" % (
            default_of(registry, "viewareas.count"), default_of(registry, "navigation.url"))),
        ("Navigation composition", "surface `%s`, ETA `%s`, speed limit `%s`, compass `%s`, "
         "maneuver `%s`" % (default_of(registry, "navigation.surface"),
                            default_of(registry, "navigation.ETA"),
                            default_of(registry, "navigation.speedLimit"),
                            default_of(registry, "navigation.compass"),
                            default_of(registry, "navigation.maneuver"))),
        ("Auto-Direct", "legacy auto-direct `%s` (0 = off); shipped as legacy, not activated" %
         default_of(registry, "legacy.autodirect")),
        ("D2 (keyframes)", "mode `%s`, interval frames `%s`, ms `%s`" % (
            default_of(registry, "keyframe.mode"), default_of(registry, "keyframe.interval_frames"),
            default_of(registry, "keyframe.interval_ms"))),
        ("Diagnostics", "SD log `%s`" % sw.get("sd_log", "n/a")),
        ("Menu brand", "`%s` (standard menu)" % menu["brand_hint"]),
    ]
    out = ["# MIBR CarPlay - MU1440 installation README", ""]
    if not complete:
        out += ["> **INCOMPLETE PACKAGE - NOT INSTALLABLE.** Required inputs are missing; see "
                "`package.json` field `%s`. Do not install." % MISSING_FIELD, ""]
    out += ["Profile: `%s` (single-profile MU1440 developer package, scope `%s`)." % (
        PROFILE, SCOPE_VALUE), "",
        "The profile is selected by exact SHA-256 match of `/ifs/lsd.jxe` against "
        "`installer/config/profiles.list`; an unknown hash stops the installer.", "",
        "## Packaged defaults (source-defined, per preset where marked)", "",
        "CarPlay presets: %s." % presets, "", "| Area | Packaged default |", "|---|---|"]
    out += ["| %s | %s |" % (a, md_cell(v)) for a, v in rows]
    out += ["", "Full inventory: `%s`. These describe packaged sources only; they do not prove "
            "an active unit state or completed vehicle tests." % MATRIX, "",
            "## Install / check / uninstall", "",
            "Run `installer/check.ksh` first (read-only), then `installer/install.ksh`, then "
            "restart the head unit normally. `installer/uninstall.ksh` restores backed-up files. "
            "Copy the package to an SD card as a whole; do not run single files.", "",
            "## Recovery", "",
            "Uninstall via `installer/uninstall.ksh`. The boot guard kill switch is the file "
            "`/mnt/app/root/mibr-kit/disabled`.", "",
            "## Not included", "",
            "OEM firmware files, OEM icons, the menu JAR when built outside this package, RGI "
            "binaries and the boot probe JAR. Source coverage is PARTIAL "
            "(`source/SOURCE_MANIFEST.json`).", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ assembly
def read_repo_file(repo, rel, files, prov, pkg_path, mode=None):
    data = (repo / rel).read_bytes()
    add(files, prov, pkg_path, data, {"origin": "repo", "repo_path": rel,
                                      "git_blob": git(repo, "hash-object", rel)}, mode)


def add(files, prov, path, data, origin, mode=None):
    if path in files:
        raise AssembleError("duplicate package path: " + path)
    files[path] = (data, mode if mode is not None else mode_for(path, data))
    prov[path] = dict(origin, sha256=sha(data))


def verify_native_sums(native):
    """Cross-check mu1440-source/SHA256SUMS against the files when present."""
    sums = native / "mu1440-source" / "SHA256SUMS"
    if not sums.is_file():
        return
    for line in sums.read_text().splitlines():
        digest, _, name = line.partition("  ")
        target = native / "mu1440-source" / name.removeprefix("./")
        if name and target.is_file() and sha(target.read_bytes()) != digest:
            raise AssembleError("native input differs from its SHA256SUMS: " + name)


def native_commit(native):
    for base in (native, native.parent):
        f = base / "SOURCE_COMMIT.txt"
        if f.is_file():
            return f.read_text().split()[0] if f.read_text().strip() else None
    return None


def assemble(native, repo=ROOT, installer=None, menu_jar=None, allow_incomplete=False,
             allow_dirty=False):
    """Return (zip entries {name: (bytes, mode)}, package metadata)."""
    native, repo = Path(native), Path(repo)
    if not native.is_dir():
        raise AssembleError("native input directory not found")
    dirty = bool(git(repo, "status", "--porcelain", "--untracked-files=no"))
    if dirty and not allow_dirty:
        raise AssembleError("repository has uncommitted tracked changes (use --allow-dirty)")
    verify_native_sums(native)
    files, prov, missing, hard = {}, {}, [], []
    manifest, profile_manifest = [], []

    for pkg, candidates, targets in NATIVE:
        found = next((native / c for c in candidates if (native / c).is_file()), None)
        if found is None:
            hard.append("native output " + candidates[0])
            continue
        data = found.read_bytes()
        add(files, prov, pkg, data, {"origin": "native",
                                     "input": found.relative_to(native).as_posix()})
        for t in targets:
            manifest.append((sha(data), "%o" % mode_for(pkg, data), t, pkg))
    if hard:
        raise MissingInput(hard)

    for rdir in CARPLAY_RUNTIME:
        for p in sorted((repo / "modules/carplay/runtime" / rdir).glob("*.sh")):
            rel = p.relative_to(repo).as_posix()
            if rel not in git(repo, "ls-files", rel).split("\n"):
                continue
            read_repo_file(repo, rel, files, prov, "common/carplay/scripts/" + p.name)
            manifest.append((sha(p.read_bytes()), "755", APP + "/scripts/" + p.name,
                             "common/carplay/scripts/" + p.name))
    read_repo_file(repo, "modules/carplay/runtime/auto-direct/altscreen111.conf", files, prov,
                   "common/carplay/config/altscreen111.conf")
    manifest.append((sha(files["common/carplay/config/altscreen111.conf"][0]), "644",
                     APP + "/config/altscreen111.conf", "common/carplay/config/altscreen111.conf"))
    for name in BROKER_SCRIPTS:
        pkg = "common/broker/scripts/" + name
        read_repo_file(repo, "modules/broker/runtime/mibr-control/" + name, files, prov, pkg)
        manifest.append((sha(files[pkg][0]), "755", MIBR_V3 + "/" + name, pkg))
    read_repo_file(repo, "tools/menu-editor/standard-menu.txt", files, prov,
                   "common/menu/config/mibr-menu.conf")
    manifest.append((sha(files["common/menu/config/mibr-menu.conf"][0]), "644",
                     APP + "/config/mibr-menu.conf", "common/menu/config/mibr-menu.conf"))
    for name in SCROLL:
        read_repo_file(repo, "modules/menu/source/assets/scroll/" + name, files, prov,
                       "common/menu/icons/" + name)
    for rel in SUPPORT_JARS:
        read_repo_file(repo, rel, files, prov, "common/menu/bin/" + Path(rel).name)
    for name in ("gen2_nav_config.sh", "gen2_safearea.sh"):
        read_repo_file(repo, "modules/navigation/runtime/" + name, files, prov,
                       "common/navigation/scripts/" + name)
    read_repo_file(repo, "modules/navigation/source/platform-defaults/skoda-mu1440.conf", files,
                   prov, "profiles/%s/display/mibr-platform-defaults.conf" % PROFILE)
    pdata = files["profiles/%s/display/mibr-platform-defaults.conf" % PROFILE][0]
    profile_manifest.append((sha(pdata), "644", inv.broker_inventory(
        inv.read(repo, inv.BROKER_C), inv.read(repo, inv.BROKER_H))["platform_override"],
        "profiles/%s/display/mibr-platform-defaults.conf" % PROFILE))
    for name in EDITOR:
        read_repo_file(repo, "tools/menu-editor/" + name, files, prov, "tools/menu-editor/" + name)
    read_repo_file(repo, "tools/validate_modular_package.py", files, prov,
                   "tools/package/validate_modular_package.py")
    for rel, pkg in (("LICENSE", "docs/LICENSE"), ("THIRD_PARTY_NOTICES.md", "docs/THIRD_PARTY_NOTICES.md"),
                     ("THIRD_PARTY/NavIgnore/LICENSE-MIT.txt", "docs/third_party/NavIgnore-LICENSE-MIT.txt"),
                     ("THIRD_PARTY/Most20FPS/LICENSE-MIT.txt", "docs/third_party/Most20FPS-LICENSE-MIT.txt")):
        read_repo_file(repo, rel, files, prov, pkg)
    src_rows = []
    for rel in git(repo, "ls-files", "modules/menu/source").split("\n"):
        pkg = "source/hmi/" + rel[len("modules/menu/source/"):]
        read_repo_file(repo, rel, files, prov, pkg)
        src_rows.append(pkg)

    # profile groups (text only, no OEM bytes)
    root = "profiles/%s/" % PROFILE
    gen = lambda p, text: add(files, prov, p, text.encode(), {"origin": "generated"})  # noqa: E731
    gen(root + "hmi/BUILD-ON-PC.md",
        "# Menu JAR build\n\nThe HMI JAR derives from OEM classes and is built locally on a "
        "machine holding the firmware (see `source/hmi/README.md`). Supply it to the assembler "
        "with `--menu-jar`.\n")
    gen(root + "hmi/expected-inputs.json", json.dumps(
        {"jar": "MIBR-CarPlay.jar", "source": "source/hmi", "oem_derived": True},
        indent=2, sort_keys=True) + "\n")
    gen(root + "icons/README.md", "OEM-derived icons are not included. The installer requires "
        "the icons already present on the unit.\n")
    gen(root + "input/README.md", "Profile input mapping: no profile-specific data in this "
        "package revision.\n")
    gen(root + "integration/README.md", "OEM file transformations (smartphone integrator, "
        "startup preload, Lua) are supplied by the installer; no OEM bytes are shipped.\n")
    gen(root + "integration/variants.list", "# target stock-sha expected-patched-sha "
        "transform-file mode (no entries in this package revision)\n")
    gen(root + "payload.manifest", "# sha256 mode target source\n" + "".join(
        "%s %s %s %s\n" % row for row in sorted(profile_manifest, key=lambda r: r[2])))
    gen("installer/config/profiles.list", "# profile selector (sha256 of /ifs/lsd.jxe)\n"
        "%s %s\n" % (PROFILE, json.loads(inv.read(
            repo, "modules/profiles/%s/profile.json" % PROFILE))["selector"]["digest"]))
    gen("installer/config/payload.manifest", "# sha256 mode target source\n" + "".join(
        "%s %s %s %s\n" % row for row in sorted(manifest, key=lambda r: (r[2], r[3]))))

    # externally supplied inputs
    if installer is not None and (Path(installer) / "mibr-kit.ksh").is_file():
        base = Path(installer)
        for p in sorted(x for x in base.rglob("*") if x.is_file()):
            rel = p.relative_to(base).as_posix()
            pkg = "installer/" + rel
            if pkg in files:
                continue  # generated config and bundled tools take precedence
            add(files, prov, pkg, p.read_bytes(), {"origin": "installer-input", "input": rel})
        for mode in ("install", "check", "uninstall", "status"):
            pkg = "installer/%s.ksh" % mode
            if pkg not in files:
                gen(pkg, '#!/bin/ksh\nD=${0%%/*}\nexec ksh "$D/mibr-kit.ksh" %s "$@"\n' % mode)
    else:
        missing.append("installer/mibr-kit.ksh")
    if menu_jar is not None and Path(menu_jar).is_file():
        add(files, prov, root + "hmi/MIBR-CarPlay.jar", Path(menu_jar).read_bytes(),
            {"origin": "menu-jar-input"})
    else:
        missing.append(root + "hmi/MIBR-CarPlay.jar")
    if missing and not allow_incomplete:
        raise MissingInput(missing)
    complete = not missing
    for m in missing:
        holder = "installer/MISSING_INPUT.txt" if m.startswith("installer/") else \
            root + "hmi/MISSING_INPUT.txt"
        prior = files[holder][0].decode() if holder in files else ""
        files.pop(holder, None)
        prov.pop(holder, None)
        gen(holder, prior + "MISSING_INPUT: %s\n" % m)

    menu_text = files["common/menu/config/mibr-menu.conf"][0].decode()
    gen(README, render_readme(repo, menu_text, complete))
    gen(MATRIX, render_matrix(repo, menu_text))

    source = {
        "coverage": "PARTIAL",
        "repo": {"commit": git(repo, "rev-parse", "HEAD"),
                 "tree": git(repo, "rev-parse", "HEAD^{tree}"), "dirty": dirty},
        "native_build_source_commit": native_commit(native),
        "files": [{"path": p, "sha256": prov[p]["sha256"]} for p in sorted(src_rows)],
        "inputs": [dict(path=p, **{k: v for k, v in prov[p].items()}) for p in sorted(prov)
                   if prov[p]["origin"] != "generated"],
        "gaps": ["OEM, QNX, JDK and third-party dependencies are not included",
                 "native binaries are listed with input hashes; their build commit may differ "
                 "from the repo commit",
                 "broker service outputs are renamed from the NOT-INSTALL-READY build names"],
    }
    gen("source/SOURCE_MANIFEST.json", json.dumps(source, indent=2, sort_keys=True) + "\n")
    meta = {
        "schema": 1, "package": "MIBR-CarPlay", SCOPE_FIELD: SCOPE_VALUE,
        "profiles": [PROFILE], "modules": MODULES,
        COMPLETE_FIELD: complete, INSTALLABLE_FIELD: complete, MISSING_FIELD: sorted(missing),
        "source": source["repo"],
        "profiles_list_sha256": sha(files["installer/config/profiles.list"][0]),
        "files": [{"path": p, "sha256": sha(files[p][0]), "mode": "%04o" % files[p][1],
                   "size": len(files[p][0])} for p in sorted(files)],
    }
    files["package.json"] = (json.dumps(meta, indent=2, sort_keys=True).encode() + b"\n", 0o644)
    files["PACKAGE.sha256"] = ("".join("%s  %s\n" % (sha(d), n) for n, (d, _) in sorted(files.items())
                                       ).encode(), 0o644)
    return files, meta


def write_zip(files, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(files):
            data, mode = files[name]
            info = zipfile.ZipInfo(PREFIX + name, ZIP_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | mode) << 16
            z.writestr(info, data, compresslevel=9)
    return sha(out.read_bytes())


def load_zip(path):
    with zipfile.ZipFile(path) as z:
        return {i.filename[len(PREFIX):]: z.read(i) for i in z.infolist()
                if i.filename.startswith(PREFIX) and not i.filename.endswith("/")}


def check_docs(files, repo=ROOT):
    """Return drift messages; empty list means README/matrix match the sources."""
    problems = []
    try:
        meta = json.loads(files["package.json"])
        menu = files["common/menu/config/mibr-menu.conf"].decode()
        if menu != inv.read(Path(repo), inv.MENU):
            problems.append("staged menu differs from tools/menu-editor/standard-menu.txt")
        wanted = {README: render_readme(Path(repo), menu, bool(meta[COMPLETE_FIELD])),
                  MATRIX: render_matrix(Path(repo), menu)}
    except (KeyError, ValueError) as exc:
        return ["cannot check package: %r" % (exc,)]
    for name, text in wanted.items():
        if name not in files:
            problems.append("missing " + name)
        elif files[name].decode() != text:
            problems.append("drift: " + name)
    return problems


# ---------------------------------------------------------------- self-test
def fake_native(base):
    for rel in ("gen2/libaltscreen111.so", "mu1440-source/alt111-settings",
                "mu1440-source/direct-ts-parity", "mu1440-source/parity-session",
                "mu1440-source/libmibr_isotx2_gate.so", "mu1440-source/libmibr_isotx2_guard.so",
                "direct-ts-remux/direct-ts-remux", "support-tools/sha256sum", "support-tools/tee"):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF" + rel.encode())
    for n in ("mibr-v3-service", "mibrctl-v3", "mibr-v3-genkey", "mibr-key40d"):
        p = base / ("mu1440-source/mibr-control/%s-QNX65-ARMv7-NOT-INSTALL-READY" % n)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF" + n.encode())


def raises(exc, fn):
    try:
        fn()
    except exc as e:
        return e
    raise AssertionError("expected " + exc.__name__)


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        native = tmp / "bin"
        fake_native(native)
        inst = tmp / "inst"
        inst.mkdir()
        (inst / "mibr-kit.ksh").write_text("PROFILES_SHA=x\n")
        jar = tmp / "m.jar"
        jar.write_bytes(b"PK jar")
        kw = dict(allow_dirty=True)
        # determinism
        a, _ = assemble(native, installer=inst, menu_jar=jar, **kw)
        b, _ = assemble(native, installer=inst, menu_jar=jar, **kw)
        ha, hb = write_zip(a, tmp / "a.zip"), write_zip(b, tmp / "sub/b.zip")
        assert ha == hb and (tmp / "a.zip").read_bytes() == (tmp / "sub/b.zip").read_bytes()
        meta = json.loads(a["package.json"][0])
        assert meta[COMPLETE_FIELD] and meta[INSTALLABLE_FIELD] and meta[MISSING_FIELD] == []
        assert meta[SCOPE_FIELD] == SCOPE_VALUE and meta["profiles"] == [PROFILE]
        # modes and hash coverage
        with zipfile.ZipFile(tmp / "a.zip") as z:
            for i in z.infolist():
                m = (i.external_attr >> 16) & 0o777
                assert i.date_time == ZIP_TIME and i.filename.startswith(PREFIX)
                if i.filename.endswith((".so", ".ksh", ".sh")) or "/bin/" in i.filename \
                        and not i.filename.endswith(".jar"):
                    assert m == 0o755, i.filename
                else:
                    assert m == 0o644, i.filename
            assert [i.filename for i in z.infolist()] == sorted(i.filename for i in z.infolist())
        files = load_zip(tmp / "a.zip")
        rows = dict(l.split("  ", 1)[::-1] for l in files["PACKAGE.sha256"].decode().splitlines())
        assert set(rows) == set(files) - {"PACKAGE.sha256"}
        assert all(sha(files[n]) == d for n, d in rows.items())
        assert check_docs(files) == []
        # matrix / README drift detection
        bad = dict(files)
        bad[MATRIX] = files[MATRIX].replace(b"`40`", b"`41`", 1)
        assert bad[MATRIX] != files[MATRIX] and check_docs(bad) == ["drift: " + MATRIX]
        bad = dict(files)
        bad[README] = files[README] + b"extra\n"
        assert check_docs(bad) == ["drift: " + README]
        bad = dict(files)
        bad["common/menu/config/mibr-menu.conf"] = files["common/menu/config/mibr-menu.conf"].replace(
            b"brand=skoda", b"brand=other")
        assert any("staged menu differs" in p for p in check_docs(bad))
        # missing installer / jar: explicit failure, then incomplete package
        e = raises(MissingInput, lambda: assemble(native, **kw))
        assert "installer/mibr-kit.ksh" in e.items and any(i.endswith("MIBR-CarPlay.jar") for i in e.items)
        inc, im = assemble(native, allow_incomplete=True, **kw)
        assert im[COMPLETE_FIELD] is False and im[INSTALLABLE_FIELD] is False and len(im[MISSING_FIELD]) == 2
        assert "installer/mibr-kit.ksh" not in inc and "installer/MISSING_INPUT.txt" in inc
        assert b"INCOMPLETE PACKAGE" in inc[README][0] and check_docs({k: v[0] for k, v in inc.items()}) == []
        # missing native binary fails even with --allow-incomplete
        (native / "mu1440-source/parity-session").unlink()
        e = raises(MissingInput, lambda: assemble(native, installer=inst, menu_jar=jar,
                                                  allow_incomplete=True, **kw))
        assert any("mu1440-source/parity-session" in i for i in e.items)
        # tampered native input vs SHA256SUMS
        fake_native(native)
        (native / "mu1440-source/SHA256SUMS").write_text("%s  ./alt111-settings\n" % ("0" * 64))
        raises(AssembleError, lambda: assemble(native, installer=inst, menu_jar=jar, **kw))
    print("BUILD_MU1440_MODULAR_SELF_TEST=PASS")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native-dir", type=Path, help="directory of native build outputs")
    ap.add_argument("--out", type=Path, help="output ZIP path")
    ap.add_argument("--repo", type=Path, default=ROOT)
    ap.add_argument("--installer-dir", type=Path, help="directory holding mibr-kit.ksh")
    ap.add_argument("--menu-jar", type=Path, help="locally built MIBR-CarPlay.jar")
    ap.add_argument("--allow-incomplete", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--check", type=Path, metavar="ZIP",
                    help="fail if README/matrix in ZIP drift from registry and inventory")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.check:
        problems = check_docs(load_zip(args.check), args.repo)
        for p in problems:
            print("DOCS_DRIFT: " + p, file=sys.stderr)
        print("MU1440_DOCS_CHECK=" + ("FAIL" if problems else "PASS"))
        sys.exit(1 if problems else 0)
    if not args.native_dir or not args.out:
        ap.error("--native-dir and --out are required")
    try:
        files, meta = assemble(args.native_dir, args.repo, args.installer_dir, args.menu_jar,
                               args.allow_incomplete, args.allow_dirty)
    except MissingInput as exc:
        for item in exc.items:
            print("MISSING_INPUT: " + item, file=sys.stderr)
        sys.exit(2)
    except AssembleError as exc:
        print("ASSEMBLE_FAIL: %s" % exc, file=sys.stderr)
        sys.exit(1)
    digest = write_zip(files, args.out)
    print("MU1440_PACKAGE=%s files=%d complete=%s installable=%s zip_sha256=%s" % (
        "PASS" if meta[COMPLETE_FIELD] else "INCOMPLETE", len(files),
        str(meta[COMPLETE_FIELD]).lower(), str(meta[INSTALLABLE_FIELD]).lower(), digest))


if __name__ == "__main__":
    main()
