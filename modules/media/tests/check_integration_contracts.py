#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ensure P1/P2 bridge contracts match the ONE MIBR runtime and all 3 profiles.

This checks source and package *exclusion*, not QNX/J9 linkage or on-car approval.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROFILES = ("skoda-mu1440-p4526", "seat-mu1409-p4708", "seat-mu1447-p4709")
CONTRACT = "mibr-module-binding/1"
ROOT_ON_UNIT = "/mnt/app/root/mibr"


def json_file(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def literal_assignment(path, name):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    matches = [node.value for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]
    assert len(matches) == 1, (path, name)
    return ast.literal_eval(matches[0])


def check():
    index = json_file("modules/module-index.json")
    assert index["profiles"] == list(PROFILES)
    for module in ("media", "phone"):
        item = index["modules"][module]
        assert item["distribution"] == "common/" + module
        assert set(item["depends_on"]) == {"carplay", "broker"}
        assert not item["runtime"] and not item["outputs"]
        assert "host" in item["build_coverage"]
        assert all((ROOT / src).is_dir() for src in item["source"])

    # The canonical release assembler must not stage an unbuilt source-only
    # module as a runtime or a default shared package.
    assembler = "tools/release/build_modular.py"
    assert literal_assignment(assembler, "APP") == ROOT_ON_UNIT
    assert not set(("media", "phone")) & set(literal_assignment(assembler, "MODULES"))
    text = (ROOT / assembler).read_text(encoding="utf-8")
    assert "common/media/bin/" not in text and "common/phone/bin/" not in text

    registry = json_file("settings/registry.json")
    keys = {s["key"] for s in registry["settings"]}
    switches = {s["id"] for s in registry["switches"]}
    assert not any(k.startswith(("media.", "phone.")) for k in keys)
    assert not any(k.startswith(("media_", "phone_")) for k in switches)
    # Do not claim these are switchable through MIBR/3 until a single canonical
    # broker registry change + code-generation + ACTION/ACK is tested.
    for name in PROFILES:
        p = json_file(f"modules/profiles/{name}/profile.json")
        c = json_file(f"modules/profiles/{name}/integration/media-phone-abi.json")
        i = c["integration_contract"]
        assert p["profile_id"] == c["profile"] == name
        assert p["selector"]["source"] == i["profile_selector_source"] == "/ifs/lsd.jxe"
        assert p["selector"]["digest"] == c["original_lsd_jxe_sha256"] == i["profile_selector_sha256"]
        assert p["firmware"] == c["firmware"]
        assert p["hmi"]["api_jar_sha256"] == i["hmi_api_jar_sha256"]
        assert i["schema"] == CONTRACT and i["project_runtime_root"] == ROOT_ON_UNIT
        assert i["control_plane"] == "MIBR/3"
        assert i["control_owner"] == "modules/broker/source/mibr-control"
        assert i["settings_registry"] == "settings/registry.json"
        assert i["control_binding"] == "not-implemented" and i["registry_key"] is None
        assert i["desired_enabled"] == "off"
        assert i["runtime_activation"] == "BLOCKED_PENDING_QUALIFIED_OWNER_ACK"
        assert i["data_plane"] == "existing-authenticated-iap2-owner"
        assert i["new_socket_service"] is False and i["new_iap2_session"] is False
        assert i["compiled_j9_adapter"] is None and i["build_recipe"] is None
        assert i["unit_rollback_receipt"] is None and i["safe_behavior"] == "STOCK_UNMODIFIED"
        for feature in ("media", "phone"):
            m = c[feature]
            assert m["status"] == "pending-exact-abi"
            assert m["auto_install"] is False and m["compiled_artifact"] is None
            assert (ROOT / m["common_model"]).is_file()
            assert (ROOT / m["reference_only"]).is_dir()
        assert (ROOT / i["media_ingress_source"]).is_file()
        assert (ROOT / i["phone_ingress_source"]).is_file()
        assert i["native_media_oem_sink"].startswith("pending-")
        assert i["native_phone_oem_sink"].startswith("pending-")
    print("MEDIA_PHONE_MIBR3_THREE_PROFILE_CONTRACT=PASS")


if __name__ == "__main__":
    check()
