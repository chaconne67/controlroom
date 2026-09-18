# -*- coding: utf-8 -*-
"""
글로벌 레시피 종목 ISIN 조회 스크립트

사용법:
  python lookup_isin.py AAPL NVDA TSLA
  python lookup_isin.py --etf AGG TLT IEF
  python lookup_isin.py AAPL NVDA --etf AGG TLT
  python lookup_isin.py AAPL --compare US02079K1079
  python lookup_isin.py AAPL --no-verify --delay 5

조회 방법:
  - 주식: stockanalysis.com (ISIN Number 행 추출)
  - ETF: Google 검색 (Luhn 필터) → OpenFIGI 역검증
  - 검증: OpenFIGI (ISIN → 티커 역방향 매칭)
"""

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter

# Windows 콘솔 UTF-8 강제
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# ISIN 유효성 검증 (Luhn 체크디짓)
# ---------------------------------------------------------------------------

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


def filter_valid_isins(candidates: list[str]) -> list[str]:
    """ISIN 후보 목록에서 Luhn 유효한 것만 필터"""
    return [c for c in candidates if validate_isin(c)]


# ---------------------------------------------------------------------------
# 주식 ISIN 조회 — stockanalysis.com
# ---------------------------------------------------------------------------

def lookup_stock_isin(page, ticker: str) -> str | None:
    """stockanalysis.com에서 주식 ISIN 조회"""
    url_ticker = ticker.lower().replace("-", ".")
    url = f"https://stockanalysis.com/stocks/{url_ticker}/company/"
    print(f"  [stockanalysis] {url}")
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)

        isin = page.evaluate("""
            () => {
                const rows = document.querySelectorAll('tr');
                for (const row of rows) {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 2) {
                        const label = cells[0].textContent.trim();
                        if (label === 'ISIN Number') {
                            return cells[1].textContent.trim();
                        }
                    }
                }
                return null;
            }
        """)

        if isin and re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", isin):
            if validate_isin(isin):
                return isin
            else:
                print(f"  [stockanalysis] ISIN Luhn 검증 실패: {isin}")
                return isin  # 반환은 하되 경고
        else:
            print(f"  [stockanalysis] ISIN 셀 못 찾음 (결과: {isin})")

    except Exception as e:
        print(f"  [stockanalysis] 오류: {e}")
    return None


# ---------------------------------------------------------------------------
# ETF ISIN 조회 — Google 검색 + Luhn 필터
# ---------------------------------------------------------------------------

def lookup_etf_isin_google(page, ticker: str) -> str | None:
    """Google 검색으로 ETF ISIN 조회 (Luhn 필터 적용)"""
    query = f"{ticker} ETF ISIN"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    print(f"  [google] {url}")
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        body_text = page.inner_text("body")
        isin_pattern = r"[A-Z]{2}[A-Z0-9]{9}[0-9]"
        isins = re.findall(isin_pattern, body_text)

        if not isins:
            html = page.content()
            isins = re.findall(isin_pattern, html)

        isins = filter_valid_isins(isins)

        if not isins:
            print("  [google] Luhn 유효한 ISIN 없음")
            return None

        counts = Counter(isins)
        print(f"  [google] ISIN 후보 (Luhn 통과): {dict(counts.most_common(5))}")
        best_isin, _ = counts.most_common(1)[0]
        return best_isin

    except Exception as e:
        print(f"  [google] 오류: {e}")
    return None


# ---------------------------------------------------------------------------
# OpenFIGI 검증
# ---------------------------------------------------------------------------

def verify_isin_openfigi(isins_dict: dict) -> dict:
    """OpenFIGI로 ISIN → 티커 역방향 검증"""
    print("\n=== OpenFIGI 검증 ===")
    results = {}
    items = list(isins_dict.items())

    for i in range(0, len(items), 5):
        batch = items[i : i + 5]
        payload = [{"idType": "ID_ISIN", "idValue": isin} for _, isin in batch]

        req = urllib.request.Request(
            "https://api.openfigi.com/v3/mapping",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for (ticker, isin), result in zip(batch, data):
                figi_ticker = ""
                figi_name = ""
                if "data" in result:
                    for item in result["data"]:
                        if item.get("exchCode") in ("US",):
                            figi_ticker = item.get("ticker", "")
                            figi_name = item.get("name", "")
                            break
                    if not figi_ticker and result["data"]:
                        figi_ticker = result["data"][0].get("ticker", "")
                        figi_name = result["data"][0].get("name", "")

                t1 = ticker.replace("-", "/").upper()
                t2 = figi_ticker.replace("-", "/").upper()
                match = t1 == t2
                results[ticker] = {
                    "isin": isin,
                    "figi_ticker": figi_ticker,
                    "figi_name": figi_name,
                    "verified": match,
                }
                status = "OK" if match else "FAIL"
                print(f"  [{status}] {ticker} ({isin}) -> FIGI: {figi_ticker} ({figi_name})")
        except Exception as e:
            print(f"  OpenFIGI 오류: {e}")
            for ticker, isin in batch:
                results[ticker] = {
                    "isin": isin,
                    "figi_ticker": "",
                    "figi_name": "",
                    "verified": None,
                }

        if i + 5 < len(items):
            time.sleep(2)

    return results


# ---------------------------------------------------------------------------
# 외부 호출용 API
# ---------------------------------------------------------------------------

def lookup_isin(ticker: str, is_etf: bool = False, delay: int = 15) -> dict:
    """단일 종목 ISIN 조회."""
    result = {"ticker": ticker, "isin": None, "source": None}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        if is_etf:
            isin = lookup_etf_isin_google(page, ticker)
            if isin:
                result["isin"], result["source"] = isin, "google"
        else:
            isin = lookup_stock_isin(page, ticker)
            if isin:
                result["isin"], result["source"] = isin, "stockanalysis"

        browser.close()

    return result


def lookup_isins_batch(tickers: list[str], etf_tickers: set[str] = None,
                       delay: int = 15, verify: bool = True) -> dict:
    """복수 종목 ISIN 일괄 조회. 브라우저 1회 오픈."""
    if etf_tickers is None:
        etf_tickers = set()

    found_isins = {}
    sources = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        for idx, ticker in enumerate(tickers):
            is_etf = ticker in etf_tickers
            print(f"\n[{idx+1}/{len(tickers)}] {ticker} ({'ETF' if is_etf else '주식'})")

            isin = None
            source = None

            if is_etf:
                isin = lookup_etf_isin_google(page, ticker)
                source = "google"
            else:
                isin = lookup_stock_isin(page, ticker)
                source = "stockanalysis"

            if isin:
                found_isins[ticker] = isin
                sources[ticker] = source
                print(f"  => ISIN: {isin} (via {source})")
            else:
                sources[ticker] = None
                print("  => ISIN 찾지 못함!")

            if idx < len(tickers) - 1:
                time.sleep(delay)

        browser.close()

    # OpenFIGI 역검증 (특히 ETF는 Google 결과를 검증)
    verification = {}
    if verify and found_isins:
        verification = verify_isin_openfigi(found_isins)

    results = {}
    for ticker in tickers:
        v = verification.get(ticker, {})
        results[ticker] = {
            "isin": found_isins.get(ticker),
            "source": sources.get(ticker),
            "figi_ticker": v.get("figi_ticker"),
            "figi_name": v.get("figi_name"),
            "verified": v.get("verified"),
        }

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="글로벌 레시피 종목 ISIN 조회",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python lookup_isin.py AAPL NVDA TSLA
  python lookup_isin.py --etf AGG TLT IEF
  python lookup_isin.py AAPL NVDA --etf AGG TLT
  python lookup_isin.py AAPL --compare US02079K1079
  python lookup_isin.py AAPL --no-verify --delay 5
        """,
    )
    parser.add_argument("tickers", nargs="*", help="조회할 주식 티커")
    parser.add_argument("--etf", nargs="*", default=[], metavar="TICKER",
                        help="ETF로 조회할 티커")
    parser.add_argument("--compare", nargs="*", default=[], metavar="ISIN",
                        help="기존 ISIN과 비교 (티커 순서와 1:1 대응)")
    parser.add_argument("--no-verify", action="store_true",
                        help="OpenFIGI 검증 스킵")
    parser.add_argument("--delay", type=int, default=15,
                        help="요청 간 딜레이 초 (기본: 15)")
    parser.add_argument("--output", "-o", metavar="FILE",
                        help="결과 JSON 저장 경로")
    return parser.parse_args()


def main():
    args = parse_args()

    stock_tickers = args.tickers or []
    etf_tickers = args.etf or []
    all_tickers = stock_tickers + etf_tickers

    if not all_tickers:
        print("오류: 조회할 티커를 입력하세요.")
        print("  python lookup_isin.py AAPL NVDA --etf AGG TLT")
        sys.exit(1)

    compare_isins = {}
    if args.compare:
        for ticker, isin in zip(all_tickers, args.compare):
            compare_isins[ticker] = isin

    print("=" * 70)
    print("글로벌 레시피 종목 ISIN 조회")
    print(f"  주식: {stock_tickers or '(없음)'}")
    print(f"  ETF:  {etf_tickers or '(없음)'}")
    print(f"  딜레이: {args.delay}초, 검증: {'OFF' if args.no_verify else 'ON'}")
    print("=" * 70)

    results = lookup_isins_batch(
        tickers=all_tickers,
        etf_tickers=set(etf_tickers),
        delay=args.delay,
        verify=not args.no_verify,
    )

    # 결과 출력
    print("\n" + "=" * 70)
    print("결과")
    print("=" * 70)
    header = f"{'Ticker':8s} {'ISIN':14s} {'Source':15s} {'FIGI':6s} {'FIGI Ticker':12s} FIGI Name"
    print(header)
    print("-" * 90)

    for ticker in all_tickers:
        r = results[ticker]
        isin = r["isin"] or "NOT_FOUND"
        source = r["source"] or "-"
        verified = "OK" if r.get("verified") else ("FAIL" if r.get("verified") is False else "-")
        figi_t = r.get("figi_ticker") or ""
        figi_n = r.get("figi_name") or ""
        print(f"{ticker:8s} {isin:14s} {source:15s} {verified:6s} {figi_t:12s} {figi_n}")

    if compare_isins:
        print("\n--- 기존 ISIN 비교 ---")
        mismatches = []
        for ticker in all_tickers:
            old = compare_isins.get(ticker)
            new = results[ticker]["isin"]
            if old and new:
                status = "동일" if old == new else "불일치"
                print(f"  {ticker}: {old} -> {new} [{status}]")
                if old != new:
                    mismatches.append((ticker, old, new))
        if mismatches:
            print(f"\n** {len(mismatches)}건 불일치!")

    # JSON 저장
    output = {
        "lookup_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }
    output_path = args.output
    if not output_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "isin_lookup_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_path}")


if __name__ == "__main__":
    main()
