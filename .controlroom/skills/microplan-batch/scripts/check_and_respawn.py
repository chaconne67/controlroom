#!/usr/bin/env python3
"""Periodic microplan-batch monitor.

Run this from cron/systemd timer. It checks one batch directory once, respawns
the background Codex session if needed, and exits.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SANDBOX_ERROR = re.compile(
    r"bwrap: loopback|Failed RTM_NEWADDR|Operation not permitted",
    re.IGNORECASE,
)
MIN_AVAILABLE_MIB = int(os.environ.get("MICROPLAN_MIN_AVAILABLE_MB", "512"))
MIN_HEADROOM_MIB = int(os.environ.get("MICROPLAN_MIN_HEADROOM_MB", "1200"))
CRITICAL_HEADROOM_MIB = int(os.environ.get("MICROPLAN_CRITICAL_HEADROOM_MB", "512"))


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def is_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def memory_mib() -> tuple[int, int, int]:
    mem_available = 0
    swap_free = 0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            amount = int(value.strip().split()[0]) // 1024
            if key == "MemAvailable":
                mem_available = amount
            elif key == "SwapFree":
                swap_free = amount
    except (FileNotFoundError, ValueError, IndexError):
        return (0, 0, 0)
    return (mem_available, swap_free, mem_available + swap_free)


def memory_summary() -> str:
    available, swap_free, headroom = memory_mib()
    return f"mem_available_mib={available} swap_free_mib={swap_free} headroom_mib={headroom}"


def has_launch_headroom() -> bool:
    available, _swap_free, headroom = memory_mib()
    return available >= MIN_AVAILABLE_MIB and headroom >= MIN_HEADROOM_MIB


def is_critically_low_memory() -> bool:
    _available, _swap_free, headroom = memory_mib()
    return headroom and headroom < CRITICAL_HEADROOM_MIB


def terminate_session(pid: int | None) -> None:
    if not pid:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return


def read_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, text=True)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def log(plan_dir: Path, message: str) -> None:
    log_path = plan_dir / "logs" / "monitor.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(f"{now()} {message}\n")


def contains_sandbox_error(path: Path) -> bool:
    try:
        for line in path.read_text(errors="ignore").splitlines():
            if "SKILL.md" in line:
                continue
            if SANDBOX_ERROR.search(line):
                return True
        return False
    except FileNotFoundError:
        return False


def launch_session(plan_dir: Path, repo_dir: Path, flags: str) -> int:
    logs = plan_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    session_log = (logs / "session.log").open("wb")
    prompt = (plan_dir / "session-prompt.txt").open("rb")
    cmd = [
        "codex",
        "exec",
        "--cd",
        str(repo_dir),
        *flags.split(),
        "--json",
        "--output-last-message",
        str(logs / "last-message.txt"),
        "-",
    ]
    proc = subprocess.Popen(
        cmd,
        stdin=prompt,
        stdout=session_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    prompt.close()
    session_log.close()
    return proc.pid


def tail_text(path: Path, max_chars: int = 6000) -> str:
    try:
        text = path.read_text(errors="ignore")
    except FileNotFoundError:
        return ""
    return text[-max_chars:]


def git_summary(repo_dir: Path) -> str:
    result = subprocess.run(
        ["git", "log", "--oneline", "-3"],
        cwd=repo_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip()


def task_commit(task: dict) -> str:
    return task.get("task_commit") or task.get("merge_commit") or ""


def progress_signature(data: dict) -> str:
    tasks = data.get("tasks") or []
    reported = []
    for task in tasks:
        status = task.get("status")
        if status in {"completed", "failed", "skipped", "blocked"}:
            reported.append(
                {
                    "slug": task.get("slug"),
                    "status": status,
                    "task_commit": task_commit(task),
                    "reason": task.get("reason"),
                }
            )
    return json.dumps(
        {
            "batch_status": data.get("batch_status"),
            "reported_tasks": reported,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def has_reportable_change(data: dict) -> bool:
    if data.get("batch_status") in {
        "complete",
        "complete_with_failures",
        "failed",
        "blocked",
    }:
        return True
    tasks = data.get("tasks") or []
    return any(
        task.get("status") in {"completed", "failed", "skipped", "blocked"}
        for task in tasks
    )


def notification_state(data: dict) -> dict:
    notifications = data.get("notifications")
    if not isinstance(notifications, dict):
        notifications = {}
    data["notifications"] = notifications
    return notifications


def update_notification_state(progress: Path, updates: dict) -> dict:
    data = read_json(progress)
    notifications = notification_state(data)
    notifications.update(updates)
    write_json(progress, data)
    return data


def send_telegram(plan_dir: Path, subject: str, body: str) -> None:
    helper = Path.home() / ".codex" / "mcp" / "telegram" / "lib" / "telegram.sh"
    if not helper.exists():
        return
    command = (
        f"source {str(helper)!r}; "
        "notify_telegram \"$1\" \"$2\" \"$3\" SUPERUSER"
    )
    subprocess.run(
        ["bash", "-lc", command, "bash", str(plan_dir), subject, body],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def fallback_report(data: dict, event: str) -> str:
    tasks = data.get("tasks") or []
    total = len(tasks)
    completed = [task for task in tasks if task.get("status") == "completed"]
    failed = [task for task in tasks if task.get("status") == "failed"]
    skipped = [task for task in tasks if task.get("status") == "skipped"]
    blocked = [task for task in tasks if task.get("status") == "blocked"]
    running = [task for task in tasks if task.get("status") == "running"]
    pending = [task for task in tasks if task.get("status") == "pending"]
    current = (running or pending or [{}])[0].get("slug") or "-"
    last_commit = ""
    for task in tasks:
        commit = task_commit(task)
        if commit:
            last_commit = commit
    lines = [
        "microplan-batch 진행 보고",
        f"이벤트: {event}",
        f"상태: {data.get('batch_status')}",
        f"현재: {current}",
        f"완료: {len(completed)}/{total}",
        f"실패: {len(failed)} / 스킵: {len(skipped)} / 대기: {len(blocked)}",
    ]
    if last_commit:
        lines.append(f"마지막 커밋: {last_commit}")
    if failed:
        lines.append(f"문제: {failed[-1].get('slug')}")
    if blocked:
        lines.append(f"대기: {blocked[-1].get('slug')}")
    return "\n".join(lines)


def agent_report(plan_dir: Path, repo_dir: Path, data: dict, event: str) -> str:
    logs = plan_dir / "logs"
    report_progress = dict(data)
    if event not in {"failed", "blocked", "complete", "complete_with_failures"}:
        reason = str(report_progress.get("reason") or "")
        if "sandbox" in reason or "bwrap" in reason or "full-auto" in reason:
            report_progress.pop("reason", None)
    payload = {
        "event": event,
        "progress": report_progress,
        "recent_git_log": git_summary(repo_dir),
        "last_message_tail": tail_text(logs / "last-message.txt", 3000),
        "session_log_tail": tail_text(logs / "session.log", 3000),
        "monitor_log_tail": "\n".join(
            tail_text(logs / "monitor.log", 3000).splitlines()[-8:]
        ),
    }
    prompt = (
        "다음 microplan-batch 진행 데이터를 텔레그램으로 받을 짧은 한국어 진행 보고로 정리하라.\n"
        "지시:\n"
        "- 10줄 이하.\n"
        "- 원시 JSON이나 긴 로그를 붙이지 말라.\n"
        "- 현재 상태, 완료 수, 문제 여부, 마지막 커밋, 다음 동작만 적어라.\n"
        "- monitor_log_tail의 최신 3줄에 sandbox fallback detected가 없으면 sandbox fallback을 언급하지 말라.\n"
        "- event가 respawn이어도 previous_pid가 비어 있으면 정상적인 다음 작업 세션 시작으로 설명하라.\n"
        "- 사유 설명이나 일반론을 쓰지 말라.\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n"
    )
    result = subprocess.run(
        [
            "codex",
            "exec",
            "--cd",
            str(repo_dir),
            "--dangerously-bypass-approvals-and-sandbox",
            "-",
        ],
        input=prompt,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    text = result.stdout.strip()
    if result.returncode != 0 or not text:
        return fallback_report(data, event)
    return text[-3500:]


def maybe_notify_progress(
    plan_dir: Path,
    repo_dir: Path,
    progress: Path,
    data: dict,
    event: str = "progress",
    force: bool = False,
) -> None:
    notifications = notification_state(data)
    signature = progress_signature(data)
    previous = notifications.get("telegram:progress_signature")
    if not force and signature == previous:
        return
    if not force and not has_reportable_change(data):
        return
    subject = f"microplan-batch {event.upper()}"
    body = agent_report(plan_dir, repo_dir, data, event)
    send_telegram(plan_dir, subject, body)
    update_notification_state(
        progress,
        {
            "telegram:progress_signature": signature,
            "telegram:progress_at": now(),
            "telegram:progress_event": event,
        },
    )
    log(plan_dir, f"telegram_progress event={event}")


def notification_already_sent(data: dict, status: str) -> bool:
    notifications = notification_state(data)
    return bool(notifications.get(f"telegram:{status}"))


def mark_notification_sent(progress: Path, data: dict, status: str) -> None:
    update_notification_state(progress, {f"telegram:{status}": now()})


def terminal_body(data: dict, status: str) -> str:
    tasks = data.get("tasks") or []
    total = len(tasks)
    completed = sum(1 for task in tasks if task.get("status") == "completed")
    failed = sum(1 for task in tasks if task.get("status") == "failed")
    skipped = sum(1 for task in tasks if task.get("status") == "skipped")
    blocked = sum(1 for task in tasks if task.get("status") == "blocked")
    last_commit = ""
    for task in tasks:
        commit = task_commit(task)
        if commit:
            last_commit = commit
    return "\n".join(
        [
            f"directory: {data.get('plan_dir') or ''}",
            f"성공: {completed}/{total}",
            f"실패: {failed}",
            f"스킵: {skipped}",
            f"대기: {blocked}",
            f"마지막 커밋: {last_commit}",
            f"상태: {status}",
        ]
    )


def notify_terminal_status(plan_dir: Path, progress: Path, data: dict, status: str) -> None:
    if notification_already_sent(data, status):
        return
    subjects = {
        "complete": "microplan-batch COMPLETE",
        "complete_with_failures": "microplan-batch COMPLETE_WITH_FAILURES",
        "failed": "microplan-batch FAILED",
        "blocked": "microplan-batch BLOCKED",
    }
    subject = subjects.get(status, f"microplan-batch {status.upper()}")
    send_telegram(plan_dir, subject, terminal_body(data, status))
    mark_notification_sent(progress, data, status)
    log(plan_dir, f"telegram_notified status={status}")


def remove_cron_entry(cron_tag: str | None, plan_dir: Path) -> None:
    if not cron_tag:
        return
    current = subprocess.run(
        ["crontab", "-l"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if current.returncode != 0:
        return
    kept = [line for line in current.stdout.splitlines() if cron_tag not in line]
    if len(kept) == len(current.stdout.splitlines()):
        return
    new_cron = "\n".join(kept)
    if new_cron:
        new_cron += "\n"
    subprocess.run(
        ["crontab", "-"],
        input=new_cron,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    log(plan_dir, f"removed_cron tag={cron_tag}")


def check_once(plan_dir: Path, repo_dir: Path, cron_tag: str | None) -> int:
    progress = plan_dir / "microplan-progress.json"
    if not progress.exists():
        log(plan_dir, "skip progress_missing")
        return 0

    data = read_json(progress)
    status = data.get("batch_status", "missing")
    if status != "running":
        log(plan_dir, f"skip status={status}")
        if status in {"complete", "complete_with_failures", "failed", "blocked"}:
            if not notification_already_sent(data, status):
                maybe_notify_progress(
                    plan_dir,
                    repo_dir,
                    progress,
                    data,
                    event=status,
                    force=True,
                )
                data = read_json(progress)
                mark_notification_sent(progress, data, status)
                log(plan_dir, f"telegram_notified status={status}")
        remove_cron_entry(cron_tag, plan_dir)
        return 0

    logs = plan_dir / "logs"
    pid = data.get("last_pid")
    flags = data.get("codex_exec_flags") or (
        "--dangerously-bypass-approvals-and-sandbox"
    )

    if is_alive(pid):
        if is_critically_low_memory():
            log(plan_dir, f"critical_memory pid={pid} {memory_summary()}")
            terminate_session(pid)
            data["batch_status"] = "blocked"
            data["last_pid"] = None
            data["reason"] = (
                "microplan-batch monitor stopped the background session because "
                f"memory headroom dropped below {CRITICAL_HEADROOM_MIB}MiB. "
                "Review the worktree and resume manually when the server has enough memory."
            )
            write_json(progress, data)
            maybe_notify_progress(
                plan_dir,
                repo_dir,
                progress,
                data,
                event="blocked",
                force=True,
            )
            remove_cron_entry(cron_tag, plan_dir)
            return 0
        log(plan_dir, f"alive pid={pid} {memory_summary()}")
        maybe_notify_progress(plan_dir, repo_dir, progress, data)
        return 0

    if "--full-auto" in flags and (
        contains_sandbox_error(logs / "session.log")
        or contains_sandbox_error(logs / "last-message.txt")
    ):
        log(plan_dir, "sandbox fallback detected")
        if is_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        data["codex_exec_flags"] = "--dangerously-bypass-approvals-and-sandbox"
        flags = data["codex_exec_flags"]
        data["reason"] = (
            "codex exec --full-auto failed before local commands with "
            "bwrap/loopback sandbox setup error; periodic monitor switched this "
            "batch to --dangerously-bypass-approvals-and-sandbox."
        )
        write_json(progress, data)
        (logs / "session.log").write_text("")
        (logs / "last-message.txt").write_text("")
        pid = None

    if not has_launch_headroom():
        log(plan_dir, f"skip low_memory_no_respawn {memory_summary()}")
        return 0
    new_pid = launch_session(plan_dir, repo_dir, flags)
    data = read_json(progress)
    data["last_pid"] = new_pid
    write_json(progress, data)
    if pid:
        event = "respawn"
        log(plan_dir, f"respawn previous_pid={pid} new_pid={new_pid}")
        force_notify = True
    else:
        event = "progress"
        log(plan_dir, f"continue new_pid={new_pid}")
        force_notify = False
    maybe_notify_progress(
        plan_dir,
        repo_dir,
        progress,
        data,
        event=event,
        force=force_notify,
    )
    print(new_pid)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-dir", required=True)
    parser.add_argument("--repo-dir", required=True)
    parser.add_argument("--cron-tag")
    args = parser.parse_args()
    return check_once(
        Path(args.plan_dir).resolve(),
        Path(args.repo_dir).resolve(),
        args.cron_tag,
    )


if __name__ == "__main__":
    raise SystemExit(main())
