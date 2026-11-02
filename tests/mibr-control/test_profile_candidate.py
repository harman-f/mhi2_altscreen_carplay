"""CPVC R5 profile candidate: exact existing 45 keys, original C core validates it."""
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

from public_paths import ROOT as APP, TESTS
if not (TESTS / "profile_candidate.py").is_file():
    raise unittest.SkipTest("Research-only profile-candidate model is omitted from the public source tree")
sys.path.insert(0,str(TESTS))
from profile_candidate import candidate,CandidateRejected
ROOT=APP.parents[1]
PROFILE=ROOT.parent/"cpvc-r5/CPVC-Install/profile/default.profile"
REGISTRY=ROOT/"reference/alt111-settings-registry-324b4f249883.json"
CLI=os.environ.get("MIBR_PINNED_ALT111_CLI")

class ProfileCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=PROFILE.read_bytes()
        cls.registry=json.loads(REGISTRY.read_text())
    def prepare(self,blob=None,**kw):
        return candidate(self.original if blob is None else blob,self.original,
                         self.registry,kw or {"maxFPS":"25"},22,22)
    def test_full_45_key_preservation_and_noop(self):
        out,changed=self.prepare(maxFPS="25",**{"navigation.compass":"no"})
        self.assertTrue(changed)
        before=dict(x.split("=",1) for x in self.original.decode().splitlines())
        after=dict(x.split("=",1) for x in out.decode().splitlines())
        self.assertEqual(len(after),45)
        for key in before:
            if key not in ("maxFPS","navigation.compass"):
                self.assertEqual(after[key],before[key])
        self.assertEqual(after["maxFPS"],"25")
        self.assertEqual(after["navigation.compass"],"no")
        self.assertEqual(candidate(self.original,self.original,self.registry,
                                   {"maxFPS":before["maxFPS"]},22,22),
                         (self.original,False))
    def test_rejects_drift_unknown_hidden_stale_and_duplicate(self):
        cases=[self.original+b"maxFPS=40\n",
               self.original.replace(b"maxFPS=30\n",b""),
               self.original+b"rogue.key=1\n",
               self.original.replace(b"\n",b"\r\n")]
        for blob in cases:
            with self.subTest(blob=blob[-30:]),self.assertRaises(CandidateRejected):
                self.prepare(blob)
        for edits in ({"display.widthPixels":"123"},{"nope":"1"},{"maxFPS":"bad\nvalue"}):
            with self.subTest(edits=edits),self.assertRaises(CandidateRejected):
                candidate(self.original,self.original,self.registry,edits,22,22)
        with self.assertRaisesRegex(CandidateRejected,"STALE_REVISION"):
            candidate(self.original,self.original,self.registry,{"maxFPS":"25"},22,23)
    @unittest.skipUnless(CLI,"Exact original native CLI built only in CI")
    def test_candidate_is_accepted_by_pinned_original_full_batch_validator(self):
        out,_=self.prepare(maxFPS="25")
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)
            (path/"temp").mkdir();(path/"persistent").mkdir()
            env={**os.environ,"ALT111_SETTINGS_TEMP_ROOT":str(path/"temp"),
                 "ALT111_SETTINGS_PERSISTENT_ROOT":str(path/"persistent")}
            def cli(*args):
                return subprocess.run([CLI,*args],env=env,capture_output=True,
                                      text=True,timeout=5)
            rev=cli("status")
            self.assertEqual(rev.returncode,0,rev.stdout+rev.stderr)
            revision=re.search(r"revision=(\d+)",rev.stdout).group(1)
            candidate_path=path/"candidate.profile"
            candidate_path.write_bytes(out) # HOST ONLY; never /mnt/app
            checked=cli("batch","--input",str(candidate_path),"--layer","temp",
                        "--expected-revision",revision)
            self.assertEqual(checked.returncode,0,checked.stdout+checked.stderr)
            self.assertIn("maxFPS.value=25",cli("get","--key","maxFPS").stdout)

if __name__=="__main__":
    unittest.main()
