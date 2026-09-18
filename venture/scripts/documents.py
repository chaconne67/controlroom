from __future__ import annotations

import re
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import olefile
from lxml import etree
from pypdf import PdfReader


HWP5_OLE_MAGIC = bytes.fromhex("D0 CF 11 E0 A1 B1 1A E1")
HWP_BODY_TEXT_TAG = 67
SUPPORTED_SUFFIXES = {".hwp", ".hwpx", ".pdf", ".pptx", ".txt", ".md"}


class DocumentReadError(RuntimeError):
    """Raised when a document cannot be converted to useful text."""


@dataclass(frozen=True)
class ExtractedDocument:
    path: Path
    kind: str
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


def extract_text(path: str | Path) -> ExtractedDocument:
    """Extract readable text from a local document.

    The venture application workflow mostly needs text from Korean application
    materials. This function supports HWP/HWPX first, with PDF and plain text as
    useful companions for the same raw material folder.
    """

    document_path = Path(path)
    if not document_path.exists():
        raise DocumentReadError(f"File not found: {document_path}")

    suffix = document_path.suffix.lower()
    if suffix == ".hwp":
        text = extract_hwp_text(document_path)
        return ExtractedDocument(document_path, "hwp", text)
    if suffix == ".hwpx":
        text = extract_hwpx_text(document_path)
        return ExtractedDocument(document_path, "hwpx", text)
    if suffix == ".pdf":
        text = extract_pdf_text(document_path)
        return ExtractedDocument(document_path, "pdf", text)
    if suffix == ".pptx":
        text = extract_pptx_text(document_path)
        return ExtractedDocument(document_path, "pptx", text)
    if suffix in {".txt", ".md"}:
        text = document_path.read_text(encoding="utf-8-sig")
        return ExtractedDocument(document_path, suffix.lstrip("."), clean_text(text))

    raise DocumentReadError(f"Unsupported document format: {suffix or '(none)'}")


def extract_hwp_text(path: str | Path) -> str:
    """Extract paragraph text from an HWP 5 OLE document."""

    document_path = Path(path)
    with document_path.open("rb") as fp:
        magic = fp.read(8)
    if magic != HWP5_OLE_MAGIC:
        raise DocumentReadError("Not an OLE-based HWP file")

    try:
        with olefile.OleFileIO(str(document_path)) as ole:
            if not ole.exists("FileHeader"):
                raise DocumentReadError("Missing HWP FileHeader stream")

            compressed = _is_hwp_compressed(ole)
            sections = sorted(_hwp_body_sections(ole), key=_section_sort_key)
            if not sections:
                raise DocumentReadError("Missing HWP BodyText sections")

            chunks: list[str] = []
            for section in sections:
                raw = ole.openstream(section).read()
                data = _decompress_hwp_stream(raw) if compressed else raw
                chunks.extend(_iter_hwp_text_records(data))
    except OSError as exc:
        raise DocumentReadError(f"Cannot open HWP document: {exc}") from exc
    except zlib.error as exc:
        raise DocumentReadError(f"Cannot decompress HWP section: {exc}") from exc

    text = clean_text("\n".join(chunks))
    if not text:
        raise DocumentReadError("No readable text found in HWP document")
    return text


def extract_hwpx_text(path: str | Path) -> str:
    """Extract text from an HWPX zip/XML document."""

    document_path = Path(path)
    if not zipfile.is_zipfile(document_path):
        raise DocumentReadError("Not a ZIP-based HWPX file")

    chunks: list[str] = []
    with zipfile.ZipFile(document_path) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith(".xml"))
        section_names = [name for name in names if "section" in Path(name).name.lower()]
        for name in section_names or names:
            xml = archive.read(name)
            chunks.extend(_extract_xml_text(xml))

    text = clean_text("\n".join(chunks))
    if not text:
        raise DocumentReadError("No readable text found in HWPX document")
    return text


def extract_pptx_text(path: str | Path) -> str:
    """Extract slide text from a PPTX zip/XML document."""

    document_path = Path(path)
    if not zipfile.is_zipfile(document_path):
        raise DocumentReadError("Not a ZIP-based PPTX file")

    chunks: list[str] = []
    with zipfile.ZipFile(document_path) as archive:
        slides = [
            name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        ]
        for name in sorted(slides, key=lambda item: int(re.findall(r"(\d+)\.xml$", item)[0])):
            chunks.extend(_extract_xml_text(archive.read(name)))
            chunks.append("")

    text = clean_text("\n".join(chunks))
    if not text:
        raise DocumentReadError("No readable text found in PPTX document")
    return text


def extract_pdf_text(path: str | Path) -> str:
    reader = PdfReader(str(path))
    chunks = [page.extract_text() or "" for page in reader.pages]
    text = clean_text("\n".join(chunks))
    if not text:
        raise DocumentReadError("No readable text found in PDF document")
    return text


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = "".join(ch for ch in text if not _looks_like_ascii_control_artifact(ch))
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]

    cleaned: list[str] = []
    previous = None
    for line in lines:
        if not line:
            if cleaned and cleaned[-1]:
                cleaned.append("")
            continue
        if line == previous:
            continue
        cleaned.append(line)
        previous = line

    return "\n".join(cleaned).strip()


def _looks_like_ascii_control_artifact(ch: str) -> bool:
    """Detect HWP control bytes that were decoded as a CJK code point.

    Some paragraph payloads contain compact control markers before the visible
    text. If those bytes are decoded as UTF-16LE, pairs of ASCII bytes can become
    rare CJK characters such as U+6364. Real Korean/Hanja text does not have both
    bytes in the printable ASCII range, so this keeps normal Korean text intact.
    """

    codepoint = ord(ch)
    if not 0x4E00 <= codepoint <= 0x9FFF:
        return False
    low = codepoint & 0xFF
    high = codepoint >> 8
    return 0x20 <= low <= 0x7E and 0x20 <= high <= 0x7E


def _is_hwp_compressed(ole: olefile.OleFileIO) -> bool:
    header = ole.openstream("FileHeader").read()
    if len(header) < 40:
        raise DocumentReadError("HWP FileHeader is too short")
    flags = int.from_bytes(header[36:40], "little")
    return bool(flags & 0x01)


def _hwp_body_sections(ole: olefile.OleFileIO) -> Iterable[list[str]]:
    for entry in ole.listdir(streams=True, storages=False):
        if len(entry) == 2 and entry[0] == "BodyText" and entry[1].startswith("Section"):
            yield entry


def _section_sort_key(entry: list[str]) -> tuple[int, str]:
    name = entry[-1]
    match = re.search(r"(\d+)$", name)
    return (int(match.group(1)) if match else 0, name)


def _decompress_hwp_stream(data: bytes) -> bytes:
    return zlib.decompress(data, -15)


def _iter_hwp_text_records(data: bytes) -> Iterable[str]:
    offset = 0
    size = len(data)
    while offset + 4 <= size:
        header = int.from_bytes(data[offset : offset + 4], "little")
        offset += 4

        tag = header & 0x3FF
        payload_size = (header >> 20) & 0xFFF
        if payload_size == 0xFFF:
            if offset + 4 > size:
                break
            payload_size = int.from_bytes(data[offset : offset + 4], "little")
            offset += 4

        payload = data[offset : offset + payload_size]
        offset += payload_size
        if tag == HWP_BODY_TEXT_TAG and payload:
            text = payload.decode("utf-16le", errors="ignore")
            text = text.replace("\u2028", "\n")
            if text.strip():
                yield text


def _extract_xml_text(xml: bytes) -> list[str]:
    parser = etree.XMLParser(recover=True, resolve_entities=False, no_network=True)
    root = etree.fromstring(xml, parser=parser)

    preferred: list[str] = []
    for element in root.iter():
        local_name = etree.QName(element).localname.lower()
        if local_name in {"t", "text"} and element.text:
            preferred.append(element.text)
    if preferred:
        return preferred

    return [piece for piece in root.itertext() if piece and piece.strip()]
