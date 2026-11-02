"""Actual C recovery/read-only GEN2 parser and abrupt-cut HOST matrix.
No QNX/media/power-loss PASS: a host process kill is not an electrical power cut.
"""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from test_native_v3_readonly import APP,api
from public_paths import write_default_profile

REC=os.environ.get("MIBR_V3_RECOVERY_PROBE_BIN")
RUNTIME=os.environ.get("MIBR_V3_RUNTIME_PROBE_BIN")
SERVICE=os.environ.get("MIBR_V3_NATIVE_SERVICE_BIN")
CLI=os.environ.get("MIBR_PINNED_ALT111_CLI")
@unittest.skipUnless(REC and RUNTIME and SERVICE and CLI,"native compiled HOST prerequisites")
class RecoveryAndRuntime(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix="v3-powercut-host-")
        self.root=Path(self.t.name);self.profile=self.root/"cpvc-r5.profile"
        write_default_profile(self.profile)
        (self.root/"temp").mkdir();(self.root/"persistent").mkdir()
        self.secret=self.root/"secret";self.secret.write_text("a"*64+"\n");self.secret.chmod(0o600)
        self.env={**os.environ,"ALT111_SETTINGS_TEMP_ROOT":str(self.root/"temp"),
            "ALT111_SETTINGS_PERSISTENT_ROOT":str(self.root/"persistent"),
            "MIBR_V3_HOST_PROFILE_PATH":str(self.profile)}
        p=subprocess.run([CLI,"batch","--input",str(self.profile),"--layer","temp"],
            env=self.env,capture_output=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr)
    def tearDown(self):self.t.cleanup()
    def probe(self):
        return subprocess.run([REC,str(self.profile)],capture_output=True,text=True,timeout=5)
    def start(self,extra=None):
        e={**self.env,**(extra or {})}
        p=subprocess.Popen([SERVICE,"--port","0","--secret-file",str(self.secret)],
            env=e,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        line=p.stdout.readline().strip()
        self.assertTrue(line.startswith("MIBR_V3_HOST_SERVICE_PORT="),line)
        return p,int(line.split("=")[1])
    def request(self,port,rid,op,fields=None):
        request=api.request(rid,op,fields)
        auth=request[:-1]+(b";auth=" if fields else b" auth=")+b"a"*64+b"\n"
        with socket.create_connection(("127.0.0.1",port),timeout=3) as s:
            s.sendall(auth);data=b""
            while not data.endswith(b"\n"):
                x=s.recv(4096)
                if not x:break
                data+=x
        return api.parse(data,is_response=True)
    def test_recovery_structural_gate_and_lastgood(self):
        self.assertEqual(self.probe().returncode,0)
        backup=self.root/"cpvc-r5.profile.lastgood"
        shutil.copyfile(self.profile,backup)
        self.assertEqual(self.probe().returncode,0)
        stage=self.root/"cpvc-r5.profile.stage.123"
        stage.write_text("incomplete\n")
        self.assertEqual(self.probe().returncode,2)
        stage.unlink()
        backup.write_text("BROKEN\n")
        self.assertEqual(self.probe().returncode,2)
        shutil.copyfile(self.profile,backup)
        self.profile.write_text("maxFPS=25\n")
        self.assertEqual(self.probe().returncode,2)
    def test_real_service_startup_blocks_torn_stage(self):
        stage=self.root/"cpvc-r5.profile.lastgood.stage.4";stage.write_text("bad\n")
        p,port=self.start()
        try:
            result=self.request(port,"cap","CAPABILITIES")["fields"]
            self.assertEqual(result["durable_set"],"0")
            self.assertEqual(self.request(port,"get","GET",{"key":"maxFPS"})["fields"]["active"],"UNKNOWN")
        finally:p.terminate();p.wait(timeout=5);p.stdout.close();p.stderr.close()
    def test_abrupt_process_cutpoints_and_recovery(self):
        for point in ("BACKUP_STAGED","BACKUP_COMMITTED","PROFILE_STAGED",
                      "PROFILE_RENAMED","PROFILE_SYNCED","RO_VERIFIED"):
            with self.subTest(point=point):
                shutil.copyfile(PROFILE,self.profile)
                (self.root/"cpvc-r5.profile.lastgood").unlink(missing_ok=True)
                for item in self.root.glob("cpvc-r5.profile.stage.*"):item.unlink()
                for item in self.root.glob("cpvc-r5.profile.lastgood.stage.*"):item.unlink()
                p,port=self.start({"MIBR_V3_HOST_CUTPOINT":point})
                try:
                    cap=self.request(port,"cap","CAPABILITIES")["fields"]
                    self.assertEqual(cap["durable_set"],"1",cap)
                    rev=self.request(port,"before","GET",{"key":"maxFPS"})["fields"]["revision"]
                    try:self.request(port,"crash_"+point,"SET",{
                        "key":"maxFPS","value":"25","expected_revision":rev,
                        "activation":"AUTO","request_id":"crash_"+point})
                    except (OSError,ValueError):pass
                    self.assertEqual(p.wait(timeout=5),96,point)
                    outcome=self.probe()
                    if point in ("BACKUP_STAGED","PROFILE_STAGED"):
                        self.assertEqual(outcome.returncode,2,(point,outcome.stdout))
                    else:
                        self.assertEqual(outcome.returncode,0,(point,outcome.stdout))
                    value=self.profile.read_text()
                    self.assertIn("maxFPS="+("30" if point in ("BACKUP_STAGED","BACKUP_COMMITTED","PROFILE_STAGED") else "25")+"\n",value)
                    self.assertIn("maxFPS=30\n",(self.root/"cpvc-r5.profile.lastgood").read_text()
                                      if point!="BACKUP_STAGED" else value)
                finally:
                    if p.poll() is None:p.terminate();p.wait(timeout=5)
                    p.stdout.close();p.stderr.close()
    def test_runtime_observer_fails_closed_and_never_correlates_aggregates(self):
        path=self.root/"gen2.status"
        payload=("control_session=51\nstream_gen=7\nsettings_desired_revision=24\n"
            "settings_active_revision=23\nsettings_active_confirmed=1\n"
            "settings_active_present=1\nsettings_valid=1\n")
        path.write_text(payload)
        good=subprocess.run([RUNTIME,str(path)],capture_output=True,text=True,timeout=5)
        self.assertEqual(good.returncode,0,good.stdout+good.stderr)
        self.assertIn("confirmed=1 correlated=0",good.stdout)
        path.write_text(payload+"settings_active_revision=24\n")
        self.assertEqual(subprocess.run([RUNTIME,str(path)]).returncode,2)
        path.write_text(payload.replace("control_session=51","control_session=0"))
        o=subprocess.run([RUNTIME,str(path)],capture_output=True,text=True,timeout=5)
        self.assertEqual(o.returncode,0);self.assertIn("confirmed=0 correlated=0",o.stdout)
        path.write_text(payload);old=time.time()-20;os.utime(path,(old,old))
        self.assertEqual(subprocess.run([RUNTIME,str(path)]).returncode,2)

if __name__=="__main__":unittest.main()
