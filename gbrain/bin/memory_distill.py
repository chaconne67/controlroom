#!/usr/bin/env python3
"""Daily Codex-to-GBrain memory distillation.

This script intentionally does not run GBrain's `dream` cycle. It reuses the
useful distillation rubric from GBrain, then keeps the runtime small:

Codex JSONL -> dated transcript -> one LLM JSON distillation -> gbrain capture.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


HOME = Path.home()
CODEX_HOME = HOME / ".codex"
GBRAIN_HOME = HOME / ".gbrain"
GBRAIN_CLI = HOME / ".bun/bin/gbrain"
GBRAIN_WRAPPER = GBRAIN_HOME / "bin" / "gbrain_with_google_env.sh"
PROVIDER_ENV_PATH = GBRAIN_HOME / "provider.env"
REPORTS_DIR = GBRAIN_HOME / "reports"
LEDGER_PATH = REPORTS_DIR / "index.json"
TRANSCRIPT_DIR = GBRAIN_HOME / "transcripts" / "codex"
DISTILLED_PAGES_DIR = REPORTS_DIR / "distilled-pages"
OPENROUTER_MODEL = "google/gemini-3-flash-preview"
KST = dt.timezone(dt.timedelta(hours=9), "Asia/Seoul")

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+"),
]
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*$")


def local_date_from_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(KST).date().isoformat()


def default_target_date() -> str:
    return (dt.datetime.now(KST).date() - dt.timedelta(days=1)).isoformat()


def today() -> str:
    return dt.datetime.now(KST).date().isoformat()


def now_iso() -> str:
    return dt.datetime.now(KST).isoformat(timespec="seconds")


def load_provider_env_value(target_key: str) -> str:
    if not PROVIDER_ENV_PATH.exists():
        return ""
    try:
        lines = PROVIDER_ENV_PATH.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
    except OSError:
        return ""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == target_key:
            return value.strip().strip('"').strip("'")
    return ""


def run_env() -> dict[str, str]:
    env = dict(os.environ)
    gemini_key = load_provider_env_value("GEMINI_API_KEY") or env.get("GEMINI_API_KEY", "")
    openrouter_key = load_provider_env_value("OPENROUTER_API_KEY") or env.get("OPENROUTER_API_KEY", "")
    if gemini_key and not env.get("GOOGLE_GENERATIVE_AI_API_KEY"):
        env["GOOGLE_GENERATIVE_AI_API_KEY"] = gemini_key
    if openrouter_key:
        env["OPENROUTER_API_KEY"] = openrouter_key
    env["PATH"] = f"{HOME}/.bun/bin:" + env.get("PATH", "")
    for key in ["DATABASE_URL", "OPENAI_API_KEY"]:
        env.pop(key, None)
    return env


def redact(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def iter_codex_jsonl_files() -> list[Path]:
    candidates: list[Path] = []
    for root in [CODEX_HOME / "archived_sessions", CODEX_HOME / "sessions"]:
        if root.exists():
            candidates.extend(root.rglob("*.jsonl"))
    history = CODEX_HOME / "history.jsonl"
    if history.exists():
        candidates.append(history)
    return sorted(set(candidates))


def extract_user_messages(target_date: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for path in iter_codex_jsonl_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if local_date_from_timestamp(obj.get("timestamp")) != target_date:
                continue
            payload = obj.get("payload") or {}
            text = None
            if obj.get("type") == "event_msg" and payload.get("type") == "user_message":
                text = payload.get("message")
            if not text or text.startswith("# AGENTS.md instructions"):
                continue
            messages.append(
                {
                    "timestamp": obj.get("timestamp"),
                    "path": str(path),
                    "line": line_no,
                    "text": redact(text).strip(),
                }
            )
    return messages


def transcript_path_for(target_date: str, messages: list[dict[str, Any]]) -> Path:
    digest = hashlib.sha1(
        "\n".join(f"{m['timestamp']} {m['path']}:{m['line']}" for m in messages).encode("utf-8")
    ).hexdigest()[:8]
    return TRANSCRIPT_DIR / f"{target_date}-codex-session-{digest}.txt"


def render_transcript(target_date: str, messages: list[dict[str, Any]]) -> str:
    lines = [
        "Codex session transcript for memory distillation",
        f"Date: {target_date} Asia/Seoul",
        "",
        "Purpose:",
        "- Distill durable agent-evolution lessons, work rules, project rationale, user feedback, and repeated-correction patterns.",
        "- Keep routine one-off operations out of long-term memory.",
        "- Do not preserve secrets or raw transcript details that are not reusable.",
        "",
    ]
    for i, msg in enumerate(messages, start=1):
        lines.extend(
            [
                f"## User message {i}",
                f"Timestamp: {msg['timestamp']}",
                f"Source: {msg['path']}:{msg['line']}",
                "",
                msg["text"],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_transcript(target_date: str) -> tuple[Path | None, int]:
    messages = extract_user_messages(target_date)
    if not messages:
        return None, 0
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    for old_path in TRANSCRIPT_DIR.glob(f"{target_date}-codex-session-*.txt"):
        old_path.unlink()
    path = transcript_path_for(target_date, messages)
    path.write_text(render_transcript(target_date, messages), encoding="utf-8")
    return path, len(messages)


def gbrain_available() -> bool:
    return GBRAIN_WRAPPER.exists()


def run_gbrain(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(GBRAIN_WRAPPER), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        cwd=str(HOME),
        env=run_env(),
    )


def load_ledger() -> dict[str, Any]:
    if not LEDGER_PATH.exists():
        return {"reports": {}}
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"reports": {}}


def save_ledger(ledger: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    temp = LEDGER_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(LEDGER_PATH)


def compact_multiline(text: str, limit: int = 500) -> str:
    one_line = re.sub(r"\s+", " ", text or "").strip()
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1].rstrip() + "..."


def slugify(value: str) -> str:
    lower = value.lower()
    lower = re.sub(r"[^a-z0-9가-힣/ -]+", "", lower)
    lower = re.sub(r"[가-힣]+", "", lower)
    lower = re.sub(r"[\s_]+", "-", lower)
    lower = re.sub(r"-+", "-", lower).strip("-/")
    return lower or "memory"


def normalize_slug(raw_slug: Any, title: str, fallback_prefix: str = "reference") -> str:
    slug = str(raw_slug or "").strip().lower()
    slug = slug.replace("_", "-").strip("/")
    slug = re.sub(r"[^a-z0-9/-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = re.sub(r"/+", "/", slug).strip("-/")
    if SLUG_RE.match(slug):
        return slug
    title_part = slugify(title)[:80].strip("-") or "distilled-memory"
    return f"{fallback_prefix}/{title_part}"


def page_type_for_slug(slug: str) -> str:
    if slug.startswith("project/"):
        return "project"
    if slug.startswith("reference/"):
        return "reference"
    if slug.startswith("feedback/"):
        return "concept"
    if slug.startswith("report/"):
        return "report"
    return "concept"


def build_distillation_prompt(target_date: str, transcript: str) -> list[dict[str, str]]:
    system = """You distill Codex conversation logs into durable GBrain memory.

Use this rubric.

Worth storing:
- new project/domain rules, feature behavior, model/status/field rationale
- user feedback that should change future agent behavior
- root-cause debugging lessons and verification order
- strategic decisions, rejected alternatives, durable implementation direction
- repeated correction patterns that prevent the user from explaining again

Usually skip:
- routine commands, short acknowledgements, simple status checks
- one-off code debugging with no reusable lesson
- raw transcript details, secrets, screenshots/attachment boilerplate
- content already captured unless the new message corrects or sharpens it

Memory shape:
- Store by domain or feature, not by chat transcript.
- Prefer slugs under project/, reference/, or feedback/.
- Keep memories directly actionable for future agents.
- Quote the user's wording only when it matters, and keep quotes short.
- Do not invent decisions that were not in the transcript.

Return JSON only with this schema:
{
  "summary": "short summary",
  "candidates": [
    {
      "decision": "store|needs_review|skip",
      "title": "short page title",
      "slug": "project/... or reference/... or feedback/...",
      "kind": "work_rule|project_context|design_decision|debug_lesson|operator_preference|pattern|other",
      "reason": "why this decision",
      "memory": "markdown body for the durable memory, empty for skip",
      "evidence": ["short source quote or source pointer"],
      "confidence": "high|medium|low"
    }
  ]
}

Limit store candidates to the highest-value 12 items."""
    user = f"Target local date: {target_date}\n\nTranscript:\n\n{transcript}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def openrouter_chat(messages: list[dict[str, str]], model: str, timeout: int = 900) -> str:
    api_key = load_provider_env_value("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not available")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 12000,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "gbrain_memory_distillation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "decision": {"type": "string", "enum": ["store", "needs_review", "skip"]},
                                    "title": {"type": "string"},
                                    "slug": {"type": "string"},
                                    "kind": {"type": "string"},
                                    "reason": {"type": "string"},
                                    "memory": {"type": "string"},
                                    "evidence": {"type": "array", "items": {"type": "string"}},
                                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                                },
                                "required": ["decision", "title", "slug", "kind", "reason", "memory", "evidence", "confidence"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["summary", "candidates"],
                    "additionalProperties": False,
                },
            },
        },
        "provider": {"require_parameters": True},
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost/gbrain-memory-distill",
            "X-Title": "GBrain Memory Distillation",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {compact_multiline(body)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenRouter request failed: {exc.reason}") from exc
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter response had no choices")
    content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        raise RuntimeError("OpenRouter response content was empty")
    return content


def parse_json_payload(output: str) -> Any:
    text = output.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(text[start : end + 1])


def normalize_distillation(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("LLM JSON root must be an object")
    candidates_in = raw.get("candidates")
    if not isinstance(candidates_in, list):
        raise ValueError("LLM JSON must contain candidates[]")
    candidates: list[dict[str, Any]] = []
    for item in candidates_in:
        if not isinstance(item, dict):
            continue
        decision = str(item.get("decision") or "needs_review").strip().lower()
        if decision not in {"store", "needs_review", "skip"}:
            decision = "needs_review"
        title = str(item.get("title") or "Distilled Memory").strip()
        slug = normalize_slug(item.get("slug"), title)
        memory = str(item.get("memory") or "").strip()
        if decision == "store" and not memory:
            decision = "needs_review"
        evidence = item.get("evidence") if isinstance(item.get("evidence"), list) else []
        candidates.append(
            {
                "decision": decision,
                "title": title,
                "slug": slug,
                "kind": str(item.get("kind") or "other").strip(),
                "reason": str(item.get("reason") or "").strip(),
                "memory": memory,
                "evidence": [str(e).strip() for e in evidence if str(e).strip()][:5],
                "confidence": str(item.get("confidence") or "medium").strip().lower(),
            }
        )
    return {"summary": str(raw.get("summary") or "").strip(), "candidates": candidates}


def render_memory_page(candidate: dict[str, Any], target_date: str) -> str:
    tags = ["gbrain", "memory-distillation", candidate["kind"] or "distilled"]
    lines = [
        "---",
        f"type: {page_type_for_slug(candidate['slug'])}",
        f"title: {json.dumps(candidate['title'], ensure_ascii=False)}",
        f"created: '{now_iso()}'",
        "page_type: project",
        f"distilled_from: codex-jsonl-{target_date}",
        "tags:",
        *(f"  - {slugify(tag)}" for tag in tags),
        "---",
        "",
        f"# {candidate['title']}",
        "",
        candidate["memory"].strip(),
        "",
        "## Distillation Metadata",
        "",
        f"- Source date: {target_date}",
        f"- Kind: {candidate['kind']}",
        f"- Confidence: {candidate['confidence']}",
        f"- Reason: {candidate['reason'] or 'n/a'}",
    ]
    if candidate["evidence"]:
        lines.extend(["", "## Evidence", ""])
        lines.extend(f"- {e}" for e in candidate["evidence"])
    return "\n".join(lines).rstrip() + "\n"


def capture_page(slug: str, markdown: str) -> tuple[bool, str]:
    if not gbrain_available():
        return False, "gbrain CLI unavailable"
    DISTILLED_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    path = DISTILLED_PAGES_DIR / f"{slug.replace('/', '__')}.md"
    path.write_text(markdown, encoding="utf-8")
    proc = run_gbrain(["capture", "--file", str(path), "--slug", slug, "--type", page_type_for_slug(slug), "--quiet"], timeout=120)
    if proc.returncode != 0:
        return False, compact_multiline(proc.stderr or proc.stdout)
    return True, str(path)


def write_gbrain_report(slug: str, report_path: Path) -> None:
    if not gbrain_available():
        return
    subprocess.run(
        [str(GBRAIN_WRAPPER), "capture", "--file", str(report_path), "--slug", slug, "--type", "report", "--quiet"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        cwd=str(HOME),
        env=run_env(),
    )


def render_report(
    target_date: str,
    transcript: Path | None,
    message_count: int,
    model: str,
    result: dict[str, Any],
    applied: list[dict[str, str]],
    blockers: list[str],
) -> str:
    candidates = result.get("candidates") or []
    counts = {
        "store": sum(1 for c in candidates if c.get("decision") == "store"),
        "needs_review": sum(1 for c in candidates if c.get("decision") == "needs_review"),
        "skip": sum(1 for c in candidates if c.get("decision") == "skip"),
    }
    lines = [
        "---",
        "type: report",
        f"title: GBrain Memory Distillation {target_date}",
        f"created: '{now_iso()}'",
        "page_type: report",
        "tags:",
        "  - gbrain",
        "  - memory-distillation",
        "  - review-required",
        "---",
        "",
        f"# GBrain Memory Distillation Report - {target_date}",
        "",
        "This report uses the lightweight Codex JSONL distillation pipeline.",
        "It does not run `gbrain dream`, Minions, subagents, workers, or autopilot.",
        "",
        "## Inputs",
        "",
        f"- Transcript file: `{transcript}`" if transcript else "- Transcript file: none",
        f"- User messages extracted: {message_count}",
        f"- Model: `{model}`",
        "",
        "## Result",
        "",
        f"- Store recommended: {counts['store']}",
        f"- Needs judgment: {counts['needs_review']}",
        f"- Skip recommended: {counts['skip']}",
        f"- Memories applied: {len(applied)}",
        f"- Blockers: {len(blockers)}",
    ]
    if result.get("summary"):
        lines.extend(["", "## Summary", "", result["summary"]])
    if blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {b}" for b in blockers)
    if applied:
        lines.extend(["", "## Applied Memories", ""])
        lines.extend(f"- `{item['slug']}` -> `{item['path']}`" for item in applied)
    if candidates:
        lines.extend(["", "## Candidates", ""])
        for candidate in candidates:
            lines.extend(
                [
                    f"### {candidate.get('title') or candidate.get('slug')}",
                    "",
                    f"- Decision: `{candidate.get('decision')}`",
                    f"- Slug: `{candidate.get('slug')}`",
                    f"- Kind: `{candidate.get('kind')}`",
                    f"- Confidence: `{candidate.get('confidence')}`",
                    f"- Reason: {candidate.get('reason') or 'n/a'}",
                ]
            )
            if candidate.get("evidence"):
                lines.append(f"- Evidence: {' / '.join(candidate['evidence'])}")
            if candidate.get("memory") and candidate.get("decision") != "skip":
                lines.extend(["", candidate["memory"][:2500].rstrip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def generate(args: argparse.Namespace) -> int:
    target_date = args.date or default_target_date()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    transcript_path, message_count = write_transcript(target_date)
    blockers: list[str] = []
    applied: list[dict[str, str]] = []
    result: dict[str, Any] = {"summary": "", "candidates": []}

    if transcript_path is None:
        result["summary"] = "No Codex user messages for date."
    else:
        try:
            transcript = transcript_path.read_text(encoding="utf-8", errors="replace")
            messages = build_distillation_prompt(target_date, transcript)
            raw = openrouter_chat(messages, args.model)
            result = normalize_distillation(parse_json_payload(raw))
        except Exception as exc:
            blockers.append(str(exc))

    if not blockers and not args.no_apply:
        for candidate in result.get("candidates") or []:
            if candidate.get("decision") != "store":
                continue
            ok, detail = capture_page(candidate["slug"], render_memory_page(candidate, target_date))
            if ok:
                applied.append({"slug": candidate["slug"], "path": detail})
            else:
                blockers.append(f"{candidate['slug']}: {detail}")

    report_path = REPORTS_DIR / f"{target_date}-memory-distillation.md"
    report_slug = f"report/gbrain-distillation-{target_date}"
    report_path.write_text(
        render_report(target_date, transcript_path, message_count, args.model, result, applied, blockers),
        encoding="utf-8",
    )
    if not args.no_gbrain:
        write_gbrain_report(report_slug, report_path)

    candidates = result.get("candidates") or []
    summary = {
        "mode": "simple-llm-capture",
        "model": args.model,
        "messages_extracted": message_count,
        "transcript_path": str(transcript_path) if transcript_path else None,
        "store_recommended": sum(1 for c in candidates if c.get("decision") == "store"),
        "needs_review": sum(1 for c in candidates if c.get("decision") == "needs_review"),
        "skip_recommended": sum(1 for c in candidates if c.get("decision") == "skip"),
        "memories_applied": len(applied),
        "applied_slugs": [item["slug"] for item in applied],
        "blockers": blockers,
    }
    ledger = load_ledger()
    existing = ledger.setdefault("reports", {}).get(target_date, {})
    status = existing.get("status")
    if message_count == 0:
        status = "skipped"
    elif status not in {"reviewed", "applied", "skipped"}:
        status = "unchecked"
    ledger["reports"][target_date] = {
        **existing,
        "report_path": str(report_path),
        "gbrain_slug": report_slug,
        "generated_at": now_iso(),
        "status": status,
        "reviewed_at": existing.get("reviewed_at"),
        "review_decision": existing.get("review_decision"),
        "last_prompted_date": existing.get("last_prompted_date"),
        "summary": summary,
    }
    save_ledger(ledger)
    print(json.dumps({"date": target_date, "report_path": str(report_path), "summary": summary}, ensure_ascii=False))
    return 2 if blockers else 0


def pending_reports(ledger: dict[str, Any], today_value: str) -> list[tuple[str, dict[str, Any]]]:
    reports = ledger.get("reports", {})
    return sorted(
        (date, data)
        for date, data in reports.items()
        if date < today_value and data.get("status") == "unchecked"
    )


def check_pending(args: argparse.Namespace) -> int:
    today_value = args.today or today()
    ledger = load_ledger()
    pending = pending_reports(ledger, today_value)
    if not pending:
        print(json.dumps({"pending": False, "message": "No unchecked memory distillation reports."}, ensure_ascii=False))
        return 0
    date, data = pending[0]
    already_prompted = data.get("last_prompted_date") == today_value
    message = (
        f"{date} GBrain memory distillation 리포트가 미확인 상태입니다. "
        f"리포트: {data.get('report_path')}. 지금 리뷰할까요?"
    )
    if already_prompted:
        print(json.dumps({"pending": True, "prompt": False, "date": date, "message": "Already prompted today."}, ensure_ascii=False))
        return 0
    if not args.dry_run:
        data["last_prompted_date"] = today_value
        ledger["reports"][date] = data
        save_ledger(ledger)
    print(json.dumps({"pending": True, "prompt": True, "date": date, "message": message}, ensure_ascii=False))
    return 0


def mark(args: argparse.Namespace) -> int:
    ledger = load_ledger()
    report = ledger.setdefault("reports", {}).get(args.date)
    if not report:
        print(f"No report for {args.date}", file=sys.stderr)
        return 1
    report["status"] = args.status
    if args.status in {"reviewed", "applied", "skipped"}:
        report["reviewed_at"] = now_iso()
    if args.decision:
        report["review_decision"] = args.decision
    ledger["reports"][args.date] = report
    save_ledger(ledger)
    print(json.dumps({"date": args.date, "status": args.status}, ensure_ascii=False))
    return 0


def list_reports(_: argparse.Namespace) -> int:
    print(json.dumps(load_ledger(), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight GBrain memory distillation")
    sub = parser.add_subparsers(dest="command", required=True)

    generate_parser = sub.add_parser("generate", help="Generate a daily memory distillation report")
    generate_parser.add_argument("--date", help="Target local date YYYY-MM-DD. Defaults to yesterday.")
    generate_parser.add_argument("--model", default=OPENROUTER_MODEL, help="OpenRouter model id.")
    generate_parser.add_argument("--no-gbrain", action="store_true", help="Do not write the report into GBrain.")
    generate_parser.add_argument("--no-apply", action="store_true", help="Do not apply store candidates to GBrain.")
    generate_parser.add_argument("--review-only", action="store_true", dest="no_apply", help=argparse.SUPPRESS)
    generate_parser.add_argument("--no-dream", action="store_true", help=argparse.SUPPRESS)
    generate_parser.add_argument("--dream-dry-run", action="store_true", dest="no_apply", help=argparse.SUPPRESS)
    generate_parser.set_defaults(func=generate)

    check_parser = sub.add_parser("check-pending", help="Check unchecked reports and prompt at most once per day")
    check_parser.add_argument("--today", help="Override local today YYYY-MM-DD, for tests.")
    check_parser.add_argument("--dry-run", action="store_true", help="Do not update last_prompted_date.")
    check_parser.set_defaults(func=check_pending)

    mark_parser = sub.add_parser("mark", help="Mark a report status")
    mark_parser.add_argument("date")
    mark_parser.add_argument("--status", required=True, choices=["unchecked", "reviewed", "applied", "skipped"])
    mark_parser.add_argument("--decision", help="Optional review decision note")
    mark_parser.set_defaults(func=mark)

    list_parser = sub.add_parser("list", help="Print the ledger")
    list_parser.set_defaults(func=list_reports)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
