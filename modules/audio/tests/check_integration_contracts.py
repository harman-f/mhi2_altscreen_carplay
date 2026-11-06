#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""P6 source-only integration: exact profile, one MIBR/3 and no packaged audio."""
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PROFILES=("skoda-mu1440-p4526","seat-mu1409-p4708","seat-mu1447-p4709")
UNIT_ROOT="/mnt/app/root/mibr"

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def assign(path,name):
    tree=ast.parse((ROOT/path).read_text(encoding="utf-8"))
    found=[n.value for n in tree.body if isinstance(n,ast.Assign)
           and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
    assert len(found)==1
    return ast.literal_eval(found[0])

def verify():
    d=load("modules/module-index.json")
    assert d["profiles"]==list(PROFILES)
    a=d["modules"]["audio"]
    assert a["distribution"]=="common/audio"
    assert set(a["depends_on"])=={"carplay","broker"}
    assert not a["runtime"] and not a["outputs"]
    assert all((ROOT/p).is_dir() for p in a["source"])
    assert "host" in a["build_coverage"]

    pack="tools/release/build_modular.py"
    assert assign(pack,"APP")==UNIT_ROOT
    assert "audio" not in assign(pack,"MODULES")
    assert "common/audio/bin/" not in (ROOT/pack).read_text(encoding="utf-8")
    reg=load("settings/registry.json")
    assert not any(k["key"].startswith("audio.") for k in reg["settings"])
    assert not any(k["id"].startswith("audio_") for k in reg["switches"])
    for name in PROFILES:
        p=load(f"modules/profiles/{name}/profile.json")
        a=load(f"modules/profiles/{name}/integration/audio-abi.json")
        c=a["integration_contract"]
        v=a["audio"]
        assert p["profile_id"]==a["profile"]==name
        assert p["firmware"]==a["firmware"]
        assert p["selector"]["source"]==c["profile_selector_source"]=="/ifs/lsd.jxe"
        assert p["selector"]["digest"]==a["original_lsd_jxe_sha256"]==c["profile_selector_sha256"]
        assert p["hmi"]["api_jar_sha256"]==c["hmi_api_jar_sha256"]
        assert c["schema"]=="mibr-module-binding/1"
        assert c["project_runtime_root"]==UNIT_ROOT
        assert c["control_plane"]=="MIBR/3" and c["control_owner"]=="modules/broker/source/mibr-control"
        assert c["settings_registry"]=="settings/registry.json"
        assert c["control_binding"]=="not-implemented" and c["registry_key"] is None
        assert c["desired_enabled"]=="off"
        assert c["runtime_activation"]=="BLOCKED_PENDING_QUALIFIED_AUDIO_OWNER_ACK"
        assert c["data_plane"]=="existing-stock-audio-owner"
        assert not c["new_socket_service"] and not c["new_audio_daemon"] and not c["new_carplay_session"]
        assert c["qnx_pcm_sink"].startswith("pending-")
        assert c["most_channel_mapping"].startswith("pending-")
        assert c["compiled_audio_adapter"] is None and c["compiled_j9_adapter"] is None
        assert c["build_recipe"] is None and c["unit_rollback_receipt"] is None
        assert c["safe_behavior"]=="STOCK_UNMODIFIED"
        assert (ROOT/c["existing_audio_owner_source"]).is_file()
        assert v["status"]=="pending-exact-audio-abi"
        assert v["auto_install"] is False and v["compiled_artifact"] is None
        assert v["spatial_audio_enabled"] is False and v["stereo_upmix_enabled"] is False
    print("AUDIO_MIBR3_THREE_PROFILE_CONTRACT=PASS")

if __name__=="__main__":
    verify()
