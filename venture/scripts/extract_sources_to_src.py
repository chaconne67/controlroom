from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import fitz

from documents import DocumentReadError, SUPPORTED_SUFFIXES, extract_text


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}


class TextOnlyHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            text = data.strip()
            if text:
                self.chunks.append(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract README source paths into src.")
    parser.add_argument("company", help="회사명")
    parser.add_argument(
        "--project-root",
        default=None,
        help="venture 프로젝트 루트. 미지정 시 스크립트 위치에서 .git/companies가 있는 루트를 자동 탐지",
    )
    return parser.parse_args()


def find_project_root(start: Path) -> Path:
    """스크립트 위치에서 위로 올라가며 .git 또는 기존 companies/가 있는 프로젝트 루트를 찾는다."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "companies").is_dir():
            return parent
    return start


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    assert_no_korean_corruption(text, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def assert_no_korean_corruption(text: str, path: Path) -> None:
    if re.search(r"\?{2,}", text) or "\ufffd" in text:
        raise SystemExit(f"Korean text corruption guard failed before writing: {path}")


def md_unescape(value: str) -> str:
    return value.strip().replace("\\|", "|").replace("\\\\", "\\")


def md_escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def parse_homepage_url(readme: str) -> str:
    match = re.search(r"^\s*-\s*homepage_url:\s*(.+?)\s*$", readme, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_sources(readme: str) -> list[tuple[str, Path]]:
    sources: list[tuple[str, Path]] = []
    in_section = False
    for line in readme.splitlines():
        if line.strip() == "## 원본 자료":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"source_id", "---"}:
            continue
        source_id, raw_path, status = cells[:3]
        if not source_id or not raw_path or status == "missing":
            continue
        sources.append((source_id, Path(md_unescape(raw_path))))
    return sources


def parse_raw_sources(raw_dir: Path) -> list[tuple[str, Path]]:
    sources: list[tuple[str, Path]] = []
    if not raw_dir.exists():
        return sources
    for index, path in enumerate(sorted(p for p in raw_dir.iterdir() if p.is_file()), start=1):
        match = re.match(r"^(SRC-\d{3})_(.+)$", path.name)
        source_id = match.group(1) if match else f"SRC-{index:03d}"
        sources.append((source_id, path))
    return sources


def safe_name(value: str) -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", value).strip()
    return value[:120] or "source"


def raw_target_path(raw_dir: Path, source_id: str, source_path: Path) -> Path:
    source_name = source_path.name
    prefix = f"{source_id}_"
    if source_name.startswith(prefix):
        return raw_dir / safe_name(source_name)
    return raw_dir / f"{safe_name(source_id)}_{safe_name(source_name)}"


def extracted_target_path(src_dir: Path, source_id: str, source_path: Path) -> Path:
    stem = source_path.stem
    prefix = f"{source_id}_"
    if stem.startswith(prefix):
        stem = stem[len(prefix):]
    return src_dir / f"{safe_name(source_id)}_{safe_name(stem)}.md"


def capture_dir(raw_dir: Path, source_id: str, source_path: Path) -> Path:
    return raw_dir / f"{safe_name(source_id)}_{safe_name(source_path.stem)}_captures"


def source_markdown(
    *,
    source_id: str,
    source_path: Path,
    status: str,
    method: str,
    text: str,
    raw_path: Path | None = None,
    capture_paths: list[Path] | None = None,
    note: str = "",
) -> str:
    raw_line = f"- raw_path: {md_escape(raw_path)}\n" if raw_path else ""
    captures = capture_paths or []
    capture_lines = "".join(f"- {md_escape(path)}\n" for path in captures)
    capture_block = f"\n## 캡처\n\n{capture_lines}" if captures else ""
    return f"""# {source_id} {source_path.name}

## 메타

- source_id: {source_id}
- source_path: {md_escape(source_path)}
{raw_line.rstrip()}
- status: {status}
- extraction_method: {method}
- char_count: {len(text)}
- note: {note}
{capture_block}

## 추출 텍스트

{text}
"""


def demote_if_empty(status: str, text: str, note: str = "") -> tuple[str, str]:
    """추출 텍스트가 비면 ready로 두지 않는다.

    추출기가 예외 없이 빈 문자열을 돌려주는 경우가 있다(JS 렌더링 페이지, 텍스트
    레이어가 없는 PDF, 판독 실패). ready로 남기면 빈 산출물이 후속 phase로 그대로
    넘어가므로 failed로 떨어뜨려 눈에 보이게 한다.
    """
    if status == "ready" and not text.strip():
        reason = "추출된 텍스트가 없음(char_count=0)"
        return "failed", f"{note} / {reason}" if note else reason
    return status, note


def copy_raw_source(source_id: str, source_path: Path, raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_target_path(raw_dir, source_id, source_path)
    if source_path.exists() and source_path.resolve() != target.resolve():
        shutil.copy2(source_path, target)
    return target


def render_pdf_pages(pdf_path: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            output_path = output_dir / f"page{page_index:03d}.png"
            pixmap.save(output_path)
            paths.append(output_path)
    return paths


def resolve_codex_executable() -> str:
    env_path = os.environ.get("CODEX_EXE")
    if env_path and Path(env_path).exists():
        return env_path

    codex_bin = Path.home() / "AppData" / "Local" / "OpenAI" / "Codex" / "bin"
    candidates = sorted(
        codex_bin.glob("*/codex.exe"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return str(candidates[0])

    command = shutil.which("codex")
    if command:
        return command

    raise RuntimeError("Codex CLI 실행 파일을 찾을 수 없음")


def codex_extract_text_from_images(image_paths: list[Path], *, source_name: str) -> str:
    if not image_paths:
        return ""

    codex = resolve_codex_executable()
    prompt = (
        "첨부된 이미지는 벤처인증 원본 자료입니다. "
        "이미지에 보이는 모든 한국어/영어 텍스트를 문서 순서대로 최대한 정확히 전사하세요. "
        "설명, 요약, 추측, 마크다운 표 작성 없이 보이는 텍스트만 줄바꿈을 유지해 출력하세요. "
        f"자료명: {source_name}"
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = Path(tmp_dir) / "codex_ocr.txt"
        command = [
            codex,
            "exec",
            "--skip-git-repo-check",
            "--ignore-rules",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--output-last-message",
            str(output_file),
        ]
        for image_path in image_paths:
            command.extend(["--image", str(image_path)])
        command.append("--")
        command.append(prompt)

        completed = subprocess.run(
            command,
            cwd=tmp_dir,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=300,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
        if output_file.exists():
            return normalize_codex_transcription(output_file.read_text(encoding="utf-8"))
        return normalize_codex_transcription(completed.stdout)


def normalize_codex_transcription(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:text)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and (
        not lines[0].strip()
        or "전사" in lines[0]
        or lines[0].startswith("주인님")
    ):
        lines.pop(0)
    return "\n".join(lines).strip()


def extract_source_file(source_id: str, source_path: Path, src_dir: Path) -> str:
    raw_dir = src_dir / "raw"
    output_path = extracted_target_path(src_dir, source_id, source_path)
    if not source_path.exists():
        text = source_markdown(
            source_id=source_id,
            source_path=source_path,
            status="missing",
            method="source_file_not_found",
            text="",
            note="원본 파일을 찾을 수 없음",
        )
        write_text(output_path, text)
        return "missing"

    raw_path = copy_raw_source(source_id, source_path, raw_dir)
    suffix = source_path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        try:
            extracted = codex_extract_text_from_images([raw_path], source_name=source_path.name)
        except RuntimeError as exc:
            text = source_markdown(
                source_id=source_id,
                source_path=source_path,
                status="failed",
                method="image_codex_cli_text_extract_failed",
                text="",
                raw_path=raw_path,
                capture_paths=[raw_path],
                note=str(exc),
            )
            write_text(output_path, text)
            return "failed"
        status, note = demote_if_empty("ready", extracted)
        text = source_markdown(
            source_id=source_id,
            source_path=source_path,
            status=status,
            method="image_codex_cli_text_extract",
            text=extracted,
            raw_path=raw_path,
            capture_paths=[raw_path],
            note=note,
        )
        write_text(output_path, text)
        return status

    if suffix not in SUPPORTED_SUFFIXES:
        text = source_markdown(
            source_id=source_id,
            source_path=source_path,
            status="unsupported",
            method="unsupported_format",
            text="",
            raw_path=raw_path,
            note=f"지원하지 않는 원본 형식: {suffix or '(확장자 없음)'}",
        )
        write_text(output_path, text)
        return "unsupported"

    try:
        document = extract_text(raw_path)
    except DocumentReadError as exc:
        capture_paths: list[Path] = []
        status = "failed"
        method = f"{suffix.lstrip('.') or 'file'}_text_extract_failed"
        note = str(exc)
        if suffix == ".pdf":
            capture_paths = render_pdf_pages(
                raw_path,
                capture_dir(raw_dir, source_id, source_path),
            )
            if capture_paths:
                try:
                    extracted = codex_extract_text_from_images(
                        capture_paths,
                        source_name=source_path.name,
                    )
                except RuntimeError as codex_exc:
                    status = "failed"
                    method = "pdf_image_codex_cli_text_extract_failed"
                    note = str(codex_exc)
                else:
                    method = "pdf_image_pymupdf_capture_codex_cli_text_extract"
                    status, note = demote_if_empty(
                        "ready", extracted, "PyMuPDF로 페이지 캡처 후 Codex CLI로 텍스트 판독"
                    )
                    text = source_markdown(
                        source_id=source_id,
                        source_path=source_path,
                        status=status,
                        method=method,
                        text=extracted,
                        raw_path=raw_path,
                        capture_paths=capture_paths,
                        note=note,
                    )
                    write_text(output_path, text)
                    return status
        text = source_markdown(
            source_id=source_id,
            source_path=source_path,
            status=status,
            method=method,
            text="",
            raw_path=raw_path,
            capture_paths=capture_paths,
            note=note,
        )
        write_text(output_path, text)
        return status

    status, note = demote_if_empty("ready", document.text)
    text = source_markdown(
        source_id=source_id,
        source_path=source_path,
        status=status,
        method=f"{document.kind}_text_extract",
        text=document.text,
        raw_path=raw_path,
        note=note,
    )
    write_text(output_path, text)
    return status


def homepage_markdown(url: str) -> str:
    if not url:
        return ""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        return f"""# 홈페이지

## 메타

- homepage_url: {url}
- status: failed
- note: {exc}

## 추출 텍스트

"""
    parser = TextOnlyHTMLParser()
    parser.feed(html)
    lines = [line.strip() for line in parser.chunks if line.strip()]
    text = "\n".join(dict.fromkeys(lines))
    if not text:
        # 응답은 받았지만 본문이 비었다. JS 리다이렉트 스텁이나 JS 렌더링 페이지가 대표적이다.
        # ready로 두면 빈 홈페이지가 후속 phase로 넘어가므로 failed로 떨어뜨린다.
        return f"""# 홈페이지

## 메타

- homepage_url: {url}
- status: failed
- extraction_method: homepage_html_text
- char_count: 0
- note: 응답은 받았으나 추출된 본문이 없음. JS 리다이렉트 또는 JS 렌더링 페이지인지 확인하고, 본문이 있는 실제 주소로 homepage_url을 교정할 것

## 추출 텍스트

"""
    return f"""# 홈페이지

## 메타

- homepage_url: {url}
- status: ready
- extraction_method: homepage_html_text
- char_count: {len(text)}

## 추출 텍스트

{text}
"""


def update_current_phase(readme: str) -> str:
    replacement = "- current_phase: venture-phase3-distillation"
    if re.search(r"^\s*-\s*current_phase:\s*.+$", readme, flags=re.MULTILINE):
        return re.sub(r"^\s*-\s*current_phase:\s*.+$", replacement, readme, flags=re.MULTILINE)
    return readme.rstrip() + "\n\n## 진행 상태\n\n" + replacement + "\n"


def extracted_documents_table(documents: list[tuple[str, Path, str]]) -> str:
    rows = ["| source_id | document | status |", "|---|---|---|"]
    for source_id, document_path, status in documents:
        rows.append(f"| {source_id} | {md_escape(document_path)} | {status} |")
    if not documents:
        rows.append("|  |  | missing |")
    return "\n".join(rows)


def update_extracted_documents(
    readme: str,
    documents: list[tuple[str, Path, str]],
) -> str:
    section = "## 추출 문서\n\n" + extracted_documents_table(documents) + "\n"
    for heading in ("추출 문서", "원본 자료"):
        pattern = rf"\n## {heading}\n.*?(?=\n## |\Z)"
        if re.search(pattern, readme, flags=re.DOTALL):
            return re.sub(pattern, "\n" + section.rstrip() + "\n", readme, flags=re.DOTALL)
    if "\n## 자료 위치" in readme:
        return readme.replace("\n## 자료 위치", "\n" + section + "\n## 자료 위치", 1)
    if "\n## 진행 상태" in readme:
        return readme.replace("\n## 진행 상태", "\n" + section + "\n## 진행 상태", 1)
    return readme.rstrip() + "\n\n" + section


def update_source_locations(readme: str) -> str:
    section = """## 자료 위치

- src: src/
"""
    pattern = r"\n## 자료 위치\n.*?(?=\n## |\Z)"
    if re.search(pattern, readme, flags=re.DOTALL):
        return re.sub(pattern, "\n" + section.rstrip() + "\n", readme, flags=re.DOTALL)
    if "\n## 진행 상태" in readme:
        return readme.replace("\n## 진행 상태", "\n" + section + "\n## 진행 상태", 1)
    return readme.rstrip() + "\n\n" + section


def main() -> int:
    args = parse_args()
    if args.project_root:
        project_root = Path(args.project_root).expanduser().resolve()
    else:
        project_root = find_project_root(Path(__file__).resolve().parent)
    company_dir = project_root / "companies" / args.company
    readme_path = company_dir / "README.md"
    src_dir = company_dir / "src"

    if not readme_path.exists():
        raise SystemExit(f"README.md를 찾을 수 없습니다: {readme_path}")

    readme = read_text(readme_path)
    raw_dir = src_dir / "raw"
    sources = parse_sources(readme) or parse_raw_sources(raw_dir)
    if not sources:
        raise SystemExit("src/raw/에서 추출할 파일을 찾지 못했습니다.")

    summary = {
        "ready": 0,
        "failed": 0,
        "missing": 0,
        "unsupported": 0,
        "visual_review_required": 0,
    }
    extracted_documents: list[tuple[str, Path, str]] = []
    for source_id, source_path in sources:
        status = extract_source_file(source_id, source_path, src_dir)
        summary[status] = summary.get(status, 0) + 1
        extracted_documents.append(
            (
                source_id,
                extracted_target_path(Path("src"), source_id, source_path),
                status,
            )
        )

    homepage_url = parse_homepage_url(readme)
    if homepage_url:
        homepage_text = homepage_markdown(homepage_url)
        write_text(src_dir / "homepage.md", homepage_text)
        homepage_status = "failed" if "- status: failed" in homepage_text else "ready"
        summary[homepage_status] = summary.get(homepage_status, 0) + 1
        extracted_documents.insert(0, ("homepage", Path("src") / "homepage.md", homepage_status))

    updated_readme = update_current_phase(
        update_source_locations(update_extracted_documents(readme, extracted_documents))
    )
    write_text(readme_path, updated_readme)
    print(
        "src={src} ready={ready} failed={failed} missing={missing} unsupported={unsupported} visual_review_required={visual_review_required}".format(
            src=src_dir,
            **summary,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
