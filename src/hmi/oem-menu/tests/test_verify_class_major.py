import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


MODULE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_class_major", MODULE / "verify_class_major.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


def class_bytes(major):
    return b"\xca\xfe\xba\xbe\x00\x00" + major.to_bytes(2, "big") + b"\x00\x00"


class VerifyClassMajorTests(unittest.TestCase):
    def make_jar(self, directory, data):
        path = Path(directory) / "target.jar"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("sample/Target.class", data)
        return path

    def test_accepts_all_major_46_classes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_jar(directory, class_bytes(46))
            self.assertEqual(VERIFY.verify(str(path), 46), 1)

    def test_rejects_wrong_class_major(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_jar(directory, class_bytes(52))
            with self.assertRaisesRegex(ValueError, "expected 46"):
                VERIFY.verify(str(path), 46)

    def test_rejects_jar_without_classes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.jar"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("README.txt", "empty")
            with self.assertRaisesRegex(ValueError, "no class files"):
                VERIFY.verify(str(path), 46)


if __name__ == "__main__":
    unittest.main()
