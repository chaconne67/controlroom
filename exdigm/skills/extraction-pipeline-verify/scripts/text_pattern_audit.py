"""40건 텍스트의 공통 노이즈/중복 패턴 정량 분석."""
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path("/home/chaconne/exdigm-debug")
spec = json.loads((ROOT / "snapshots/step_b2_text_v2.json").read_text())

PATTERNS = {
    "self_intro_header": re.compile(
        r"자기\s*소개(서)?|지원\s*동기|성장\s*과정|입사\s*포부|"
        r"personal\s*statement|cover\s*letter|career\s*objective|objective\s*:|"
        r"about\s+me|professional\s+summary",
        re.IGNORECASE,
    ),
    "page_number": re.compile(
        r"\bpage\s*\d+\s*(?:of|/)\s*\d+\b|^\s*\d+\s*/\s*\d+\s*$|^\s*-\s*\d+\s*-\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "url": re.compile(
        r"https?://\S+|www\.\S+\.\S+",
        re.IGNORECASE,
    ),
    "consent_statement": re.compile(
        r"본인은\s+위\s*(?:내용|사항|기재).*?(?:사실|상이|틀림|동의)|"
        r"위와\s*같이|위\s*기재.*?(?:사실|동의)|"
        r"i\s+(?:hereby\s+)?(?:certify|declare|confirm)\s+that",
        re.IGNORECASE,
    ),
    "signature_line": re.compile(
        r"^[ \t]*\d{4}[.\-/년 ]+\d{1,2}[.\-/월 ]+\d{1,2}[일\s]*$|"
        r"\b(?:서명|성명|날인|signature)\s*[:：]?\s*\(?\s*인\s*\)?",
        re.IGNORECASE | re.MULTILINE,
    ),
    "form_label_only": re.compile(
        r"^\s*(?:이름|성명|name|성별|gender|나이|age|연락처|tel|phone|email|"
        r"이메일|주소|address|학력|education|경력|experience|career|"
        r"자격증|certification|어학|language|특기|취미|병역|military)\s*[:：]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "long_table_separator": re.compile(r"^[\s\-=|+_]{20,}$", re.MULTILINE),
    "image_alt_or_caption": re.compile(
        r"\[(?:사진|이미지|그림|figure|image|photo)[^\]]*\]|"
        r"<(?:사진|이미지|그림)[^>]*>",
        re.IGNORECASE,
    ),
    "address_full": re.compile(
        r"(?:서울|경기|인천|부산|대구|대전|광주|울산|세종|강원|충[북남]|전[북남]|경[북남]|제주)"
        r"[가-힣\d\s\-,\.()]{10,80}(?:동|로|길|아파트|apt|빌라|타워|호)",
    ),
    "salary_table": re.compile(
        r"(?:연봉|월급|급여|salary|연소득)[:\s].*?(?:만\s*원|원|won|usd|\$)",
        re.IGNORECASE,
    ),
    "long_run_of_korean_prose": re.compile(r"[가-힣\s,\.]{300,}"),
    "english_long_paragraph": re.compile(r"[A-Za-z\s,\.]{500,}"),
}


def analyze(text: str) -> dict:
    return {
        name: len(pat.findall(text))
        for name, pat in PATTERNS.items()
    }


def line_stats(text: str) -> dict:
    lines = text.split("\n")
    non_empty = [ln for ln in lines if ln.strip()]
    line_lens = sorted(len(ln) for ln in non_empty)
    n = len(non_empty)
    if n == 0:
        return {"lines": 0, "very_short": 0, "very_long": 0}
    very_short = sum(1 for ln in non_empty if len(ln.strip()) < 5)
    very_long = sum(1 for ln in non_empty if len(ln) > 200)
    return {
        "lines": n,
        "very_short": very_short,
        "very_long": very_long,
        "median_line_len": line_lens[n // 2],
    }


def detect_korean_english_repeat(text: str) -> dict:
    """라인의 한국어/영어 비율로 중복 섹션 추정."""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    ko_lines = []
    en_lines = []
    for ln in lines:
        ko = len(re.findall(r"[가-힣]", ln))
        en = len(re.findall(r"[A-Za-z]", ln))
        if ko + en == 0:
            continue
        if ko >= en:
            ko_lines.append(ln)
        else:
            en_lines.append(ln)
    return {
        "ko_lines": len(ko_lines),
        "en_lines": len(en_lines),
        "ko_chars": sum(len(ln) for ln in ko_lines),
        "en_chars": sum(len(ln) for ln in en_lines),
    }


print(f"{'cat':<13} {'file':<32} {'len':>6} {'lines':>5} {'med':>4} "
      f"{'self':>4} {'pg':>3} {'url':>3} {'consent':>7} {'sig':>3} "
      f"{'lbl':>3} {'tbl':>3} {'img':>3} {'sal':>3} {'addr':>4} "
      f"{'KOln':>4} {'ENln':>4}")
print("-" * 145)

agg = Counter()
total_files = 0

for r in spec["results"]:
    if not r.get("ok") or not r.get("text_path"):
        continue
    text = Path(r["text_path"]).read_text(encoding="utf-8")
    a = analyze(text)
    ls = line_stats(text)
    le = detect_korean_english_repeat(text)
    total_files += 1
    for k, v in a.items():
        if v > 0:
            agg[k] += 1

    print(f"{r['category'][:11]:<13} {r['file_name'][:30]:<32} "
          f"{r['preprocessed_length']:>6d} {ls['lines']:>5d} {ls.get('median_line_len',0):>4d} "
          f"{a['self_intro_header']:>4d} {a['page_number']:>3d} {a['url']:>3d} "
          f"{a['consent_statement']:>7d} {a['signature_line']:>3d} "
          f"{a['form_label_only']:>3d} {a['long_table_separator']:>3d} "
          f"{a['image_alt_or_caption']:>3d} {a['salary_table']:>3d} "
          f"{a['address_full']:>4d} {le['ko_lines']:>4d} {le['en_lines']:>4d}")

print()
print(f"=== {total_files}건 중 패턴 출현 빈도 (1건 이상) ===")
for k in PATTERNS:
    print(f"  {k:<28} {agg[k]:>3d} / {total_files}")
