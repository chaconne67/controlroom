#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""사업계획서 요약 양식 빈칸 치환 조립 스크립트.

고정 문구가 박힌 템플릿(skills/venture/references/business_plan_summary_template.md)의
`{{key}}` 플레이스홀더만 values JSON 값으로 치환한다. 고정 문구는 템플릿 그대로 보존되므로
LLM이 양식을 재생성하다 고정 문구를 변형하는 오류가 원천 차단된다.

사용:
  uv run python scripts/fill_business_plan_summary.py \
    --values companies/<회사>/texts/business_plan_summary_values.json \
    --out    companies/<회사>/texts/business_plan_summary.md
"""
import argparse
import json
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_]+)\s*\}\}")
DEFAULT_TEMPLATE = (
    Path(__file__).resolve().parent.parent
    / "skills" / "venture" / "references" / "business_plan_summary_template.md"
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fill business plan summary template placeholders.")
    ap.add_argument("--values", required=True, help="placeholder values JSON file")
    ap.add_argument("--out", required=True, help="output markdown path")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="template path")
    args = ap.parse_args()

    template = Path(args.template).read_text(encoding="utf-8")
    values = json.loads(Path(args.values).read_text(encoding="utf-8"))

    missing = []

    def repl(m: "re.Match[str]") -> str:
        key = m.group(1)
        v = values.get(key)
        if v is None or str(v).strip() == "":
            missing.append(key)
            return m.group(0)
        return str(v)

    filled = PLACEHOLDER.sub(repl, template)
    unfilled = sorted(set(PLACEHOLDER.findall(filled)) | set(missing))
    if unfilled:
        sys.stderr.write("ERROR unfilled/missing keys: " + ", ".join(unfilled) + "\n")
        return 1

    # char_count: 프론트매터와 제목을 제외한 본문 글자수(공백·줄바꿈 포함)
    body = filled
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) == 3:
            body = parts[2]
    body = re.sub(r"^\s*#\s*사업계획서 요약\s*", "", body.lstrip(), count=1)
    count = len(body.strip())
    filled = re.sub(r"char_count:\s*\d+", f"char_count: {count}", filled, count=1)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(filled, encoding="utf-8")
    sys.stdout.write(f"OK {args.out} (char_count={count})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
