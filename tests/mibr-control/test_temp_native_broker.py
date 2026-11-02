"""Exact original Classic111 host core + TEMP broker. No vehicle/effective ACK."""
import os,re,socket,subprocess,tempfile,unittest,json
from pathlib import Path
from public_paths import NATIVE, OEM_MENU

BIN=os.environ.get("MIBR_NATIVE_BROKER_HOST_BIN")
CLI=os.environ.get("MIBR_PINNED_ALT111_CLI")
TOKEN="a"*32

class VisiblePolicyAgreement(unittest.TestCase):
 def test_11_visible_are_exactly_current_json_menu_not_registry_hmi_category(self):
  menu=json.loads((OEM_MENU/"menu-definition.json").read_text())
  keys=list(menu["native_ui_keys"])
  text=(NATIVE/"mibr_control.c").read_text()
  block=text.split("static const char *const UI_VISIBLE_KEYS[]={",1)[1].split("};",1)[0]
  native=re.findall(r'"([^"]+)"',block)
  self.assertEqual(len(native),11)
  self.assertEqual(native,keys)
  self.assertEqual(len(set(native)),11)

@unittest.skipUnless(BIN and CLI,"CI must build original native core binaries")
class NativeTempBroker(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix="mibr-native-host-")
  root=Path(self.tmp.name);self.temp=root/"temp";self.persistent=root/"persistent"
  self.temp.mkdir();self.persistent.mkdir()
  self.env={**os.environ,"ALT111_SETTINGS_TEMP_ROOT":str(self.temp),
             "ALT111_SETTINGS_PERSISTENT_ROOT":str(self.persistent)}
  self.process=subprocess.Popen([BIN,"--port","0","--token",TOKEN,"--enable-temp"],
       env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
  line=self.process.stdout.readline()
  match=re.fullmatch(r"MIBR_CONTROL_HOST_TEST_PORT=(\d+)\n",line)
  self.assertIsNotNone(match,(line,self.process.poll()))
  self.port=int(match.group(1))
 def tearDown(self):
  self.process.terminate()
  try:self.process.wait(timeout=3)
  except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
  self.process.stdout.close();self.process.stderr.close();self.tmp.cleanup()
 def ask(self,line):
  with socket.create_connection(("127.0.0.1",self.port),timeout=3) as s:
   s.settimeout(3);s.sendall((line+"\n").encode("ascii"))
   return s.makefile("rb").readline(769).decode("ascii").strip()
 def revision(self):
  value=self.ask("STATUS "+TOKEN)
  self.assertIn("mode=TEMP_NATIVE",value)
  m=re.search(r"\brevision=(\d+)\b",value);self.assertIsNotNone(m,value)
  self.assertGreater(int(m.group(1)),0,value)
  return m.group(1)
 def cli(self,*args):
  r=subprocess.run([CLI,*args],capture_output=True,text=True,env=self.env,timeout=4)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  return r.stdout
 def test_native_temp_and_cas_are_real_but_effective_unconfirmed(self):
  self.assertEqual(self.ask("HELLO "+TOKEN+" MIBR/2"),
      "HELLO MIBR/2 mode=TEMP_NATIVE mutations=TEMP_ONLY keys=48 effective=UNCONFIRMED")
  rev=self.revision()
  self.assertIn("effective=UNCONFIRMED",self.ask("GET "+TOKEN+" maxFPS"))
  a=self.ask("TEMP "+TOKEN+" "+rev+" maxFPS 25")
  self.assertIn("state=RECONNECT_REQUIRED",a);self.assertIn("effective=UNCONFIRMED",a)
  self.assertIn("maxFPS.value=25",self.cli("get","--key","maxFPS"))
  self.assertIn("desired=25",self.ask("GET "+TOKEN+" maxFPS"))
  self.assertEqual("ERROR STALE_REVISION",self.ask("TEMP "+TOKEN+" "+rev+" maxFPS 30"))
  self.assertNotEqual(rev,self.revision())
  b=self.ask("TEMP "+TOKEN+" "+self.revision()+" navigation.surface instructioncard")
  self.assertIn("state=PRESENTATION_REFRESH_REQUIRED",b)
  self.assertIn("navigation.surface.value=instructioncard",self.cli("get","--key","navigation.surface"))
  self.assertIn("effective=UNCONFIRMED",self.ask("GET "+TOKEN+" navigation.surface"))
 def test_atomic_multikey_batch_and_group_validation(self):
  rev=self.revision()
  value="TEMPBATCH "+TOKEN+" "+rev+" navigation.surface=map;navigation.ETA=yes"
  response=self.ask(value)
  self.assertIn("state=PRESENTATION_REFRESH_REQUIRED",response)
  self.assertIn("count=2",response)
  self.assertIn("effective=UNCONFIRMED",response)
  self.assertIn("navigation.surface.value=map",self.cli("get","--key","navigation.surface"))
  self.assertIn("navigation.ETA.value=yes",self.cli("get","--key","navigation.ETA"))
  now=self.revision()
  self.assertNotEqual(rev,now)
  for bad,expected in (
    ("navigation.surface=base;navigation.surface=map","ERROR DUPLICATE_KEY"),
    ("maxFPS=35;navigation.surface=base","ERROR INVALID_OR_LOCKED_VALUE"),
    ("keyframe.mode=off;maxFPS=30","ERROR INVALID_OR_LOCKED_VALUE"),
    ("maxFPS=30;unknown.key=1","ERROR INVALID_KEY"),
    ("maxFPS=30;","ERROR INVALID_BATCH"),
  ):
   with self.subTest(bad=bad):
    self.assertEqual(self.ask("TEMPBATCH "+TOKEN+" "+now+" "+bad),expected)
    self.assertEqual(self.revision(),now)
  self.assertEqual(self.ask("TEMPBATCH "+TOKEN+" "+rev+" maxFPS=30"),"ERROR STALE_REVISION")
  self.assertEqual(self.revision(),now)
 def test_actual_java_menu_session_over_original_c_core(self):
  classes=os.environ.get("MIBR_JAVA_WIRE_CLASSES")
  if not classes:self.skipTest("Java host UI classes not provided")
  r=subprocess.run(["java","-cp",classes,"de.mibr.hmi.UiWireHarness",str(self.port),TOKEN],
       capture_output=True,text=True,timeout=25,env=self.env)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertIn("MIBR_UI_WIRE_TEMP_PASS",r.stdout)
  self.assertIn("maxFPS.value=25",self.cli("get","--key","maxFPS"))
 def test_rejection_never_mutates_original_settings(self):
  old=self.revision()
  cases=[
   ("STATUS "+("b"*32),"ERROR AUTH_REQUIRED"),
   ("TEMP "+TOKEN+" "+old+" maxFPS 35","ERROR INVALID_OR_LOCKED_VALUE"),
   ("TEMP "+TOKEN+" "+old+" display.uuid abc","ERROR INVALID_OR_LOCKED_VALUE"),
   ("TEMP "+TOKEN+" "+old+" keyframe.mode off","ERROR INVALID_OR_LOCKED_VALUE"),
   ("TEMP "+TOKEN+" "+old+" unknown 1","ERROR INVALID_KEY"),
   ("TEMP "+TOKEN+" 0 maxFPS 25","ERROR INVALID_REQUEST"),
   ("SAVE "+TOKEN,"ERROR POLICY_BLOCKED"),
   ("BATCH "+TOKEN,"ERROR POLICY_BLOCKED"),
   ("ACTION "+TOKEN+" restart","ERROR POLICY_BLOCKED"),
  ]
  for command,expected in cases:
   with self.subTest(command=command):
    self.assertEqual(self.ask(command),expected)
    self.assertEqual(self.revision(),old)
  self.assertEqual(self.ask("X"*513),"ERROR INVALID_FRAME")
  self.assertEqual(self.revision(),old)
 def test_rollback_barrier_stops_before_writes(self):
  rev=self.revision()
  (self.temp/"mibr-parity-rollback.pending").write_text("reboot_required\n")
  answer=self.ask("TEMP "+TOKEN+" "+rev+" maxFPS 25")
  self.assertIn(answer,("ERROR CORE_LOAD_FAILED","ERROR CORE_MUTATION_FAILED"))
  self.assertFalse((self.temp/"mibr-carplay111-fps").exists())
  self.assertFalse((self.temp/"mibr-alt111-settings.journal").exists())

if __name__=="__main__":unittest.main()
