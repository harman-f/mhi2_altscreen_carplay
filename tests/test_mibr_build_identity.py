"""Identity metadata: immutable/reproducible source evidence, not install success."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.mibr_build_identity import (make_identity, properties, elf_note,
                                       collect_configs, validate_profile)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40


class BuildIdentityTests(unittest.TestCase):
    def make(self, target="target-profiles/skoda-mu1440-p4526-aid10.json", version="1.3.3-rc.1"):
        return make_identity(ROOT, version, SHA, ROOT / target, ROOT / "config-identity.json")

    def test_skoda_and_config_hashes(self):
        meta = self.make()
        self.assertEqual(meta["target_brand"], "SKODA")
        self.assertEqual(meta["stage"], "SOURCE_ONLY")
        self.assertIsNone(meta["package_id"])
        self.assertIsNone(meta["binary_set_id"])
        self.assertEqual({x["brand"] for x in meta["configurations"]}, {"GENERIC", "SKODA"})
        for item in meta["configurations"]:
            from hashlib import sha256
            self.assertEqual(item["sha256"], sha256((ROOT / item["path"]).read_bytes()).hexdigest())
        self.assertEqual(json.dumps(meta, sort_keys=True), json.dumps(self.make(), sort_keys=True))

    def test_generic_is_not_vehicle_qualified(self):
        with self.assertRaisesRegex(ValueError, "CONFIG_BRAND_MISMATCH"):
            self.make("target-profiles/generic.json")
        generic = make_identity(ROOT,"1.3.3",SHA,ROOT/"target-profiles/generic.json",
                                ROOT/"config-identity-generic.json")
        self.assertEqual(generic["target_brand"],"GENERIC")
        self.assertEqual(generic["target_qualification"],"unqualified")
        self.assertEqual(len(generic["configurations"]),1)
        self.assertEqual(generic["configurations"][0]["brand"],"GENERIC")
        validate_profile({"schema":1,"id":"generic","brand":"GENERIC","qualification":"unqualified",
                          "firmware_train":None,"mu_version":None,"cluster_family":None})
        with self.assertRaisesRegex(ValueError, "GENERIC_CANNOT_ASSERT_TARGET"):
            validate_profile({"schema":1,"id":"generic","brand":"GENERIC","qualification":"vehicle-qualified",
                              "firmware_train":None,"mu_version":None,"cluster_family":None})

    def test_future_vw_seat_profiles_supported_without_claiming_qualification(self):
        for brand in ("VW", "SEAT"):
            validate_profile({"schema":1,"id":brand.lower()+"-prototype","brand":brand,"qualification":"unqualified",
                              "firmware_train":None,"mu_version":None,"cluster_family":None})

    def test_bad_version_and_sha_refused(self):
        for version in ("R57", "1.3.2 ", "1.3.3+local", "../../danger"):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, "VERSION_OR_COMMIT"):
                self.make(version=version)
        with self.assertRaisesRegex(ValueError, "VERSION_OR_COMMIT"):
            make_identity(ROOT, "1.3.3", "short", ROOT/"target-profiles/skoda-mu1440-p4526-aid10.json", ROOT/"config-identity.json")

    def test_config_path_traversal_duplicate_brand_and_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/"test.json"
            for path in ("../secret.json", "/etc/shadow", "settings//registry.json", "settings/../registry.json"):
                out.write_text(json.dumps({"schema":1,"configurations":[
                    {"path":path,"brand":"GENERIC","schema_version":2}]}))
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "CONFIG_PATH"):
                    collect_configs(ROOT,out,"SKODA")
            out.write_text(json.dumps({"schema":1,"configurations":[
                {"path":"settings/registry.json","brand":"VW","schema_version":2}]}))
            with self.assertRaisesRegex(ValueError, "CONFIG_BRAND_MISMATCH"):
                collect_configs(ROOT,out,"SKODA")
            out.write_text(json.dumps({"schema":1,"configurations":[
                {"path":"settings/registry.json","brand":"GENERIC","schema_version":2},
                {"path":"settings/registry.json","brand":"GENERIC","schema_version":2}]}))
            with self.assertRaisesRegex(ValueError, "CONFIG_PATH_OR_DUPLICATE"):
                collect_configs(ROOT,out,"SKODA")

    def test_host_elf_metadata_is_readable_not_executable(self):
        meta = self.make()
        data = elf_note(meta,"mibr-v3-service")
        self.assertIn('section(".mibr.ident")',data)
        self.assertIn("MIBR_BUILD_INFO:",data)
        self.assertIn("brand=SKODA",data)
        self.assertNotIn("package_id=",data)
        with self.assertRaisesRegex(ValueError,"COMPONENT_ID"):
            elf_note(meta,"../mibr-v3-service")

    def test_java_properties_have_no_false_install_claim(self):
        txt = properties(self.make())
        self.assertIn("target_brand=SKODA\n",txt)
        self.assertIn("identity_stage=SOURCE_ONLY\n",txt)
        self.assertIn("config.0.brand=GENERIC\n",txt)
        self.assertIn("config.1.brand=SKODA\n",txt)
        self.assertIn("config.0.schema=2\n",txt)
        self.assertIn("config.1.schema=3\n",txt)
        self.assertNotIn("package_id=",txt)
        txt.encode("ascii")
        self.assertEqual(len(txt.splitlines()),len(set(txt.splitlines())))


if __name__ == "__main__":
    unittest.main()
