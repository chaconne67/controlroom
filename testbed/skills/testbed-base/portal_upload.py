# -*- coding: utf-8 -*-
"""RA Testbed 포털 문서 업로드 자동화 스크립트

사용법:
  uv run --with playwright portal_upload.py \
    --url "https://www.ratestbed.kr:7443/cop/bbs/forUpdate.do?nttId=XXX&algrthSn=YYY" \
    --file "/path/to/file.pdf" \
    --title "새 제목_20260313" \
    --content-append "2026-03-13 정기리밸런싱 반영" \
    [--dry-run]

출력 (JSON to stdout):
  {"status": "success", "message": "uploaded and submitted"}
  {"status": "error", "message": "...", "step": "login|delete|upload|fill|submit", "screenshot": "..."}
"""

import argparse
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Windows 콘솔 UTF-8 강제
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_env():
    """환경변수 로드 (~/.env 파일 지원)"""
    env_path = Path.home() / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def output_success(message: str):
    """성공 JSON 출력 후 exit 0"""
    print(json.dumps({"status": "success", "message": message}, ensure_ascii=False))
    sys.exit(0)


def output_error(message: str, step: str, page=None):
    """에러 JSON 출력 후 exit 1. 가능하면 스크린샷 첨부."""
    screenshot_path = None
    if page:
        try:
            fd, screenshot_path = tempfile.mkstemp(prefix="error_", suffix=".png", dir=tempfile.gettempdir())
            os.close(fd)
            page.screenshot(path=screenshot_path)
        except Exception:
            screenshot_path = None

    result = {"status": "error", "message": message, "step": step}
    if screenshot_path:
        result["screenshot"] = screenshot_path
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(1)


def log(msg: str):
    """stderr에 디버그 로그 (stdout은 JSON 전용)"""
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Portal automation steps
# ---------------------------------------------------------------------------

def step_login(page, portal_root: str, user_id: str, password: str):
    """Step 1: 포털 로그인"""
    log("[Step 1] 포털 로그인 시작")
    page.goto(portal_root, timeout=30000)
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    time.sleep(1)

    # 로그인 폼 채우기
    page.fill('input[name="userId"]', user_id)
    page.fill('input[name="userPw"]', password)
    page.click('input[type="submit"], button[type="submit"], .btn_login, a[onclick*="login"], #loginBtn')
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    time.sleep(2)
    log("[Step 1] 로그인 완료")


def step_navigate(page, url: str):
    """Step 2: forUpdate.do URL로 이동"""
    log(f"[Step 2] 수정 페이지 이동: {url}")
    page.goto(url, timeout=30000)
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    time.sleep(2)
    log("[Step 2] 수정 페이지 로딩 완료")


def step_delete_existing_file(page):
    """Step 3-4: 기존 첨부파일 삭제 (confirm 오버라이드 + dialog 리스너)"""
    log("[Step 3] window.confirm 오버라이드 및 dialog 리스너 등록")

    # Override window.confirm to always return true
    page.evaluate("window.confirm = () => true")

    # Register dialog listener for the "successfully deleted" alert
    page.once("dialog", lambda dialog: dialog.accept())

    log("[Step 4] 기존 파일 삭제 클릭")
    # Find and click the delete link/button for the existing file
    delete_selector = 'a[onclick*="fn_egov_deleteFile"], a[onclick*="deleteFile"], a[href*="deleteFile"], .file_del, a:has-text("삭제")'
    delete_el = page.query_selector(delete_selector)
    if delete_el:
        delete_el.click()
        # File deletion triggers a full page reload — wait for it
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        time.sleep(3)
        log("[Step 4] 파일 삭제 완료 (페이지 리로드됨)")
    else:
        log("[Step 4] 삭제할 기존 파일 없음 — 건너뜀")


def step_upload_file(page, file_path: str):
    """Step 5: 새 파일 업로드"""
    log(f"[Step 5] 파일 업로드: {file_path}")
    file_input = page.query_selector('input[type="file"]')
    if not file_input:
        raise RuntimeError("파일 업로드 input을 찾을 수 없음")
    file_input.set_input_files(file_path)
    time.sleep(2)
    log("[Step 5] 파일 업로드 완료")


def step_fill_form(page, title: str, content_append: str):
    """Step 6: 제목 및 내용 필드 채우기"""
    log("[Step 6] 폼 필드 채우기")

    # Fill title
    title_selector = 'input[name="nttSj"], input[name="title"], input#nttSj'
    title_el = page.query_selector(title_selector)
    if title_el:
        title_el.fill(title)
        log(f"  제목 설정: {title}")
    else:
        raise RuntimeError("제목 입력 필드를 찾을 수 없음")

    # Prepend content to existing content field
    content_selector = 'textarea[name="nttCn"], textarea[name="content"], textarea#nttCn'
    content_el = page.query_selector(content_selector)
    if content_el:
        existing_content = content_el.input_value()
        new_content = f"{content_append}\n{existing_content}" if existing_content else content_append
        content_el.fill(new_content)
        log(f"  내용 앞에 추가: {content_append}")
    else:
        raise RuntimeError("내용 입력 필드를 찾을 수 없음")

    log("[Step 6] 폼 채우기 완료")


def step_submit(page):
    """Step 7: 제출 버튼 클릭"""
    log("[Step 7] dialog 리스너 재등록 및 제출")

    # Re-register dialog listener (previous one died on page reload)
    page.evaluate("window.confirm = () => true")
    page.once("dialog", lambda dialog: dialog.accept())

    submit_selector = 'a[onclick*="fn_egov_update"], a[onclick*="update"], button[onclick*="update"], .btn_submit, a:has-text("수정"), input[value="수정"]'
    submit_el = page.query_selector(submit_selector)
    if not submit_el:
        raise RuntimeError("제출 버튼을 찾을 수 없음")

    submit_el.click()
    time.sleep(3)

    # Handle any additional dialog (e.g. "successfully updated" alert)
    # The dialog listener above should handle the first one; register another just in case
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass

    log("[Step 7] 제출 완료")


def get_form_state(page) -> dict:
    """dry-run용: 현재 폼 상태를 읽어서 반환"""
    state = {}

    title_selector = 'input[name="nttSj"], input[name="title"], input#nttSj'
    title_el = page.query_selector(title_selector)
    if title_el:
        state["title"] = title_el.input_value()

    content_selector = 'textarea[name="nttCn"], textarea[name="content"], textarea#nttCn'
    content_el = page.query_selector(content_selector)
    if content_el:
        state["content"] = content_el.input_value()

    file_input = page.query_selector('input[type="file"]')
    if file_input:
        state["file_input_present"] = True

    return state


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="RA Testbed 포털 문서 업로드 자동화",
    )
    parser.add_argument("--url", required=True,
                        help="forUpdate.do 직접 URL")
    parser.add_argument("--file", required=True,
                        help="업로드할 파일 경로")
    parser.add_argument("--title", required=True,
                        help="문서 제목")
    parser.add_argument("--content-append", required=True,
                        help="내용 필드 앞에 추가할 텍스트")
    parser.add_argument("--dry-run", action="store_true",
                        help="제출 건너뛰기 — 폼 상태만 JSON 출력")
    return parser.parse_args()


def main():
    args = parse_args()

    # 환경변수 로드
    load_env()
    user_id = os.environ.get("TESTBED_ID")
    password = os.environ.get("TESTBED_PW")
    if not user_id or not password:
        print(json.dumps({
            "status": "error",
            "message": "TESTBED_ID 또는 TESTBED_PW 환경변수가 설정되지 않음 (~/.env 확인)",
            "step": "login",
        }, ensure_ascii=False))
        sys.exit(1)

    # 파일 존재 확인
    file_path = os.path.abspath(args.file)
    if not os.path.isfile(file_path):
        print(json.dumps({
            "status": "error",
            "message": f"파일을 찾을 수 없음: {file_path}",
            "step": "upload",
        }, ensure_ascii=False))
        sys.exit(1)

    # 포털 루트 URL 추출
    from urllib.parse import urlparse
    parsed = urlparse(args.url)
    portal_root = f"{parsed.scheme}://{parsed.netloc}"

    page = None
    browser = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="ko-KR",
                ignore_https_errors=True,
            )
            page = context.new_page()

            # Step 1: Login
            try:
                step_login(page, portal_root, user_id, password)
            except Exception as e:
                output_error(f"로그인 실패: {e}", "login", page)

            # Step 2: Navigate to forUpdate page
            try:
                step_navigate(page, args.url)
            except Exception as e:
                output_error(f"수정 페이지 이동 실패: {e}", "navigate", page)

            # Steps 3-4: Delete existing file
            if args.dry_run:
                log("[Step 3-4] dry-run — 기존 파일 삭제 건너뜀")
            else:
                try:
                    step_delete_existing_file(page)
                except Exception as e:
                    output_error(f"파일 삭제 실패: {e}", "delete", page)

            # Step 5: Upload new file
            try:
                step_upload_file(page, file_path)
            except Exception as e:
                output_error(f"파일 업로드 실패: {e}", "upload", page)

            # Step 6: Fill form fields
            try:
                step_fill_form(page, args.title, args.content_append)
            except Exception as e:
                output_error(f"폼 채우기 실패: {e}", "fill", page)

            # Step 7: Submit (or dry-run)
            if args.dry_run:
                form_state = get_form_state(page)
                log("[dry-run] 제출 건너뜀")
                print(json.dumps({
                    "status": "dry_run",
                    "message": "제출 건너뜀 (dry-run 모드)",
                    "form_state": form_state,
                }, ensure_ascii=False))
                browser.close()
                sys.exit(0)

            try:
                step_submit(page)
            except Exception as e:
                output_error(f"제출 실패: {e}", "submit", page)

            browser.close()
            output_success("uploaded and submitted")

    except SystemExit:
        raise
    except Exception as e:
        output_error(f"예상치 못한 오류: {e}", "unknown", page)


if __name__ == "__main__":
    main()
