"""texts/*.md 본문 글자수 실측 검증.

작성 sub-agent의 char_count 자기보고는 자주 틀리므로(실측과 수백 자 차이),
메인 에이전트가 이 스크립트로 실측해 900~1000자 범위와 선언값 일치를 검증한다.

사용법:
  uv run python scripts/check_charcount.py <회사명> [field_id ...]
  - field_id를 지정하면 해당 파일만 검사(예: funding_plan target_market).
  - 지정하지 않으면 texts/*.md 전체 검사.

판정:
  - 본문 글자수 = 프론트매터와 H1 제목을 제외한 본문(공백·줄바꿈 포함) 길이.
  - 자유 서술형 본문은 900자 이상 1000자 미만이어야 한다.
  - business_plan_summary는 요약 양식이므로 글자수 범위 검사에서 제외(실측값만 표시).
  - 프론트매터 char_count 선언값이 실측값과 다르면 불일치로 표시한다.
종료코드: 위반이 1건 이상이면 1, 없으면 0.
"""
import glob
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def find_project_root(start: Path) -> Path:
    """스크립트 위치에서 위로 올라가며 .git 또는 기존 companies/가 있는 프로젝트 루트를 찾는다."""
    for parent in [start, *start.parents]:
        if (parent / ".git").exists() or (parent / "companies").is_dir():
            return parent
    return start

# 글자수 범위 검사를 적용하지 않는 항목(요약 양식 등).
SUMMARY_EXEMPT = {"business_plan_summary"}
# 산출물이 아닌 참조 파일(문체 샘플 등)은 검사에서 완전 제외.
SKIP_FILES = {"sample"}


def measure(text: str) -> int:
    m = re.match(r"^---\n.*?\n---\n(.*)", text, re.S)
    body = m.group(1) if m else text
    body = re.sub(r"^#\s+.*\n+", "", body.strip())  # H1 제목 제거
    return len(body)


def declared_char_count(text: str):
    m = re.search(r"char_count:\s*(\d+)", text)
    return int(m.group(1)) if m else None


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: uv run python scripts/check_charcount.py <회사명> [field_id ...]")
        return 2
    company = sys.argv[1]
    selected = set(sys.argv[2:])
    project_root = find_project_root(Path(__file__).resolve().parent)
    texts_dir = os.path.join(str(project_root), "companies", company, "texts")
    files = sorted(glob.glob(os.path.join(texts_dir, "*.md")))
    if not files:
        print(f"대상 파일 없음: {texts_dir}/*.md")
        return 2

    violations = 0
    for path in files:
        name = os.path.splitext(os.path.basename(path))[0]
        if name in SKIP_FILES:
            continue
        if selected and name not in selected:
            continue
        text = open(path, encoding="utf-8").read()
        actual = measure(text)
        declared = declared_char_count(text)
        if name in SUMMARY_EXEMPT:
            print(f"{name:22} actual={actual:5} (요약 양식: 글자수 범위 미적용)")
            continue
        flags = []
        if not (900 <= actual < 1000):
            flags.append("범위밖(900~1000)")
        if declared is not None and declared != actual:
            flags.append(f"선언값{declared}≠실측{actual}")
        if flags:
            violations += 1
        status = "OK" if not flags else " / ".join(flags)
        print(f"{name:22} actual={actual:5} declared={declared} {status}")

    if violations:
        print(f"\n위반 {violations}건 → 900자 미만은 보강, 1000자 이상은 압축한 뒤 char_count를 실측값으로 갱신하라.")
    else:
        print("\n전부 OK (실측 900~1000자, char_count 일치)")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
