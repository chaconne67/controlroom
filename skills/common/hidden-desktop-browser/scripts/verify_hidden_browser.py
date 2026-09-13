#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow==12.3.0",
#   "playwright==1.62.0",
#   "pywin32==312",
#   "pywinauto==0.6.9",
# ]
# ///
"""End-to-end verification of the shared hidden browser on this Windows PC.

It serves ``fixtures/test-page.html`` locally, drives the real CLI entry point
(``run-hidden-browser.ps1``) for one backend, checks that typed values never reach
any output, exercises the import contract in a child process, races two ``open``
commands with the same name, and records every input-desktop or foreground change
with the owning PID so interference by tool-created windows can be told apart from
the user's own activity.

    uv run --script hidden_browser.py --help          # resolves dependencies once
    uv run --script verify_hidden_browser.py --backend playwright
    uv run --script verify_hidden_browser.py --backend uia
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hidden_browser

RUNNER = HERE / "run-hidden-browser.ps1"
SENTINEL = "ZQ9-SENTINEL-VALUE"
FIELDS_BY_ID = ["plain", "hint", "email", "combo", "search", "amount", "secret", "memo"]
FIELD_VALUES = {"email": "zq9sentinel@example.com", "amount": "424242"}
UIA_ROLE_BY_ID = {"combo": "combobox", "amount": "spinbutton"}


class DesktopObserver(threading.Thread):
    """Poll the input desktop and foreground window every 50 ms."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.events: list[dict[str, object]] = []
        self.stop_flag = threading.Event()

    def run(self) -> None:
        last = (hidden_browser.input_desktop_name(), hidden_browser.foreground_window()["hwnd"])
        while not self.stop_flag.is_set():
            desktop = hidden_browser.input_desktop_name()
            foreground = hidden_browser.foreground_window()
            current = (desktop, foreground["hwnd"])
            if current != last:
                self.events.append(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "input_desktop": desktop,
                        "hwnd": foreground["hwnd"],
                        "pid": foreground["pid"],
                        "image": hidden_browser.process_image(foreground["pid"]),
                    }
                )
                last = current
            time.sleep(0.05)


def serve_fixtures() -> tuple[http.server.ThreadingHTTPServer, str]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE / "fixtures"))
    handler.log_message = lambda *_args, **_kwargs: None  # type: ignore[attr-defined]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/test-page.html"


def profile_chrome_pids(profile: Path) -> list[int]:
    script = (
        "Get-CimInstance Win32_Process -Filter \"name='chrome.exe'\" | Where-Object { "
        f"$_.CommandLine -like '*{profile}*' }} | Select-Object -ExpandProperty ProcessId"
    )
    completed = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
    return [int(value) for value in completed.stdout.split()]


class Verification:
    def __init__(self, backend: str, data_root: Path, name: str) -> None:
        self.backend = backend
        self.data_root = data_root
        self.name = name
        self.steps: list[dict[str, object]] = []
        self.outputs: list[str] = []
        self.tool_pids: set[int] = set()
        self.profile = hidden_browser.paths_for(data_root, name)["profile"]

    def cli(self, *arguments: str, expect_ok: bool = True, name: str | None = None) -> dict[str, object]:
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUNNER),
            "--name",
            name or self.name,
            "--data-root",
            str(self.data_root),
            *arguments,
        ]
        started = time.monotonic()
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
        self.outputs.append(completed.stdout + completed.stderr)
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"non-JSON output for {arguments}: {completed.stdout[:400]} {completed.stderr[:400]}") from exc
        step = {
            "command": list(arguments),
            "ok": payload.get("ok"),
            "exit_code": completed.returncode,
            "seconds": round(time.monotonic() - started, 2),
            "input_desktop_unchanged": payload.get("input_desktop_unchanged"),
            "foreground_unchanged": payload.get("foreground_unchanged"),
        }
        if not payload.get("ok"):
            step["error"] = payload.get("error")
        self.steps.append(step)
        if expect_ok and (not payload.get("ok") or completed.returncode != 0):
            raise AssertionError(f"{arguments} failed: {payload}")
        if not expect_ok and (payload.get("ok") or completed.returncode == 0):
            raise AssertionError(f"{arguments} should have failed: {payload}")
        self.tool_pids.update(profile_chrome_pids(self.profile))
        return payload

    def assert_no_sentinel(self) -> None:
        leaks = [index for index, output in enumerate(self.outputs) if SENTINEL in output or "zq9sentinel" in output.lower() or "424242" in output]
        if leaks:
            raise AssertionError(f"typed values leaked into outputs of steps {leaks}")

    def fill_all(self) -> None:
        for field in FIELDS_BY_ID:
            value = FIELD_VALUES.get(field, SENTINEL)
            if self.backend == "playwright":
                self.cli("fill", "--selector", f"#{field}", "--value", value)
            else:
                self.cli("fill", "--role", UIA_ROLE_BY_ID.get(field, "textbox"), "--automation-id", field, "--value", value)
        if self.backend == "playwright":
            self.cli("fill", "--selector", "#editor", "--value", SENTINEL)
        # uia: contenteditable regions expose no ValuePattern, so fill is playwright-only there;
        # the fixture's initial editor text stands in for typed editor content below.

    def run_cli_flow(self, url: str) -> None:
        opened = self.cli("open", url, "--backend", self.backend)
        assert opened["backend"] == self.backend, opened
        status = self.cli("status")
        assert status["alive"] is True and status["windows"], status
        if self.backend == "playwright":
            assert status["cdp_ready"] is True, status
            navigated = self.cli("goto", url)
            observed = navigated["observed"]
            assert any("fixture console error" in item["text"] for item in observed["console_errors"]), observed
            assert any(item["status"] == 404 for item in observed["responses"]), observed
        snapshot = self.cli("snapshot")
        assert Path(str(snapshot["screenshot"])).stat().st_size > 0, snapshot
        assert "Hidden browser fixture" in snapshot["text"], snapshot["text"][:200]
        self.fill_all()
        after_fill = self.cli("snapshot")
        assert "Hidden browser fixture" in after_fill["text"]
        assert "initial editor text" not in after_fill["text"], "editable region must be excluded from the summary"
        text = self.cli("text")
        assert text["text"].count("Same Co") == 2, "text must keep repeated table values"
        assert "initial editor text" not in text["text"], "editable region must be excluded from text"
        self.cli("wait", "--text", "Before click")
        self.cli("click", "--role", "button", "--accessible-name", "Apply", "--exact")
        self.cli("wait", "--text", "After click")
        self.cli("click", "--role", "button", "--accessible-name", "Delayed", "--exact")
        self.cli("wait", "--text", "Delayed done")
        if self.backend == "playwright":
            target = self.data_root / "evidence" / self.name / "fixture-sample.txt"
            downloaded = self.cli("click", "--role", "link", "--accessible-name", "Download sample", "--exact", "--download-to", str(target))
            assert downloaded["download"]["size"] > 0 and target.is_file(), downloaded
            evaluated = self.cli("eval", "--js", "() => ({title: document.title, overflow: document.documentElement.scrollWidth > window.innerWidth})")
            assert evaluated["value"]["title"] == "Hidden browser fixture", evaluated
        self.cli("click", "--role", "button", "--accessible-name", "No such button", "--exact", expect_ok=False)
        stopped = self.cli("stop")
        assert stopped["stopped"] is True, stopped
        assert not hidden_browser.pid_alive(int(stopped["pid"])), "chrome pid still alive after stop"
        assert profile_chrome_pids(self.profile) == [], "chrome processes for the profile remain after stop"
        self.assert_no_sentinel()

    def run_library_flow(self, url: str) -> dict[str, object]:
        script = HERE / "verify_library_contract.py"
        completed = subprocess.run(
            [sys.executable, str(script), "--name", f"{self.name}-lib", "--data-root", str(self.data_root), "--url", url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.outputs.append(completed.stdout + completed.stderr)
        if completed.returncode != 0:
            raise AssertionError(f"library contract failed: {completed.stdout[-1500:]} {completed.stderr[-1500:]}")
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        self.tool_pids.update(payload.get("chrome_pids", []))
        return payload

    def run_race(self, url: str) -> dict[str, object]:
        race_name = f"{self.name}-race"
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RUNNER), "--name", race_name, "--data-root", str(self.data_root), "open", url, "--backend", self.backend]
        first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        second = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        results = []
        for process in (first, second):
            out, err = process.communicate(timeout=120)
            self.outputs.append(out + err)
            results.append(json.loads(out) if out.strip().startswith("{") else {"ok": False, "error": err[-300:]})
        winners = [result for result in results if result.get("ok")]
        assert len(winners) == 1, f"expected exactly one successful open, got {results}"
        state = json.loads(hidden_browser.paths_for(self.data_root, race_name)["state"].read_text(encoding="utf-8"))
        assert state["pid"] == winners[0]["pid"], "winner's state was overwritten or removed"
        assert hidden_browser.pid_alive(int(state["pid"]))
        stopped = self.cli("stop", name=race_name)
        return {"results": results, "state_pid": state["pid"], "stopped": stopped["stopped"]}


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--backend", choices=hidden_browser.BACKENDS, required=True)
    cli.add_argument("--data-root", type=Path, default=hidden_browser.default_data_root())
    cli.add_argument("--name", default=None)
    cli.add_argument("--skip-race", action="store_true")
    cli.add_argument("--skip-library", action="store_true")
    args = cli.parse_args(argv)
    name = args.name or f"verify-{args.backend}"
    observer = DesktopObserver()
    observer.start()
    server, url = serve_fixtures()
    verification = Verification(args.backend, args.data_root, name)
    report: dict[str, object] = {"backend": args.backend, "name": name, "url": url, "data_root": str(args.data_root)}
    ok = True
    try:
        verification.run_cli_flow(url)
        report["cli"] = "passed"
        if not args.skip_library:
            report["library"] = verification.run_library_flow(url)
        if not args.skip_race:
            report["race"] = verification.run_race(url)
    except AssertionError as exc:
        ok = False
        report["failure"] = str(exc)
    finally:
        observer.stop_flag.set()
        observer.join(timeout=2)
        server.shutdown()
    tool_pids = verification.tool_pids
    interference = [event for event in observer.events if event["pid"] in tool_pids or event["input_desktop"] != "Default"]
    report["steps"] = verification.steps
    report["foreground_events"] = observer.events
    report["tool_chrome_pids"] = sorted(tool_pids)
    report["interference_events"] = interference
    report["ok"] = ok and not interference
    evidence = hidden_browser.paths_for(args.data_root, name)["evidence"]
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / f"verify-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report"] = str(report_path)
    print(json.dumps({key: value for key, value in report.items() if key not in {"steps", "foreground_events"}}, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
