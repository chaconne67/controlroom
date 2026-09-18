#!/usr/bin/env python3
"""장문 본문 10개와 사업계획서 요약을 하나의 PDF로 조립한다.

포털 입력 전에 전체 흐름을 한 번에 검토하기 위한 산출물이며, 기존 회사
산출물(`에브모우_사업계획서_장문통합.pdf`) 형식을 따른다.
A4, 맑은 고딕 10.5pt, 여백 18mm, 표지 + 요약 + 번호 항목 순.

렌더링은 시스템 Chrome의 `--headless --print-to-pdf`를 직접 호출한다.
Chrome은 종료 과정에서 STATUS_STACK_BUFFER_OVERRUN(0xC0000409)으로 죽는 경우가 있어
종료코드를 신뢰할 수 없으므로, **산출된 PDF 파일로 성공 여부를 판정**한다.

사용:
    uv run python scripts/build_longtext_pdf.py <회사폴더명>
    uv run python scripts/build_longtext_pdf.py V260720-제노 --date 2026.07
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

# 포털 제출 순서와 동일하게 배열한다. 순서를 바꾸면 검토 흐름이 깨진다.
SECTIONS: list[tuple[str, str, bool]] = [
    ("business_plan_summary", "사업계획서 요약", True),
    ("problem_background", "기술(제품/서비스)의 개발 배경 및 필요성", False),
    ("solution", "솔루션으로서의 기술(제품/서비스) 소개와 경쟁력 확보 방안", False),
    ("tech_progress", "제품/서비스 관련 기술개발 추진 경과", False),
    ("tech_plan", "향후 3년간 기술개발 계획", False),
    ("target_market", "목표시장 및 고객 정의", False),
    ("competition", "경쟁사 분석", False),
    ("market_progress", "시장진입 및 확대 전략 추진경과", False),
    ("market_plan", "시장진입 및 확대 전략 향후 3년 계획", False),
    ("funding_plan", "자금운용 계획", False),
    ("entrepreneurship", "기업가 정신", False),
]

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="장문 본문을 하나의 PDF로 조립한다.")
    parser.add_argument("company", help="회사 폴더명 (예: V260720-제노)")
    parser.add_argument("--project-root", default=None, help="venture 프로젝트 루트. 미지정 시 자동 탐지")
    parser.add_argument("--out", default=None, help="출력 PDF 경로. 미지정 시 회사 폴더에 생성")
    parser.add_argument("--date", default="", help="표지 날짜 표기(예: 2026.07). 미지정 시 이번 달")
    return parser.parse_args()


def find_project_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "companies").is_dir():
            return parent
    return start


def resolve_chrome() -> str:
    env = os.environ.get("CHROME_EXE")
    if env and Path(env).exists():
        return env
    for candidate in CHROME_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    found = shutil.which("chrome")
    if found:
        return found
    raise SystemExit("Chrome 실행 파일을 찾지 못했습니다. CHROME_EXE 환경변수로 지정하세요.")


def read_body(path: Path) -> str:
    """프론트매터와 제목 줄을 걷어내고 본문만 돌려준다."""
    raw = path.read_text(encoding="utf-8").lstrip("﻿")
    stripped = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", raw, count=1, flags=re.S)
    return re.sub(r"^#\s+.*\r?\n", "", stripped, count=1).strip()


def read_meta(readme: Path) -> dict[str, str]:
    meta: dict[str, str] = {}
    if not readme.exists():
        return meta
    for line in readme.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^-\s*([A-Za-z_]+):\s*(.*)$", line.strip())
        if m:
            meta[m.group(1)] = m.group(2).strip()
    return meta


def read_value(values: Path, key: str) -> str:
    if not values.exists():
        return ""
    m = re.search(rf"###\s*{re.escape(key)}\s*\r?\n```yaml\r?\nvalue:\s*(.+)", values.read_text(encoding="utf-8"))
    return m.group(1).strip() if m else ""


def render_body(body: str) -> str:
    """`1.` 상위 항목, `1)` 하위 항목, 콜론형 소제목을 구분해 들여쓴다."""
    out: list[str] = []
    for line in body.splitlines():
        t = line.strip()
        if not t:
            out.append('<div class="gap"></div>')
            continue
        e = html.escape(t)
        if re.match(r"^\d+\.\s", t):
            out.append(f'<p class="lv1">{e}</p>')
        elif re.match(r"^\d+\)\s", t) or re.match(r"^\[[^\]]+\]", t) or re.match(r"^[^:：]{1,24}[:：]\s*\S", t):
            out.append(f'<p class="lv2">{e}</p>')
        else:
            out.append(f'<p class="lv1">{e}</p>')
    return "\n".join(out)


def build_html(company_name: str, tech_name: str, meta: dict[str, str], sections: list[tuple[str, str, str]], stamp: str) -> str:
    bits = []
    if meta.get("representative_name"):
        bits.append(f"대표 {meta['representative_name']}")
    if meta.get("homepage_url"):
        bits.append(meta["homepage_url"])
    bits.append(stamp)
    cover_meta = html.escape(" · ".join(bits))

    body_parts = []
    number = 0
    for title, body, unnumbered in sections:
        if unnumbered:
            heading = title
        else:
            number += 1
            heading = f"{number}. {title}"
        body_parts.append(
            f'<section class="item">\n  <h2>{html.escape(heading)}</h2>\n{render_body(body)}\n</section>'
        )

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>{html.escape(company_name)} 사업계획서</title>
<style>
  @page {{ size: A4; margin: 18mm 18mm 16mm 18mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Malgun Gothic", "맑은 고딕", sans-serif; font-size: 10.5pt; line-height: 1.65; color: #111; margin: 0; }}
  .cover {{ height: 247mm; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; page-break-after: always; }}
  .cover-kind {{ font-size: 12pt; font-weight: 700; margin-bottom: 14mm; }}
  .cover-title {{ font-size: 30pt; font-weight: 700; margin: 0 0 12mm; letter-spacing: -0.5px; }}
  .cover-sub {{ font-size: 12pt; line-height: 1.7; margin-bottom: 16mm; max-width: 150mm; }}
  .cover-meta {{ font-size: 10.5pt; color: #333; }}
  .item {{ page-break-inside: avoid; margin-bottom: 9mm; }}
  .item h2 {{ font-size: 14pt; font-weight: 700; margin: 0 0 4mm; padding-bottom: 2mm; border-bottom: 1.2px solid #111; }}
  p {{ margin: 0 0 1.2mm; text-align: justify; word-break: keep-all; }}
  p.lv2 {{ padding-left: 5mm; }}
  .gap {{ height: 2.6mm; }}
</style></head>
<body>
<section class="cover">
  <div class="cover-kind">벤처기업확인 (혁신성장유형)</div>
  <h1 class="cover-title">{html.escape(company_name)} 사업계획서</h1>
  <div class="cover-sub">{html.escape(tech_name)}</div>
  <div class="cover-meta">{cover_meta}</div>
</section>
{chr(10).join(body_parts)}
</body></html>"""


def render_pdf(chrome: str, html_path: Path, out_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    with tempfile.TemporaryDirectory(prefix="longtext_pdf_") as profile:
        subprocess.run(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={out_path}",
                html_path.as_uri(),
            ],
            capture_output=True,
            timeout=180,
            check=False,  # Chrome 종료코드는 신뢰할 수 없다. 산출물로 판정한다.
        )


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).expanduser().resolve() if args.project_root else find_project_root(Path(__file__).resolve().parent)
    company_dir = root / "companies" / args.company
    if not company_dir.is_dir():
        raise SystemExit(f"회사 폴더가 없습니다: {company_dir}")

    texts_dir = company_dir / "texts"
    missing = [key for key, _, _ in SECTIONS if not (texts_dir / f"{key}.md").exists()]
    if missing:
        raise SystemExit("본문 파일이 없습니다: " + ", ".join(missing))

    sections: list[tuple[str, str, str]] = []
    empty: list[str] = []
    for key, title, unnumbered in SECTIONS:
        body = read_body(texts_dir / f"{key}.md")
        if not body:
            empty.append(key)
        sections.append((title, body, unnumbered))
    if empty:
        raise SystemExit("본문이 비어 있습니다: " + ", ".join(empty))

    meta = read_meta(company_dir / "README.md")
    values = company_dir / "values.md"
    company_name = meta.get("company_name") or re.sub(r"^V\d{6}-", "", args.company)
    meta.setdefault("representative_name", read_value(values, "representative_name"))
    tech_name = read_value(values, "tech_name")
    stamp = args.date.strip() or date.today().strftime("%Y.%m")

    out_path = Path(args.out).expanduser().resolve() if args.out else company_dir / f"{company_name}_사업계획서_장문통합.pdf"
    html_path = company_dir / ".longtext_bundle.html"
    html_path.write_text(build_html(company_name, tech_name, meta, sections, stamp), encoding="utf-8")

    try:
        render_pdf(resolve_chrome(), html_path, out_path)
    finally:
        html_path.unlink(missing_ok=True)

    if not out_path.exists() or out_path.stat().st_size < 10_000:
        raise SystemExit(f"PDF 생성 실패: {out_path}")

    total = sum(len(body) for _, body, _ in sections)
    try:
        shown = out_path.relative_to(root)
    except ValueError:
        shown = out_path  # --out으로 프로젝트 밖 경로를 지정한 경우
    print(f"OK {shown} ({out_path.stat().st_size:,} bytes, 섹션 {len(sections)}개, 본문 합계 {total:,}자)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
