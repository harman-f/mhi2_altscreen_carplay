#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic assembler for the modular MIBR-CarPlay package ZIP.

Default: ONE three-profile beta package (Skoda MU1440 P4526, SEAT MU1409 P4708,
SEAT MU1447 P4709). ``--profiles X --scope single-profile`` builds a
single-profile package for explicit test use only.

Inputs
  --native-dir  build-output layout: bin/mu1440-source, bin/gen2, bin/support-tools,
                bin/direct-ts-remux plus SOURCE_COMMIT.txt, COMPILER.txt and
                IMAGE_SOURCE.txt at its root (recorded as provenance).
  --hmi-dir     <dir>/<profile_id>/MIBR-CarPlay.jar per profile (OEM-derived,
                built elsewhere). Absent -> MISSING_INPUT, package "incomplete".
  --installer-dir  defaults to <repo>/installer; mibr-install.ksh,
                mibr-uninstall.ksh and mibr-status.ksh are required inputs
                (MISSING_INPUT when absent).
  Profiles come from modules/profiles/*/profile.json via tools/check_profiles.py.

Rebuilt binaries are recorded as ``SOURCE_BUILD_PASS`` (never vehicle-tested).
The only name change applied to a native output is the explicit RENAME table
below (strips the ``-QNX65-ARMv7-NOT-INSTALL-READY`` build suffix); each
renamed binary keeps its original name in package.json ``renamed_from``.

Determinism: sorted entries, fixed timestamp, modes from mode_for(). Host-only.
Contains no OEM bytes.
"""
import argparse
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERSION_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._+-")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import source_defaults_inventory as inv  # noqa: E402
import check_profiles  # noqa: E402
import generate_profiles_list  # noqa: E402

PREFIX = "MIBR-CarPlay/"
MODULES = ["carplay", "broker", "menu", "navigation"]
SCOPE_VALUE = "single-profile"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
SCRIPT_SUFFIXES = {".sh", ".ksh"}
APP = "/mnt/app/root/mibr"  # the single MIB Runtime root (M1)
ESO_LIB = "/mnt/app/eso/lib"
README = "INSTALLATION-README.md"
MATRIX = "docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md"
GROUPS = ("hmi", "icons", "display", "input", "integration")
REQUIRED_INSTALLER = ("mibr-install.ksh", "mibr-uninstall.ksh", "mibr-status.ksh")
PROVENANCE_FILES = (("source_commit", "SOURCE_COMMIT.txt"), ("compiler", "COMPILER.txt"),
                    ("image_source", "IMAGE_SOURCE.txt"))
BUILD_SUFFIX = "-QNX65-ARMv7-NOT-INSTALL-READY"
# Explicit rename table: native output name -> package name. Nothing else is renamed.
RENAME = {
    "mibr-v3-service" + BUILD_SUFFIX: "mibr-v3-service",
    "mibrctl-v3" + BUILD_SUFFIX: "mibrctl-v3",
    "mibr-v3-genkey" + BUILD_SUFFIX: "mibr-v3-genkey",
    "mibr-key40d" + BUILD_SUFFIX: "mibr-key40d",
}
STATUS_BINARY = "SOURCE_BUILD_PASS"


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
    """Mode table: executable for ELF, shell scripts and files under a bin/ directory
    (except JARs); everything else 0644."""
    parts = path.split("/")
    if data[:4] == b"\x7fELF" or Path(path).suffix in SCRIPT_SUFFIXES:
        return 0o755
    if "bin" in parts[:-1] and not path.endswith(".jar"):
        return 0o755
    return 0o644


def rename_native(name):
    """Package name of a native output: only names in RENAME change."""
    return RENAME.get(name, name)


# (package path, [native candidates relative to --native-dir], payload targets)
N = "bin/"
NATIVE = [
    ("common/carplay/bin/libaltscreen111.so",
     [N + "gen2/libaltscreen111.so", N + "mu1440-source/libaltscreen111.so"],
     [ESO_LIB + "/libmibr_carplay111.so", APP + "/bin/libaltscreen111.so"]),
    ("common/carplay/bin/alt111-settings", [N + "mu1440-source/alt111-settings"],
     [APP + "/bin/alt111-settings"]),
    ("common/carplay/bin/direct-ts-parity", [N + "mu1440-source/direct-ts-parity"],
     [APP + "/bin/direct-ts-parity"]),
    ("common/carplay/bin/parity-session", [N + "mu1440-source/parity-session"],
     [APP + "/bin/parity-session"]),
    ("common/carplay/bin/direct-ts-remux", [N + "direct-ts-remux/direct-ts-remux"],
     [APP + "/bin/direct-ts-remux"]),
    ("common/carplay/bin/libmibr_isotx2_gate.so", [N + "mu1440-source/libmibr_isotx2_gate.so"],
     [ESO_LIB + "/libmibr_isotx2_gate.so"]),
    ("common/carplay/bin/libmibr_isotx2_guard.so", [N + "mu1440-source/libmibr_isotx2_guard.so"],
     [ESO_LIB + "/libmibr_isotx2_guard.so"]),
    ("common/broker/bin/mibr-v3-service",
     [N + "mu1440-source/mibr-control/mibr-v3-service" + BUILD_SUFFIX], [APP + "/bin/mibr-v3-service"]),
    ("common/broker/bin/mibrctl-v3",
     [N + "mu1440-source/mibr-control/mibrctl-v3" + BUILD_SUFFIX], [APP + "/bin/mibrctl-v3"]),
    ("common/broker/bin/mibr-v3-genkey",
     [N + "mu1440-source/mibr-control/mibr-v3-genkey" + BUILD_SUFFIX], [APP + "/bin/mibr-v3-genkey"]),
    ("common/broker/bin/mibr-key40d",
     [N + "mu1440-source/mibr-control/mibr-key40d" + BUILD_SUFFIX], [APP + "/bin/mibr-key40d"]),
    # route guidance (RGI): modules/navigation/source/build.sh (clang/lld + MU1440 libiap2client.so.1).
    # mm-ipod-rgi (repo script) preloads the library and starts the helper from $APP/bin.
    ("common/navigation/bin/libmibr_rgi_ipod.so", [N + "navigation/libmibr_rgi_ipod.so"],
     [APP + "/bin/libmibr_rgi_ipod.so"]),
    ("common/navigation/bin/mibr-rgi", [N + "navigation/mibr-rgi"], [APP + "/bin/mibr-rgi"]),
    # calibration clip read by GEN2 from $APP/bin (navigation/source/tools/make_calib_clip.py output)
    ("common/navigation/assets/mibr-calib.avcc", [N + "navigation/mibr-calib.avcc"],
     [APP + "/bin/mibr-calib.avcc"]),
    # host-side helpers used by the installer before anything is deployed
    # also installed: the runtime (carplay/auto-direct common.sh) runs $BASE/bin/sha256sum and tee
    ("common/bin/sha256sum", [N + "support-tools/sha256sum"], [APP + "/bin/sha256sum"]),
    ("common/bin/tee", [N + "support-tools/tee"], [APP + "/bin/tee"]),
]

# boot.ksh / boot-guard.ksh are called by the lsd.sh block (installer/config/lsd-block.txt).
BROKER_SCRIPTS = ("boot.ksh", "boot-guard.ksh", "mibr-engine.ksh", "mibr-menu.ksh", "mibr-v3-boot.ksh",
                  "mibr-view.ksh", "mibr-watch.ksh")
# cpvc holds cpvc_config.sh, called by boot.ksh.
CARPLAY_RUNTIME = ("auto-direct", "parity", "isotx2-gate", "cpvc")
# The boot classpath of the lsd.sh block loads these from $BASE_DIR/lsd/jars.
LSD_JARS = "/mnt/app/eso/hmi/lsd/jars/"
# Own (non-OEM) J9 JAR built with the menu toolchain: <hmi-dir>/common/<name>.
EXTENDER_JAR = "MIBR-Extender-P1-BootProbe.jar"
SCROLL = ("mibr_scroll_thumb.png", "mibr_scroll_thumb_v2.png",
          "mibr_scroll_track.png", "mibr_scroll_track_v2.png")
# Versioned binaries come from the protected, SHA-pinned HMI staging root.
# Historical vehicle-test copies in artifacts/ are reference evidence only.
SUPPORT_JARS = ("MIBR-NavIgnore.jar", "MIBR-Most20FPS.jar")
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
           "staged standard menu by `tools/release/build_modular.py`. Do not edit by hand.",
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
            md_cell(s["compiled_default"]), md_cell(s["declared_path"])))
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


def render_readme(repo, menu_text, complete, profiles, scope=None):
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
    out = ["# MIBR CarPlay - installation README", ""]
    if not complete:
        out += ["> **INCOMPLETE PACKAGE - NOT INSTALLABLE.** Required inputs are missing; see "
                "`package.json` field `missing_inputs`. Do not install.", ""]
    if scope == SCOPE_VALUE:
        out += ["Single-profile TEST package (scope `%s`); not the beta distribution." % SCOPE_VALUE, ""]
    else:
        out += ["Three-profile beta package: all listed profiles are packaged; final combined "
                "system tests are pending.", ""]
    out += ["| Profile | Firmware | Installer |", "|---|---|---|"]
    for pid in sorted(profiles):
        d = profiles[pid]
        out.append("| `%s` | `%s` | %s |" % (pid, d["firmware"], "enabled" if d["selector"][
            "install_enabled"] else "**refused** (selector not unit-measured)"))
    out += ["", "The profile is selected by exact SHA-256 match of `/ifs/lsd.jxe` against "
            "`installer/config/profiles.list`; an unknown, ambiguous or install-disabled hash "
            "stops the installer before any write.", "",
            "## Packaged defaults (source-defined, per preset where marked)", "",
            "CarPlay presets: %s." % presets, "", "| Area | Packaged default |", "|---|---|"]
    out += ["| %s | %s |" % (a, md_cell(v)) for a, v in rows]
    out += ["", "Full inventory: `%s`. These describe packaged sources only; they do not prove "
            "an active unit state or completed vehicle tests." % MATRIX, "",
            "## Install / status / uninstall", "",
            "Run `installer/mibr-status.ksh` first (read-only), then `installer/mibr-install.ksh`, "
            "then restart the head unit normally. `installer/mibr-uninstall.ksh` restores backed-up "
            "files. Runtime files live under `%s/`. Copy the package to an SD card as a whole; "
            "do not run single files." % APP, "",
            "## Recovery", "",
            "Uninstall via `installer/mibr-uninstall.ksh`. The boot guard kill switch is the file "
            "`%s/state/boot/disabled`." % APP, "",
            "## Not included", "",
            "OEM firmware files, OEM icons, RGI binaries and the boot probe JAR. The per-profile "
            "HMI JAR derives from OEM classes and is supplied to the assembler from outside "
            "(`profiles/<id>/hmi/MIBR-CarPlay.jar`). Source coverage is PARTIAL "
            "(`source/SOURCE_MANIFEST.json`).", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ assembly
def add(files, prov, path, data, origin, mode=None):
    if path in files:
        raise AssembleError("duplicate package path: " + path)
    files[path] = (data, mode if mode is not None else mode_for(path, data))
    prov[path] = dict(origin, sha256=sha(data))


def read_repo_file(repo, rel, files, prov, pkg_path, mode=None):
    data = (repo / rel).read_bytes()
    add(files, prov, pkg_path, data, {"origin": "repo", "repo_path": rel,
                                      "git_blob": git(repo, "hash-object", rel)}, mode)


def verify_native_sums(native):
    """Cross-check bin/mu1440-source/SHA256SUMS against the files when present."""
    base = native / "bin" / "mu1440-source"
    sums = base / "SHA256SUMS"
    if not sums.is_file():
        return
    for line in sums.read_text().splitlines():
        digest, _, name = line.partition("  ")
        target = base / name.removeprefix("./")
        if name and target.is_file() and sha(target.read_bytes()) != digest:
            raise AssembleError("native input differs from its SHA256SUMS: " + name)


def native_provenance(native):
    prov, missing = {}, []
    for key, fname in PROVENANCE_FILES:
        f = native / fname
        text = f.read_text().strip() if f.is_file() else ""
        if not text:
            missing.append("native provenance " + fname)
        prov[key] = text
    if missing:
        raise MissingInput(missing)
    return prov


# Inputs of the prebuilt artifacts. An artifact is reused only while none of its inputs changed
# since the commit it was built from (REPOSITORY_LAYOUT: do not rebuild unchanged artifacts, but
# never ship a stale one). Native: every QNX module source and build script; HMI: the Java menu.
NATIVE_INPUT_MODULES = ("carplay", "broker", "navigation")
NATIVE_INPUT_EXTRA = ("tools/qnx65-image.lock", "tools/ci_qnx65_image.sh", "settings/registry.json")
NATIVE_RUNTIME_DATA_EXCLUDE = ":(exclude)modules/navigation/source/platform-defaults"
HMI_INPUTS = ("modules/menu/source", ":(glob)modules/profiles/*/hmi/**",
              ":(glob)modules/profiles/*/profile.json", "settings/registry.json")


def native_inputs(repo):
    index = json.loads((Path(repo) / "modules/module-index.json").read_text())
    paths = list(NATIVE_INPUT_EXTRA)
    for name in NATIVE_INPUT_MODULES:
        spec = index["modules"][name]
        for key in ("source", "build_scripts", "support_tools"):
            paths += spec.get(key) or []
    # Per-car platform defaults are runtime data copied into the profile (see assemble), never a
    # compiler input; a new or changed car must not mark the prebuilt native binaries stale.
    return sorted(set(paths)) + [NATIVE_RUNTIME_DATA_EXCLUDE]


def stale_inputs(repo, commit, paths):
    """Files under paths that differ between the artifact's source commit and the work tree HEAD."""
    try:
        git(repo, "cat-file", "-e", commit + "^{commit}")
    except subprocess.CalledProcessError:
        return ["<source commit %s not in this repository>" % commit]
    out = git(repo, "diff", "--name-only", commit, "HEAD", "--", *paths)
    return [l for l in out.split("\n") if l]


def check_fresh(repo, kind, commit, paths, allow_stale):
    stale = stale_inputs(repo, commit, paths)
    if stale and not allow_stale:
        raise AssembleError("%s artifacts are stale (built from %s, changed since: %s); rebuild them"
                            % (kind, commit[:12], ", ".join(stale[:8])))
    return {"built_from": commit, "stale_inputs": stale}


def select_profiles(repo, wanted):
    docs = check_profiles.load_profiles(repo)
    errors = check_profiles.validate_all(docs)
    if errors:
        raise AssembleError("invalid profiles: " + "; ".join(errors))
    unknown = sorted(set(wanted or ()) - set(docs))
    if unknown:
        raise AssembleError("unknown profile: " + ", ".join(unknown))
    return {pid: docs[pid] for pid in sorted(wanted or docs)}


def assemble(native, repo=ROOT, installer=None, hmi_dir=None, profiles=None, scope=None,
             allow_dirty=False, menu_jar=None, allow_stale=False, version=None,
             use_research_prebuilts=False):
    """Return (zip entries {name: (bytes, mode)}, package metadata)."""
    native, repo = Path(native), Path(repo)
    installer = Path(installer) if installer is not None else repo / "installer"
    if not native.is_dir():
        raise AssembleError("native input directory not found")
    selected = select_profiles(repo, profiles)
    if scope not in (None, SCOPE_VALUE):
        raise AssembleError("unknown scope: %r" % (scope,))
    if scope == SCOPE_VALUE and len(selected) != 1:
        raise AssembleError("single-profile scope requires exactly one profile")
    if scope is None and set(selected) != set(check_profiles.load_profiles(repo)):
        raise AssembleError("a profile subset requires --scope single-profile (one profile only)")
    dirty = bool(git(repo, "status", "--porcelain", "--untracked-files=no"))
    if dirty and not allow_dirty:
        raise AssembleError("repository has uncommitted tracked changes (use --allow-dirty)")
    verify_native_sums(native)
    build_prov = native_provenance(native)
    if use_research_prebuilts:
        # Research provenance uses a commit in the private repository. Verify
        # its immutable archive receipt, exact staged payload bytes and a
        # reviewed public source-content lock instead of faking a main commit.
        if allow_stale:
            raise AssembleError("research prebuilt mode cannot bypass source freshness")
        if hmi_dir is None:
            raise AssembleError("research prebuilt mode requires an HMI staging directory")
        from stage_research_prebuilts import PrebuiltError, verify_staged
        try:
            native_gate = verify_staged(repo, native, hmi_dir)
        except (PrebuiltError, OSError, ValueError) as exc:
            raise AssembleError("RESEARCH_NATIVE_PREBUILT_BLOCKED: " + str(exc)) from exc
        build_prov["research_reference_sha256"] = native_gate["reference_archive_sha256"]
    else:
        native_gate = check_fresh(repo, "native", build_prov["source_commit"],
                                  native_inputs(repo), allow_stale)
    freshness = {"native": native_gate}
    hmi_commit = Path(hmi_dir) / "SOURCE_COMMIT.txt" if hmi_dir is not None else None
    if hmi_commit is not None and hmi_commit.is_file():
        freshness["hmi"] = check_fresh(repo, "HMI", hmi_commit.read_text().strip(), list(HMI_INPUTS), allow_stale)
    elif hmi_dir is not None and not allow_stale:
        raise AssembleError("--hmi-dir needs SOURCE_COMMIT.txt (the commit the JARs were built from)")
    files, prov, missing, hard = {}, {}, [], []
    manifest, profile_manifests, binaries = [], {}, []

    for pkg, candidates, targets in NATIVE:
        found = next((native / c for c in candidates if (native / c).is_file()), None)
        if found is None:
            hard.append("native output " + candidates[0])
            continue
        data = found.read_bytes()
        if rename_native(found.name) != pkg.rsplit("/", 1)[-1]:
            raise AssembleError("rename table does not map %s to %s" % (found.name, pkg))
        add(files, prov, pkg, data, {"origin": "native",
                                     "input": found.relative_to(native).as_posix()})
        row = {"path": pkg, "sha256": sha(data), "status": STATUS_BINARY,
               "native_input": found.relative_to(native).as_posix()}
        if found.name != pkg.rsplit("/", 1)[-1]:
            row["renamed_from"] = found.name
        binaries.append(row)
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
                     APP + "/config/carplay/altscreen111.conf", "common/carplay/config/altscreen111.conf"))
    for name in BROKER_SCRIPTS:
        pkg = "common/broker/scripts/" + name
        read_repo_file(repo, "modules/broker/runtime/mibr-control/" + name, files, prov, pkg)
        manifest.append((sha(files[pkg][0]), "755", APP + "/scripts/" + name, pkg))
    read_repo_file(repo, "tools/menu-editor/standard-menu.txt", files, prov,
                   "common/menu/config/mibr-menu.conf")
    manifest.append((sha(files["common/menu/config/mibr-menu.conf"][0]), "644",
                     APP + "/config/menu/layout.conf", "common/menu/config/mibr-menu.conf"))
    for name in SCROLL:
        pkg = "common/menu/icons/" + name
        read_repo_file(repo, "modules/menu/source/assets/scroll/" + name, files, prov, pkg)
        # MibrIconState.ROOT
        manifest.append((sha(files[pkg][0]), "644", "/mnt/app/eso/hmi/lsd/mibr/icons/" + name, pkg))
    for name in SUPPORT_JARS:
        pkg = "common/menu/bin/" + name
        support = Path(hmi_dir) / "common" / name if hmi_dir is not None else None
        if support is None or not support.is_file() or support.is_symlink():
            missing.append(pkg)
            continue
        data = support.read_bytes()
        add(files, prov, pkg, data, {"origin": "hmi-input", "input": "common/" + name})
        manifest.append((sha(data), "644", LSD_JARS + name, pkg))
    ext = Path(hmi_dir) / "common" / EXTENDER_JAR if hmi_dir is not None else None
    if ext is not None and ext.is_file():
        pkg = "common/menu/bin/" + EXTENDER_JAR
        add(files, prov, pkg, ext.read_bytes(), {"origin": "hmi-input"})
        manifest.append((sha(files[pkg][0]), "644", LSD_JARS + EXTENDER_JAR, pkg))
    else:
        missing.append("common/menu/bin/" + EXTENDER_JAR)
    for name in ("gen2_nav_config.sh", "gen2_safearea.sh"):
        pkg = "common/navigation/scripts/" + name
        read_repo_file(repo, "modules/navigation/runtime/" + name, files, prov, pkg)
        manifest.append((sha(files[pkg][0]), "755", APP + "/scripts/" + name, pkg))
    # the mm-ipod wrapper selected by the usblauncher_otg.lua variant (lua-rgi.awk)
    pkg = "common/navigation/scripts/mm-ipod-rgi.sh"
    read_repo_file(repo, "modules/navigation/runtime/mm-ipod-rgi.sh", files, prov, pkg)
    manifest.append((sha(files[pkg][0]), "755", APP + "/bin/mm-ipod-rgi", pkg))
    for name in EDITOR:
        read_repo_file(repo, "tools/menu-editor/" + name, files, prov, "tools/menu-editor/" + name)
    read_repo_file(repo, "tools/validate_modular_package.py", files, prov,
                   "tools/package/validate_modular_package.py")
    read_repo_file(repo, "tools/check_mu1440_target_shell.py", files, prov,
                   "tools/package/check_mu1440_target_shell.py")
    # guide for testers and their AI agents: where the source is, how to report and fix
    if git(repo, "ls-files", "release/PACKAGE_AGENTS.md"):
        read_repo_file(repo, "release/PACKAGE_AGENTS.md", files, prov, "AGENTS.md")
    for rel, pkg in (("LICENSE", "docs/LICENSE"), ("THIRD_PARTY_NOTICES.md", "docs/THIRD_PARTY_NOTICES.md"),
                     ("THIRD_PARTY/NavIgnore/LICENSE-MIT.txt", "docs/third_party/NavIgnore-LICENSE-MIT.txt"),
                     ("THIRD_PARTY/Most20FPS/LICENSE-MIT.txt", "docs/third_party/Most20FPS-LICENSE-MIT.txt")):
        read_repo_file(repo, rel, files, prov, pkg)
    src_rows = []
    for rel in git(repo, "ls-files", "modules/menu/source").split("\n"):
        pkg = "source/hmi/" + rel[len("modules/menu/source/"):]
        read_repo_file(repo, rel, files, prov, pkg)
        src_rows.append(pkg)
    platform_override = inv.broker_inventory(
        inv.read(repo, inv.BROKER_C), inv.read(repo, inv.BROKER_H))["platform_override"]
    gen = lambda p, text: add(files, prov, p, text.encode(), {"origin": "generated"})  # noqa: E731

    # profiles: every tracked file of the profile directory, plus generated stubs
    for pid, doc in selected.items():
        root = "profiles/%s/" % pid
        pm = profile_manifests.setdefault(pid, [])
        for rel in git(repo, "ls-files", "modules/profiles/" + pid).split("\n"):
            sub = rel[len("modules/profiles/%s/" % pid):]
            # The checked-in reference JAR is not a second package payload.
            # Package only the freshly built profile JAR supplied via --hmi-dir.
            if sub.startswith("hmi/prebuilt/"):
                continue
            pkg = root + sub
            read_repo_file(repo, rel, files, prov, pkg)
            if sub.startswith("hmi/java/"):
                src_rows.append(pkg)
        defaults = "modules/navigation/source/platform-defaults/%s.conf" % pid.rsplit("-", 1)[0]
        if git(repo, "ls-files", defaults):
            read_repo_file(repo, defaults, files, prov, root + "display/mibr-platform-defaults.conf")
            pm.append((sha(files[root + "display/mibr-platform-defaults.conf"][0]), "644",
                       platform_override, root + "display/mibr-platform-defaults.conf"))
        gen(root + "hmi/expected-inputs.json", json.dumps(
            {"jar": "MIBR-CarPlay.jar", "source": "source/hmi", "oem_derived": True},
            indent=2, sort_keys=True) + "\n")
        # OEM integration rows are maintained with the profile (measured stock/patched hashes,
        # transform hash of the committed bytes) and copied by the loop above; the installer
        # re-checks every hash on the unit. Without a committed list an empty one is generated.
        if root + "integration/variants.list" not in files:
            gen(root + "integration/variants.list", "# target stock-sha expected-patched-sha "
                "transform-file transform-sha mode (no entries in this package revision; "
                "no OEM bytes are shipped)\n")
        jar = Path(hmi_dir) / pid / "MIBR-CarPlay.jar" if hmi_dir is not None else None
        if jar is None and menu_jar is not None and len(selected) == 1:
            jar = Path(menu_jar)
        if jar is not None and jar.is_file():
            add(files, prov, root + "hmi/MIBR-CarPlay.jar", jar.read_bytes(),
                {"origin": "hmi-input"})
            pm.append((sha(files[root + "hmi/MIBR-CarPlay.jar"][0]), "644",
                       LSD_JARS + "MIBR-CarPlay.jar", root + "hmi/MIBR-CarPlay.jar"))
        else:
            missing.append(root + "hmi/MIBR-CarPlay.jar")
        gen(root + "payload.manifest", "# sha256 mode target source\n" + "".join(
            "%s %s %s %s\n" % row for row in sorted(pm, key=lambda r: r[2])))

    listing = generate_profiles_list.render_list(selected)
    disk = installer / "config/profiles.list"
    if scope is None and disk.is_file() and disk.read_text() != listing:
        raise AssembleError("installer/config/profiles.list drifts from profile.json "
                            "(run tools/release/generate_profiles_list.py --write)")
    gen("installer/config/profiles.list", listing)
    gen("installer/config/payload.manifest", "# sha256 mode target source\n" + "".join(
        "%s %s %s %s\n" % row for row in sorted(manifest, key=lambda r: (r[2], r[3]))))

    # installer inputs (written by the installer owner; absent -> MISSING_INPUT)
    for rel in sorted(x.relative_to(installer).as_posix() for x in installer.rglob("*")
                      if x.is_file() and "__pycache__" not in x.parts) if installer.is_dir() else ():
        pkg = "installer/" + rel
        if pkg in files:
            continue  # generated config takes precedence
        add(files, prov, pkg, (installer / rel).read_bytes(), {"origin": "installer-input", "input": rel})
    for rel in REQUIRED_INSTALLER + ("select-profile.ksh", "lib/migrate-root.ksh",
                                      "config/root-migration.list"):
        if "installer/" + rel not in files:
            missing.append("installer/" + rel)
    complete = not missing
    if not complete:
        by_holder = {}
        for m in missing:
            holder = "installer/MISSING_INPUT.txt" if m.startswith("installer/") else \
                m.rsplit("/", 1)[0] + "/MISSING_INPUT.txt"
            by_holder.setdefault(holder, []).append(m)
        for holder, items in sorted(by_holder.items()):
            gen(holder, "".join("MISSING_INPUT: %s\n" % m for m in sorted(items)))

    menu_text = files["common/menu/config/mibr-menu.conf"][0].decode()
    gen(README, render_readme(repo, menu_text, complete, selected, scope))
    gen(MATRIX, render_matrix(repo, menu_text))

    source = {
        "coverage": "PARTIAL",
        "repo": {"commit": git(repo, "rev-parse", "HEAD"),
                 "tree": git(repo, "rev-parse", "HEAD^{tree}"), "dirty": dirty},
        "native_build_source_commit": build_prov["source_commit"].split()[0],
        "files": [{"path": p, "sha256": prov[p]["sha256"]} for p in sorted(src_rows)],
        "inputs": [dict(path=p, **{k: v for k, v in prov[p].items()}) for p in sorted(prov)
                   if prov[p]["origin"] != "generated"],
        "gaps": ["OEM, QNX, JDK and third-party dependencies are not included",
                 "native binaries are listed with input hashes; their build commit may differ "
                 "from the repo commit",
                 "broker service outputs are renamed from the NOT-INSTALL-READY build names "
                 "through the explicit rename table in tools/release/build_modular.py"],
    }
    gen("source/SOURCE_MANIFEST.json", json.dumps(source, indent=2, sort_keys=True) + "\n")
    meta = {
        "schema": 2, "package": "MIBR-CarPlay",
        "profiles": sorted(selected), "modules": MODULES,
        "profile_info": {pid: {"install_enabled": bool(d["selector"]["install_enabled"]),
                               "firmware": d["firmware"], "selector_sha256": d["selector"]["digest"]}
                         for pid, d in selected.items()},
        "package_status": "complete" if complete else "incomplete",
        "complete": complete, "installable": complete and any(
            d["selector"]["install_enabled"] for d in selected.values()),
        "missing_inputs": sorted(missing),
        "status": {"SOURCE_BUILD_PASS": True, "PACKAGE_VALIDATED": "NOT_RUN",
                   "UNIT_TESTED": "NOT_RUN", "VEHICLE_RELEASE_APPROVED": False},
        "native_build": dict(build_prov, sha256sums_verified=True),
        "input_freshness": freshness,
        "binaries": sorted(binaries, key=lambda r: r["path"]),
        "source": source["repo"],
        "profiles_list_sha256": sha(files["installer/config/profiles.list"][0]),
        "files": [{"path": p, "sha256": sha(files[p][0]), "mode": "%04o" % files[p][1],
                   "size": len(files[p][0])} for p in sorted(files)],
    }
    if scope:
        meta["scope"] = scope
    # Product version (release/VERSION, committed) and the exact source commit; the installer
    # copies both into version/installed-version.properties for the menu's version page.
    if version is None and git(repo, "ls-files", "release/VERSION"):
        version = git(repo, "show", "HEAD:release/VERSION").strip()
    if version is not None:
        if not version or len(version) > 40 or any(c not in VERSION_CHARS for c in version):
            raise AssembleError("release/VERSION is not a plain version string: %r" % version)
        meta["version"] = version
    meta["source_commit"] = git(repo, "rev-parse", "HEAD")
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
        menu_bytes = files["common/menu/config/mibr-menu.conf"]
        # Compare exact packaged bytes. read_text() normalizes CRLF on Windows,
        # while the ZIP correctly preserves the checked-in source bytes.
        if menu_bytes != (Path(repo) / inv.MENU).read_bytes():
            problems.append("staged menu differs from tools/menu-editor/standard-menu.txt")
        menu = menu_bytes.decode()
        selected = select_profiles(Path(repo), meta["profiles"])
        wanted = {README: render_readme(Path(repo), menu, bool(meta["complete"]), selected,
                                        meta.get("scope")),
                  MATRIX: render_matrix(Path(repo), menu)}
    except (KeyError, ValueError, AssembleError) as exc:
        return ["cannot check package: %r" % (exc,)]
    for name, text in wanted.items():
        if name not in files:
            problems.append("missing " + name)
        elif files[name].decode() != text:
            problems.append("drift: " + name)
    return problems


# ---------------------------------------------------------------- self-test
def fake_native(base):
    """Synthetic native-dir (not real binaries) incl. provenance files."""
    for rel in ("gen2/libaltscreen111.so", "mu1440-source/alt111-settings",
                "mu1440-source/direct-ts-parity", "mu1440-source/parity-session",
                "mu1440-source/libmibr_isotx2_gate.so", "mu1440-source/libmibr_isotx2_guard.so",
                "direct-ts-remux/direct-ts-remux", "support-tools/sha256sum", "support-tools/tee",
                "navigation/libmibr_rgi_ipod.so", "navigation/mibr-rgi"):
        p = base / "bin" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF" + rel.encode())
    for n in ("mibr-v3-service", "mibrctl-v3", "mibr-v3-genkey", "mibr-key40d"):
        p = base / ("bin/mu1440-source/mibr-control/%s%s" % (n, BUILD_SUFFIX))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF" + n.encode())
    clip = base / "bin/navigation/mibr-calib.avcc"
    clip.write_bytes(b"\x00\x00\x00\x04synthetic-avcc")
    (base / "SOURCE_COMMIT.txt").write_text("0123456789abcdef0123456789abcdef01234567\n")
    (base / "COMPILER.txt").write_text("synthetic-gcc 0.0\n")
    (base / "IMAGE_SOURCE.txt").write_text("IMAGE_SOURCE=synthetic\n")


def fake_installer(base, repo=ROOT):
    """Copy the repo installer tree and add stub entrypoints (tests only)."""
    shutil.copytree(Path(repo) / "installer", base, ignore=shutil.ignore_patterns("__pycache__"))
    for n in REQUIRED_INSTALLER:
        (base / n).write_text("#!/bin/ksh\n# synthetic stub\nexit 0\n")


def fake_hmi(base):
    (base / "common").mkdir(parents=True)
    (base / "common" / EXTENDER_JAR).write_bytes(b"PK synthetic extender jar")
    for name in SUPPORT_JARS:
        (base / "common" / name).write_bytes(b"PK synthetic support jar " + name.encode())
    for pid in check_profiles.load_profiles():
        (base / pid).mkdir(parents=True)
        (base / pid / "MIBR-CarPlay.jar").write_bytes(b"PK synthetic jar " + pid.encode())


def raises(exc, fn):
    try:
        fn()
    except exc as e:
        return e
    raise AssertionError("expected " + exc.__name__)


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        native, inst, hmi = tmp / "bo", tmp / "inst", tmp / "hmi"
        fake_native(native)
        fake_installer(inst)
        fake_hmi(hmi)
        kw = dict(allow_dirty=True, installer=inst, allow_stale=True)
        # determinism
        a, meta = assemble(native, hmi_dir=hmi, **kw)
        b, _ = assemble(native, hmi_dir=hmi, **kw)
        ha, hb = write_zip(a, tmp / "a.zip"), write_zip(b, tmp / "sub/b.zip")
        assert ha == hb and (tmp / "a.zip").read_bytes() == (tmp / "sub/b.zip").read_bytes()
        assert meta["complete"] and meta["package_status"] == "complete" and meta["missing_inputs"] == []
        assert "scope" not in meta and len(meta["profiles"]) == 3
        assert meta["profile_info"]["seat-mu1409-p4708"]["install_enabled"] is \
            check_profiles.load_profiles()["seat-mu1409-p4708"]["selector"]["install_enabled"]
        assert all(r["status"] == "SOURCE_BUILD_PASS" for r in meta["binaries"])
        assert any(r.get("renamed_from") == "mibrctl-v3" + BUILD_SUFFIX for r in meta["binaries"])
        with zipfile.ZipFile(tmp / "a.zip") as z:
            for i in z.infolist():
                assert i.date_time == ZIP_TIME and i.filename.startswith(PREFIX)
                m = (i.external_attr >> 16) & 0o777
                data = z.read(i)
                assert m == mode_for(i.filename[len(PREFIX):], data), i.filename
            assert [i.filename for i in z.infolist()] == sorted(i.filename for i in z.infolist())
        files = load_zip(tmp / "a.zip")
        doc_problems = check_docs(files)
        assert doc_problems == [], doc_problems
        bad = dict(files)
        bad[MATRIX] = files[MATRIX].replace(b"`40`", b"`41`", 1)
        assert bad[MATRIX] != files[MATRIX] and check_docs(bad) == ["drift: " + MATRIX]
        bad = dict(files)
        bad[README] = files[README] + b"extra\n"
        assert check_docs(bad) == ["drift: " + README]
        # incomplete (no HMI dir, no installer entrypoints)
        inc, im = assemble(native, allow_dirty=True, installer=tmp / "none", allow_stale=True)
        assert im["package_status"] == "incomplete" and not im["installable"]
        assert any(m.endswith("MIBR-CarPlay.jar") for m in im["missing_inputs"])
        assert "installer/mibr-install.ksh" in im["missing_inputs"]
        assert b"INCOMPLETE PACKAGE" in inc[README][0]
        # single-profile scope
        one, om = assemble(native, hmi_dir=hmi, profiles=["skoda-mu1440-p4526"], scope=SCOPE_VALUE, **kw)
        assert om["scope"] == SCOPE_VALUE and om["profiles"] == ["skoda-mu1440-p4526"]
        raises(AssembleError, lambda: assemble(native, profiles=["skoda-mu1440-p4526"], **kw))
        raises(AssembleError, lambda: assemble(native, profiles=["nope"], scope=SCOPE_VALUE, **kw))
        # missing native binary and provenance fail hard
        (native / "bin/mu1440-source/parity-session").unlink()
        e = raises(MissingInput, lambda: assemble(native, hmi_dir=hmi, **kw))
        assert any("parity-session" in i for i in e.items)
        fake_native(native)
        (native / "COMPILER.txt").unlink()
        raises(MissingInput, lambda: assemble(native, hmi_dir=hmi, **kw))
        fake_native(native)
        (native / "bin/mu1440-source/SHA256SUMS").write_text("%s  ./alt111-settings\n" % ("0" * 64))
        raises(AssembleError, lambda: assemble(native, hmi_dir=hmi, **kw))
    print("BUILD_MODULAR_SELF_TEST=PASS")


def main(argv=None, default_profiles=None, default_scope=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native-dir", type=Path, help="native build output directory")
    ap.add_argument("--hmi-dir", type=Path, help="<dir>/<profile_id>/MIBR-CarPlay.jar")
    ap.add_argument("--out", type=Path, help="output ZIP path")
    ap.add_argument("--repo", type=Path, default=ROOT)
    ap.add_argument("--installer-dir", type=Path, help="default: <repo>/installer")
    ap.add_argument("--profiles", nargs="+", default=default_profiles,
                    help="profile ids (default: all profiles)")
    ap.add_argument("--scope", choices=[SCOPE_VALUE], default=default_scope,
                    help="single-profile: explicit test package with exactly one profile")
    ap.add_argument("--menu-jar", type=Path, help="legacy: HMI JAR for a single-profile package")
    ap.add_argument("--require-complete", action="store_true",
                    help="exit 2 when any input is missing")
    ap.add_argument("--allow-incomplete", action="store_true", help="accepted for compatibility")
    ap.add_argument("--version", help="product version written to package.json (default: release/VERSION), [A-Za-z0-9._+-]+")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--allow-stale", action="store_true",
                    help="tests only: accept prebuilt artifacts whose inputs changed since their build")
    ap.add_argument("--use-research-prebuilts", action="store_true",
                    help="verify immutable private Research archive receipt and Git object source lock")
    ap.add_argument("--check", type=Path, metavar="ZIP",
                    help="fail if README/matrix in ZIP drift from registry and inventory")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.check:
        problems = check_docs(load_zip(args.check), args.repo)
        for p in problems:
            print("DOCS_DRIFT: " + p, file=sys.stderr)
        print("MODULAR_DOCS_CHECK=" + ("FAIL" if problems else "PASS"))
        sys.exit(1 if problems else 0)
    if not args.native_dir or not args.out:
        ap.error("--native-dir and --out are required")
    try:
        files, meta = assemble(args.native_dir, args.repo, args.installer_dir, args.hmi_dir,
                               args.profiles, args.scope, args.allow_dirty, args.menu_jar, args.allow_stale,
                                args.version, args.use_research_prebuilts)
    except MissingInput as exc:
        for item in exc.items:
            print("MISSING_INPUT: " + item, file=sys.stderr)
        sys.exit(2)
    except AssembleError as exc:
        print("ASSEMBLE_FAIL: %s" % exc, file=sys.stderr)
        sys.exit(1)
    for item in meta["missing_inputs"]:
        print("MISSING_INPUT: " + item, file=sys.stderr)
    if meta["missing_inputs"] and args.require_complete:
        sys.exit(2)
    digest = write_zip(files, args.out)
    print("MODULAR_PACKAGE=%s files=%d profiles=%d installable=%s zip_sha256=%s" % (
        meta["package_status"].upper(), len(files), len(meta["profiles"]),
        str(meta["installable"]).lower(), digest))


if __name__ == "__main__":
    main()
