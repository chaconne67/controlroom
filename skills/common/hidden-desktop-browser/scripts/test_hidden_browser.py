from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import hidden_browser


class HiddenBrowserContractTests(unittest.TestCase):
    def test_url_requires_http_or_https(self) -> None:
        self.assertEqual(hidden_browser.validate_url("http://127.0.0.1:8000/"), "http://127.0.0.1:8000/")
        with self.assertRaises(ValueError):
            hidden_browser.validate_url("file:///C:/secret.txt")

    def test_desktop_name_cannot_escape_state_directory(self) -> None:
        self.assertEqual(hidden_browser.validate_name("codex-web_hidden.1"), "codex-web_hidden.1")
        for unsafe in ("../other", "a/b", "", "space name"):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                hidden_browser.validate_name(unsafe)

    def test_paths_are_scoped_to_the_named_tool(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = hidden_browser.paths_for(Path(directory), "test-browser")
            self.assertEqual(paths["profile"], Path(directory) / "profiles" / "test-browser")
            self.assertEqual(paths["state"], Path(directory) / "state" / "test-browser.json")
            self.assertEqual(paths["lock"], Path(directory) / "state" / "test-browser.lock")
            self.assertEqual(paths["evidence"], Path(directory) / "evidence" / "test-browser")
            with_run = hidden_browser.paths_for(Path(directory), "test-browser", "run-1")
            self.assertEqual(with_run["profile"], paths["profile"])
            self.assertEqual(with_run["evidence"], paths["evidence"] / "run-1")

    def test_default_data_root_is_outside_appdata(self) -> None:
        root = str(hidden_browser.default_data_root()).lower()
        self.assertNotIn("appdata", root)
        self.assertNotIn("packages", root)

    def test_strip_ranges_removes_each_editable_region_once(self) -> None:
        text = "Header\nSECRET body\nSame Co 1,000\nSame Co 1,000\nSECRET body"
        self.assertEqual(
            hidden_browser.strip_ranges(text, ["SECRET body", " "]),
            "Header\n\nSame Co 1,000\nSame Co 1,000\nSECRET body",
        )

    def test_backend_choices(self) -> None:
        args = hidden_browser.parser().parse_args(["open", "http://127.0.0.1/", "--backend", "playwright"])
        self.assertEqual(args.backend, "playwright")
        with self.assertRaises(SystemExit):
            hidden_browser.parser().parse_args(["open", "http://127.0.0.1/", "--backend", "selenium"])

    def test_summary_js_never_reads_values(self) -> None:
        self.assertNotIn(".value", hidden_browser.SUMMARY_JS.replace("getAttribute('value')", ""))
        self.assertNotIn("textContent", hidden_browser.SUMMARY_JS.replace("n.textContent", ""))

    @unittest.skipUnless(os.name == "nt", "Windows desktop API test")
    def test_hidden_desktop_does_not_replace_input_desktop(self) -> None:
        before = hidden_browser.input_desktop_name()
        with hidden_browser.open_desktop("codex-hidden-unit-test", create=True) as (handle, _created):
            self.assertEqual(hidden_browser.object_name(handle), "codex-hidden-unit-test")
        self.assertEqual(hidden_browser.input_desktop_name(), before)

    @unittest.skipUnless(os.name == "nt", "Windows file lock test")
    def test_name_lock_is_exclusive_across_processes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "state" / "x.lock"
            holder = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sys, time; sys.path.insert(0, sys.argv[1]); import hidden_browser as h; from pathlib import Path\n"
                        "with h.name_lock(Path(sys.argv[2])):\n    print('held', flush=True); time.sleep(3)"
                    ),
                    str(Path(__file__).parent),
                    str(lock),
                ],
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                self.assertEqual(holder.stdout.readline().strip(), "held")
                with self.assertRaises(RuntimeError), hidden_browser.name_lock(lock):
                    pass
            finally:
                holder.wait(timeout=10)
                holder.stdout.close()
            with hidden_browser.name_lock(lock):
                pass

    def test_stop_reports_failure_when_process_survives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            browser = hidden_browser.HiddenBrowser("stop-test", data_root=Path(directory), timeout=1)
            hidden_browser.write_state(
                browser.paths["state"],
                {"name": "stop-test", "pid": os.getpid(), "chrome": sys.executable, "backend": "uia"},
            )
            original = hidden_browser.owns_chrome_window
            hidden_browser.owns_chrome_window = lambda _name, _pid: True
            killed: list[tuple[int, bool]] = []
            original_kill = hidden_browser.kill_process_tree
            hidden_browser.kill_process_tree = lambda pid, *, force: (
                killed.append((pid, force)) or subprocess.CompletedProcess([], 1, "", "")
            )
            try:
                with self.assertRaises(RuntimeError):
                    browser.stop()
            finally:
                hidden_browser.owns_chrome_window = original
                hidden_browser.kill_process_tree = original_kill
            self.assertTrue(killed)
            self.assertTrue(browser.paths["state"].is_file(), "state must survive a failed stop")

    def test_cli_returns_nonzero_json_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("hidden_browser.py")), "--data-root", directory, "--name", "absent", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error_type"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
