from pathlib import Path
from zipfile import ZipFile

import pytest

from documents import extract_text


ROOT = Path(__file__).resolve().parents[1]

# 회사 폴더명은 V<YYMMDD>-<한글회사명> 형식이라 날짜가 바뀔 수 있으므로 파일명으로 찾는다.
HWP_FIXTURE = next(ROOT.glob("companies/**/출원-LED전광판-COB모듈.hwp"), None)


@pytest.mark.skipif(HWP_FIXTURE is None, reason="hwp 원본 자료가 없는 작업공간")
def test_extract_hwp_patent_text() -> None:
    document = extract_text(HWP_FIXTURE)

    assert document.kind == "hwp"
    assert "LED 전광판" in document.text
    assert "발명의 명칭" in document.text
    assert document.char_count > 1000


def test_extract_markdown_text() -> None:
    document = extract_text(ROOT / "docs" / "한글파일-포맷-처리-정리.md")

    assert document.kind == "md"
    assert "한글파일 포맷 처리 정리" in document.text


def test_extract_pptx_text_in_numeric_slide_order(tmp_path: Path) -> None:
    fixture = tmp_path / "slides.pptx"
    with ZipFile(fixture, "w") as archive:
        archive.writestr(
            "ppt/slides/slide10.xml",
            '<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><a:t>열 번째 슬라이드</a:t></p:sld>',
        )
        archive.writestr(
            "ppt/slides/slide2.xml",
            '<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><a:t>두 번째 슬라이드</a:t></p:sld>',
        )

    document = extract_text(fixture)

    assert document.kind == "pptx"
    assert document.text.index("두 번째 슬라이드") < document.text.index("열 번째 슬라이드")
