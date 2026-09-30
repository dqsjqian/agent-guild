#!/usr/bin/env python3
"""Offline installer regressions; every run uses a temporary HOME and curl.

Run with: python3 scripts/test_install.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@unittest.skipUnless(shutil.which("bash"), "bash is required for the shell installer")
class ShellInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ag-install-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.central = self.home / ".agent-guild"
        self.repo = self.base / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".DS_Store"))
        self.bin = self.base / "bin"
        self.bin.mkdir()
        # Deliberately emulate curl's refusal to create a missing parent and
        # its possible partial output on an interrupted transfer.
        curl = self.bin / "curl"
        curl.write_text(f"#!{sys.executable}\n" + r'''
import os
import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
url = next(arg for arg in args if arg.startswith("mock://repo/"))
relative = url.removeprefix("mock://repo/")
target = Path(args[args.index("-o") + 1])
try:
    if relative == os.environ.get("MOCK_CURL_FAIL"):
        target.write_text("partial transfer", encoding="utf-8")
        raise OSError("simulated transfer failure")
    shutil.copyfile(Path(os.environ["MOCK_REPO"]) / relative, target)
except OSError as error:
    print(f"curl: {error}", file=sys.stderr)
    sys.exit(23)
''', encoding="utf-8")
        curl.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        AGENT_GUILD_REPO="mock://repo", MOCK_REPO=str(self.repo))

    def install(self, fail=None):
        env = dict(self.env)
        if fail:
            env["MOCK_CURL_FAIL"] = fail
        return subprocess.run(["bash", str(ROOT / "scripts/install.sh")],
                              env=env, capture_output=True, text=True)

    def assertInstalled(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Read ~/.agent-guild/ONBOARDING.md", result.stdout)
        self.assertTrue((self.central / "ONBOARDING.md").is_file())
        package = self.central / "skills/agent-guild"
        skill = (package / "SKILL.md").read_text(encoding="utf-8")
        for reference in set(re.findall(r"references/[\w.-]+\.md", skill)):
            self.assertTrue((package / reference).is_file(), reference)
        self.assertTrue((package / "scripts/ag.py").is_file())
        for name in ("README.md", "README_EN.md", "references/dsh.md"):
            document = package / name
            for link in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in link:
                    continue
                target = link.split("#", 1)[0]
                if target:
                    self.assertTrue((document.parent / target).is_file(), f"{name}: {link}")
        registry = (self.central / "registry.json").read_text(encoding="utf-8")
        self.assertIsInstance(json.loads(registry)["agents"], dict)

    def test_fresh_install_contains_runtime_and_referenced_docs(self):
        self.assertInstalled(self.install())

    def test_reinstall_refreshes_protocol_and_preserves_user_files(self):
        self.assertInstalled(self.install())
        profile = self.central / "identity/profile.md"
        registry = self.central / "registry.json"
        profile.write_text("my profile\n", encoding="utf-8")
        registry.write_text('{"agents":{"my-agent":{}}}\n', encoding="utf-8")
        source = self.repo / "references/ONBOARDING.md"
        source.write_text("new protocol instructions\n", encoding="utf-8")
        self.assertInstalled(self.install())
        self.assertEqual(profile.read_text(encoding="utf-8"), "my profile\n")
        self.assertEqual(registry.read_text(encoding="utf-8"),
                         '{"agents":{"my-agent":{}}}\n')
        self.assertEqual((self.central / "ONBOARDING.md").read_text(encoding="utf-8"),
                         source.read_text(encoding="utf-8"))

    def test_failed_download_reports_failure_without_success_message(self):
        result = self.install(fail="references/ONBOARDING.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("simulated transfer failure", result.stderr)
        self.assertNotIn("Read ~/.agent-guild/ONBOARDING.md", result.stdout)

    def test_interrupted_reinstall_preserves_previous_file(self):
        self.assertInstalled(self.install())
        onboarding = self.central / "ONBOARDING.md"
        previous = onboarding.read_bytes()
        result = self.install(fail="references/ONBOARDING.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(onboarding.read_bytes(), previous)
        self.assertEqual(list(self.central.rglob("*.download.*")), [])


@unittest.skipUnless(POWERSHELL, "PowerShell is not installed")
class PowerShellInstallerTests(ShellInstallerTests):
    """The same integration contract, with Invoke-WebRequest mocked offline."""

    def setUp(self):
        super().setUp()
        self.wrapper = self.base / "mock-install.ps1"
        self.wrapper.write_text(r'''
function Invoke-WebRequest {
    param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile, [string]$ErrorAction)
    $relative = $Uri.Substring('mock://repo/'.Length)
    if ($relative -eq $env:MOCK_CURL_FAIL) {
        [System.IO.File]::WriteAllText($OutFile, 'partial transfer')
        throw 'simulated transfer failure'
    }
    Copy-Item -LiteralPath (Join-Path $env:MOCK_REPO $relative) -Destination $OutFile -ErrorAction Stop
}
& $env:INSTALL_SCRIPT
''', encoding="utf-8-sig")
        self.env["USERPROFILE"] = str(self.home)
        self.env["INSTALL_SCRIPT"] = str(ROOT / "scripts/install.ps1")

    def install(self, fail=None):
        env = dict(self.env)
        if fail:
            env["MOCK_CURL_FAIL"] = fail
        return subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive",
                               "-File", str(self.wrapper)], env=env,
                              capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
