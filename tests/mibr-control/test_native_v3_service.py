"""Actual loopback MIBR/3 service against the pinned original C core; host-only."""
import os
import shutil
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from test_native_v3_readonly import APP, api
from public_paths import write_default_profile
BIN=os.environ.get("MIBR_V3_NATIVE_SERVICE_BIN")
CLI=os.environ.get("MIBR_V3_NATIVE_CLIENT_BIN")
ENGINE_CONFIG=APP/"release/visual-qa-pr95-r43/mibr-r43-identify-vehicle-pascd/iap2.cfg.new"
@unittest.skipUnless(BIN,"requires pinned original C host service build")
class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="v3-svc-")
        base=Path(self.temp.name)
        (base/"temp").mkdir();(base/"persistent").mkdir()
        self.secret=base/"client.secret"
        self.secret.write_text("a"*64+"\n")
        self.secret.chmod(0o600)
        env={**os.environ,"ALT111_SETTINGS_TEMP_ROOT":str(base/"temp"),
             "ALT111_SETTINGS_PERSISTENT_ROOT":str(base/"persistent"),
             "MIBR_V3_HOST_SCALING_PATH":str(base/"persistent"/"display-scaling.conf"),
             "MIBR_V3_HOST_SCALING_STATUS_PATH":str(base/"scaling.status"),
             "MIBR_V3_HOST_CARPLAY_NAV_PATH":str(base/"persistent"/"mibr-carplay-nav.conf"),
             "MIBR_V3_HOST_SD_LOG_PATH":str(base/"persistent"/"mibr-sd-log.conf")}
        self.env=env
        self.start_service()
        ready=self.p.stdout.readline().strip()
        if not ready and self.p.poll() is not None:
            ready="exit=%s stderr=%s"%(self.p.returncode,self.p.stderr.read())
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
        self.port=int(ready.split("=")[1])
    def start_service(self):
        self.p=subprocess.Popen([BIN,"--port","0","--secret-file",str(self.secret)],
                  env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    def restart_service(self, input_secret=None):
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        args=[BIN,"--port","0","--secret-file",str(self.secret)]
        if input_secret is not None:
            args.extend(["--input-secret-file",str(input_secret)])
        self.p=subprocess.Popen(args,env=self.env,stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,text=True)
        ready=self.p.stdout.readline().strip()
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
        self.port=int(ready.split("=")[1])
    def tearDown(self):
        self.p.terminate()
        self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close();self.temp.cleanup()
    def wire(self,b):
        with socket.create_connection(("127.0.0.1",self.port),timeout=3) as s:
            s.sendall(b)
            chunks=[];size=0
            while size<16384:
                piece=s.recv(4096)
                if not piece: break
                chunks.append(piece);size+=len(piece)
                if b"\n" in piece: break
            return b"".join(chunks)
    def req(self,rid,op,args=None,secret="a"*64):
        line=api.request(rid,op,args)
        return api.parse(self.wire(line[:-1]+
             (b";" if args else b" ")+b"auth="+secret.encode()+b"\n"),is_response=True)
    def test_readonly_transport_and_authorization(self):
        self.assertEqual(self.req("a","HELLO")["fields"]["version"],"MIBR/3")
        self.assertEqual(self.req("b","CAPABILITIES")["fields"]["durable_set"],"0")
        self.assertEqual(self.req("c","SNAPSHOT",{"scope":"ui"})["fields"]["row_count"],"11")
        self.assertEqual(self.req("d","SNAPSHOT",{"scope":"all"})["error"],"FORBIDDEN")
        self.assertEqual(self.req("e","SET",{"key":"maxFPS"})["error"],"POLICY_BLOCKED")
        self.assertEqual(self.req("f","GET",{"key":"keyframe.mode"})["error"],"FORBIDDEN")
        self.assertEqual(self.req("g","HELLO",secret="b"*64)["error"],"AUTH_REQUIRED")
        self.assertEqual(api.parse(self.wire(b"MIBR/3 h HELLO\n"),is_response=True)["error"],"AUTH_REQUIRED")
        self.assertEqual(self.req("i","HELLO",{"unexpected":"yes"})["error"],"INVALID_REQUEST")
    def test_carplay_navigation_switch_cas_persistence(self):
        self.assertEqual(self.req("nav_cap","CAPABILITIES")["fields"]["carplay_nav"],"1")
        got=self.req("nav_get0","CARPLAY_NAV_GET")
        self.assertIsNone(got["error"],got)
        self.assertEqual((got["fields"]["value"],got["fields"]["stored"],got["fields"]["revision"],
                          got["fields"]["writer"]),("off","DEFAULT","0","ENABLED"))
        saved=self.req("nav_set1","CARPLAY_NAV_SET",{"value":"on","expected_revision":"0","request_id":"nav_set1"})
        self.assertIsNone(saved["error"],saved)
        self.assertEqual((saved["fields"]["value"],saved["fields"]["revision"]),("on","1"))
        path=Path(self.env["MIBR_V3_HOST_CARPLAY_NAV_PATH"])
        self.assertEqual(path.read_text(),"MIBR_CARPLAY_NAV/1\nrevision=1\nvalue=on\n")
        # replayed request id answers from the receipt, a changed frame with the same id is refused
        again=self.req("nav_set1","CARPLAY_NAV_SET",{"value":"on","expected_revision":"0","request_id":"nav_set1"})
        self.assertEqual(again["fields"]["revision"],"1")
        self.assertEqual(self.req("nav_set1","CARPLAY_NAV_SET",{"value":"off","expected_revision":"0",
                         "request_id":"nav_set1"})["error"],"IDEMPOTENCY_COLLISION")
        self.assertEqual(self.req("nav_stale","CARPLAY_NAV_SET",{"value":"off","expected_revision":"0",
                         "request_id":"nav_stale"})["error"],"STALE_REVISION")
        self.assertEqual(self.req("nav_bad","CARPLAY_NAV_SET",{"value":"yes","expected_revision":"1",
                         "request_id":"nav_bad"})["error"],"INVALID_REQUEST")
        self.restart_service()
        got=self.req("nav_get1","CARPLAY_NAV_GET")
        self.assertEqual((got["fields"]["value"],got["fields"]["stored"],got["fields"]["revision"]),
                         ("on","VERIFIED","1"))
        off=self.req("nav_set2","CARPLAY_NAV_SET",{"value":"off","expected_revision":"1","request_id":"nav_set2"})
        self.assertEqual((off["fields"]["value"],off["fields"]["revision"]),("off","2"))
    def test_sd_log_switch_cas_persistence(self):
        self.assertEqual(self.req("sdl_cap","CAPABILITIES")["fields"]["sd_log"],"1")
        got=self.req("sdl_get0","SD_LOG_GET")
        self.assertIsNone(got["error"],got)
        self.assertEqual((got["fields"]["value"],got["fields"]["stored"],got["fields"]["revision"],
                          got["fields"]["writer"]),("off","DEFAULT","0","ENABLED"))
        saved=self.req("sdl_set1","SD_LOG_SET",{"value":"on","expected_revision":"0","request_id":"sdl_set1"})
        self.assertIsNone(saved["error"],saved)
        self.assertEqual((saved["fields"]["value"],saved["fields"]["revision"]),("on","1"))
        path=Path(self.env["MIBR_V3_HOST_SD_LOG_PATH"])
        self.assertEqual(path.read_text(),"MIBR_SD_LOG/1\nrevision=1\nvalue=on\n")
        # replayed request id answers from the receipt, a changed frame with the same id is refused
        again=self.req("sdl_set1","SD_LOG_SET",{"value":"on","expected_revision":"0","request_id":"sdl_set1"})
        self.assertEqual(again["fields"]["revision"],"1")
        self.assertEqual(self.req("sdl_set1","SD_LOG_SET",{"value":"off","expected_revision":"0",
                         "request_id":"sdl_set1"})["error"],"IDEMPOTENCY_COLLISION")
        self.assertEqual(self.req("sdl_stale","SD_LOG_SET",{"value":"off","expected_revision":"0",
                         "request_id":"sdl_stale"})["error"],"STALE_REVISION")
        self.assertEqual(self.req("sdl_bad","SD_LOG_SET",{"value":"yes","expected_revision":"1",
                         "request_id":"sdl_bad"})["error"],"INVALID_REQUEST")
        self.restart_service()
        got=self.req("sdl_get1","SD_LOG_GET")
        self.assertEqual((got["fields"]["value"],got["fields"]["stored"],got["fields"]["revision"]),
                         ("on","VERIFIED","1"))
        off=self.req("sdl_set2","SD_LOG_SET",{"value":"off","expected_revision":"1","request_id":"sdl_set2"})
        self.assertEqual((off["fields"]["value"],off["fields"]["revision"]),("off","2"))
    def test_display_scaling_native_cas_persistence_and_truthful_unknowns(self):
        caps=self.req("scale_cap","CAPABILITIES")["fields"]
        self.assertEqual(caps["scaling"],"1")
        main=self.req("scale_get0","SCALE_GET",{"id":"scaling.main.zoomFactor"})
        self.assertIsNone(main["error"],main)
        self.assertEqual(main["fields"]["desired"],"AUTO")
        self.assertEqual(main["fields"]["writer"],"ENABLED")
        self.assertEqual(main["fields"]["effective"],"UNKNOWN")
        saved=self.req("scale_set1","SCALE_SET",{
            "id":"scaling.main.zoomFactor","value":"100","expected_revision":"0",
            "request_id":"scale_set1"})
        self.assertIsNone(saved["error"],saved)
        self.assertEqual((saved["fields"]["desired"],saved["fields"]["revision"],
                          saved["fields"]["stored"],saved["fields"]["effective"],
                          saved["fields"]["pending"]),("100","1","VERIFIED","UNKNOWN","1"))
        scaling=Path(self.env["MIBR_V3_HOST_SCALING_PATH"])
        self.assertEqual(scaling.read_text(),"MIBR_SCALING/3\nrevision=1\nmain=100\ncluster=AUTO\nphysical=BASE\nmain_physical=BASE\n")
        physical=self.req("scale_physical0","SCALE_GET",{"id":"scaling.cluster.physicalSize"})["fields"]
        self.assertEqual((physical["desired"],physical["stored"],physical["effective"]),("BASE","VERIFIED","UNKNOWN"))
        main_physical=self.req("scale_main_physical0","SCALE_GET",{"id":"scaling.main.physicalSize"})["fields"]
        self.assertEqual((main_physical["id"],main_physical["desired"],main_physical["stored"]),
                         ("scaling.main.physicalSize","BASE","VERIFIED"))
        main_size=self.req("scale_main_physical1","SCALE_SET",{
            "id":"scaling.main.physicalSize","value":"P30","expected_revision":"1",
            "request_id":"scale_main_physical1"})
        self.assertIsNone(main_size["error"],main_size)
        self.assertEqual(main_size["fields"]["desired"],"P30")
        self.assertEqual(scaling.read_text(),"MIBR_SCALING/3\nrevision=2\nmain=100\ncluster=AUTO\nphysical=BASE\nmain_physical=P30\n")
        self.assertEqual(self.req("scale_set1","SCALE_SET",{
            "id":"scaling.main.zoomFactor","value":"100","expected_revision":"0",
            "request_id":"scale_set1"}),saved)
        status=Path(self.env["MIBR_V3_HOST_SCALING_STATUS_PATH"])
        status.write_text("MIBR_SCALING_ADVERTISED/3\nrevision=2\nmain=100\ncluster=AUTO\nphysical=BASE\nmain_physical=P30\n")
        observed=self.req("scale_get2","SCALE_GET",{"id":"scaling.cluster.zoomFactor"})["fields"]
        self.assertEqual((observed["desired"],observed["revision"],observed["advertised"],
                          observed["advertised_scope"],observed["pending"],observed["effective"]),
                         ("AUTO","2","AUTO","HISTORICAL","1","UNKNOWN"))
        status.write_text("MIBR_SCALING_ADVERTISED/3\nrevision=0\nmain=100\ncluster=AUTO\nphysical=BASE\nmain_physical=P30\n")
        stale=self.req("scale_stale_advert","SCALE_GET",{"id":"scaling.main.zoomFactor"})["fields"]
        self.assertEqual((stale["advertised"],stale["advertised_scope"],stale["pending"],stale["effective"]),
                         ("UNKNOWN","UNKNOWN","1","UNKNOWN"))
        status.write_text("corrupt\n")
        corrupt=self.req("scale_corrupt_advert","SCALE_GET",{"id":"scaling.main.zoomFactor"})["fields"]
        self.assertEqual((corrupt["advertised"],corrupt["pending"],corrupt["effective"]),
                         ("UNKNOWN","1","UNKNOWN"))
        self.assertEqual(self.req("scale_stale","SCALE_SET",{
            "id":"scaling.cluster.zoomFactor","value":"125","expected_revision":"0",
            "request_id":"scale_stale"})["error"],"STALE_REVISION")
        explicit_auto=self.req("scale_auto","SCALE_SET",{
            "id":"scaling.main.zoomFactor","value":"AUTO","expected_revision":"2",
            "request_id":"scale_auto"})
        self.assertIsNone(explicit_auto["error"],explicit_auto)
        self.assertEqual(Path(str(scaling)+".lastgood").read_text(),
                         "MIBR_SCALING/3\nrevision=2\nmain=100\ncluster=AUTO\nphysical=BASE\nmain_physical=P30\n")

    def test_physical_preset_writes_both_mm_values_atomically_as_single_cas(self):
        saved=self.req("size30","SCALE_SET",{
            "id":"scaling.cluster.physicalSize","value":"P30","expected_revision":"0",
            "request_id":"size30"})
        self.assertIsNone(saved["error"],saved)
        self.assertEqual((saved["fields"]["desired"],saved["fields"]["apply"],
                          saved["fields"]["effective"]),("P30","RECONNECT","UNKNOWN"))
        stored=Path(self.env["MIBR_V3_HOST_SCALING_PATH"]).read_text()
        self.assertEqual(stored,"MIBR_SCALING/3\nrevision=1\nmain=AUTO\ncluster=AUTO\nphysical=P30\nmain_physical=BASE\n")
        original=self.req("size_base","SCALE_SET",{
            "id":"scaling.cluster.physicalSize","value":"BASE","expected_revision":"1",
            "request_id":"size_base"})
        self.assertIsNone(original["error"],original)
        self.assertIn("physical=BASE\n",Path(self.env["MIBR_V3_HOST_SCALING_PATH"]).read_text())
        invalid=self.req("size_bad","SCALE_SET",{
            "id":"scaling.cluster.physicalSize","value":"P25","expected_revision":"2",
            "request_id":"size_bad"})
        self.assertEqual(invalid["error"],"INVALID_REQUEST")

    def test_bad_scaling_input_is_rejected_without_persistence(self):
        for rid,key,value in (("badrow","display.zoomFactor","125"),
                              ("badvalue","scaling.main.zoomFactor","101")):
            result=self.req(rid,"SCALE_SET",{"id":key,"value":value,
                "expected_revision":"0","request_id":rid})
            self.assertEqual(result["error"],"INVALID_REQUEST")
        self.assertFalse(Path(self.env["MIBR_V3_HOST_SCALING_PATH"]).exists())

    def test_scaling_rw_refusal_does_not_mutate_file(self):
        self.env["MIBR_V3_HOST_SCALING_FAIL_RW"]="1"
        self.restart_service()
        result=self.req("scale_rw_fail","SCALE_SET",{"id":"scaling.main.zoomFactor",
            "value":"85","expected_revision":"0","request_id":"scale_rw_fail"})
        self.assertEqual(result["error"],"STORAGE_UNAVAILABLE")
        self.assertFalse(Path(self.env["MIBR_V3_HOST_SCALING_PATH"]).exists())

    def test_scaling_ro_restore_failure_has_no_success_and_disables_writer(self):
        self.env["MIBR_V3_HOST_SCALING_FAIL_RO"]="1"
        self.restart_service()
        result=self.req("scale_ro_fail","SCALE_SET",{"id":"scaling.main.zoomFactor",
            "value":"70","expected_revision":"0","request_id":"scale_ro_fail"})
        self.assertEqual(result["error"],"RO_RESTORE_FAILED")
        fields=self.req("scale_ro_get","SCALE_GET",{"id":"scaling.main.zoomFactor"})["fields"]
        self.assertEqual((fields["desired"],fields["revision"],fields["writer"],
                          fields["effective"],fields["pending"]),
                         ("70","1","DISABLED","UNKNOWN","1"))
        again=self.req("scale_ro_again","SCALE_SET",{"id":"scaling.main.zoomFactor",
            "value":"85","expected_revision":"1","request_id":"scale_ro_again"})
        self.assertEqual(again["error"],"POLICY_BLOCKED")

    def test_scaling_receipt_replay_does_not_bypass_input_role(self):
        input_secret=Path(self.temp.name)/"input.secret"
        input_secret.write_text("b"*64+"\n")
        input_secret.chmod(0o600)
        self.restart_service(input_secret)
        request={"id":"scaling.main.zoomFactor","value":"125",
                 "expected_revision":"0","request_id":"scale_role_replay"}
        ui=self.req("scale_role_replay","SCALE_SET",request)
        self.assertIsNone(ui["error"],ui)
        replay=self.req("scale_role_replay","SCALE_SET",request,secret="b"*64)
        self.assertEqual(replay["error"],"FORBIDDEN")
        self.assertEqual(Path(self.env["MIBR_V3_HOST_SCALING_PATH"]).read_text(),
            "MIBR_SCALING/3\nrevision=1\nmain=125\ncluster=AUTO\nphysical=BASE\nmain_physical=BASE\n")

    def test_scaling_get_refreshes_external_drift_before_cas(self):
        path=Path(self.env["MIBR_V3_HOST_SCALING_PATH"])
        path.write_text("MIBR_SCALING/1\nrevision=1\nmain=125\ncluster=AUTO\n")
        fields=self.req("scale_drift_get","SCALE_GET",{
            "id":"scaling.main.zoomFactor"})["fields"]
        self.assertEqual((fields["desired"],fields["revision"]),("125","1"))
        stale=self.req("scale_drift_set","SCALE_SET",{"id":"scaling.cluster.zoomFactor",
            "value":"150","expected_revision":"0","request_id":"scale_drift_set"})
        self.assertEqual(stale["error"],"STALE_REVISION")
        self.assertEqual(path.read_text(),
            "MIBR_SCALING/1\nrevision=1\nmain=125\ncluster=AUTO\n")

    def test_invalid_scaling_file_disables_only_scaling(self):
        path=Path(self.env["MIBR_V3_HOST_SCALING_PATH"])
        path.write_text("MIBR_SCALING/1\nrevision=01\nmain=AUTO\ncluster=AUTO\n")
        self.restart_service()
        caps=self.req("bad_scale_cap","CAPABILITIES")["fields"]
        self.assertEqual(caps["scaling"],"0")
        self.assertEqual(self.req("bad_scale_get","SCALE_GET",{
            "id":"scaling.main.zoomFactor"})["error"],"NOT_READY")
        self.assertIsNone(self.req("still_alive","HELLO")["error"])

    def durable_service(self):
        cli=os.environ.get("MIBR_PINNED_ALT111_CLI")
        self.assertTrue(cli)
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        profile=Path(self.temp.name)/"cpvc-r5.profile"
        write_default_profile(profile)
        self.env["MIBR_V3_HOST_PROFILE_PATH"]=str(profile)
        subprocess.run([cli,"batch","--input",str(profile),"--layer","temp"],
            env=self.env,capture_output=True,text=True,check=True,timeout=5)
        self.start_service()
        ready=self.p.stdout.readline().strip()
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
        self.port=int(ready.split("=")[1])
    def show_state(self,rid):
        raw=self.wire(("MIBR/3 %s SHOW_STATUS auth=%s"%(rid,"a"*64)).encode()+chr(10).encode()).decode()
        self.assertIn(" OK ",raw,raw)
        return raw.split("state=")[1].split(";")[0].strip()
    def snapshot_row(self,key):
        snap=self.req("s"+key[:3],"SNAPSHOT",{"scope":"ui"})
        self.assertIsNone(snap["error"],snap)
        fields=snap["fields"]
        for i in range(11):
            if fields["row.%d.key"%i]==key:
                return fields["row.%d.value"%i],fields["revision"]
        self.fail("row missing")
    @unittest.skipUnless(ENGINE_CONFIG.is_file(), "Research-only vehicle configuration fixture is omitted from the public source tree")
    def test_engine_type_get_set_through_helper_script(self):
        """r46: ENGINE_GET/ENGINE_SET run the helper on a COPY of the real iap2.cfg; values are enum-validated twice."""
        root=APP
        cfg=Path(self.temp.name)/"iap2.cfg"
        shutil.copyfile(ENGINE_CONFIG,cfg)
        self.p.terminate();self.p.wait(timeout=5);self.p.stdout.close();self.p.stderr.close()
        self.env.update({"MIBR_ENGINE_SHELL":shutil.which("bash") or "/bin/sh","MIBR_ENGINE_SCRIPT":str(root/"runtime/mibr-control/mibr-engine.ksh"),
                         "MIBR_ENGINE_CFG":str(cfg),"MIBR_ENGINE_BOOT":str(Path(self.temp.name)/"boot"),
                         "MIBR_ENGINE_LOCK":str(Path(self.temp.name)/"lock"),"MIBR_ENGINE_NOMOUNT":"1"})
        self.start_service()
        ready=self.p.stdout.readline().strip()
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
        self.port=int(ready.split("=")[1])
        got=self.req("e1","ENGINE_GET")
        self.assertEqual((got["error"],got["fields"]["engine"],got["fields"]["announced"],got["fields"]["pending"]),(None,"gas","gas","0"))
        got=self.req("e2","ENGINE_SET",{"value":"diesel"})
        self.assertEqual((got["error"],got["fields"]["engine"],got["fields"]["announced"],got["fields"]["pending"]),(None,"diesel","gas","1"))
        self.assertIn("engine=diesel",cfg.read_text())
        for bad in ("petrol","gas;x","Diesel"):
            self.assertEqual(self.req("e3","ENGINE_SET",{"value":bad})["error"],"INVALID_REQUEST")
        self.assertEqual(self.req("e4","ENGINE_SET")["error"],"INVALID_REQUEST")
        self.assertEqual(self.req("e5","ENGINE_GET",{"x":"1"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.req("e6","ENGINE_GET",secret="b"*64)["error"],"AUTH_REQUIRED")
        got=self.req("e7","ENGINE_SET",{"value":"gas"})
        self.assertEqual((got["fields"]["engine"],got["fields"]["pending"]),("gas","0"))
    def test_view_follow_get_set_through_helper_script(self):
        """r55: VIEW_GET/VIEW_SET run mibr-view.ksh against a temp state dir; key and value are allowlisted twice."""
        root=APP
        t=Path(self.temp.name)
        (t/"vd").mkdir()
        cli=t/"cli";cli.write_text("#!/bin/sh"+chr(10)+"exit 0"+chr(10))
        self.p.terminate();self.p.wait(timeout=5);self.p.stdout.close();self.p.stderr.close()
        sh=shutil.which("bash") or "/bin/sh"
        self.env.update({"MIBR_VIEW_SHELL":sh,"MIBR_VIEW_SCRIPT":str(root/"runtime/mibr-control/mibr-view.ksh"),
                         "MIBR_VIEW_DIR":str(t/"vd"),"MIBR_VIEW_NOMOUNT":"1","MIBR_VIEW_CLI":str(cli),
                         "MIBR_VIEW_POS":str(t/"vpos"),"MIBR_VIEW_GEN":str(t/"vgen"),"MIBR_VIEW_LOCK":str(t/"vlock"),
                         "MIBR_VIEW_AREA":str(t/"varea"),"MIBR_VIEW_LOG":str(t/"vlog"),"MIBR_VIEW_DEBOUNCE":"1"})
        self.start_service()
        ready=self.p.stdout.readline().strip()
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
        self.port=int(ready.split("=")[1])
        got=self.req("v1","VIEW_GET")
        self.assertEqual((got["error"],[got["fields"][k] for k in ("follow","sport","m0","m1","m4","rs","pos")]),
                         (None,["0","1","1","0","2","0","0"]))
        got=self.req("v1b","VIEW_SET",{"name":"rs","value":"4"})
        self.assertEqual((got["error"],got["fields"]["rs"]),(None,"4"))
        self.assertEqual(self.req("v1c","VIEW_SET",{"name":"rs","value":"5"})["error"],"INVALID_REQUEST")
        got=self.req("v2","VIEW_SET",{"name":"follow","value":"1"})
        self.assertEqual((got["error"],got["fields"]["follow"]),(None,"1"))
        got=self.req("v3","VIEW_SET",{"name":"pos","value":"4"})
        self.assertEqual((got["error"],got["fields"]["pos"]),(None,"4"))
        got=self.req("v4","VIEW_SET",{"name":"m4","value":"1"})
        self.assertEqual((got["error"],got["fields"]["m4"]),(None,"1"))
        for bad in ({"name":"follow","value":"2"},{"name":"pos","value":"5"},{"name":"m0","value":"3"},
                    {"name":"sport","value":"11"},{"name":"engine","value":"1"},{"name":"pos","value":"1;x"},
                    {"name":"pos"},{"value":"1"}):
            self.assertEqual(self.req("v5","VIEW_SET",bad)["error"],"INVALID_REQUEST",bad)
        self.assertEqual(self.req("v6","VIEW_GET",{"x":"1"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.req("v7","VIEW_GET",secret="b"*64)["error"],"AUTH_REQUIRED")
    def test_carplay_pause_through_the_menu_key(self):
        self.durable_service()
        pause=Path(self.temp.name)/"temp"/"mibr-parity-drive.pause"
        value,revision=self.snapshot_row("carplay.enabled")
        self.assertEqual(value,"1")
        out=self.req("p0","SET",{"key":"carplay.enabled","value":"0","expected_revision":revision,
                                  "activation":"AUTO","request_id":"p0"})
        self.assertIsNone(out["error"],out)
        self.assertEqual(out["fields"]["stored"],"RUNTIME_ONLY")
        self.assertTrue(pause.exists(),"pause file written")
        value,revision2=self.snapshot_row("carplay.enabled")
        self.assertEqual(value,"0","snapshot shows the live pause state")
        self.assertEqual(revision,revision2,"no settings revision change")
        out=self.req("p1","SET",{"key":"carplay.enabled","value":"1","expected_revision":revision2,
                                  "activation":"AUTO","request_id":"p1"})
        self.assertIsNone(out["error"],out)
        self.assertFalse(pause.exists(),"pause file removed")
        self.assertEqual(self.snapshot_row("carplay.enabled")[0],"1")
    def test_show_confirmation_only_from_gen2_completion(self):
        self.durable_service()
        temp=Path(self.temp.name)/"temp"
        self.assertEqual(self.show_state("w0"),"NONE")
        status=temp/"mibr-alt111-gen2.status"
        status.write_text("last_completed_request=5"+chr(10)+"last_completion_status=0"+chr(10))
        value,revision=self.snapshot_row("navigation.compass")
        wanted="no" if value!="no" else "yes"
        out=self.req("w1","SET",{"key":"navigation.compass","value":wanted,"expected_revision":revision,
                                  "activation":"AUTO","request_id":"w1"})
        self.assertIsNone(out["error"],out)
        self.assertEqual(self.show_state("w2"),"PENDING",
                         "a request alone never counts as shown")
        status.write_text("last_completed_request=6"+chr(10)+"last_completion_status=0"+chr(10))
        self.assertEqual(self.show_state("w3"),"SHOWN")
        value,revision=self.snapshot_row("navigation.compass")
        again="yes" if wanted=="no" else "no"
        status.write_text("last_completed_request=6"+chr(10)+"last_completion_status=0"+chr(10))
        self.req("w4","SET",{"key":"navigation.compass","value":again,"expected_revision":revision,
                              "activation":"AUTO","request_id":"w4"})
        status.write_text("last_completed_request=7"+chr(10)+"last_completion_status=3"+chr(10))
        self.assertEqual(self.show_state("w5"),"FAILED")
    def test_guarded_profile_commit_and_readback_host_only(self):
        cli=os.environ.get("MIBR_PINNED_ALT111_CLI")
        self.assertTrue(cli)
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        profile=Path(self.temp.name)/"cpvc-r5.profile"
        write_default_profile(profile)
        self.env["MIBR_V3_HOST_PROFILE_PATH"]=str(profile)
        subprocess.run([cli,"batch","--input",str(profile),"--layer","temp"],
            env=self.env,capture_output=True,text=True,check=True,timeout=5)
        self.start_service()
        ready=self.p.stdout.readline().strip()
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
        self.port=int(ready.split("=")[1])
        self.assertEqual(self.req("cap","CAPABILITIES")["fields"]["durable_set"],"1")
        before=self.req("pre","GET",{"key":"maxFPS"})["fields"]
        self.assertEqual(before["value"],"30")
        fields={"key":"maxFPS","value":"25","expected_revision":before["revision"],
                "activation":"AUTO","request_id":"save1"}
        out=self.req("save1","SET",fields)
        self.assertIsNone(out["error"],out)
        self.assertEqual(out["fields"]["stored"],"VERIFIED")
        self.assertEqual(out["fields"]["active"],"UNKNOWN")
        self.assertEqual(out["fields"]["apply"],"PENDING")
        self.assertEqual(out["fields"]["activation"],"UNIT_REBOOT")
        self.assertIn("maxFPS=25\n",profile.read_text())
        self.assertEqual(self.req("get","GET",{"key":"maxFPS"})["fields"]["value"],"25")
        self.assertEqual(self.req("stale","SET",{**fields,"request_id":"stale"})["error"],"STALE_REVISION")
        self.assertIn("maxFPS=30\n",(Path(str(profile)+".lastgood")).read_text())
        self.assertEqual(self.req("save1","SET",fields),out)  # identical ID+frame, no second flash write
        self.assertEqual(self.req("save1","SET",{**fields,"value":"30"})["error"],"IDEMPOTENCY_COLLISION")
        receipt=self.req("lookup","REQUEST_STATUS",{"request_id":"save1"})
        self.assertEqual(receipt["fields"]["stored"],"VERIFIED")
        self.assertEqual(receipt["fields"]["materialized"],"1")
        self.assertEqual(self.req("unknown","REQUEST_STATUS",{"request_id":"notseen"})["error"],"UNKNOWN_COMMIT")
        if CLI:
            p=subprocess.run([CLI,"--port",str(self.port),"--secret-file",str(self.secret),
                "GET","maxFPS"],capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("value=25",p.stdout)
    def test_guarded_fps_keyframe_profile_tuple_durable_restart_and_failure(self):
        # Match the target's delayed persistence policy. Reboot-required tuples
        # must still be VERIFIED on SET, without waiting for the 25 s flush.
        self.env["MIBR_V3_PERSIST_DELAY_MS"]="25000"
        self.env["MIBR_V3_PERSIST_MAX_MS"]="90000"
        cli=os.environ.get("MIBR_PINNED_ALT111_CLI")
        self.assertTrue(cli)
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        profile=Path(self.temp.name)/"cpvc-r5.profile"
        write_default_profile(profile)
        self.env["MIBR_V3_HOST_PROFILE_PATH"]=str(profile)
        original=profile.read_text()
        unrelated={key:value for key,value in
            (line.split("=",1) for line in original.splitlines())
            if key not in ("maxFPS","keyframe.mode","keyframe.interval_frames")}
        expected={"30":{"maxFPS":"30","keyframe.mode":"source_frames",
                        "keyframe.interval_frames":"20"},
                  "60":{"maxFPS":"60","keyframe.mode":"source_frames",
                        "keyframe.interval_frames":"180"}}
        def stored_tuple():
            values=dict(line.split("=",1) for line in profile.read_text().splitlines())
            return {key:values[key] for key in expected["30"]}
        def assert_profile_tuple(fps):
            self.assertEqual(stored_tuple(),expected[fps])
            values=dict(line.split("=",1) for line in profile.read_text().splitlines())
            for key,value in unrelated.items():
                self.assertEqual(values[key],value,key)
        def replay_profile_and_restart():
            self.p.terminate();self.p.wait(timeout=5)
            self.p.stdout.close();self.p.stderr.close()
            for child in Path(self.env["ALT111_SETTINGS_TEMP_ROOT"]).iterdir():
                if child.is_file(): child.unlink()
                elif child.is_dir(): shutil.rmtree(child)
            subprocess.run([cli,"batch","--input",str(profile),"--layer","temp"],
                env=self.env,capture_output=True,text=True,check=True,timeout=5)
            self.start_service()
            ready=self.p.stdout.readline().strip()
            self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
            self.port=int(ready.split("=")[1])
        def save(fps,rid):
            unchanged=(stored_tuple()==expected[fps])
            before=self.req(rid+"g","GET",{"key":"maxFPS"})["fields"]
            out=self.req(rid,"SET",{"key":"maxFPS","value":fps,
                "expected_revision":before["revision"],"activation":"AUTO",
                "request_id":rid})
            self.assertIsNone(out["error"],out)
            self.assertEqual(out["fields"]["stored"],"VERIFIED")
            self.assertEqual(out["fields"]["activation"],"UNIT_REBOOT")
            self.assertEqual(out["fields"]["apply"],"UNCHANGED" if unchanged else "PENDING")
            return out
        subprocess.run([cli,"batch","--input",str(profile),"--layer","temp"],
            env=self.env,capture_output=True,text=True,check=True,timeout=5)
        self.start_service()
        ready=self.p.stdout.readline().strip()
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
        self.port=int(ready.split("=")[1])

        # A→B→A is three guarded, atomic writes; every readback checks all tuple keys.
        for fps,rid in (("30","fps_a1"),("60","fps_b"),("30","fps_a2")):
            save(fps,rid)
            assert_profile_tuple(fps)
            self.assertEqual(self.req(rid+"v","GET",{"key":"maxFPS"})
                             ["fields"]["value"],fps)
            replay_profile_and_restart()
            assert_profile_tuple(fps)
            self.assertEqual(self.snapshot_row("maxFPS")[0],fps)
        lastgood=Path(str(profile)+".lastgood")
        self.assertEqual(dict(line.split("=",1) for line in lastgood.read_text().splitlines())
                         .get("maxFPS"),"60")

        # A fresh service receives the persisted profile through the normal TEMP replay path.
        replay_profile_and_restart()
        assert_profile_tuple("30")
        # The UI snapshot exposes maxFPS; the full persisted tuple above also
        # verifies keyframe.interval_ms stays unchanged while frames mode is active.
        snapshot_value,_=self.snapshot_row("maxFPS")
        self.assertEqual(snapshot_value,"30")

        # An RW mount failure cannot alter any member of the stored tuple.
        before=profile.read_bytes()
        self.env["MIBR_V3_HOST_FAIL_RW"]="1"
        self.restart_service()  # the failure-injection environment is read at process start
        current=self.req("fps_fail_get","GET",{"key":"maxFPS"})["fields"]
        failed=self.req("fps_fail_set","SET",{"key":"maxFPS","value":"60",
            "expected_revision":current["revision"],"activation":"AUTO",
            "request_id":"fps_fail_set"})
        self.assertEqual(failed["error"],"STORAGE_UNAVAILABLE")
        self.assertEqual(profile.read_bytes(),before)
        assert_profile_tuple("30")
        self.assertEqual(self.req("fps_snapfail","SNAPSHOT",{"scope":"ui"})
                         ["error"],None)
    def test_external_temp_write_is_stale_once_not_a_permanent_lock(self):
        # Field r12 2026-10-20: after an outside TEMP rewrite (iPhone reconnect / GEN2) every
        # later SET failed until restart. A drift must cost one STALE_REVISION, then a fresh
        # read may save again; the profile itself is still CAS-protected.
        cli=os.environ.get("MIBR_PINNED_ALT111_CLI")
        self.assertTrue(cli)
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        profile=Path(self.temp.name)/"cpvc-r5.profile"
        write_default_profile(profile)
        self.env["MIBR_V3_HOST_PROFILE_PATH"]=str(profile)
        subprocess.run([cli,"batch","--input",str(profile),"--layer","temp"],
            env=self.env,capture_output=True,text=True,check=True,timeout=5)
        self.start_service()
        self.port=int(self.p.stdout.readline().strip().split("=")[1])
        def save(rid,value):
            rev=self.req(rid+"r","GET",{"key":"maxFPS"})["fields"]["revision"]
            return self.req(rid,"SET",{"key":"maxFPS","value":value,"expected_revision":rev,
                                       "activation":"AUTO","request_id":rid})
        self.assertIsNone(save("a","25")["error"])
        before=profile.read_text()
        subprocess.run([cli,"set","--key","navigation.compass","--value","no","--layer","temp"],
            env=self.env,capture_output=True,text=True,check=True,timeout=5)
        self.assertEqual(save("b","30")["error"],"STALE_REVISION")
        out=save("c","30")
        self.assertIsNone(out["error"],out)
        self.assertEqual(profile.read_text(),before.replace("maxFPS=25\n","maxFPS=30\n"))
        self.assertEqual(self.req("cap2","CAPABILITIES")["fields"]["durable_set"],"1")
    def test_profile_parity_prevents_premature_durable_capability(self):
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        profile=Path(self.temp.name)/"cpvc-r5.profile"
        write_default_profile(profile)
        profile.write_text(profile.read_text().replace("maxFPS=30\n", "maxFPS=40\n"))
        self.env["MIBR_V3_HOST_PROFILE_PATH"]=str(profile)
        self.start_service()
        ready=self.p.stdout.readline().strip()
        self.assertTrue(ready.startswith("MIBR_V3_HOST_SERVICE_PORT="),ready)
        self.port=int(ready.split("=")[1])
        self.assertEqual(self.req("cap","CAPABILITIES")["fields"]["durable_set"],"0")
    def test_fail_rw_then_fail_ro_never_claims_durable_commit(self):
        cli=os.environ.get("MIBR_PINNED_ALT111_CLI")
        self.assertTrue(cli)
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        profile=Path(self.temp.name)/"cpvc-r5.profile"
        write_default_profile(profile)
        self.env["MIBR_V3_HOST_PROFILE_PATH"]=str(profile)
        subprocess.run([cli,"batch","--input",str(profile),"--layer","temp"],
                       env=self.env,capture_output=True,check=True,timeout=5)
        self.env["MIBR_V3_HOST_FAIL_RW"]="1"
        self.start_service()
        self.port=int(self.p.stdout.readline().strip().split("=")[1])
        rev=self.req("pre","GET",{"key":"maxFPS"})["fields"]["revision"]
        fields={"key":"maxFPS","value":"25","expected_revision":rev,
                "activation":"AUTO","request_id":"failrw"}
        self.assertEqual(self.req("failrw","SET",fields)["error"],"STORAGE_UNAVAILABLE")
        self.assertIn("maxFPS=30\n",profile.read_text())
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        self.env.pop("MIBR_V3_HOST_FAIL_RW")
        self.env["MIBR_V3_HOST_FAIL_RO"]="1"
        self.start_service()
        self.port=int(self.p.stdout.readline().strip().split("=")[1])
        fields["request_id"]="failro"
        self.assertEqual(self.req("failro","SET",fields)["error"],"RO_RESTORE_FAILED")
        self.assertEqual(self.req("after","CAPABILITIES")["fields"]["durable_set"],"0")
        self.assertEqual(self.req("after2","GET",{"key":"maxFPS"})["error"],"NOT_READY")
    def test_separate_input_credential_and_shared_real_socket_route(self):
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        second=Path(self.temp.name)/"input.secret"
        second.write_text("b"*64+"\n");second.chmod(0o600)
        self.env["MIBR_V3_HOST_ROUTE_TEST"]="1"
        self.p=subprocess.Popen([BIN,"--port","0","--secret-file",str(self.secret),
            "--input-secret-file",str(second)],
            env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.port=int(self.p.stdout.readline().strip().split("=")[1])
        cap=self.req("cap","CAPABILITIES")["fields"]
        self.assertEqual(cap["route_action"],"1")
        self.assertEqual(cap["key40_input"],"0")  # no actual vehicle DSI intake
        a={"kind":"SET_VISIBLE_ROUTE","target":"DIRECT111","expected_route":"STOCK110",
           "expected_session":"7","expected_generation":"9","origin":"KEY40_LONG",
           "request_id":"hw1"}
        self.assertEqual(self.req("hw1","ACTION",a)["error"],"FORBIDDEN")
        self.assertEqual(self.req("hw1","ACTION",a,secret="b"*64)["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.req("hw1","ACTION",a,secret="b"*64)["fields"]["visible_route"],"DIRECT111")
        q=self.req("hquery","ACTION_STATUS",{"request_id":"hw1"},secret="b"*64)
        self.assertEqual((q["fields"]["apply"],q["fields"]["receipt_scope"]),("ACTIVE","HISTORICAL"))
        self.assertEqual(self.req("foreign","ACTION_STATUS",{"request_id":"hw1"})["error"],"FORBIDDEN")
        self.assertEqual(self.req("nope","ACTION_STATUS",{"request_id":"absent"},secret="b"*64)["error"],"UNKNOWN_COMMIT")
        self.assertEqual(self.req("denied","GET",{"key":"maxFPS"},secret="b"*64)["error"],"FORBIDDEN")
        self.assertEqual(self.req("hw2","ACTION",{**a,"request_id":"hw2"},secret="b"*64)["error"],"SESSION_STALE")
        h={"kind":"SET_VISIBLE_ROUTE","target":"STOCK110","expected_route":"DIRECT111",
           "expected_session":"7","expected_generation":"10","origin":"HMI",
           "request_id":"ui2"}
        self.assertEqual(self.req("ui2","ACTION",h)["fields"]["apply"],"ACTIVE")
        self.assertEqual(self.req("ui3","ACTION",{**h,"request_id":"ui3"},secret="b"*64)["error"],"FORBIDDEN")
        if CLI:
            p=subprocess.run([CLI,"--port",str(self.port),"--secret-file",str(self.secret),
                "ACTION_STATUS","ui2"],capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("receipt_scope=HISTORICAL",p.stdout)
        self.assertEqual(self.req("state","STATUS")["fields"]["visible_route"],"STOCK110")
        self.assertEqual(self.req("state","STATUS")["fields"]["route_generation"],"11")
    def test_callback_without_qualification_does_not_enable_route(self):
        self.p.terminate();self.p.wait(timeout=5)
        self.p.stdout.close();self.p.stderr.close()
        self.env["MIBR_V3_HOST_ROUTE_TEST"]="1"
        self.env["MIBR_V3_HOST_ROUTE_UNQUALIFIED"]="1"
        self.start_service()
        self.port=int(self.p.stdout.readline().strip().split("=")[1])
        self.assertEqual(self.req("cap","CAPABILITIES")["fields"]["route_action"],"0")
        self.assertEqual(self.req("st","STATUS")["fields"]["visible_route"],"UNKNOWN")
        f={"kind":"SET_VISIBLE_ROUTE","target":"DIRECT111","expected_route":"STOCK110",
           "expected_session":"7","expected_generation":"9","origin":"HMI","request_id":"blocked"}
        self.assertEqual(self.req("blocked","ACTION",f)["error"],"ACTIVATION_UNSUPPORTED")
    def test_secure_secret_file_enforcement(self):
        self.p.terminate();self.p.wait(timeout=5)
        self.secret.chmod(0o644)
        env={**os.environ,"ALT111_SETTINGS_TEMP_ROOT":str(Path(self.temp.name)/"temp"),
             "ALT111_SETTINGS_PERSISTENT_ROOT":str(Path(self.temp.name)/"persistent")}
        p=subprocess.run([BIN,"--port","0","--secret-file",str(self.secret)],
                         env=env,capture_output=True,timeout=5)
        self.assertEqual(p.returncode,3)
if __name__=="__main__": unittest.main()
