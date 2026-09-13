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
"""Run a dedicated Chrome window on an isolated Windows desktop.

Chrome is created directly on a named Win32 desktop so the user's input desktop,
foreground window, mouse, keyboard, and clipboard are never touched.

Two backends share the same lifecycle:

- ``uia``: Windows UI Automation reads and operates the window; PrintWindow captures it.
- ``playwright``: Chrome exposes a CDP port; every command connects with Playwright,
  acts, and disconnects while Chrome and its page state stay alive.

The module is importable (``HiddenBrowser``) for domain adapters and runs as a CLI.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import json
import msvcrt
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from collections.abc import Iterator
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_NAME = "web-hidden"
DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 1000
BACKENDS = ("uia", "playwright")
DESKTOP_ALL_ACCESS = 0x000F01FF
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SYNCHRONIZE = 0x00100000
WAIT_TIMEOUT = 0x00000102
UOI_NAME = 2
PW_RENDERFULLCONTENT = 2
CHROME_WINDOW_CLASS = "Chrome_WidgetWin_1"
NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
OBSERVED_LIMIT = 200
ROLE_TO_CONTROL_TYPE = {
    "button": "Button",
    "checkbox": "CheckBox",
    "combobox": "ComboBox",
    "link": "Hyperlink",
    "radio": "RadioButton",
    "spinbutton": "Spinner",
    "tab": "TabItem",
    "textbox": "Edit",
}
UIA_IS_KEYBOARD_FOCUSABLE = 30009
UIA_IS_TEXT_EDIT_PATTERN_AVAILABLE = 30149
UIA_VALUE_TYPES = {"Edit", "ComboBox", "Spinner"}
UIA_CONTENTEDITABLE_TYPES = {"Group", "Custom", "Text", "Pane"}
UIA_SUMMARY_TYPES = {"Button", "CheckBox", "ComboBox", "Hyperlink", "RadioButton", "TabItem", "Text"}
UIA_INTERACTIVE_TYPES = set(ROLE_TO_CONTROL_TYPE.values())

# Page summary for the playwright backend. It never reads .value or the text of
# editable regions, so automatically generated output cannot leak typed input.
SUMMARY_JS = r"""
() => {
  const implicitRole = (el) => {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || 'text').toLowerCase();
    if (tag === 'a' && el.hasAttribute('href')) return 'link';
    if (tag === 'button') return 'button';
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'input') {
      if (['button', 'submit', 'reset', 'image'].includes(type)) return 'button';
      if (type === 'checkbox') return 'checkbox';
      if (type === 'radio') return 'radio';
      if (type === 'search') return 'searchbox';
      if (type === 'number') return 'spinbutton';
      if (type === 'range') return 'slider';
      return 'textbox';
    }
    if (el.isContentEditable) return 'textbox';
    return '';
  };
  const labelText = (el) => {
    const byAttr = el.getAttribute('aria-label');
    if (byAttr) return byAttr.trim();
    const labelled = el.getAttribute('aria-labelledby');
    if (labelled) {
      const parts = labelled.split(/\s+/).map((id) => document.getElementById(id)).filter(Boolean);
      if (parts.length) return parts.map((n) => n.innerText || n.textContent || '').join(' ').trim();
    }
    if (el.labels && el.labels.length) return Array.from(el.labels).map((l) => l.innerText || '').join(' ').trim();
    const role = implicitRole(el);
    if (role === 'button' || role === 'link') {
      const own = (el.innerText || el.getAttribute('value') || el.getAttribute('title') || '').trim();
      if (own) return own;
    }
    return (el.getAttribute('title') || '').trim();
  };
  const selector = 'a[href], button, input, select, textarea, [role], [contenteditable]';
  const interactive = [];
  for (const el of document.querySelectorAll(selector)) {
    if (interactive.length >= 200) break;
    const role = el.getAttribute('role') || implicitRole(el);
    if (!role) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    interactive.push({
      role,
      name: labelText(el),
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      placeholder: el.getAttribute('placeholder') || '',
      enabled: !el.disabled,
      rectangle: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.right), Math.round(rect.bottom)],
    });
  }
  let text = document.body ? document.body.innerText : '';
  for (const editable of document.querySelectorAll('[contenteditable]')) {
    if (!editable.isContentEditable) continue;
    const own = editable.innerText;
    if (own && own.trim()) text = text.replace(own, '');
  }
  return {
    title: document.title,
    url: location.href,
    ready_state: document.readyState,
    viewport: [window.innerWidth, window.innerHeight],
    scroll_size: [document.documentElement.scrollWidth, document.documentElement.scrollHeight],
    text,
    interactive,
  };
}
"""


class StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class ProcessInformation(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


def require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("hidden-browser runs only on Windows")


def validate_name(name: str) -> str:
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError("desktop name must contain only A-Z, a-z, 0-9, dot, underscore, or hyphen")
    return name


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute http:// or https:// address")
    return url


def default_data_root() -> Path:
    # Outside AppData on purpose: packaged apps (the Codex desktop app) virtualize
    # AppData\Local, so a path there would give each agent a different profile store.
    return Path.home() / ".hidden-browser"


def paths_for(data_root: Path, name: str, run_id: str | None = None) -> dict[str, Path]:
    root = data_root.resolve()
    evidence = root / "evidence" / name
    if run_id:
        evidence = evidence / validate_name(run_id)
    return {
        "root": root,
        "profile": root / "profiles" / name,
        "state": root / "state" / f"{name}.json",
        "lock": root / "state" / f"{name}.lock",
        "evidence": evidence,
    }


def chrome_path() -> Path:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Google Chrome is not installed in a standard location")


def win32() -> tuple[Any, Any]:
    require_windows()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenDesktopW.restype = wintypes.HANDLE
    user32.CreateDesktopW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    user32.CreateDesktopW.restype = wintypes.HANDLE
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.CloseDesktop.restype = wintypes.BOOL
    user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
    user32.SetThreadDesktop.restype = wintypes.BOOL
    user32.GetUserObjectInformationW.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetUserObjectInformationW.restype = wintypes.BOOL
    user32.EnumDesktopWindows.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.LPARAM]
    user32.EnumDesktopWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetForegroundWindow.restype = wintypes.HWND

    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(StartupInfo),
        ctypes.POINTER(ProcessInformation),
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    return user32, kernel32


def object_name(handle: Any) -> str:
    user32, _ = win32()
    needed = wintypes.DWORD()
    user32.GetUserObjectInformationW(handle, UOI_NAME, None, 0, ctypes.byref(needed))
    if not needed.value:
        raise ctypes.WinError(ctypes.get_last_error())
    character_count = max(needed.value // ctypes.sizeof(ctypes.c_wchar), 1)
    buffer = ctypes.create_unicode_buffer(character_count)
    if not user32.GetUserObjectInformationW(handle, UOI_NAME, buffer, needed, ctypes.byref(needed)):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.value


def input_desktop_name() -> str:
    user32, _ = win32()
    handle = user32.OpenInputDesktop(0, False, 0x0001)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return object_name(handle)
    finally:
        user32.CloseDesktop(handle)


def foreground_window() -> dict[str, int]:
    user32, _ = win32()
    hwnd = user32.GetForegroundWindow()
    owner = wintypes.DWORD()
    if hwnd:
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    return {"hwnd": int(hwnd or 0), "pid": int(owner.value)}


@contextlib.contextmanager
def open_desktop(name: str, *, create: bool = False) -> Iterator[tuple[Any, bool]]:
    """Yield (handle, created). The handle is closed on exit; the desktop itself lives
    while any process or handle still references it."""
    user32, _ = win32()
    created = False
    handle = user32.OpenDesktopW(name, 0, False, DESKTOP_ALL_ACCESS)
    if not handle and create:
        handle = user32.CreateDesktopW(name, None, None, 0, DESKTOP_ALL_ACCESS, None)
        created = bool(handle)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield handle, created
    finally:
        user32.CloseDesktop(handle)


def windows_on_handle(handle: Any, *, pid: int | None = None) -> list[dict[str, Any]]:
    user32, _ = win32()
    found: list[dict[str, Any]] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _parameter: int) -> bool:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if (pid is None or owner.value == pid) and user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            found.append({"hwnd": int(hwnd), "pid": owner.value, "title": title.value})
        return True

    procedure = callback_type(callback)
    # An empty desktop can return zero while leaving an unrelated Win32 error
    # value behind. The handle was already validated by open_desktop.
    user32.EnumDesktopWindows(handle, ctypes.cast(procedure, ctypes.c_void_p), 0)
    return found


def desktop_windows(name: str, *, pid: int | None = None) -> list[dict[str, Any]]:
    with open_desktop(name) as (handle, _created):
        return windows_on_handle(handle, pid=pid)


def chrome_windows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item["title"].endswith("- Chrome")]


def owns_chrome_window(name: str, pid: int) -> bool:
    try:
        return bool(chrome_windows(desktop_windows(name, pid=pid)))
    except OSError:
        return False


def pid_alive(pid: int) -> bool:
    _, kernel32 = win32()
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return False
    try:
        return kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


def process_image(pid: int) -> str | None:
    _, kernel32 = win32()
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        capacity = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(capacity.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(capacity)):
            return None
        return buffer.value
    finally:
        kernel32.CloseHandle(handle)


def kill_process_tree(pid: int, *, force: bool) -> subprocess.CompletedProcess[str]:
    command = ["taskkill", "/PID", str(pid), "/T"] + (["/F"] if force else [])
    return subprocess.run(command, capture_output=True, text=True, check=False)


def read_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError("hidden browser is not running; use open first")
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


@contextlib.contextmanager
def name_lock(lock_path: Path) -> Iterator[None]:
    """Exclusive per-name lock so two ``open``/``stop`` commands cannot interleave.
    The OS releases the byte lock when the holding process exits."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+b")  # noqa: SIM115 - closed in finally after unlocking.
    try:
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError("another hidden-browser command holds this name; wait for it to finish") from exc
        try:
            yield
        finally:
            handle.seek(0)
            with contextlib.suppress(OSError):
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        handle.close()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def cdp_ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
            return response.status == 200
    except OSError:
        return False


def strip_ranges(text: str, ranges: list[str]) -> str:
    """Remove editable regions' text from a body text, one occurrence per region."""
    for fragment in ranges:
        fragment = fragment.strip()
        if fragment:
            text = text.replace(fragment, "", 1)
    return text


_DESKTOP_ATTACHMENTS: dict[int, tuple[str, int]] = {}
_ATTACHMENT_LOCK = threading.Lock()


def attach_thread_to_desktop(name: str) -> int:
    """Attach the calling thread to the named desktop once and keep the handle for the
    life of the process. A thread can only ever be attached to one desktop name."""
    thread_id = threading.get_ident()
    with _ATTACHMENT_LOCK:
        current = _DESKTOP_ATTACHMENTS.get(thread_id)
        if current is not None:
            if current[0] != name:
                raise RuntimeError(
                    f"this thread is attached to hidden desktop {current[0]!r}; use a new thread for {name!r}"
                )
            return current[1]
        user32, _ = win32()
        handle = user32.OpenDesktopW(name, 0, False, DESKTOP_ALL_ACCESS)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if not user32.SetThreadDesktop(handle):
            user32.CloseDesktop(handle)
            raise RuntimeError(
                "could not attach this thread to the hidden desktop; call uia_session() before any GUI "
                "module (pywinauto, comtypes, tkinter) is imported in this thread"
            )
        _DESKTOP_ATTACHMENTS[thread_id] = (name, int(handle))
        return int(handle)


def control_text(control: Any) -> str:
    try:
        return str(control.window_text() or "").strip()
    except Exception:  # noqa: BLE001 - UIA wrappers expose backend-specific exceptions.
        return ""


def editable_controls(document: Any) -> list[Any]:
    """Controls that hold typed text: input-like control types, plus contenteditable
    regions, which Chrome exposes as keyboard-focusable containers with the TextEdit
    pattern. Plain labels also advertise TextEdit, so focusability is required."""
    found = []
    for control in document.descendants():
        try:
            info = control.element_info
            control_type = str(info.control_type or "")
            if control_type in UIA_VALUE_TYPES:
                found.append(control)
            elif control_type in UIA_CONTENTEDITABLE_TYPES:
                raw = info.element
                if raw.GetCurrentPropertyValue(UIA_IS_KEYBOARD_FOCUSABLE) and raw.GetCurrentPropertyValue(
                    UIA_IS_TEXT_EDIT_PATTERN_AVAILABLE
                ):
                    found.append(control)
        except Exception:  # noqa: BLE001, S112 - a vanished element is simply not editable text.
            continue
    return found


def editable_runtime_ids(editables: list[Any]) -> set[tuple[int, ...]]:
    ids: set[tuple[int, ...]] = set()
    for editable in editables:
        for control in (editable, *editable.descendants()):
            with contextlib.suppress(Exception):
                ids.add(tuple(control.element_info.runtime_id))
    return ids


def uia_summary(window: Any, document: Any, *, text_limit: int) -> dict[str, Any]:
    """Screen-judgement summary: de-duplicated visible texts plus interactive controls.
    Text inside editable regions is never collected, so typed values do not appear."""
    excluded = editable_runtime_ids(editable_controls(document))
    texts: list[str] = []
    interactive: list[dict[str, Any]] = []
    for control in document.descendants():
        info = control.element_info
        control_type = str(info.control_type or "")
        inside_editable = tuple(info.runtime_id) in excluded
        text = "" if inside_editable else control_text(control)
        if control_type in UIA_SUMMARY_TYPES and text and text not in texts:
            texts.append(text)
        if control_type in UIA_INTERACTIVE_TYPES and len(interactive) < 200:
            rectangle = info.rectangle
            interactive.append(
                {
                    "control_type": control_type,
                    "name": control_text(control) if control_type != "Edit" else info.name or "",
                    "automation_id": str(info.automation_id or ""),
                    "enabled": bool(control.is_enabled()),
                    "rectangle": [rectangle.left, rectangle.top, rectangle.right, rectangle.bottom],
                }
            )
    horizontally_scrollable = None
    try:
        horizontally_scrollable = bool(document.iface_scroll.CurrentHorizontallyScrollable)
    except Exception:  # noqa: BLE001 - the Scroll pattern is optional in UIA.
        horizontally_scrollable = None
    rectangle = window.rectangle()
    text = "\n".join(texts)
    return {
        "title": window.window_text(),
        "window_rectangle": [rectangle.left, rectangle.top, rectangle.right, rectangle.bottom],
        "horizontal_scrollable": horizontally_scrollable,
        "text": text[:text_limit],
        "interactive": interactive,
    }


def uia_document_text(document: Any) -> str:
    """Full document text with editable regions removed. No de-duplication or truncation."""
    text = str(document.iface_text.DocumentRange.GetText(-1))
    editable: list[str] = []
    for control in editable_controls(document):
        # A control without TextPattern (a native select) contributes no typed text range;
        # its name is a label, so nothing is stripped for it.
        with contextlib.suppress(Exception):
            editable.append(str(control.iface_text.DocumentRange.GetText(-1)))
    return strip_ranges(text, editable)


def print_window(hwnd: int, output: Path) -> tuple[bool, tuple[int, int]]:
    # Imported after the thread is attached to the hidden desktop.
    import win32gui
    import win32ui
    from PIL import Image

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise RuntimeError("hidden Chrome window has no drawable size")
    source_handle = win32gui.GetWindowDC(hwnd)
    source_dc = win32ui.CreateDCFromHandle(source_handle)
    target_dc = source_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(source_dc, width, height)
    target_dc.SelectObject(bitmap)
    try:
        rendered = bool(ctypes.windll.user32.PrintWindow(hwnd, target_dc.GetSafeHdc(), PW_RENDERFULLCONTENT))
        info = bitmap.GetInfo()
        bits = bitmap.GetBitmapBits(True)
        image = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]), bits, "raw", "BGRX", 0, 1)
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output)
        if not rendered or image.getbbox() is None:
            raise RuntimeError("PrintWindow did not render the hidden Chrome window")
        return rendered, image.size
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        target_dc.DeleteDC()
        source_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, source_handle)


def invoke_control(control: Any) -> str:
    for pattern, action in (
        ("iface_invoke", "Invoke"),
        ("iface_selection_item", "Select"),
        ("iface_toggle", "Toggle"),
    ):
        try:
            interface = getattr(control, pattern)
            getattr(interface, action)()
            return action.lower()
        except Exception:  # noqa: BLE001, S112 - probe the next supported UIA pattern.
            continue
    raise RuntimeError("target control has no UI Automation invoke, selection, or toggle action")


def match_controls(candidates: list[Any], name: str, *, exact: bool) -> list[Any]:
    if exact:
        return [control for control in candidates if control_text(control) == name]
    needle = name.casefold()
    return [control for control in candidates if needle in control_text(control).casefold()]


def one_control(document: Any, *, control_type: str, name: str | None, automation_id: str | None, exact: bool) -> Any:
    candidates = document.descendants(control_type=control_type)
    if automation_id:
        matches = [control for control in candidates if str(control.element_info.automation_id or "") == automation_id]
    elif name is not None:
        matches = match_controls(candidates, name, exact=exact)
    else:
        raise ValueError("either --accessible-name or --automation-id is required")
    if len(matches) != 1:
        names = [control_text(control) for control in candidates[:30]]
        raise RuntimeError(f"expected one matching control, found {len(matches)}; available={names}")
    return matches[0]


def new_observed() -> dict[str, list[dict[str, Any]]]:
    return {"console_errors": [], "failed_requests": [], "responses": [], "downloads": []}


def observe_page(page: Any, observed: dict[str, list[dict[str, Any]]]) -> None:
    def push(key: str, item: dict[str, Any]) -> None:
        if len(observed[key]) < OBSERVED_LIMIT:
            observed[key].append(item)

    page.on(
        "console",
        lambda message: message.type in {"error", "warning"}
        and push("console_errors", {"type": message.type, "text": message.text[:500]}),
    )
    page.on("pageerror", lambda error: push("console_errors", {"type": "pageerror", "text": str(error)[:500]}))
    page.on(
        "requestfailed",
        lambda request: push("failed_requests", {"url": request.url, "error": str(request.failure or "")}),
    )
    page.on(
        "response",
        lambda response: response.request.resource_type in {"document", "stylesheet", "script", "xhr", "fetch"}
        and push(
            "responses",
            {"url": response.url, "status": response.status, "type": response.request.resource_type},
        ),
    )


class HiddenBrowser:
    """One named hidden Chrome: its profile, desktop, state, and both backends."""

    def __init__(self, name: str = DEFAULT_NAME, *, data_root: Path | None = None, run_id: str | None = None, timeout: int = 30):
        self.name = validate_name(name)
        self.paths = paths_for(data_root or default_data_root(), self.name, run_id)
        self.timeout = timeout

    # ----- lifecycle -------------------------------------------------------------------

    def open(self, url: str, *, backend: str = "uia", width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> dict[str, Any]:
        validate_url(url)
        if backend not in BACKENDS:
            raise ValueError(f"backend must be one of {BACKENDS}")
        with name_lock(self.paths["lock"]):
            return self._open_locked(url, backend=backend, width=width, height=height)

    def _open_locked(self, url: str, *, backend: str, width: int, height: int) -> dict[str, Any]:
        locations = self.paths
        if locations["state"].is_file():
            previous = json.loads(locations["state"].read_text(encoding="utf-8"))
            if pid_alive(int(previous.get("pid", 0))):
                raise RuntimeError("this hidden browser is already running")
            locations["state"].unlink()

        locations["profile"].mkdir(parents=True, exist_ok=True)
        executable = chrome_path()
        cdp_port = free_port() if backend == "playwright" else None
        arguments = [
            str(executable),
            f"--user-data-dir={locations['profile']}",
            "--no-first-run",
            "--no-default-browser-check",
            "--force-renderer-accessibility",
            "--disable-session-crashed-bubble",
            "--window-position=0,0",
            f"--window-size={width},{height}",
            "--new-window",
        ]
        if cdp_port is not None:
            arguments.append(f"--remote-debugging-port={cdp_port}")
        arguments.append(url)
        command_buffer = ctypes.create_unicode_buffer(subprocess.list2cmdline(arguments))
        startup = StartupInfo()
        startup.cb = ctypes.sizeof(startup)
        startup.lpDesktop = self.name
        info = ProcessInformation()
        _user32, kernel32 = win32()
        launcher_pid = 0
        pid = 0
        windows: list[dict[str, Any]] = []
        try:
            with open_desktop(self.name, create=True) as (desktop_handle, _created):
                if windows_on_handle(desktop_handle):
                    raise RuntimeError(
                        "hidden desktop already contains a window that this run did not create; "
                        "use its recorded state or another name"
                    )
                if not kernel32.CreateProcessW(
                    None,
                    command_buffer,
                    None,
                    None,
                    False,
                    DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    None,
                    None,
                    ctypes.byref(startup),
                    ctypes.byref(info),
                ):
                    raise ctypes.WinError(ctypes.get_last_error())
                launcher_pid = int(info.dwProcessId)
                pid = launcher_pid
                kernel32.CloseHandle(info.hThread)
                kernel32.CloseHandle(info.hProcess)
                deadline = time.monotonic() + self.timeout
                while time.monotonic() < deadline:
                    windows = windows_on_handle(desktop_handle)
                    ready = chrome_windows(windows)
                    if ready and (cdp_port is None or cdp_ready(cdp_port)):
                        pid = int(ready[0]["pid"])
                        break
                    time.sleep(0.25)
                else:
                    raise TimeoutError("Chrome hidden window (and CDP endpoint) did not become ready")

            state = {
                "name": self.name,
                "backend": backend,
                "pid": pid,
                "launcher_pid": launcher_pid,
                "cdp_port": cdp_port,
                "profile": str(locations["profile"]),
                "chrome": str(executable),
                "started_at": datetime.now(UTC).isoformat(),
                "initial_url": url,
                "width": width,
                "height": height,
                "data_root": str(locations["root"]),
            }
            write_state(locations["state"], state)
            return {**state, "windows": windows}
        except Exception:
            # Clean up only what this run created: the process tree it launched.
            # The state file was not written yet, so no other run's state is touched.
            for candidate in {candidate for candidate in (pid, launcher_pid) if candidate}:
                image = process_image(candidate)
                if image and Path(image).resolve() == executable.resolve():
                    kill_process_tree(candidate, force=True)
            raise

    def state(self) -> dict[str, Any]:
        return read_state(self.paths["state"])

    def status(self) -> dict[str, Any]:
        state = self.state()
        pid = int(state["pid"])
        alive = pid_alive(pid)
        return {
            **state,
            "alive": alive,
            "process_image": process_image(pid),
            "windows": desktop_windows(self.name, pid=pid) if alive else [],
            "cdp_ready": cdp_ready(int(state["cdp_port"])) if alive and state.get("cdp_port") else None,
        }

    def stop(self) -> dict[str, Any]:
        with name_lock(self.paths["lock"]):
            state = self.state()
            pid = int(state["pid"])
            expected = Path(state["chrome"]).resolve()
            if pid_alive(pid):
                image = process_image(pid)
                if image is None or Path(image).resolve() != expected or not owns_chrome_window(self.name, pid):
                    raise RuntimeError("refusing to stop a process whose executable is not the recorded Chrome")
                result = kill_process_tree(pid, force=False)
                if result.returncode and pid_alive(pid):
                    result = kill_process_tree(pid, force=True)
                deadline = time.monotonic() + self.timeout
                while pid_alive(pid) and time.monotonic() < deadline:
                    time.sleep(0.2)
            if pid_alive(pid):
                raise RuntimeError(f"dedicated Chrome pid {pid} is still running after stop")
            self.paths["state"].unlink(missing_ok=True)
            return {"name": self.name, "pid": pid, "stopped": True, "profile_preserved": str(self.paths["profile"])}

    # ----- backend sessions ------------------------------------------------------------

    def _running_state(self, backend: str | None = None) -> dict[str, Any]:
        state = self.state()
        if not pid_alive(int(state["pid"])):
            raise RuntimeError("hidden Chrome is not running")
        if backend and state.get("backend") != backend:
            raise RuntimeError(f"this hidden browser was opened with backend {state.get('backend')!r}, not {backend!r}")
        return state

    @contextlib.contextmanager
    def uia_session(self) -> Iterator[tuple[Any, Any]]:
        """Attach the calling thread to the hidden desktop and yield (window, document).
        Call it before importing any GUI module in this thread; one thread serves one name."""
        state = self._running_state()
        pid = int(state["pid"])
        attach_thread_to_desktop(self.name)
        # Imported only after SetThreadDesktop: GUI imports create thread-owned objects.
        from pywinauto.application import Application

        app = Application(backend="uia").connect(process=pid, timeout=self.timeout)
        window = next(
            (item for item in app.windows(class_name=CHROME_WINDOW_CLASS) if item.window_text().endswith("- Chrome")),
            None,
        )
        if window is None:
            raise RuntimeError("dedicated Chrome window was not found on the hidden desktop")
        document = window.descendants(control_type="Document")
        if not document:
            raise RuntimeError("Chrome page document was not exposed through UI Automation")
        yield window, document[0]

    @contextlib.contextmanager
    def playwright_session(self) -> Iterator[tuple[Any, dict[str, list[dict[str, Any]]]]]:
        """Connect to the hidden Chrome over CDP and yield (page, observed). Only the
        connection is closed afterwards; Chrome keeps running. Use the page in this thread only."""
        state = self._running_state("playwright")
        # The bundled Node driver prints url.parse() deprecation warnings to stderr; keep evidence clean.
        os.environ.setdefault("NODE_OPTIONS", "--no-deprecation")
        from playwright.sync_api import sync_playwright

        observed = new_observed()
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{state['cdp_port']}", timeout=self.timeout * 1000
            )
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                pages = [page for page in context.pages if not page.is_closed()]
                page = pages[-1] if pages else context.new_page()
                page.set_default_timeout(self.timeout * 1000)
                observe_page(page, observed)
                yield page, observed
            finally:
                browser.close()  # disconnects; the CDP-launched Chrome stays alive

    # ----- commands --------------------------------------------------------------------

    def _backend(self) -> str:
        return str(self._running_state().get("backend", "uia"))

    def _evidence_path(self, output: Path | None, suffix: str = ".png") -> Path:
        if output is None:
            self.paths["evidence"].mkdir(parents=True, exist_ok=True)
            output = self.paths["evidence"] / f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}{suffix}"
        return output.resolve()

    def _pw_summary(self, page: Any) -> dict[str, Any]:
        return page.evaluate(SUMMARY_JS)

    def snapshot(self, *, output: Path | None = None, text_limit: int = 5000) -> dict[str, Any]:
        output = self._evidence_path(output)
        if self._backend() == "playwright":
            with self.playwright_session() as (page, observed):
                page.screenshot(path=str(output))
                summary = self._pw_summary(page)
            summary["text"] = summary["text"][:text_limit]
            return {**summary, "screenshot": str(output), "observed": observed}
        with self.uia_session() as (window, document):
            rendered, image_size = print_window(window.handle, output)
            summary = uia_summary(window, document, text_limit=text_limit)
        return {**summary, "screenshot": str(output), "rendered": rendered, "image_size": list(image_size)}

    def text(self) -> dict[str, Any]:
        if self._backend() == "playwright":
            with self.playwright_session() as (page, observed):
                summary = self._pw_summary(page)
            return {"title": summary["title"], "url": summary["url"], "text": summary["text"], "observed": observed}
        with self.uia_session() as (window, document):
            return {"title": window.window_text(), "text": uia_document_text(document)}

    def goto(self, url: str, *, text_limit: int = 5000) -> dict[str, Any]:
        validate_url(url)
        with self.playwright_session() as (page, observed):
            response = page.goto(url, wait_until="domcontentloaded")
            summary = self._pw_summary(page)
        summary["text"] = summary["text"][:text_limit]
        return {**summary, "status": response.status if response else None, "observed": observed}

    def click(
        self,
        *,
        role: str | None = None,
        accessible_name: str | None = None,
        automation_id: str | None = None,
        selector: str | None = None,
        exact: bool = False,
        wait: float = 0.5,
        download_to: Path | None = None,
        text_limit: int = 5000,
    ) -> dict[str, Any]:
        if self._backend() == "playwright":
            return self._pw_click(
                role=role,
                accessible_name=accessible_name,
                selector=selector,
                exact=exact,
                wait=wait,
                download_to=download_to,
                text_limit=text_limit,
            )
        if not role:
            raise ValueError("--role is required for the uia backend")
        with self.uia_session() as (window, document):
            control = one_control(
                document,
                control_type=ROLE_TO_CONTROL_TYPE[role],
                name=accessible_name,
                automation_id=automation_id,
                exact=exact,
            )
            control.set_focus()
            action = invoke_control(control)
            time.sleep(wait)
            refreshed = window.descendants(control_type="Document")
            if not refreshed:
                raise RuntimeError("Chrome page document disappeared after the action")
            summary = uia_summary(window, refreshed[0], text_limit=text_limit)
        return {**summary, "action": action, "role": role, "accessible_name": accessible_name}

    def _pw_locator(self, page: Any, *, role: str | None, accessible_name: str | None, selector: str | None, exact: bool) -> Any:
        if selector:
            locator = page.locator(selector)
        elif role and accessible_name is not None:
            locator = page.get_by_role(role, name=accessible_name, exact=exact)
        else:
            raise ValueError("either --selector or --role with --accessible-name is required")
        count = locator.count()
        if count != 1:
            raise RuntimeError(f"expected one matching element, found {count}")
        return locator

    def _pw_click(
        self,
        *,
        role: str | None,
        accessible_name: str | None,
        selector: str | None,
        exact: bool,
        wait: float,
        download_to: Path | None,
        text_limit: int,
    ) -> dict[str, Any]:
        with self.playwright_session() as (page, observed):
            locator = self._pw_locator(page, role=role, accessible_name=accessible_name, selector=selector, exact=exact)
            download_result: dict[str, Any] | None = None
            if download_to is not None:
                target = download_to.resolve()
                with page.expect_download(timeout=self.timeout * 1000) as pending:
                    locator.click()
                download = pending.value
                failure = download.failure()
                if failure:
                    raise RuntimeError(f"download failed: {failure}")
                target.parent.mkdir(parents=True, exist_ok=True)
                download.save_as(str(target))
                size = target.stat().st_size
                if size <= 0:
                    raise RuntimeError("download produced an empty file")
                download_result = {"path": str(target), "size": size, "suggested_filename": download.suggested_filename}
                observed["downloads"].append(download_result)
            else:
                locator.click()
            page.wait_for_timeout(int(wait * 1000))
            summary = self._pw_summary(page)
        summary["text"] = summary["text"][:text_limit]
        return {**summary, "action": "click", "role": role, "accessible_name": accessible_name, "selector": selector, "download": download_result, "observed": observed}

    def fill(
        self,
        value: str,
        *,
        role: str | None = None,
        accessible_name: str | None = None,
        automation_id: str | None = None,
        selector: str | None = None,
        exact: bool = False,
        text_limit: int = 5000,
    ) -> dict[str, Any]:
        """Set a field's value. The value never appears in results or errors."""
        if self._backend() == "playwright":
            with self.playwright_session() as (page, observed):
                locator = self._pw_locator(page, role=role or "textbox", accessible_name=accessible_name, selector=selector, exact=exact)
                locator.fill(value)
                summary = self._pw_summary(page)
            summary["text"] = summary["text"][:text_limit]
            return {**summary, "action": "fill", "filled": True, "accessible_name": accessible_name, "selector": selector, "observed": observed}
        with self.uia_session() as (window, document):
            control = one_control(
                document,
                control_type=ROLE_TO_CONTROL_TYPE[role or "textbox"],
                name=accessible_name,
                automation_id=automation_id,
                exact=exact,
            )
            control.set_focus()
            control.iface_value.SetValue(value)
            summary = uia_summary(window, document, text_limit=text_limit)
        return {**summary, "action": "fill", "filled": True, "accessible_name": accessible_name, "automation_id": automation_id}

    def wait_text(self, marker: str, *, timeout: float | None = None, interval: float = 0.5) -> dict[str, Any]:
        deadline = time.monotonic() + (timeout if timeout is not None else self.timeout)
        backend = self._backend()
        attempts = 0
        while True:
            attempts += 1
            if backend == "playwright":
                with self.playwright_session() as (page, _observed):
                    found = marker in self._pw_summary(page)["text"]
            else:
                with self.uia_session() as (_window, document):
                    found = marker in uia_document_text(document)
            if found:
                return {"marker": marker, "found": True, "attempts": attempts}
            if time.monotonic() >= deadline:
                raise TimeoutError(f"marker not found within timeout: {marker!r}")
            time.sleep(interval)

    def eval_js(self, js: str) -> dict[str, Any]:
        """Caller-requested extraction. Values are returned as-is; the caller owns secrecy."""
        with self.playwright_session() as (page, observed):
            value = page.evaluate(js)
        return {"value": value, "observed": observed}


# ----- CLI ------------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument("--name", default=DEFAULT_NAME, type=validate_name)
    cli.add_argument("--data-root", type=Path, default=default_data_root())
    cli.add_argument("--run-id", type=validate_name, default=None, help="evidence sub-folder for this run")
    cli.add_argument("--timeout", type=int, default=30)
    commands = cli.add_subparsers(dest="command", required=True)

    open_command = commands.add_parser("open", help="open dedicated Chrome on the hidden desktop")
    open_command.add_argument("url", type=validate_url)
    open_command.add_argument("--backend", choices=BACKENDS, default="uia")
    open_command.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    open_command.add_argument("--height", type=int, default=DEFAULT_HEIGHT)

    commands.add_parser("status", help="show the hidden desktop and Chrome state")

    snapshot = commands.add_parser("snapshot", help="capture the page and summarize it for screen judgement")
    snapshot.add_argument("--output", type=Path)
    snapshot.add_argument("--text-limit", type=int, default=5000)

    commands.add_parser("text", help="full page text without editable regions; no de-duplication")

    goto = commands.add_parser("goto", help="navigate (playwright backend) and report observed console/network")
    goto.add_argument("url", type=validate_url)
    goto.add_argument("--text-limit", type=int, default=5000)

    click = commands.add_parser("click", help="click one control by role and name, automation id, or CSS selector")
    click.add_argument("--role", choices=sorted(ROLE_TO_CONTROL_TYPE))
    click.add_argument("--accessible-name")
    click.add_argument("--automation-id", help="uia backend only")
    click.add_argument("--selector", help="playwright backend only (CSS)")
    click.add_argument("--exact", action="store_true")
    click.add_argument("--wait", type=float, default=0.5)
    click.add_argument("--download-to", type=Path, help="playwright: wait for the download this click starts and save it")
    click.add_argument("--text-limit", type=int, default=5000)

    fill = commands.add_parser("fill", help="set one field's value (never echoed)")
    fill.add_argument("--value", required=True)
    fill.add_argument("--role", choices=sorted(ROLE_TO_CONTROL_TYPE))
    fill.add_argument("--accessible-name")
    fill.add_argument("--automation-id", help="uia backend only")
    fill.add_argument("--selector", help="playwright backend only (CSS)")
    fill.add_argument("--exact", action="store_true")
    fill.add_argument("--text-limit", type=int, default=5000)

    wait = commands.add_parser("wait", help="poll until the page text contains a marker")
    wait.add_argument("--text", required=True)
    wait.add_argument("--interval", type=float, default=0.5)

    evaluate = commands.add_parser("eval", help="run JavaScript in the page (playwright backend) and return JSON")
    evaluate.add_argument("--js", required=True)

    commands.add_parser("stop", help="stop only the dedicated Chrome process tree")
    return cli


def run_command(args: argparse.Namespace) -> dict[str, Any]:
    browser = HiddenBrowser(args.name, data_root=args.data_root, run_id=args.run_id, timeout=args.timeout)
    if args.command == "open":
        return browser.open(args.url, backend=args.backend, width=args.width, height=args.height)
    if args.command == "status":
        return browser.status()
    if args.command == "snapshot":
        return browser.snapshot(output=args.output, text_limit=args.text_limit)
    if args.command == "text":
        return browser.text()
    if args.command == "goto":
        return browser.goto(args.url, text_limit=args.text_limit)
    if args.command == "click":
        return browser.click(
            role=args.role,
            accessible_name=args.accessible_name,
            automation_id=args.automation_id,
            selector=args.selector,
            exact=args.exact,
            wait=args.wait,
            download_to=args.download_to,
            text_limit=args.text_limit,
        )
    if args.command == "fill":
        return browser.fill(
            args.value,
            role=args.role,
            accessible_name=args.accessible_name,
            automation_id=args.automation_id,
            selector=args.selector,
            exact=args.exact,
            text_limit=args.text_limit,
        )
    if args.command == "wait":
        return browser.wait_text(args.text, interval=args.interval)
    if args.command == "eval":
        return browser.eval_js(args.js)
    if args.command == "stop":
        return browser.stop()
    raise ValueError(f"unknown command {args.command}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args(argv)
    try:
        before_desktop = input_desktop_name()
        before_foreground = foreground_window()
        result = run_command(args)
        after_desktop = input_desktop_name()
        after_foreground = foreground_window()
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports every operational failure as JSON.
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False))
        return 1
    guard = {
        "input_desktop_before": before_desktop,
        "input_desktop_after": after_desktop,
        "input_desktop_unchanged": before_desktop == after_desktop,
        "foreground_before": before_foreground,
        "foreground_after": after_foreground,
        "foreground_unchanged": before_foreground["hwnd"] == after_foreground["hwnd"],
    }
    print(json.dumps({"ok": True, **result, **guard}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
