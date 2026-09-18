#!/usr/bin/env python3
"""Create a venture company workspace with one README.md file."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import date
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create companies/V<YYMMDD>-<한글회사명>/ with README.md."
    )
    parser.add_argument("company", help="한글 회사명")
    parser.add_argument(
        "--date",
        default="",
        help="작업공간 폴더명에 쓸 날짜(YYMMDD). 미지정 시 오늘 날짜",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="venture 프로젝트 루트. 미지정 시 스크립트 위치에서 .git/companies가 있는 루트를 자동 탐지",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="원본 자료 파일 또는 폴더 경로. 여러 번 지정 가능",
    )
    parser.add_argument("--homepage", default="", help="회사 홈페이지 주소")
    parser.add_argument("--smes-id", default="", help="SMES 포털 아이디")
    parser.add_argument("--smes-pw", default="", help="SMES 포털 비밀번호")
    parser.add_argument(
        "--writing-direction",
        default="",
        help="회사별 사업계획서 작성 방향성",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="README.md가 있어도 재생성",
    )
    return parser.parse_args()


def has_hangul(value: str) -> bool:
    return bool(re.search(r"[가-힣]", value))


def resolve_workspace_date(value: str) -> str:
    """폴더명에 쓸 YYMMDD 날짜를 정한다. 미지정이면 오늘 날짜."""
    text = value.strip()
    if not text:
        return date.today().strftime("%y%m%d")
    if not re.fullmatch(r"\d{6}", text):
        raise SystemExit("--date는 YYMMDD 6자리 숫자로 입력하세요.")
    return text


def workspace_dir_name(workspace_date: str, company: str) -> str:
    """회사 작업공간 폴더명 규칙: V<YYMMDD>-<한글회사명>."""
    return f"V{workspace_date}-{company}"


def find_existing_workspace(companies_dir: Path, company: str) -> Path | None:
    """같은 한글회사명의 기존 작업공간(V<YYMMDD>-<회사명>)을 찾는다."""
    if not companies_dir.is_dir():
        return None
    matches = sorted(
        p for p in companies_dir.iterdir()
        if p.is_dir() and re.fullmatch(rf"V\d{{6}}-{re.escape(company)}", p.name)
    )
    if len(matches) > 1:
        choices = "\n".join(f"- {path.name}" for path in matches)
        raise SystemExit(
            "같은 회사 작업공간이 여러 개입니다. 기존 작업은 phase1을 실행하지 말고 "
            f"사용할 폴더를 선택하세요. 새 작업공간은 --date를 지정하세요:\n{choices}"
        )
    return matches[-1] if matches else None


def find_project_root(start: Path) -> Path:
    """스크립트 위치에서 위로 올라가며 .git 또는 기존 companies/가 있는 프로젝트 루트를 찾는다."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "companies").is_dir():
            return parent
    return start


def source_records(source_values: list[str]) -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    missing: list[str] = []
    for value in source_values:
        src = Path(value).expanduser().resolve()
        if not src.exists():
            missing.append(value)
            continue
        if src.is_file():
            records.append(file_record(src))
        elif src.is_dir():
            for file_path in sorted(p for p in src.rglob("*") if p.is_file()):
                records.append(file_record(file_path))
    return records, missing


def file_record(path: Path) -> dict[str, object]:
    return {
        "source_path": str(path),
        "type": "file",
    }


def safe_name(value: str) -> str:
    return re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", value).strip()[:120] or "source"


def md_escape(value: object) -> str:
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def copy_sources_to_raw(company_dir: Path, records: list[dict[str, object]]) -> int:
    raw_dir = company_dir / "src" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for index, record in enumerate(records, start=1):
        source_path = Path(str(record["source_path"]))
        target = raw_dir / f"SRC-{index:03d}_{safe_name(source_path.name)}"
        shutil.copy2(source_path, target)
    return len(records)


def write_env(path: Path, smes_id: str, smes_pw: str) -> None:
    """포털 자격증명은 git에 올리지 않는 .env에만 둔다. README.md에는 쓰지 않는다."""
    path.write_text(f"SMES_ID={smes_id}\nSMES_PW={smes_pw}\n", encoding="utf-8")


def build_readme_md(
    company: str,
    work_dir: str,
    homepage: str,
    writing_direction: str,
) -> str:
    return f"""# {company} 벤처인증 작업공간

## 기본 정보

- company_name: {company}
- work_dir: companies/{work_dir}
- homepage_url: {homepage}

## 포털 계정

- 포털 자격증명은 `.env`(`SMES_ID`, `SMES_PW`)에 있다. git에 올리지 않는다.

## 작성 방향

{writing_direction}

## 진행 상태

- current_phase: venture-phase2-raw-data
"""


def assert_no_korean_corruption(text: str, path: Path) -> None:
    if re.search(r"\?{2,}", text) or "\ufffd" in text:
        raise SystemExit(f"Korean text corruption guard failed before writing: {path}")


def write_readme(path: Path, text: str) -> None:
    assert_no_korean_corruption(text, path)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    company = args.company.strip()
    if not company:
        raise SystemExit("회사명을 입력하세요.")
    if not has_hangul(company):
        raise SystemExit("회사명은 한글 이름으로 입력하세요.")
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', company) or company.endswith("."):
        raise SystemExit("회사명에는 경로 구분자나 파일명 금지 문자를 사용할 수 없습니다.")
    if not args.homepage.strip():
        raise SystemExit("회사 홈페이지 주소를 입력하세요.")
    if not args.smes_id.strip():
        raise SystemExit("SMES 포털 아이디를 입력하세요.")
    if not args.smes_pw.strip():
        raise SystemExit("SMES 포털 비밀번호를 입력하세요.")
    if not args.source:
        raise SystemExit("기초 원본 자료 파일 또는 폴더 경로를 하나 이상 입력하세요.")

    if args.project_root:
        project_root = Path(args.project_root).expanduser().resolve()
    else:
        project_root = find_project_root(Path(__file__).resolve().parent)
    companies_dir = project_root / "companies"
    existing_dir = find_existing_workspace(companies_dir, company) if not args.date else None
    if existing_dir and not args.date:
        # 날짜를 명시하지 않으면 같은 회사의 기존 작업공간을 그대로 쓴다.
        company_dir = existing_dir
    else:
        workspace_date = resolve_workspace_date(args.date)
        company_dir = companies_dir / workspace_dir_name(workspace_date, company)
    readme_path = company_dir / "README.md"

    source_values = args.source
    records, missing_sources = source_records(source_values)
    if missing_sources:
        raise SystemExit("찾지 못한 자료 위치:\n" + "\n".join(f"- {item}" for item in missing_sources))
    if not records:
        raise SystemExit("복사할 원본 자료 파일을 찾지 못했습니다.")

    if args.force:
        resolved_companies_dir = companies_dir.resolve()
        resolved_company_dir = company_dir.resolve()
        if resolved_company_dir.parent != resolved_companies_dir:
            raise SystemExit(f"재초기화 대상이 companies/ 바로 아래가 아닙니다: {resolved_company_dir}")
        workspace_sources = [
            str(record["source_path"])
            for record in records
            if Path(str(record["source_path"])).resolve().is_relative_to(resolved_company_dir)
        ]
        if workspace_sources:
            raise SystemExit(
                "재초기화할 작업공간 안의 파일은 원본 자료로 사용할 수 없습니다. "
                "작업공간 밖의 보존본을 지정하세요:\n"
                + "\n".join(f"- {path}" for path in workspace_sources)
            )
        if company_dir.exists():
            shutil.rmtree(company_dir)

    if readme_path.exists() and not args.force:
        raise SystemExit(
            f"이미 README.md가 있습니다: {readme_path}\n"
            "재생성하려면 --force를 사용하세요."
        )

    company_dir.mkdir(parents=True, exist_ok=True)

    copied_count = copy_sources_to_raw(company_dir, records)
    readme_text = build_readme_md(
        company,
        company_dir.name,
        args.homepage.strip(),
        args.writing_direction.strip(),
    )
    write_readme(readme_path, readme_text)
    env_path = company_dir / ".env"
    write_env(env_path, args.smes_id.strip(), args.smes_pw.strip())

    print(f"회사 작업공간: {company_dir}")
    print(f"README 파일: {readme_path}")
    print(f"포털 자격증명: {env_path} (git 제외)")
    print(f"src/raw 원본 자료 복사: {copied_count}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
