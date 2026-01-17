import os
import sys
import types
import importlib
import unittest
import tempfile
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

# Ensure parent folder import
CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))


def import_test2_with_fakes():
    fake_dotenv = types.SimpleNamespace(load_dotenv=lambda override=True: None)

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)

    class FakeResponse:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    class FakeChatCompletions:
        def create(self, model, messages):
            return FakeOpenAI.next_response

    class FakeChat:
        def __init__(self):
            self.completions = FakeChatCompletions()

    class FakeOpenAI:
        next_response = FakeResponse("")

        def __init__(self, base_url, api_key):
            self.base_url = base_url
            self.api_key = api_key
            self.chat = FakeChat()

    fake_openai_module = types.SimpleNamespace(OpenAI=FakeOpenAI)

    with patch.dict(sys.modules, {"dotenv": fake_dotenv, "openai": fake_openai_module}):
        os.environ["OPENROUTER_API_KEY"] = "test-key"
        if "test2" in sys.modules:
            del sys.modules["test2"]
        module = importlib.import_module("test2")
    return module, FakeOpenAI, FakeResponse


class TestTest2Module(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.FakeOpenAI, cls.FakeResponse = import_test2_with_fakes()

    def test_build_messages_structure(self):
        code = "print('hi')"
        messages = self.module.build_messages(code)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("documentation specialist", messages[0]["content"])
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn(code, messages[1]["content"])

    def test_add_documentation_uses_response_content(self):
        content = "documented code"
        self.FakeOpenAI.next_response = self.FakeResponse(content)
        result = self.module.add_documentation("x=1")
        self.assertEqual(result, content)

    def test_main_usage_wrong_args(self):
        with patch.object(sys, "argv", ["test2.py"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                status = self.module.main()
            self.assertEqual(status, 1)
            self.assertIn("Usage:", buf.getvalue())

    def test_main_file_not_found(self):
        with patch.object(sys, "argv", ["test2.py", "does_not_exist.py"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                status = self.module.main()
            self.assertEqual(status, 1)
            self.assertIn("File not found:", buf.getvalue())

    def test_main_wrong_extension(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "file.txt"
            path.write_text("x=1", encoding="utf-8")
            with patch.object(sys, "argv", ["test2.py", str(path)]):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    status = self.module.main()
                self.assertEqual(status, 1)
                self.assertIn("Please provide a .py file.", buf.getvalue())

    def test_main_empty_documentation_does_not_modify(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "file.py"
            path.write_text("x=1", encoding="utf-8")
            with patch.object(self.module, "add_documentation", return_value="   "):
                with patch.object(sys, "argv", ["test2.py", str(path)]):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        status = self.module.main()
            self.assertEqual(status, 1)
            self.assertEqual(path.read_text(encoding="utf-8"), "x=1")
            self.assertIn("Model returned empty output", buf.getvalue())

    def test_main_success_writes_documented_code(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "file.py"
            path.write_text("x=1", encoding="utf-8")
            with patch.object(self.module, "add_documentation", return_value="doc\ncode"):
                with patch.object(sys, "argv", ["test2.py", str(path)]):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        status = self.module.main()
            self.assertEqual(status, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "doc\ncode\n")
            self.assertIn("Updated documentation in:", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
