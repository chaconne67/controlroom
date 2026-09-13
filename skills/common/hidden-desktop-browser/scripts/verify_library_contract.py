#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow==12.3.0",
#   "playwright==1.58.0",
#   "pywin32==312",
#   "pywinauto==0.6.9",
# ]
# ///
"""Exercise the import contract the way a domain adapter would, in one process:
open with the playwright backend, use ``playwright_session`` twice, use ``uia_session``
twice from the main thread, reject a second desktop name on the attached thread, and
stop. Run by ``verify_hidden_browser.py``; needs the same dependencies as the module.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hidden_browser


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--name", required=True)
    cli.add_argument("--data-root", type=Path, required=True)
    cli.add_argument("--url", required=True)
    args = cli.parse_args()
    browser = hidden_browser.HiddenBrowser(args.name, data_root=args.data_root)
    result: dict[str, object] = {"name": args.name}
    opened = browser.open(args.url, backend="playwright")
    result["chrome_pids"] = [opened["pid"], opened["launcher_pid"]]
    try:
        titles = []
        for _ in range(2):
            with browser.playwright_session() as (page, observed):
                titles.append(page.title())
                result["observed_keys"] = sorted(observed)
        result["playwright_titles"] = titles
        uia_titles = []
        for _ in range(2):
            with browser.uia_session() as (window, document):
                uia_titles.append(window.window_text())
                result["uia_text_has_fixture"] = "Hidden browser fixture" in hidden_browser.uia_document_text(document)
        result["uia_titles"] = uia_titles
        other = hidden_browser.HiddenBrowser(f"{args.name}-other", data_root=args.data_root)
        try:
            hidden_browser.attach_thread_to_desktop(other.name)
        except RuntimeError as exc:
            result["second_name_rejected"] = "attached to hidden desktop" in str(exc)
        else:
            result["second_name_rejected"] = False

        worker_result: dict[str, object] = {}

        def worker() -> None:
            try:
                with browser.uia_session() as (window, _document):
                    worker_result["title"] = window.window_text()
            except Exception as exc:  # noqa: BLE001 - report the failure instead of crashing the thread.
                worker_result["error"] = f"{type(exc).__name__}: {exc}"

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=60)
        result["other_thread_uia"] = worker_result
    finally:
        stopped = browser.stop()
        result["stopped"] = stopped["stopped"]
    ok = (
        len(result["playwright_titles"]) == 2
        and len(result["uia_titles"]) == 2
        and result.get("uia_text_has_fixture") is True
        and result.get("second_name_rejected") is True
        and "title" in result["other_thread_uia"]
        and result["stopped"] is True
    )
    result["ok"] = ok
    print(json.dumps(result, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
