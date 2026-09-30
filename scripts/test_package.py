#!/usr/bin/env python3
"""Offline packaging regressions, run in a disposable repository copy."""
import posixpath
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("bash") and shutil.which("zip"),
                     "bash and zip are required for packaging")
class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ag-package-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".DS_Store"))

    def package(self, output):
        return subprocess.run(["bash", str(self.repo / "scripts/package.sh"),
                               str(output)], cwd=self.base,
                              capture_output=True, text=True)

    def test_relative_output_works_after_running_python_tests(self):
        cache = self.repo / "scripts/__pycache__"
        cache.mkdir()
        (cache / "ag.cpython-313.pyc").write_bytes(b"cached bytecode")
        (self.repo / "scripts/ag.pyc").write_bytes(b"old bytecode")
        result = self.package(Path("build/my package.zip"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        archive = self.base / "build/my package.zip"
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as package:
            names = package.namelist()
            self.assertIn("agent-guild/scripts/ag.py", names)
            self.assertIn("agent-guild/README.md", names)
            self.assertIn("agent-guild/README_EN.md", names)
            self.assertFalse(any("__pycache__" in name or name.endswith(".pyc")
                                 for name in names))
            for name in ("agent-guild/README.md", "agent-guild/README_EN.md",
                         "agent-guild/references/dsh.md"):
                body = package.read(name).decode("utf-8")
                for link in re.findall(r"\]\(([^)]+)\)", body):
                    if "://" in link:
                        continue
                    target = link.split("#", 1)[0]
                    if target:
                        member = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
                        self.assertIn(member, names, f"{name}: {link}")

    def test_invalid_frontmatter_fails_and_preserves_existing_archive(self):
        skill_path = self.repo / "SKILL.md"
        original = skill_path.read_text(encoding="utf-8")
        mutations = {
            "missing field": re.sub(r"^slug:.*\n", "", original, flags=re.M),
            "version mismatch": re.sub(r"^version:.*$", 'version: "0.0.0"',
                                       original, flags=re.M),
            "invalid name": original.replace("name: agent-guild\n", "name: Bad_Name\n", 1),
            "long description": re.sub(r"^description: \|\n.*?(?=^slug:)",
                                       "description: " + "a" * 1025 + "\n",
                                       original, flags=re.M | re.S),
        }
        output = self.base / "release.zip"
        for label, contents in mutations.items():
            with self.subTest(label=label):
                skill_path.write_text(contents, encoding="utf-8")
                output.write_bytes(b"previous release")
                result = self.package(output)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(output.read_bytes(), b"previous release")


if __name__ == "__main__":
    unittest.main()
