"""Tests de humo del scaffold: paquetes importables y entry points operativos."""

from __future__ import annotations

import contextlib
import importlib
import io
import unittest

import geoagent
from geoagent.agent import cli as agent_cli
from geoagent.backend import cli as backend_cli

PACKAGES = (
    "geoagent.common",
    "geoagent.agent",
    "geoagent.backend",
    "geoagent.spark",
    "geoagent.tools",
)

ENTRY_POINTS = (
    ("geoagent-agent", agent_cli),
    ("geoagent-backend", backend_cli),
)


class TestPackageLayout(unittest.TestCase):
    def test_all_layer_packages_are_importable(self) -> None:
        for name in PACKAGES:
            with self.subTest(package=name):
                module = importlib.import_module(name)
                self.assertEqual(module.__name__, name)

    def test_version_is_semver_string(self) -> None:
        self.assertRegex(geoagent.__version__, r"^\d+\.\d+\.\d+$")


class TestEntryPoints(unittest.TestCase):
    def test_main_without_arguments_returns_zero_and_prints_usage_to_stderr(self) -> None:
        for prog, module in ENTRY_POINTS:
            with self.subTest(prog=prog):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = module.main([])
                self.assertEqual(exit_code, 0)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn(f"usage: {prog}", stderr.getvalue())

    def test_version_flag_exits_zero_and_reports_package_version(self) -> None:
        for prog, module in ENTRY_POINTS:
            with self.subTest(prog=prog):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as ctx:
                    module.main(["--version"])
                self.assertEqual(ctx.exception.code, 0)
                self.assertEqual(stdout.getvalue().strip(), f"{prog} {geoagent.__version__}")

    def test_unknown_argument_exits_with_usage_error(self) -> None:
        for prog, module in ENTRY_POINTS:
            with self.subTest(prog=prog):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as ctx:
                    module.main(["--no-such-flag"])
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn("unrecognized arguments", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
