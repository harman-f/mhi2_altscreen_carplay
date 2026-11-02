"""Actual pinned Classic111 C core -> native MIBR/3, host-only, no product transport."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from public_paths import ROOT as APP, NATIVE, OEM_MENU, TESTS
BIN=os.environ.get("MIBR_V3_NATIVE_READONLY_HOST_BIN")
CLI=os.environ.get("MIBR_PINNED_ALT111_CLI")
import sys
sys.path.insert(0,str(TESTS))
import api_v3_contract as api

class NativeSourceContract(unittest.TestCase):
    def test_no_writer_or_product_transport_and_visible_policy(self):
        source=(NATIVE/"mibr_v3_readonly.c").read_text()
        for forbidden in ("alt111_settings_mutate(", "alt111_settings_clear(",
                          "mount(", "socket(", "send(", "recv("):
            self.assertNotIn(forbidden,source)
        keys=re.findall(r'"([^"]+)"',source.split("ui_keys[UI_COUNT] = {",1)[1].split("};",1)[0])
        menu=json.loads((OEM_MENU/"menu-definition.json").read_text())
        expected=list(menu["native_ui_keys"])
        self.assertEqual(keys,expected)
        self.assertEqual(len(set(keys)),11)
        self.assertIn("int mibr_v3_refresh(",source)
        self.assertEqual(source.count("alt111_settings_load("),2)  # one refresh + one SET-only CAS load
        flush=source.split("int mibr_v3_flush_due(",1)[1].split("int mibr_v3_refresh(",1)[0]
        self.assertIn("mibr_v3_refresh(r,&r->paths)",flush)
        self.assertNotIn("!r->ready",flush)  # pending writes can recover after a transient failed load
        self.assertIn("MIBR_V3_REFRESH_FAILED",source)
        self.assertIn("MIBR_V3_REFRESH_KEY_MISMATCH",source)
        self.assertIn("MIBR_V3_SET_PREFLIGHT_LOAD_FAILED",source)
        self.assertIn("refresh_blocked=1",source)

@unittest.skipUnless(BIN and CLI,"Separate Research read-only role harness is not built by the public service build")
class NativeV3ReadOnly(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="mibr-v3-core-")
        root=Path(self.tmp.name)
        self.temp=root/"temp";self.persistent=root/"persistent"
        self.temp.mkdir();self.persistent.mkdir()
        self.env={**os.environ,"ALT111_SETTINGS_TEMP_ROOT":str(self.temp),
                  "ALT111_SETTINGS_PERSISTENT_ROOT":str(self.persistent)}
        self.ps=[]
    def tearDown(self):
        for p in self.ps:
            p.stdin.close()
            p.wait(timeout=5)
            p.stdout.close();p.stderr.close()
        self.tmp.cleanup()
    def start(self,role):
        p=subprocess.Popen([BIN,"--"+role],env=self.env,stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                           text=False,bufsize=0)
        self.ps.append(p)
        line=p.stdout.readline()
        self.assertEqual(line,b"MIBR_V3_HOST_READY\n",p.stderr.read() if p.poll() is not None else line)
        return p
    def ask(self,p,rid,op,fields=None):
        return self.raw(p,api.request(rid,op,fields))
    def raw(self,p,data):
        p.stdin.write(data);p.stdin.flush()
        result=p.stdout.readline()
        self.assertTrue(result.startswith(b"MIBR/3 "),result)
        return api.parse(result,is_response=True)
    def host_command(self,p,command):
        p.stdin.write(command);p.stdin.flush()
        return p.stdout.readline()
    def cli(self,*args):
        return subprocess.run([CLI,*args],env=self.env,capture_output=True,
                              text=True,timeout=5,check=True).stdout
    def test_real_core_snapshot_projection_11_48_and_auth_boundary(self):
        ui=self.start("ui");shell=self.start("shell")
        first=self.ask(ui,"u0","HELLO")
        self.assertEqual(first["fields"]["version"],"MIBR/3")
        self.assertEqual(first["fields"]["phase"],"NATIVE_READONLY_OFFLINE")
        caps=self.ask(ui,"u1","CAPABILITIES")["fields"]
        self.assertEqual(caps["snapshot"],"1")
        for k in ("durable_set","reconnect","presentation_refresh","test_override","session_control"):
            self.assertEqual(caps[k],"0")
        status=self.ask(ui,"u2","STATUS")["fields"]
        self.assertEqual(status["stored"],"UNCONFIRMED")
        self.assertEqual(status["persistent_safety"],"UNQUALIFIED")
        self.assertEqual(status["runtime_correlated"],"0")
        ui_snap=self.ask(ui,"u3","SNAPSHOT",{"scope":"ui"})["fields"]
        self.assertEqual(ui_snap["row_count"],"11")
        self.assertEqual(ui_snap["revision"],status["revision"])
        self.assertEqual(ui_snap["row.0.key"],"carplay.enabled")
        self.assertEqual(ui_snap["row.0.active"],"UNKNOWN")
        self.assertEqual(self.ask(ui,"u4","SNAPSHOT",{"scope":"all"})["error"],"FORBIDDEN")
        all_snap=self.ask(shell,"s1","SNAPSHOT",{"scope":"all"})["fields"]
        self.assertEqual(all_snap["row_count"],"48")
        self.assertEqual(all_snap["revision"],status["revision"])
        self.assertEqual(len({all_snap["row.%d.key"%i] for i in range(48)}),48)
        for i in range(48):
            key=all_snap["row.%d.key"%i]
            get=self.ask(shell,"s%02d"%(i+2),"GET",{"key":key})["fields"]
            self.assertEqual(get["value"],all_snap["row.%d.value"%i])
            self.assertEqual(get["source"],all_snap["row.%d.source"%i])
            self.assertEqual(get["active"],"UNKNOWN")
        self.assertEqual(self.ask(ui,"u5","GET",{"key":"keyframe.mode"})["error"],"FORBIDDEN")
        self.assertEqual(self.ask(ui,"u6","GET",{"key":"no.such.key"})["error"],"INVALID_KEY")
        cli=self.cli("get","--key","maxFPS")
        self.assertIn("maxFPS.value="+self.ask(ui,"u7","GET",{"key":"maxFPS"})["fields"]["value"],cli)
    def test_cache_single_boot_load_and_all_writes_blocked(self):
        p=self.start("shell")
        before=self.ask(p,"a","GET",{"key":"maxFPS"})["fields"]
        self.assertEqual(before["active"],"UNKNOWN")
        for i,op in enumerate(("SET","BATCH","RESET","TEST_SET","TEST_CLEAR","TEST_LIST",
                                "ACTIVATE")):
            self.assertEqual(self.ask(p,"w%d"%i,op,{"key":"maxFPS"})["error"],"POLICY_BLOCKED")
        # A malformed request-id lookup fails parser validation before the
        # read-only policy: it must never be accepted as a successful receipt.
        self.assertEqual(self.ask(p,"w7","REQUEST_STATUS",{"key":"maxFPS"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.ask(p,"w8","REQUEST_STATUS",{"request_id":"abc"})["error"],"POLICY_BLOCKED")
        value="25" if before["value"]!="25" else "30"
        self.cli("set","--key","maxFPS","--value",value,"--expected-revision",before["revision"])
        live=self.cli("get","--key","maxFPS")
        self.assertIn("maxFPS.value="+value,live)
        cached=self.ask(p,"z","GET",{"key":"maxFPS"})["fields"]
        self.assertEqual(cached["value"],before["value"])
        self.assertEqual(cached["revision"],before["revision"])
        # No synthetic runtime active assertion after external TEMP edit.
        self.assertEqual(cached["active"],"UNKNOWN")
        # Refresh is explicit and uses exactly one new original-core load.
        self.assertEqual(self.host_command(p,b"#HOST_REFRESH\n"),b"HOST_REFRESH_OK\n")
        fresh=self.ask(p,"r1","GET",{"key":"maxFPS"})["fields"]
        self.assertEqual(fresh["value"],value)
        self.assertNotEqual(fresh["revision"],before["revision"])
        self.assertEqual(self.ask(p,"r2","SNAPSHOT",{"scope":"all"})["fields"]["revision"],fresh["revision"])
        self.assertEqual(self.ask(p,"r3","STATUS")["fields"]["revision"],fresh["revision"])
        self.assertEqual(fresh["active"],"UNKNOWN")
        # A real original-core load failure never serves stale cache. A later
        # complete safe snapshot retries the loader after storage returns.
        displaced=self.temp.with_name(self.temp.name+"-displaced")
        self.temp.rename(displaced)
        self.assertEqual(self.host_command(p,b"#HOST_REFRESH\n"),b"HOST_REFRESH_FAILED\n")
        self.assertEqual(self.ask(p,"f1","STATUS")["fields"]["ready"],"NOT_READY")
        self.assertEqual(self.ask(p,"f2","GET",{"key":"maxFPS"})["error"],"NOT_READY")
        self.assertEqual(self.ask(p,"f3","SNAPSHOT",{"scope":"all"})["error"],"NOT_READY")
        displaced.rename(self.temp)
        recovered=self.ask(p,"r4","SNAPSHOT",{"scope":"all"})["fields"]
        self.assertEqual(recovered["row_count"],"48")
        self.assertEqual(recovered["revision"],fresh["revision"])
        recovered_get=self.ask(p,"r5","GET",{"key":"maxFPS"})["fields"]
        self.assertEqual(recovered_get["value"],fresh["value"])
        self.assertEqual(recovered_get["active"],"UNKNOWN")
    def test_wire_rejects_truncated_duplicate_bad_percent_unknown_fields(self):
        p=self.start("ui")
        bad=[
            b"MIBR/3 x SNAPSHOT scope=ui;scope=all\n",
            b"MIBR/3 x SNAPSHOT scope=%75i\n",
            b"MIBR/3 x SNAPSHOT scope=%GG\n",
            b"MIBR/3 x GET key=%00\n",
            b"MIBR/3 x GET key=%FF\n",
            b"MIBR/3 x GET key=abc\r\n",
            b"MIBR/3 x GET key=abc;key=def\n",
        ]
        for i,line in enumerate(bad):
            result=self.raw(p,line)
            self.assertEqual(result["error"],"INVALID_FRAME",(i,result))
        self.assertEqual(self.ask(p,"a","SNAPSHOT",{"scope":"unknown"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.ask(p,"b","SNAPSHOT",{"bogus":"1"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.ask(p,"c","HELLO",{"extra":"x"})["error"],"INVALID_REQUEST")
        self.assertEqual(self.raw(p,b"MIBR/2 x HELLO\n")["error"],"UNSUPPORTED_VERSION")
        self.assertEqual(self.ask(p,"d","STATUS")["fields"]["ready"],"READ_ONLY")

if __name__=="__main__":
    unittest.main()
