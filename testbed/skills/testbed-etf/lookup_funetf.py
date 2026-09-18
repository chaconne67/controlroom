# -*- coding: utf-8 -*-
"""
국내 ETF 정보 조회 스크립트 (funetf.co.kr)

사용법:
  python lookup_funetf.py --isin KR7069500007
  python lookup_funetf.py --ticker 069500
  python lookup_funetf.py --batch KR7069500007 KR7379800004

출력: JSON (stdout), 진행상황은 stderr로 출력
"""

import argparse
import io
import json
import re
import sys
import time

# Windows 콘솔 UTF-8 강제
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# lookup_isin.py에서 validate_isin 임포트 시도, 실패 시 자체 구현 사용
# ---------------------------------------------------------------------------

try:
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    from lookup_isin import validate_isin
except ImportError:
    def validate_isin(isin: str) -> bool:
        """ISIN 체크디짓 검증 (Luhn 알고리즘)"""
        if not re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", isin):
            return False
        digits = ""
        for c in isin:
            digits += str(int(c, 36))
        total = 0
        for i, d in enumerate(reversed(digits)):
            n = int(d)
            if i % 2 == 1:
                n *= 2
                if n >= 10:
                    n = n // 10 + n % 10
            total += n
        return total % 10 == 0


def _luhn_checkdigit(partial_isin: str) -> str:
    """12자리 ISIN의 마지막 체크디짓 계산 (partial_isin은 11자)"""
    digits = ""
    for c in partial_isin:
        digits += str(int(c, 36))
    # ISIN Luhn: 오른쪽부터 홀수 위치(1-indexed)는 그대로, 짝수 위치는 x2
    # 체크디짓 자리를 포함하면 총합이 10의 배수가 되어야 함
    # partial에 대해 체크디짓 0을 붙인 것처럼 계산
    total = 0
    # 체크디짓 위치(index 0 from right)는 그대로이므로,
    # partial의 digit들은 index 1부터 시작 (오른쪽에서)
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        # i+1 because checkdigit (not yet appended) would be at position 0
        if (i + 1) % 2 == 1:
            n *= 2
            if n >= 10:
                n = n // 10 + n % 10
        total += n
    check = (10 - (total % 10)) % 10
    return str(check)


def make_isin(ticker: str) -> str:
    """6자리 국내 티커 → 12자리 ISIN (KR7{ticker}00{checkdigit})"""
    ticker = ticker.strip()
    if len(ticker) != 6 or not ticker.isdigit():
        raise ValueError(f"티커는 6자리 숫자여야 합니다: {ticker}")
    partial = f"KR7{ticker}00"  # 11자
    cd = _luhn_checkdigit(partial)
    isin = partial + cd
    return isin


# ---------------------------------------------------------------------------
# 자산유형 힌트 도출
# ---------------------------------------------------------------------------

# 해외 지수 키워드
_FOREIGN_KEYWORDS = [
    "S&P", "NASDAQ", "나스닥", "다우", "Dow", "MSCI", "EURO", "유럽",
    "일본", "닛케이", "Nikkei", "중국", "항셍", "Hang Seng", "HSI",
    "선진국", "신흥국", "글로벌", "미국", "Russell", "FTSE",
    "인도", "베트남", "대만", "필라델피아",
]

# 국내 지수 키워드
_DOMESTIC_EQUITY_KEYWORDS = [
    "KOSPI", "코스피", "KOSDAQ", "코스닥", "KRX", "K-",
]


def derive_asset_type_hint(base_index: str) -> str:
    """기초지수 문자열로부터 자산유형 힌트를 도출한다."""
    if not base_index:
        return ""

    text = base_index.upper()
    original = base_index

    # 원자재 계열
    commodity_kw = ["금", "은", "원유", "원자재", "COMMODITY", "OIL", "GOLD", "SILVER",
                    "구리", "천연가스", "팔라듐", "백금", "PLATINUM", "COPPER", "농산물"]
    for kw in commodity_kw:
        if kw.upper() in text or kw in original:
            return "원자재"

    # 채권 계열
    bond_kw = ["채권", "국채", "회사채", "BOND", "TREASURY", "국고채", "통안채",
               "크레딧", "하이일드", "HIGH YIELD", "머니마켓", "CD금리", "KOFR"]
    for kw in bond_kw:
        if kw.upper() in text or kw in original:
            # 듀레이션 힌트
            if any(k in original for k in ["단기", "초단기", "1년", "3개월", "6개월"]):
                duration = "단기"
            elif any(k in original for k in ["장기", "10년", "20년", "30년"]):
                duration = "장기"
            elif any(k in original for k in ["중기", "3년", "5년"]):
                duration = "중기"
            else:
                duration = ""
            # 국내/해외 판별
            is_foreign = any(fk.upper() in text for fk in _FOREIGN_KEYWORDS)
            region = "해외" if is_foreign else "국내"
            prefix = f"{region}채권"
            if duration:
                return f"{prefix}({duration})"
            return prefix

    # 주식 계열
    equity_kw = ["주식", "코스피", "코스닥", "KOSPI", "KOSDAQ", "S&P", "나스닥",
                 "NASDAQ", "다우", "DOW", "KRX", "배당", "가치", "성장", "대형",
                 "중형", "소형", "200", "50", "100", "MSCI", "섹터", "업종",
                 "반도체", "2차전지", "바이오", "IT", "자동차", "은행", "건설",
                 "에너지", "헬스케어", "인프라", "리츠", "REIT"]
    for kw in equity_kw:
        if kw.upper() in text or kw in original:
            # 국내/해외 판별
            is_domestic = any(dk.upper() in text for dk in _DOMESTIC_EQUITY_KEYWORDS)
            is_foreign = any(fk.upper() in text for fk in _FOREIGN_KEYWORDS)
            if is_domestic and not is_foreign:
                return "국내주식"
            elif is_foreign and not is_domestic:
                return "해외주식"
            elif is_domestic and is_foreign:
                return "해외주식"  # 글로벌 지수 우선
            # 200, 50 등 숫자만으로는 판단 어려움 → 국내 기본
            return "국내주식"

    # 부동산/리츠
    if any(k in original for k in ["부동산", "리츠", "REIT"]):
        return "부동산"

    # 통화
    if any(k in original for k in ["달러", "엔", "유로", "환율", "FX", "통화"]):
        return "통화"

    # 기본: 원본 텍스트 반환 (호출자가 판단)
    return original


# ---------------------------------------------------------------------------
# 위험등급 파싱
# ---------------------------------------------------------------------------

_RISK_GRADE_NAMES = {
    1: "매우높은위험",
    2: "높은위험",
    3: "다소높은위험",
    4: "보통위험",
    5: "낮은위험",
    6: "매우낮은위험",
}


def parse_risk_grade(text: str) -> tuple[int | None, str]:
    """'N등급(위험등급명)' 형태의 텍스트에서 등급 숫자와 이름을 추출한다.
    Returns (grade_number, grade_name) or (None, '') if not found.
    """
    # 패턴: "2등급(높은위험)" or "2등급 (높은위험)" or "2등급"
    m = re.search(r"(\d)\s*등급\s*(?:\(([^)]+)\))?", text)
    if m:
        grade = int(m.group(1))
        name = m.group(2) or _RISK_GRADE_NAMES.get(grade, "")
        return grade, name
    return None, ""


# ---------------------------------------------------------------------------
# funetf.co.kr 페이지 스크래핑
# ---------------------------------------------------------------------------

def _log(msg: str):
    """stderr로 진행 상황 출력"""
    print(msg, file=sys.stderr, flush=True)


def dismiss_popup(page):
    """funetf.co.kr 초기 팝업 닫기 시도"""
    try:
        # 흔한 닫기 버튼 셀렉터들
        close_selectors = [
            "button.popup-close",
            "button.close",
            ".popup .close",
            ".modal .close",
            "button:has-text('닫기')",
            "button:has-text('확인')",
            "a:has-text('닫기')",
            ".layer_popup .btn_close",
            ".pop_wrap .btn_close",
            "[class*='close']",
        ]
        for sel in close_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=500):
                    el.click(timeout=1000)
                    _log("  [popup] 닫기 버튼 클릭")
                    time.sleep(0.5)
                    return True
            except Exception:
                continue

        # Escape 키로 시도
        page.keyboard.press("Escape")
        time.sleep(0.3)
        _log("  [popup] Escape 키 전송")
        return True
    except Exception:
        return False


def lookup_single_etf(page, isin: str) -> dict:
    """funetf.co.kr에서 단일 ETF 정보를 조회한다.

    Returns dict with keys: isin, name, base_index, risk_grade, risk_grade_name,
                            risk_score, is_risk_asset, asset_type_hint
    Raises Exception on failure.
    """
    url = f"https://www.funetf.co.kr/product/etf/view/{isin}"
    _log(f"  [funetf] {url}")

    page.goto(url, timeout=30000)
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    time.sleep(2)

    # 팝업 닫기 시도
    dismiss_popup(page)
    time.sleep(1)

    # --- 종목명 추출 ---
    name = ""
    # 방법1: 페이지 내 주요 헤딩에서 추출
    name_selectors = [
        "h2.name", "h3.name", ".fund_name", ".etf_name",
        "h2", "h1", ".tit", ".title",
        "h2.tit", "h3.tit",
    ]
    for sel in name_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1000):
                candidate = el.inner_text(timeout=2000).strip()
                if candidate and len(candidate) > 2 and len(candidate) < 100:
                    name = candidate
                    break
        except Exception:
            continue

    # 방법2: title 태그
    if not name:
        title = page.title()
        if title:
            # "KODEX 200 | funetf" 같은 형태에서 앞부분만
            name = title.split("|")[0].split("-")[0].strip()

    # 방법3: JavaScript로 추출 시도
    if not name:
        try:
            name = page.evaluate("""
                () => {
                    const h = document.querySelector('h2, h3, h1, .fund_name, .etf_name');
                    return h ? h.textContent.trim() : '';
                }
            """) or ""
        except Exception:
            pass

    _log(f"  [종목명] {name}")

    # --- 기초지수 추출 ---
    base_index = ""
    try:
        base_index = page.evaluate("""
            () => {
                // th/td 테이블 패턴
                const ths = document.querySelectorAll('th, dt, .label');
                for (const th of ths) {
                    const label = th.textContent.trim();
                    if (label.includes('기초지수') || label.includes('추적지수') || label.includes('벤치마크')) {
                        const td = th.nextElementSibling;
                        if (td) return td.textContent.trim();
                    }
                }
                // dl/dd 패턴
                const dts = document.querySelectorAll('dt');
                for (const dt of dts) {
                    if (dt.textContent.trim().includes('기초지수')) {
                        const dd = dt.nextElementSibling;
                        if (dd && dd.tagName === 'DD') return dd.textContent.trim();
                    }
                }
                // 텍스트 검색 fallback
                const body = document.body.innerText;
                const m = body.match(/기초지수[:\\s]*([^\\n]+)/);
                if (m) return m[1].trim();
                return '';
            }
        """) or ""
    except Exception as e:
        _log(f"  [기초지수] 추출 오류: {e}")

    _log(f"  [기초지수] {base_index}")

    # --- 위험등급 추출 ---
    risk_grade = None
    risk_grade_name = ""
    try:
        risk_text = page.evaluate("""
            () => {
                const body = document.body.innerText;
                // "N등급" 패턴 검색
                const m = body.match(/(\\d)\\s*등급\\s*(?:\\(([^)]+)\\))?/);
                if (m) return m[0];
                return '';
            }
        """) or ""
        if risk_text:
            risk_grade, risk_grade_name = parse_risk_grade(risk_text)
    except Exception as e:
        _log(f"  [위험등급] 추출 오류: {e}")

    _log(f"  [위험등급] {risk_grade}등급 ({risk_grade_name})")

    # --- 계산 필드 ---
    risk_score = (7 - risk_grade) if risk_grade is not None else None
    is_risk_asset = "Y" if (risk_grade is not None and risk_grade <= 3) else (
        "N" if risk_grade is not None else None
    )
    asset_type_hint = derive_asset_type_hint(base_index)

    return {
        "isin": isin,
        "name": name,
        "base_index": base_index,
        "risk_grade": risk_grade,
        "risk_grade_name": risk_grade_name,
        "risk_score": risk_score,
        "is_risk_asset": is_risk_asset,
        "asset_type_hint": asset_type_hint,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="국내 ETF 정보 조회 (funetf.co.kr)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python lookup_funetf.py --isin KR7069500007
  python lookup_funetf.py --ticker 069500
  python lookup_funetf.py --batch KR7069500007 KR7379800004
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--isin", type=str, help="단일 ISIN으로 조회")
    group.add_argument("--ticker", type=str, help="6자리 티커로 조회 (ISIN 자동 생성)")
    group.add_argument("--batch", nargs="+", metavar="ISIN", help="복수 ISIN 일괄 조회")
    return parser.parse_args()


def main():
    args = parse_args()

    # ISIN 목록 구성
    isins = []
    if args.isin:
        isins = [args.isin.strip().upper()]
    elif args.ticker:
        try:
            isin = make_isin(args.ticker)
            _log(f"[ticker→isin] {args.ticker} → {isin}")
            isins = [isin]
        except ValueError as e:
            _log(f"[오류] {e}")
            output = {"results": [], "errors": [{"ticker": args.ticker, "error": str(e)}]}
            print(json.dumps(output, ensure_ascii=False, indent=2))
            sys.exit(1)
    elif args.batch:
        isins = [i.strip().upper() for i in args.batch]

    # ISIN 유효성 사전 검증 (경고만, 진행은 함)
    for isin in isins:
        if not validate_isin(isin):
            _log(f"[경고] ISIN 체크디짓 검증 실패: {isin} (계속 진행)")

    if not isins:
        output = {"results": [], "errors": []}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 브라우저 열고 조회
    results = []
    errors = []
    _log(f"\n=== funetf.co.kr ETF 조회 ({len(isins)}건) ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
        )
        page = context.new_page()

        for idx, isin in enumerate(isins):
            _log(f"\n[{idx + 1}/{len(isins)}] {isin}")
            try:
                result = lookup_single_etf(page, isin)
                results.append(result)
                _log(f"  => {result['name']} | {result['base_index']} | "
                     f"{result['risk_grade']}등급 | {result['asset_type_hint']}")
            except Exception as e:
                _log(f"  [오류] {isin}: {e}")
                errors.append({"isin": isin, "error": str(e)})

            # 다음 요청 전 딜레이 (마지막 건 제외)
            if idx < len(isins) - 1:
                _log("  [대기] 3초...")
                time.sleep(3)

        browser.close()

    # JSON 출력 (stdout)
    output = {"results": results, "errors": errors}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
