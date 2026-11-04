#!/usr/bin/env python3
"""Proposed A2/A3 storage identities; host-only and NOT an installer.

This is a source-derived naming/ownership collision gate for the existing
63-candidate graph. A proposed destination is not a verified active path or
permission to write. Keep legacy native grammars and early-boot consumers
unchanged until a separately qualified coordinated release.
"""
import argparse
import copy
import json
import re
from pathlib import Path

import sys

# Sibling tools are imported by name; keep that working under `python3 -I`,
# which drops the script directory from sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import storage_access_graph as access
import storage_migration_review as review

ROOT = Path(__file__).resolve().parents[2]
OLD = "/mnt/app/root/"
NEW = OLD + "altscreen-u2/"
VALID_RELATIVE = re.compile(
    r"(?:config/(?:carplay|navigation|cockpit|menu|vehicle|platform|features)"
    r"|state/[a-z0-9-]+|version(?:/[a-z0-9-]+)?|backup/[a-z0-9-]+)"
    r"/[a-z0-9][a-z0-9._-]*"
)

# Exactly the 37 *additional candidates*, not a claim of 37 real settings.
# relative old path | reserved relative name or '-' | owner/role | file policy
# | A3 disposition
# "hold-*" means no automatic migration target exists yet. In particular,
# two opposite bit26 markers must never become competing writers of one file.
# Only MIGRATE rows receive a candidate destination. KEEP_AT_LEGACY,
# EXCLUDE_NONCONFIG and BLOCKED_INPUT rows keep their reserved name as
# documentation only, so two legacy stores can never collide in a target.
ADDITIONAL_SPECS = """
altscreen-u2/config/cpvc-r5.profile|config/cockpit/cpvc-r5.profile|cockpit-profile|preserve-native|KEEP_AT_LEGACY
altscreen-u2/config/display-scaling.conf|config/cockpit/scaling.conf|display-scaling|preserve-native|MIGRATE
altscreen-u2/config/mibr-calib.avcc|-|carplay-calibration|opaque-format|EXCLUDE_NONCONFIG
altscreen-u2/config/mibr-menu-language.conf|config/menu/language.conf|menu-language|preserve-native|MIGRATE
altscreen-u2/config/mibr-menu.conf|config/menu/layout.conf|menu-layout|preserve-crc|MIGRATE
altscreen-u2/config/mibr-platform-defaults.conf|config/platform/defaults.conf|platform-defaults|preserve-native|MIGRATE
altscreen-u2/config/vdata.mode|config/vehicle/data-mode.conf|vehicle-data|preserve-native|KEEP_AT_LEGACY
altscreen-u2/config/vstatus.mode|config/vehicle/status-mode.conf|vehicle-status|preserve-native|KEEP_AT_LEGACY
mibr-carplay111-nav-query.enabled|-|legacy-navigation|hold-alias|KEEP_AT_LEGACY
mibr-carplay111-nav.maneuverLayout|-|legacy-navigation|hold-alias|KEEP_AT_LEGACY
mibr-carplay111-nav.showCompass|-|legacy-navigation|hold-alias|KEEP_AT_LEGACY
mibr-carplay111-nav.showETA|-|legacy-navigation|hold-alias|KEEP_AT_LEGACY
mibr-carplay111-nav.showSpeedLimit|-|legacy-navigation|hold-alias|KEEP_AT_LEGACY
mibr-carplay111-nav.surface|-|legacy-navigation|hold-alias|KEEP_AT_LEGACY
mibr-carplay111-safearea.conf|-|legacy-navigation|hold-alias|KEEP_AT_LEGACY
mibr-carplay111-url-map.enabled|-|legacy-navigation|hold-alias|KEEP_AT_LEGACY
mibr-alt111-keyframe-policy.enabled|config/features/keyframe-recovery.conf|boot-policy|convert-presence|KEEP_AT_LEGACY
mibr-carplay-autodirect.enabled|config/features/auto-direct.conf|boot-policy|convert-presence|KEEP_AT_LEGACY
mibr-carplay111-bit26.force-off|-|conflicting-polarity-markers|hold-conflict|KEEP_AT_LEGACY
mibr-carplay111-bit26.force-on|-|conflicting-polarity-markers|hold-conflict|KEEP_AT_LEGACY
mibr-carplay111-viewareas.enabled|config/features/view-areas.conf|legacy-activation|convert-presence|KEEP_AT_LEGACY
mibr-direct-output-fps|config/carplay/direct-output-fps.conf|legacy-frame-policy|preserve-scalar|KEEP_AT_LEGACY
mibr-isotx2-gate-disable|config/features/isotx2-gate.conf|early-boot-policy|convert-inverted-presence|KEEP_AT_LEGACY
mibr-parity-drive.enabled|config/features/parity-drive.conf|runtime-policy|preserve-scalar|KEEP_AT_LEGACY
mibr-parity-statistics-enabled|config/features/parity-statistics.conf|runtime-policy|preserve-value-boolean-default-on|KEEP_AT_LEGACY
mibr-parity-status-enabled|config/features/parity-status.conf|runtime-policy|preserve-value-boolean-default-on|KEEP_AT_LEGACY
mibr-rgi/rgi.on|config/features/rgi.conf|navigation-activation|convert-presence|KEEP_AT_LEGACY
mibr-carplay111-backup|-|legacy-backup-directory|hold-backup|KEEP_AT_LEGACY
mibr-gen2-backup|-|legacy-backup-directory|hold-backup|KEEP_AT_LEGACY
mibr-isotx2-gate-backup|-|early-boot-backup-directory|hold-backup|KEEP_AT_LEGACY
mibr-isotx2-gate-backup/startup.sh.stock|-|stock-boot-preimage|preserve-exact-original|KEEP_AT_LEGACY
mibr-pr93-visual-rollback.ksh|-|test-only-candidate|hold-unproven-runtime|EXCLUDE_NONCONFIG
mibr-deploy-most20-owned|version/ownership/most20.marker|installer-ownership-receipt|preserve-presence|MIGRATE
mibr-deploy-navignore-owned|version/ownership/navignore.marker|installer-ownership-receipt|preserve-presence|MIGRATE
mibr-kit/components.manifest|version/components.manifest|component-version-receipt|preserve-native|BLOCKED_INPUT
mibr-kit/installed-version.properties|version/installed-version.properties|product-version-receipt|preserve-native|BLOCKED_INPUT
altscreen-u2/config/mibr-v3-single-writer.enabled|-|early-boot-safety-gate|hold-exact-two-byte-contract|KEEP_AT_LEGACY
""".strip()

DISPOSITIONS = ("MIGRATE", "KEEP_AT_LEGACY", "EXCLUDE_NONCONFIG",
                "BLOCKED_INPUT")

# Why a row is not migrated. Each reason names the source fact that would
# have to change before the row can be reconsidered.
REASONS = {
    "registry-no-native-persistent-writer":
        "native settings refuse persistent writes; durability is the CPVC "
        "profile replay, so a rename would move nothing the product writes",
    "broker-sd-log-consumer-unproven":
        "a second reader of the SD-log switch is claimed but not in source",
    "cpvc-replay-reader-outside-source":
        "the boot replay of the CPVC profile is not in this repository",
    "no-writer-in-source":
        "readers exist but no writer is in source; moving gains nothing",
    "legacy-alias-of-registry-value":
        "older GEN2 binaries read this file; the registry is the new owner",
    "early-boot-or-stock-backup-contract":
        "embedded in a generated boot hook or an exact stock backup",
    "opposite-polarity-pair":
        "two markers with opposite meaning and unproven precedence",
    "value-file-paired-writer":
        "value file written together with another store by one script",
    "safety-gate-exact-bytes":
        "exact two-byte authorization gate; never created by a migration",
    "payload-not-state":
        "installed asset or test reference, not configuration",
    "receipt-writer-not-in-source":
        "the installer that writes this receipt is not in source",
    "migrate-single-writer-proven":
        "one source writer and all source readers are known",
}

ADDITIONAL_REASON = {
    "altscreen-u2/config/cpvc-r5.profile": "cpvc-replay-reader-outside-source",
    "altscreen-u2/config/mibr-calib.avcc": "payload-not-state",
    "altscreen-u2/config/vdata.mode": "no-writer-in-source",
    "altscreen-u2/config/vstatus.mode": "no-writer-in-source",
    "mibr-alt111-keyframe-policy.enabled": "early-boot-or-stock-backup-contract",
    "mibr-carplay-autodirect.enabled": "early-boot-or-stock-backup-contract",
    "mibr-carplay111-bit26.force-off": "opposite-polarity-pair",
    "mibr-carplay111-bit26.force-on": "opposite-polarity-pair",
    "mibr-carplay111-viewareas.enabled": "no-writer-in-source",
    "mibr-direct-output-fps": "value-file-paired-writer",
    "mibr-isotx2-gate-disable": "early-boot-or-stock-backup-contract",
    "mibr-parity-drive.enabled": "early-boot-or-stock-backup-contract",
    "mibr-parity-statistics-enabled": "value-file-paired-writer",
    "mibr-parity-status-enabled": "value-file-paired-writer",
    "mibr-rgi/rgi.on": "no-writer-in-source",
    "mibr-carplay111-backup": "early-boot-or-stock-backup-contract",
    "mibr-gen2-backup": "early-boot-or-stock-backup-contract",
    "mibr-isotx2-gate-backup": "early-boot-or-stock-backup-contract",
    "mibr-isotx2-gate-backup/startup.sh.stock":
        "early-boot-or-stock-backup-contract",
    "mibr-carplay111-safearea.conf": "legacy-alias-of-registry-value",
    "mibr-pr93-visual-rollback.ksh": "payload-not-state",
    "mibr-kit/components.manifest": "receipt-writer-not-in-source",
    "mibr-kit/installed-version.properties": "receipt-writer-not-in-source",
    "altscreen-u2/config/mibr-v3-single-writer.enabled":
        "safety-gate-exact-bytes",
}

# The single writer of every MIGRATE row, as found in source. A migrated
# store must have exactly one; the cutover moves writer and readers together.
MIGRATE_WRITERS = {
    "altscreen-u2/config/display-scaling.conf":
        "modules/carplay/source/display-scaling/mibr_display_scaling.c",
    "altscreen-u2/config/mibr-menu-language.conf":
        "modules/broker/source/mibr-control/mibr_menu_language.c",
    "altscreen-u2/config/mibr-menu.conf":
        "modules/broker/runtime/mibr-control/mibr-menu.ksh",
    "altscreen-u2/config/mibr-platform-defaults.conf": "installer",
    "mibr-deploy-most20-owned": "deployment/mu1440/install.sh",
    "mibr-deploy-navignore-owned": "deployment/mu1440/install.sh",
}
BROKER_SWITCH_WRITER = "modules/broker/source/mibr-control/mibr_durable_switch.c"
BROKER_BLOCKED = {"sd_log"}

# Value-bearing booleans whose absence means ON. A presence converter would
# turn a stored "0" into ON.
VALUE_BOOLEAN_DEFAULT_ON = {"mibr-parity-statistics-enabled",
                            "mibr-parity-status-enabled"}


# Long-term architecture class of every candidate, IN ADDITION to the A3
# disposition above (which only says what may move safely now). A KEEP_AT_LEGACY
# row is not automatically the end state. Fields: class | long-term relative
# target or '-' | sole long-term owner | concrete gate that blocks the change.
ARCH_CLASSES = ("MIGRATE_AS_PLANNED", "KEEP_TECHNICALLY_REQUIRED",
                "DEFER_MIGRATION", "CONSOLIDATE_OR_RETIRE",
                "EXCLUDE_NONCONFIG", "BLOCKED_INPUT")

REGISTRY_ARCH = (
    "DEFER_MIGRATION", None, "broker via alt111-settings persistent layer",
    "persistent registry layer has no native writer (settings refuse "
    "persistent writes); needs a guarded persistent writer, per-profile GEN2 "
    "rebuild for the new root, power-loss test, and import of the CPVC "
    "profile so only one persistent channel remains")

ARCH_SPECS = """
altscreen-u2/config/cpvc-r5.profile|CONSOLIDATE_OR_RETIRE|-|broker (import into registry persistent layer, then retire)|boot replay reader of the profile is not in source; must be proven before the replay is removed
altscreen-u2/config/display-scaling.conf|MIGRATE_AS_PLANNED|config/cockpit/scaling.conf|broker|joint C/GEN2 constant change
altscreen-u2/config/mibr-calib.avcc|EXCLUDE_NONCONFIG|-|installer payload|none: asset follows the payload layout
altscreen-u2/config/mibr-menu-language.conf|MIGRATE_AS_PLANNED|config/menu/language.conf|broker|joint C constant change
altscreen-u2/config/mibr-menu.conf|MIGRATE_AS_PLANNED|config/menu/layout.conf|mibr-menu.ksh|Java constant, ksh default and editor docs together
altscreen-u2/config/mibr-platform-defaults.conf|MIGRATE_AS_PLANNED|config/platform/defaults.conf|installer (fingerprint-selected, fallback only)|GEN2 must stop letting a platform default shadow a stored user value
altscreen-u2/config/vdata.mode|DEFER_MIGRATION|config/vehicle/data-mode.conf|menu/broker (to be added)|no writer in source; C hook and Java reader move together
altscreen-u2/config/vstatus.mode|DEFER_MIGRATION|config/vehicle/status-mode.conf|menu/broker (to be added)|no writer in source; C hook and Java reader move together
mibr-carplay111-nav-query.enabled|CONSOLIDATE_OR_RETIRE|-|registry navigation group|legacy file read only by the older GEN2 generation; retire when no supported profile ships it
mibr-carplay111-nav.maneuverLayout|CONSOLIDATE_OR_RETIRE|-|registry navigation group|as nav-query.enabled
mibr-carplay111-nav.showCompass|CONSOLIDATE_OR_RETIRE|-|registry navigation group|as nav-query.enabled
mibr-carplay111-nav.showETA|CONSOLIDATE_OR_RETIRE|-|registry navigation group|as nav-query.enabled
mibr-carplay111-nav.showSpeedLimit|CONSOLIDATE_OR_RETIRE|-|registry navigation group|as nav-query.enabled
mibr-carplay111-nav.surface|CONSOLIDATE_OR_RETIRE|-|registry navigation group|as nav-query.enabled; installer must stop writing the five-file profile for a GEN2 that does not read it
mibr-carplay111-safearea.conf|CONSOLIDATE_OR_RETIRE|-|broker safe-area CAS|rollback-only; no native reader; remove its writer script once no rollback needs it
mibr-carplay111-url-map.enabled|CONSOLIDATE_OR_RETIRE|-|registry navigation group|older binary reads it, no source writer
mibr-alt111-keyframe-policy.enabled|CONSOLIDATE_OR_RETIRE|-|registry keyframes group|the binary that reads the marker is unproven; installer forces it on
mibr-carplay-autodirect.enabled|DEFER_MIGRATION|config/features/auto-direct.conf|auto-direct enable/disable scripts|literal inside the generated lsd.sh hook; needs hook regeneration and removal of old blocks by marker lines
mibr-carplay111-bit26.force-off|BLOCKED_INPUT|-|one bit26 diagnostic value (after proof)|meaning and precedence of the pair inside the binary
mibr-carplay111-bit26.force-on|BLOCKED_INPUT|-|one bit26 diagnostic value (after proof)|meaning and precedence of the pair inside the binary
mibr-carplay111-viewareas.enabled|CONSOLIDATE_OR_RETIRE|-|registry key viewareas.enabled|no writer in source; binaries read the string
mibr-direct-output-fps|CONSOLIDATE_OR_RETIRE|-|registry fps group|direct_fps.sh writes this and the registry fps file non-atomically; keep one value
mibr-isotx2-gate-disable|KEEP_TECHNICALLY_REQUIRED|-|preload_control.sh|literal in the hash-classified startup.sh patch; a rename makes installed patches UNKNOWN and blocks restore
mibr-parity-drive.enabled|DEFER_MIGRATION|config/features/parity-drive.conf|parity enable/disable scripts|lsd.sh hook literal; two diverging supervisor copies must become one
mibr-parity-statistics-enabled|DEFER_MIGRATION|config/features/parity-statistics.conf|parity_drive_status.sh|value boolean, absent means ON; shell and supervisors move together
mibr-parity-status-enabled|DEFER_MIGRATION|config/features/parity-status.conf|parity_drive_status.sh|value boolean, absent means ON; native reader too
mibr-rgi/rgi.on|DEFER_MIGRATION|config/features/rgi.conf|menu/broker (to be added)|no writer in source; two native readers in different processes
mibr-carplay111-backup|EXCLUDE_NONCONFIG|-|auto-direct patcher|exact OEM backup; restore depends on the path
mibr-gen2-backup|EXCLUDE_NONCONFIG|-|gen2 prerequisite script|exact backup
mibr-isotx2-gate-backup|EXCLUDE_NONCONFIG|-|isoTX2 installer|exact stock startup.sh backup
mibr-isotx2-gate-backup/startup.sh.stock|EXCLUDE_NONCONFIG|-|isoTX2 installer|exact stock preimage, stays with its directory
mibr-pr93-visual-rollback.ksh|EXCLUDE_NONCONFIG|-|none|test reference only
mibr-deploy-most20-owned|MIGRATE_AS_PLANNED|version/ownership/most20.marker|installer|only together with the installer that replaces install.sh/uninstall.sh
mibr-deploy-navignore-owned|MIGRATE_AS_PLANNED|version/ownership/navignore.marker|installer|only together with the installer that replaces install.sh/uninstall.sh
mibr-kit/components.manifest|BLOCKED_INPUT|version/components.manifest|installer|receipt writer is not in source
mibr-kit/installed-version.properties|BLOCKED_INPUT|version/installed-version.properties|installer|receipt writer is not in source
altscreen-u2/config/mibr-v3-single-writer.enabled|EXCLUDE_NONCONFIG|-|explicit authorization act|exact two-byte safety gate; never created or moved by a migration
""".strip()


def arch_spec():
    specs = {}
    for line in ARCH_SPECS.splitlines():
        old, cls, target, owner, gate = line.split("|")
        require(cls in ARCH_CLASSES, "unknown architecture class: " + old)
        require(OLD + old not in specs, "duplicate architecture row: " + old)
        specs[OLD + old] = (cls, None if target == "-" else target, owner, gate)
    return specs


def architecture(row, arch):
    path = row["current_path"]
    if row["kind"] == "carplay-registry-group":
        if path.endswith("/mibr-carplay-autodirect"):
            return ("CONSOLIDATE_OR_RETIRE", None,
                    "auto-direct boot marker (single intent store)",
                    "read-only registry key that no boot or start script reads; "
                    "parity enable writes 0 into it without effect")
        if path.endswith("/mibr-carplay111-fps"):
            return ("DEFER_MIGRATION", None, REGISTRY_ARCH[2],
                    REGISTRY_ARCH[3] + "; direct_fps.sh is a second writer "
                    "that must be retired first")
        return REGISTRY_ARCH
    if row["kind"] == "broker-durable-switch":
        if row["logical_id"] == "broker:sd_log":
            return ("BLOCKED_INPUT", None, "broker",
                    "a second reader is claimed but not in source")
        return ("MIGRATE_AS_PLANNED", None, "broker", "joint C/Java/GEN2 cutover")
    require(path in arch, "candidate without architecture class: " + path)
    return arch[path]


class PlanError(ValueError):
    pass


def require(ok, msg):
    if not ok:
        raise PlanError(msg)


def source_spec():
    specs = {}
    for line in ADDITIONAL_SPECS.splitlines():
        old, target, owner, policy, disposition = line.split("|")
        path = OLD + old
        require(path not in specs, "duplicate additional path")
        require(disposition in DISPOSITIONS, "unknown disposition: " + old)
        if disposition == "MIGRATE":
            reason = "migrate-single-writer-proven"
            require(old in MIGRATE_WRITERS, "MIGRATE without a writer: " + old)
        elif policy == "hold-alias" and old not in ADDITIONAL_REASON:
            reason = "legacy-alias-of-registry-value"
        else:
            reason = ADDITIONAL_REASON.get(old)
        require(reason in REASONS, "disposition without a reason: " + old)
        specs[path] = {"relative_target": None if target == "-" else target,
                       "owner_role": owner, "format_policy": policy,
                       "disposition": disposition, "reason": reason,
                       "writer": MIGRATE_WRITERS.get(old)}
    require(len(specs) == 37, "unexpected additional storage candidates")
    return specs


def disposition(row, specs):
    """A3 disposition, reason and single writer of one graph row."""
    path = row["current_path"]
    kind = row["kind"]
    if kind == "carplay-registry-group":
        return "KEEP_AT_LEGACY", "registry-no-native-persistent-writer", None
    if kind == "broker-durable-switch":
        key = row["logical_id"].removeprefix("broker:")
        if key in BROKER_BLOCKED:
            return "BLOCKED_INPUT", "broker-sd-log-consumer-unproven", None
        return "MIGRATE", "migrate-single-writer-proven", BROKER_SWITCH_WRITER
    item = specs[path]
    return item["disposition"], item["reason"], item["writer"]


def valid_target(relative):
    return (relative is None
            or (isinstance(relative, str) and
                VALID_RELATIVE.fullmatch(relative) is not None and
                ".." not in relative and not relative.endswith(".tmp")))


def proposed(row, specs):
    path = row["current_path"]
    kind = row["kind"]
    if kind == "carplay-registry-group":
        basename = path.rsplit("/", 1)[-1]
        if basename.startswith("mibr-carplay111-"):
            name = basename[len("mibr-carplay111-"):]
        elif basename == "mibr-carplay-autodirect":
            name = "auto-direct"
        else:
            raise PlanError("unrecognized CarPlay store: " + path)
        require(re.fullmatch(r"[a-z0-9][a-z0-9.-]*", name) is not None,
                "unreviewed CarPlay group basename: " + name)
        relative = "config/carplay/" + (name if name.endswith(".conf")
                                         else name + ".conf")
        return relative, "carplay-registry", "registry-format-unqualified"
    if kind == "broker-durable-switch":
        key = row["logical_id"].removeprefix("broker:")
        require(key in review.BROKER_GROUPS and
                row["logical_id"] == "broker:" + key, "unmapped broker key")
        basename = path.rsplit("/", 1)[-1]
        require(basename.startswith("mibr-") and basename.endswith(".conf"),
                "unreviewed broker source name")
        relative = ("config/" + review.BROKER_GROUPS[key] + "/" +
                    basename[len("mibr-"):])
        return relative, "broker-exclusive-CAS-writer", "preserve-magic-revision-CAS"
    require(path in specs, "unclassified persistent candidate: " + path)
    item = specs[path]
    return item["relative_target"], item["owner_role"], item["format_policy"]


def lifecycle_policy(owner, format_policy):
    """Design decisions only; the installer does not implement these yet."""
    if format_policy.startswith("hold-"):
        return {
            "upgrade": "retain-legacy-original-unchanged-pending-ownership",
            "uninstall": "do-not-delete-unproven-or-unowned-original",
            "user_reset": "excluded-until-legacy-alias-resolved",
        }
    if owner in ("stock-boot-preimage",):
        return {
            "upgrade": "preserve-exact-original-bytes-and-provenance",
            "uninstall": "restore-and-verify-stock-before-backup-disposal",
            "user_reset": "never-delete-stock-preimage",
        }
    if owner in ("installer-ownership-receipt",):
        return {
            "upgrade": "carry-forward-actual-patch-ownership-evidence",
            "uninstall": "clear-only-after-verified-owned-patch-rollback",
            "user_reset": "not-a-user-preference",
        }
    if owner in ("product-version-receipt", "component-version-receipt"):
        return {
            "upgrade": "write-after-complete-verified-release-install",
            "uninstall": "remove-only-after-successful-release-rollback",
            "user_reset": "not-a-user-preference",
        }
    if owner == "platform-defaults":
        return {
            "upgrade": "firmware-fingerprint-bound-replacement-only",
            "uninstall": "restore-original-if-owned-and-snapshotted",
            "user_reset": "not-a-user-preference",
        }
    return {
        "upgrade": "preserve-current-user-intent-or-fail-on-ambiguous-alias",
        "uninstall": "preserve-user-preferences-unless-explicit-authorized-reset",
        "user_reset": "remove-only-explicitly-selected-owned-preferences",
    }


def build(graph, specs=None, arch=None):
    if specs is None:
        specs = source_spec()
    if arch is None:
        arch = arch_spec()
    require(graph["migration_authorized"] is False,
            "graph unexpectedly authorized runtime writes")
    require(len(graph["records"]) == 63, "source candidate count changed")
    require(len({r["current_path"] for r in graph["records"]}) == 63,
            "duplicate current storage paths")
    require(all(r["destination_path"] is None for r in graph["records"]),
            "unexpected independently authorized graph destination")
    require(all(not any(r[k] for k in (
        "one_actual_writer_verified", "every_reader_verified",
        "installed_boot_references_verified", "format_migration_verified",
        "upgrade_uninstall_rollback_verified")) for r in graph["records"]),
        "graph evidence state changed: review new proof before reusing plan")
    expected = {r["current_path"] for r in graph["records"]
                if r["kind"] not in ("carplay-registry-group",
                                     "broker-durable-switch")}
    require(set(specs) == expected and len(specs) == 37,
            "added/removed unreviewed legacy store or source classification")
    rows, targets = [], {}
    for original in sorted(graph["records"], key=lambda r: r["current_path"]):
        reserved, owner, policy = proposed(original, specs)
        require(valid_target(reserved), "unsafe/noncanonical target for " +
                original["current_path"])
        state, reason, writer = disposition(original, specs)
        require(state in DISPOSITIONS and reason in REASONS,
                "row without A3 disposition: " + original["current_path"])
        if state == "MIGRATE":
            require(reserved is not None and writer,
                    "MIGRATE needs a target and exactly one writer: " +
                    original["current_path"])
            require(not policy.startswith("hold-"),
                    "held store marked MIGRATE: " + original["current_path"])
            relative = reserved
        else:
            relative = None
        basename = original["current_path"].rsplit("/", 1)[-1]
        if basename in VALUE_BOOLEAN_DEFAULT_ON:
            require(policy == "preserve-value-boolean-default-on",
                    "value boolean mislabelled as presence: " + basename)
        destination = NEW + relative if relative is not None else None
        arch_class, arch_target, arch_owner, arch_gate = architecture(
            original, arch)
        if arch_target is None and arch_class in ("MIGRATE_AS_PLANNED",
                                                  "DEFER_MIGRATION"):
            arch_target = relative or reserved
        require((arch_class == "MIGRATE_AS_PLANNED") == (state == "MIGRATE"),
                "architecture class contradicts disposition: " +
                original["current_path"])
        require(arch_class not in ("MIGRATE_AS_PLANNED", "DEFER_MIGRATION") or
                arch_target is not None, "planned move without long-term "
                "target: " + original["current_path"])
        require(arch_class != "DEFER_MIGRATION" or not policy.startswith("hold-"),
                "held alias deferred instead of consolidated: " +
                original["current_path"])
        if destination is not None:
            require(destination not in targets,
                    "two distinct stores share target: " + original["current_path"] +
                    " and " + targets.get(destination, "?"))
            targets[destination] = original["current_path"]
        if policy == "preserve-magic-revision-CAS":
            require(original["observed_format_identity"].startswith("MIBR_"),
                    "broker format provenance disappeared")
        if policy == "preserve-crc":
            require(original["current_path"].endswith("/mibr-menu.conf"),
                    "menu CRC owner drifted")
        rows.append({
            "current_path_candidate": original["current_path"],
            "source_kind": original["kind"],
            "logical_id": original.get("logical_id"),
            "owner_role": owner,
            "native_format_or_conversion_policy": policy,
            "candidate_destination_path": destination,
            "a3_disposition": state,
            "a3_reason": reason,
            "a3_single_writer": writer,
            "reserved_future_name": None if reserved is None else NEW + reserved,
            "architecture_class": arch_class,
            "architecture_long_term_target":
                None if arch_target is None else NEW + arch_target,
            "architecture_sole_owner": arch_owner,
            "architecture_gate": arch_gate,
            "source_certainty": original["source_certainty"],
            "source_evidence": original["evidence"],
            "selected_observed_reader_api": original.get("observed_reader_api"),
            "selected_observed_writer_api": original.get("observed_writer_api"),
            "selected_native_format_identity": original.get("observed_format_identity"),
            "proposed_lifecycle": lifecycle_policy(owner, policy),
            "verified_destination_path": None,
            "requires_joint_reader_writer_cutover": destination is not None,
            "actual_writer_and_every_reader_qualified": False,
            "actual_boot_and_rollback_qualified": False,
            "candidate_not_migration_permission": True,
        })
    # Two names are related but are not the same file or grammar. Reject
    # future refactors which silently collapse them to one target.
    by_source = {r["current_path_candidate"]: r for r in rows}
    registry = by_source[OLD + "mibr-carplay-autodirect"]
    marker = by_source[OLD + "mibr-carplay-autodirect.enabled"]
    require(registry["reserved_future_name"] != marker["reserved_future_name"]
            and (registry["candidate_destination_path"] is None or
                 registry["candidate_destination_path"] !=
                 marker["candidate_destination_path"]),
            "Auto-Direct alias collision")
    reserved = [r["reserved_future_name"] for r in rows
                if r["reserved_future_name"] is not None]
    require(len(reserved) == len(set(reserved)),
            "two stores share one reserved future name")
    # Safe area has four stores; only the broker CAS files are user authority.
    for name in ("safe-voll", "safe-wide", "safe-center"):
        require(by_source[NEW + "config/mibr-" + name + ".conf"]
                ["a3_disposition"] == "MIGRATE", "safe-area authority moved")
    for path in (OLD + "mibr-carplay111-safearea.conf",
                 OLD + "mibr-carplay111-viewareas.conf"):
        require(by_source[path]["candidate_destination_path"] is None,
                "second writable safe-area store: " + path)
    # A file inside a held backup directory must stay with its directory.
    for row in rows:
        parent = row["current_path_candidate"].rsplit("/", 1)[0]
        if parent in by_source and by_source[parent][
                "native_format_or_conversion_policy"] == "hold-backup":
            require(row["candidate_destination_path"] is None,
                    "backup file split from its held directory: " +
                    row["current_path_candidate"])
    require(by_source[OLD + "mibr-carplay111-bit26.force-on"]
            ["candidate_destination_path"] is None and
            by_source[OLD + "mibr-carplay111-bit26.force-off"]
            ["candidate_destination_path"] is None,
            "conflicting marker pair cannot be independently mapped")
    output = {
        "schema": 1,
        "kind": "source-derived-proposed-destination-names",
        "status": "A3_DISPOSITION_PROPOSED_NOT_APPROVED_FOR_RUNTIME_MIGRATION",
        "counts": {
            "input_candidate_paths": len(rows),
            "canonical_carplay_groups": 13,
            "canonical_broker_CAS_files": 13,
            "additional_candidate_paths": len(specs),
            "target_names_proposed": len(targets),
            "held_without_target": len(rows) - len(targets),
            "a3_dispositions": {d: sum(r["a3_disposition"] == d for r in rows)
                                for d in DISPOSITIONS},
            "architecture_classes": {c: sum(r["architecture_class"] == c
                                            for r in rows)
                                     for c in ARCH_CLASSES},
            "unresolved_dynamic_source_leads":
                len(graph["unresolved_nonliteral_source_leads"]),
            "external_boot_restore_boundaries":
                len(graph["outside_project_boot_hook_restore_boundaries"]),
        },
        "records": rows,
        "unresolved_cross_layer_dependencies": [
            "installed firmware and generated C/Java/QNX/boot consumer closure",
            "CarPlay registry values versus separate legacy presence markers",
            "legacy nav files versus registry nav group: format and precedence",
            "retained original stock boot preimages and patch ownership",
            "single-writer activation, mount lease, RO/readback and power-loss recovery",
            "three exact firmware-specific profile adapters and installer lifecycle",
        ],
        "final_destination_reviewed": False,
        "migration_authorized": False,
    }
    return output


def require_migration_authorized(plan):
    if plan.get("migration_authorized") is not True or \
            plan.get("final_destination_reviewed") is not True:
        raise PlanError("A2/A3 proposal is not an authorized migration plan")
    raise PlanError("migration execution is intentionally not implemented here")


def self_test():
    graph = access.build(ROOT)
    plan = build(graph)
    assert plan["counts"]["input_candidate_paths"] == 63
    assert plan["counts"]["additional_candidate_paths"] == 37
    assert not plan["migration_authorized"]
    rows = {r["current_path_candidate"]: r for r in plan["records"]}
    assert rows[OLD + "altscreen-u2/config/mibr-menu.conf"][
        "native_format_or_conversion_policy"] == "preserve-crc"
    counts = plan["counts"]["a3_dispositions"]
    assert counts == {"MIGRATE": 18, "KEEP_AT_LEGACY": 40,
                      "EXCLUDE_NONCONFIG": 2, "BLOCKED_INPUT": 3}, counts
    assert plan["counts"]["target_names_proposed"] == 18
    for row in plan["records"]:
        assert (row["candidate_destination_path"] is not None) == \
            (row["a3_disposition"] == "MIGRATE"), row["current_path_candidate"]
        assert row["a3_reason"] in REASONS
        assert (row["a3_single_writer"] is not None) == \
            (row["a3_disposition"] == "MIGRATE")
    # Auto-Direct registry value and boot-presence marker: both kept, two
    # distinct reserved names, no shared target.
    assert rows[OLD + "mibr-carplay-autodirect"]["candidate_destination_path"] is None
    assert rows[OLD + "mibr-carplay-autodirect"]["reserved_future_name"] == \
        NEW + "config/carplay/auto-direct.conf"
    assert rows[OLD + "mibr-carplay-autodirect.enabled"][
        "reserved_future_name"] == NEW + "config/features/auto-direct.conf"
    assert rows[OLD + "mibr-carplay-autodirect.enabled"][
        "candidate_destination_path"] is None
    assert rows[NEW + "config/mibr-sd-log.conf"]["a3_disposition"] == "BLOCKED_INPUT"
    assert rows[NEW + "config/mibr-safe-voll.conf"][
        "candidate_destination_path"] == NEW + "config/cockpit/safe-voll.conf"
    assert rows[OLD + "mibr-isotx2-gate-backup/startup.sh.stock"][
        "candidate_destination_path"] is None
    assert rows[OLD + "mibr-parity-status-enabled"][
        "native_format_or_conversion_policy"] == "preserve-value-boolean-default-on"
    assert rows[NEW + "config/mibr-calib.avcc"]["a3_disposition"] == \
        "EXCLUDE_NONCONFIG"
    assert all(r["a3_disposition"] == "KEEP_AT_LEGACY" for r in plan["records"]
               if r["source_kind"] == "carplay-registry-group")
    arch = plan["counts"]["architecture_classes"]
    assert arch == {"MIGRATE_AS_PLANNED": 18, "KEEP_TECHNICALLY_REQUIRED": 1,
                    "DEFER_MIGRATION": 19, "CONSOLIDATE_OR_RETIRE": 13,
                    "EXCLUDE_NONCONFIG": 7, "BLOCKED_INPUT": 5}, arch
    # KEEP now is not the end state: the registry groups have a long-term
    # target under config/carplay/ and one persistent owner.
    viewareas = rows[OLD + "mibr-carplay111-viewareas.conf"]
    assert viewareas["architecture_class"] == "DEFER_MIGRATION"
    assert viewareas["architecture_long_term_target"] == \
        NEW + "config/carplay/viewareas.conf"
    assert rows[OLD + "mibr-carplay-autodirect"]["architecture_class"] == \
        "CONSOLIDATE_OR_RETIRE"
    assert rows[OLD + "mibr-isotx2-gate-disable"]["architecture_class"] == \
        "KEEP_TECHNICALLY_REQUIRED"
    for name in ("safearea.conf", "nav.surface", "url-map.enabled"):
        assert rows[OLD + "mibr-carplay111-" + name][
            "architecture_long_term_target"] is None
    for modifier in ("arch-contradiction", "arch-hold-deferred",
                     "arch-missing"):
        arch_specs = copy.deepcopy(arch_spec())
        key = OLD + "mibr-carplay111-nav.surface"
        if modifier == "arch-contradiction":
            arch_specs[OLD + "mibr-deploy-most20-owned"] = (
                "DEFER_MIGRATION", "version/ownership/most20.marker", "x", "y")
        elif modifier == "arch-hold-deferred":
            arch_specs[key] = ("DEFER_MIGRATION",
                               "config/navigation/surface.conf", "x", "y")
        else:
            del arch_specs[key]
        try:
            build(graph, None, arch_specs)
        except PlanError:
            pass
        else:
            raise AssertionError("architecture mutation passed: " + modifier)
    assert rows[OLD + "mibr-alt111-keyframe-policy.enabled"][
        "native_format_or_conversion_policy"] == "convert-presence"
    assert rows[OLD + "mibr-carplay111-nav.surface"][
        "candidate_destination_path"] is None
    assert rows[OLD + "altscreen-u2/config/mibr-v3-single-writer.enabled"][
        "candidate_destination_path"] is None
    assert all(r["verified_destination_path"] is None for r in plan["records"])
    assert rows[OLD + "mibr-isotx2-gate-backup/startup.sh.stock"][
        "proposed_lifecycle"]["user_reset"] == "never-delete-stock-preimage"
    assert rows[OLD + "mibr-kit/components.manifest"][
        "proposed_lifecycle"]["user_reset"] == "not-a-user-preference"
    assert rows[OLD + "mibr-carplay111-viewareas.conf"][
        "proposed_lifecycle"]["upgrade"].startswith("preserve-current-user-intent")
    assert not valid_target("config/carplay/../bad.conf")
    assert not valid_target("/tmp/mibr-danger.conf")
    assert not valid_target("config/carplay/unsafe.tmp")
    for modifier in ("unknown", "collision", "unsafe", "completed",
                     "hold-migrate", "keep-collision", "value-presence",
                     "backup-split", "safe-area-second", "no-writer",
                     "bad-disposition"):
        altered = copy.deepcopy(graph)
        specs = copy.deepcopy(source_spec())
        if modifier == "unknown":
            altered["records"][0]["current_path"] = OLD + "unknown-new-file"
        elif modifier == "collision":
            specs[OLD + "altscreen-u2/config/mibr-menu-language.conf"][
                "relative_target"] = "config/menu/layout.conf"
        elif modifier == "unsafe":
            specs[OLD + "altscreen-u2/config/mibr-menu-language.conf"][
                "relative_target"] = "config/menu/../bad.conf"
        elif modifier == "hold-migrate":
            item = specs[OLD + "mibr-carplay111-nav.surface"]
            item.update(disposition="MIGRATE", relative_target=
                        "config/navigation/surface.conf",
                        writer="gen2_nav_config.sh")
        elif modifier == "keep-collision":
            specs[OLD + "mibr-carplay-autodirect.enabled"][
                "relative_target"] = "config/carplay/auto-direct.conf"
        elif modifier == "value-presence":
            specs[OLD + "mibr-parity-status-enabled"][
                "format_policy"] = "convert-presence"
        elif modifier == "backup-split":
            item = specs[OLD + "mibr-isotx2-gate-backup/startup.sh.stock"]
            item.update(disposition="MIGRATE", writer="install_preload.sh",
                        relative_target="backup/early-boot/startup.sh.stock")
        elif modifier == "safe-area-second":
            item = specs[OLD + "mibr-carplay111-safearea.conf"]
            item.update(disposition="MIGRATE", format_policy="preserve-native",
                        relative_target="config/cockpit/safearea.conf",
                        writer="gen2_safearea.sh")
        elif modifier == "no-writer":
            specs[OLD + "mibr-deploy-most20-owned"]["writer"] = None
        elif modifier == "bad-disposition":
            specs[OLD + "mibr-rgi/rgi.on"]["disposition"] = "MAYBE"
        else:
            altered["migration_authorized"] = True
        try:
            build(altered, specs)
        except PlanError:
            pass
        else:
            raise AssertionError("unsafe source/target mutation passed: " + modifier)
    try:
        require_migration_authorized(plan)
    except PlanError:
        pass
    else:
        raise AssertionError("unqualified plan allowed file migration")
    print("STORAGE_DESTINATION_PLAN_SELF_TEST=PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--require-migration-ready", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    plan = build(access.build(ROOT))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n",
                                 encoding="utf-8")
    if args.require_migration_ready:
        require_migration_authorized(plan)
    print("STORAGE_DESTINATION_PLAN=PROPOSED " +
          json.dumps(plan["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
