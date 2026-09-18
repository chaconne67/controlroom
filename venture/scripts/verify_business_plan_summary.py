#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""사업계획서 요약 고정 문구 무결성 검증 스크립트.

메인 에이전트가 조립 결과물(business_plan_summary.md)의 어미·맥락을 다듬은 뒤,
고정 문구(양식)가 훼손되지 않았는지 기계적으로 성공/실패 판정한다.

검증 방식:
- 템플릿을 `{{key}}` 플레이스홀더 기준으로 분할해 '고정 문구 세그먼트'를 추출한다.
- 결과물에서 각 세그먼트가 '순서대로' 그대로 존재하는지 확인한다(빈칸 값은 세그먼트 사이에 자유롭게 들어감).
- 세그먼트가 하나라도 깨지면(누락·변형) FAIL.
- 결과물에 미치환 `{{...}}` 가 남아 있으면 FAIL.
- char_count 값은 본문 길이에 따라 달라지므로 비교에서 정규화해 무시한다.

사용:
  uv run python scripts/verify_business_plan_summary.py \
    --file companies/<회사>/texts/business_plan_summary.md
"""
import argparse
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\{\{\s*[a-zA-Z_]+\s*\}\}")
DEFAULT_TEMPLATE = (
    Path(__file__).resolve().parent.parent
    / "skills" / "venture" / "references" / "business_plan_summary_template.md"
)


def normalize(text: str) -> str:
    # char_count 는 본문 길이에 따라 달라지므로 비교 대상에서 제외(정규화)
    return re.sub(r"char_count:\s*\d+", "char_count: N", text)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify fixed-phrase integrity of the assembled summary.")
    ap.add_argument("--file", required=True, help="assembled business_plan_summary.md to verify")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="template path")
    args = ap.parse_args()

    template = normalize(Path(args.template).read_text(encoding="utf-8"))
    result = normalize(Path(args.file).read_text(encoding="utf-8"))

    # 결과물에 미치환 플레이스홀더가 남아 있으면 실패
    leftover = sorted(set(PLACEHOLDER.findall(result)))
    if leftover:
        sys.stderr.write("FAIL 미치환 빈칸 잔존: " + ", ".join(leftover) + "\n")
        return 1

    # 템플릿의 고정 문구 세그먼트(플레이스홀더 사이 텍스트)
    segments = [s for s in PLACEHOLDER.split(template) if s.strip() != ""]

    pos = 0
    broken = []
    for seg in segments:
        idx = result.find(seg, pos)
        if idx == -1:
            # 어디서 깨졌는지 식별용으로 앞부분만 표시
            preview = seg.strip().splitlines()[0][:50] if seg.strip() else seg[:50]
            broken.append(preview)
        else:
            pos = idx + len(seg)

    if broken:
        sys.stderr.write("FAIL 고정 문구 훼손/순서 불일치:\n")
        for b in broken:
            sys.stderr.write(f"  - …{b}…\n")
        sys.stderr.write("→ 고정 문구는 원래대로 두고 빈칸 값(또는 그 표현)만 다듬어 재검증하라.\n")
        return 1

    sys.stdout.write(f"OK 고정 문구 무결성 통과 ({len(segments)}개 세그먼트 일치)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
