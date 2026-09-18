# -*- coding: utf-8 -*-
"""
국내 ETF 정보 조회 스크립트 (funetf.co.kr)

사용법:
  python lookup_funetf.py --isin KR7069500007
  python lookup_funetf.py --ticker 069500
  python lookup_funetf.py --batch KR7069500007,KR7379800004
  python lookup_funetf.py --batch KR7069500007,KR7379800004 --output lookup_batch_1.jsonl

출력: JSON (stdout), 진행상황은 stderr로 출력
--output 지정 시: 종목 1건 조회 완료마다 JSONL 파일에 즉시 append (데이터 유실 방지)
"""

import argparse
import io
import json
import os
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
    if len(ticker) != 6 or not ticker.isalnum():
        raise ValueError(f"티커는 6자리 영숫자여야 합니다: {ticker}")
    partial = f"KR7{ticker}00"  # 11자
    cd = _luhn_checkdigit(partial)
    isin = partial + cd
    return isin



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
                            risk_score, is_risk_asset
    Raises Exception on failure.
    """
    url = f"https://www.funetf.co.kr/product/etf/view/{isin}"
    _log(f"  [funetf] {url}")

    page.goto(url, timeout=30000)
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    # SPA 렌더링 대기 — 실제 컨텐츠가 body에 채워질 때까지 (초기 스켈레톤은 ~1KB)
    # '등급' 또는 '운용사' 키워드가 나오면 데이터 렌더링 완료로 판단
    try:
        page.wait_for_function(
            "() => { const t = document.body.innerText; return t.includes('등급') || t.includes('운용사') || t.length > 3000; }",
            timeout=30000,
        )
    except Exception:
        _log("  [렌더대기] 30초 초과 — 현재 상태로 진행")
    time.sleep(1)

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

    # --- 배지 추출 (개인/퇴직/자산유형/스타일 라벨) ---
    # body 텍스트에서 'ETF 상세\n{ticker}\n' 다음에 여러 배지가 한 줄씩 나열된다.
    # 티커는 ISIN의 4~9번째 자리 (KR7{6자리}00{check}).
    badges: list[str] = []
    try:
        ticker6 = isin[3:9] if isin.startswith("KR7") and len(isin) >= 9 else ""
        body_text = page.inner_text("body", timeout=3000)
        # '465580\n' 직후부터 첫 빈줄 전까지의 라인을 배지 후보로
        if ticker6 and ticker6 in body_text:
            after = body_text.split(ticker6, 1)[1]
            # 최대 12줄만 훑는다 (배지는 보통 5개 이내)
            collected: list[str] = []
            for raw in after.split("\n")[:15]:
                line = raw.strip()
                if not line:
                    if collected:
                        break
                    continue
                # 배지 조건: 짧고(2~10자), 종목명/수치/날짜가 아님
                if len(line) > 12:
                    break
                if any(ch.isdigit() for ch in line):
                    break
                # 알려진 배지/라벨 키워드 외에도 한글 단어면 수집
                collected.append(line)
                if len(collected) >= 8:
                    break
            badges = collected
    except Exception as e:
        _log(f"  [배지] 추출 오류: {e}")
    _log(f"  [배지] {badges}")

    # --- 계산 필드 ---
    risk_score = (7 - risk_grade) if risk_grade is not None else None
    is_risk_asset = "Y" if (risk_grade is not None and risk_grade <= 3) else (
        "N" if risk_grade is not None else None
    )
    # 빈 데이터 검증: 종목명과 위험등급이 모두 비어있으면 사이트 구조 변경 의심
    if not name and risk_grade is None:
        raise Exception(
            f"종목명·위험등급 모두 추출 실패 (ISIN: {isin}). "
            f"funetf.co.kr 페이지 구조가 변경되었을 수 있습니다."
        )

    return {
        "isin": isin,
        "name": name,
        "base_index": base_index,
        "risk_grade": risk_grade,
        "risk_grade_name": risk_grade_name,
        "risk_score": risk_score,
        "is_risk_asset": is_risk_asset,
        "badges": badges,
    }


# ---------------------------------------------------------------------------
# JSONL merge → universe.json lookup 업데이트
# ---------------------------------------------------------------------------

def merge_lookup_jsonl(universe_path: str, jsonl_paths: list[str]):
    """JSONL 파일들을 읽어 universe.json의 lookup 필드를 업데이트한다.

    1. JSONL 파일들에서 결과를 읽어 ISIN→데이터 매핑 생성
    2. universe.json의 각 item.lookup을 채움
    3. 무결성 검증: universe.json의 모든 ISIN이 조회 결과에 존재하는지 확인
    Args:
        universe_path: universe.json 파일 경로
        jsonl_paths: JSONL 파일 경로 리스트

    Returns:
        dict: {"updated": int, "missing": list[str], "errors": list[str], "cleaned": list[str]}
    """
    # 1. JSONL 파일들에서 결과 수집
    lookup_map = {}  # isin → result dict
    error_isins = []
    missing_files = []
    for path in jsonl_paths:
        if not os.path.exists(path):
            _log(f"[경고] JSONL 결과 파일 미존재: {path}")
            missing_files.append(path)
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    _log(f"[경고] {path}:{line_num} JSON 파싱 실패: {e}")
                    continue
                if obj.get("_error"):
                    error_isins.append(obj.get("isin", "unknown"))
                else:
                    lookup_map[obj["isin"]] = obj
    if missing_files:
        _log(f"[경고] {len(missing_files)}개 JSONL 파일 누락. 존재하는 파일의 결과만 처리합니다.")

    # 2. universe.json 로드 & lookup 채움
    with open(universe_path, "r", encoding="utf-8") as f:
        universe = json.load(f)

    # ticker → ISIN 역매핑 (current.isin이 null인 종목을 위한 폴백)
    ticker_to_isin = {}
    for map_isin, data in lookup_map.items():
        # JSONL 결과에 원본 ticker 정보가 없으므로 ISIN에서 역추출
        ticker_to_isin[map_isin] = data

    updated = 0
    missing = []
    for item in universe["items"]:
        isin = item["current"]["isin"]
        # current.isin이 null/빈값이면 ticker로 ISIN을 생성하여 매칭 시도
        if not isin and item.get("ticker"):
            try:
                isin = make_isin(item["ticker"])
            except (ValueError, Exception):
                pass
        if isin and isin in lookup_map:
            result = lookup_map[isin]
            item["lookup"] = {
                "isin": result["isin"],
                "name": result["name"],
                "base_index": result["base_index"],
                "risk_grade": result["risk_grade"],
                "risk_grade_name": result["risk_grade_name"],
                "risk_score": result["risk_score"],
                "is_risk_asset": result["is_risk_asset"],
                "badges": result.get("badges", []),
            }
            updated += 1
        else:
            missing.append(isin)

    # 3. 무결성 검증
    total = len(universe["items"])
    _log(f"[merge] {updated}/{total} 종목 lookup 업데이트 완료")
    if missing:
        _log(f"[merge] 미조회 {len(missing)}건: {missing}")
    if error_isins:
        _log(f"[merge] 조회 에러 {len(error_isins)}건: {error_isins}")

    # 4. universe.json 저장
    with open(universe_path, "w", encoding="utf-8") as f:
        json.dump(universe, f, ensure_ascii=False, indent=2)
    _log(f"[merge] universe.json 저장 완료")

    return {"updated": updated, "missing": missing, "errors": error_isins, "cleaned": []}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="국내 ETF 정보 조회 (funetf.co.kr)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 조회
  python lookup_funetf.py --isin KR7069500007
  python lookup_funetf.py --ticker 069500
  python lookup_funetf.py --batch KR7069500007,KR7379800004 --output lookup_batch_1.jsonl

  # JSONL merge → universe.json lookup 업데이트 (입력 JSONL 보존)
  python lookup_funetf.py --merge universe.json lookup_batch_*.jsonl
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--isin", type=str, help="단일 ISIN으로 조회")
    group.add_argument("--ticker", type=str, help="6자리 티커로 조회 (ISIN 자동 생성)")
    group.add_argument("--batch", type=str, metavar="ISIN,ISIN,...", help="복수 ISIN 일괄 조회 (쉼표 구분)")
    group.add_argument("--merge", type=str, nargs="+", metavar="FILE",
                        help="JSONL merge 모드. 첫 인자: universe.json, 나머지: JSONL 파일들")
    parser.add_argument("--output", type=str, metavar="FILE",
                        help="JSONL 출력 파일. 종목 1건 조회마다 즉시 append (데이터 유실 방지)")
    return parser.parse_args()


def main():
    args = parse_args()

    # --merge 모드: JSONL → universe.json lookup 업데이트
    if args.merge:
        if len(args.merge) < 2:
            _log("[오류] --merge는 최소 2개 인자 필요: universe.json + JSONL 파일(들)")
            sys.exit(1)
        universe_path = args.merge[0]
        jsonl_paths = args.merge[1:]
        result = merge_lookup_jsonl(universe_path, jsonl_paths)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if not result["missing"] and not result["errors"] else 1)

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
        isins = [i.strip().upper() for i in args.batch.split(",") if i.strip()]

    # ISIN 유효성 사전 검증 (경고만, 진행은 함)
    for isin in isins:
        if not validate_isin(isin):
            _log(f"[경고] ISIN 체크디짓 검증 실패: {isin} (계속 진행)")

    if not isins:
        _log("[오류] 조회할 ISIN이 없습니다. 입력값을 확인하세요.")
        output = {"results": [], "errors": [{"error": "빈 ISIN 목록"}]}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(1)

    # --output 파일 준비 (JSONL incremental write)
    output_file = None
    if args.output:
        output_file = os.path.abspath(args.output)
        # 기존 파일이 있으면 덮어쓰기 (새 실행)
        with open(output_file, "w", encoding="utf-8") as f:
            pass  # truncate
        _log(f"[output] JSONL 파일: {output_file}")

    # 브라우저 열고 조회
    results = []
    errors = []
    _log(f"\n=== funetf.co.kr ETF 조회 ({len(isins)}건) ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
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
                     f"{result['risk_grade']}등급")
                # JSONL 즉시 append
                if output_file:
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(result, ensure_ascii=False) + "\n")
                        f.flush()
            except Exception as e:
                _log(f"  [오류] {isin}: {e}")
                err = {"isin": isin, "error": str(e)}
                errors.append(err)
                # 에러도 JSONL에 기록 (_error 플래그로 구분)
                if output_file:
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"_error": True, **err}, ensure_ascii=False) + "\n")
                        f.flush()

            # 다음 요청 전 딜레이 (마지막 건 제외)
            if idx < len(isins) - 1:
                _log("  [대기] 3초...")
                time.sleep(3)

        browser.close()

    # JSON 출력 (stdout) — 기존 호환성 유지
    output = {"results": results, "errors": errors}
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
