"""Regression checks for authentication secret handling."""

import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "main.py"


class MainSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(SOURCE.read_text(encoding="utf-8"))

    @classmethod
    def method(cls, name):
        login_class = next(
            node for node in cls.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "ATrustLogin"
        )
        return next(
            node for node in login_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
        )

    def test_no_pickle_deserialization(self):
        self.assertFalse(any(
            isinstance(node, (ast.Import, ast.ImportFrom)) and (
                (isinstance(node, ast.Import) and any(alias.name == "pickle" for alias in node.names)) or
                (isinstance(node, ast.ImportFrom) and node.module == "pickle")
            ) for node in ast.walk(self.tree)))

    def test_local_storage_uses_script_arguments(self):
        method = self.method("load_storage")
        calls = [node for node in ast.walk(method) if isinstance(node, ast.Call) and
                 isinstance(node.func, ast.Attribute) and node.func.attr == "execute_script"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0].args), 3)
        self.assertIsInstance(calls[0].args[0], ast.Constant)
        self.assertEqual(calls[0].args[0].value,
                         "window.localStorage.setItem(arguments[0], arguments[1]);")

    def test_totp_code_never_passed_to_logger(self):
        method = self.method("login")
        calls = [node for node in ast.walk(method) if isinstance(node, ast.Call) and
                 isinstance(node.func, ast.Attribute) and
                 isinstance(node.func.value, ast.Name) and node.func.value.id == "logger"]
        for call in calls:
            names = {n.id for arg in list(call.args) + [kw.value for kw in call.keywords]
                     for n in ast.walk(arg) if isinstance(n, ast.Name)}
            self.assertNotIn("totp_code", names)


if __name__ == "__main__":
    unittest.main()
