"""HTML/CSS 기반 PDF 렌더러 (algo-report v2).

shapes_manifest.json (슬라이드 1-2) + components.json (슬라이드 3+) → HTML → PDF

사용법:
    python render_pdf.py render_input_v2.json

입력 JSON:
    {
      "manifest_path": "shapes_manifest.json",
      "components_path": "components.json",
      "output_path": "output_v2.pdf",
      "work_dir": "C:/Users/chaconne/tmp"
    }
"""
import sys, json, os, html, re, asyncio
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


# ═══════════════════════════════════════════════════════════════════
# manifest → 커버 컴포넌트 변환
# ═══════════════════════════════════════════════════════════════════

def _parse_paragraphs(paragraphs):
    """manifest paragraphs → 컴포넌트 리스트."""
    components = []
    i = 0
    is_first = True
    while i < len(paragraphs):
        p = paragraphs[i]
        text = p.get('text', '').strip()
        i += 1

        if not text:
            is_first = False
            continue

        is_bold = p.get('bold', False)
        font_size = p.get('font_size', 0)

        # 타이틀 (첫 유효 단락, 중앙 정렬 또는 큰 사이즈)
        if is_first and (p.get('align') in ('ctr', 'r') or not is_bold):
            components.append({'type': 'title', 'text': text})
            is_first = False
            continue
        is_first = False

        if is_bold and font_size:
            if font_size >= 14:
                components.append({'type': 'heading', 'level': 'section', 'text': text})
            elif font_size >= 12:
                components.append({'type': 'heading', 'level': 'subsection', 'text': text})
            elif font_size >= 11:
                clean = re.sub(r'[\uf09f\uf0d8]\s*', '• ', text)
                if clean.startswith('['):
                    steps = []
                    bracket_text = text
                    desc_text = ''
                    if i < len(paragraphs):
                        desc_text = paragraphs[i].get('text', '').strip()
                        i += 1
                    steps.append({'label': bracket_text, 'desc': desc_text})
                    while i < len(paragraphs):
                        next_text = paragraphs[i].get('text', '').strip()
                        if next_text.startswith('['):
                            label = next_text
                            desc = ''
                            i += 1
                            if i < len(paragraphs):
                                desc = paragraphs[i].get('text', '').strip()
                                i += 1
                            steps.append({'label': label, 'desc': desc})
                        else:
                            break
                    components.append({'type': 'step_list', 'steps': steps})
                else:
                    components.append({'type': 'heading', 'level': 'sub_heading', 'text': clean})
            continue

        if text.startswith('Step'):
            components.append({'type': 'text', 'lines': [text]})
            continue

        if text.startswith('- '):
            lines = [text]
            while i < len(paragraphs):
                next_text = paragraphs[i].get('text', '').strip()
                if next_text.startswith('- '):
                    lines.append(next_text)
                    i += 1
                else:
                    break
            components.append({'type': 'text', 'lines': lines})
            continue

    return components


def _collect_group_elements(group_shape):
    """그룹 shape에서 위치 정보 포함한 전체 요소 수집 (재귀)."""
    elements = []
    for child in group_shape.get('children', []):
        if child.get('type') == 'group':
            elements.extend(_collect_group_elements(child))
        else:
            text = ''
            if 'text' in child and child['text'].get('content'):
                text = child['text']['content'].strip()
            pos = child['position']
            elements.append({
                'text': text,
                'left': pos['left'],
                'top': pos['top'],
                'width': pos['width'],
                'height': pos['height'],
                'name': child.get('name', ''),
            })
    return elements


def _build_structured_diagram(group_shape):
    """그룹 shape → 구조화된 다이어그램 데이터 (행 분리, 관계 추론)."""
    elements = _collect_group_elements(group_shape)
    # 텍스트 없는 요소 제거 (화살표 등은 위치만 참고)
    text_els = [e for e in elements if e['text']]
    if not text_els:
        return None

    # top 기준 행 그룹핑 (tolerance: 높이의 30%)
    text_els.sort(key=lambda e: e['top'])
    rows = []
    cur_row = [text_els[0]]
    for e in text_els[1:]:
        if abs(e['top'] - cur_row[0]['top']) < cur_row[0]['height'] * 0.5:
            cur_row.append(e)
        else:
            rows.append(sorted(cur_row, key=lambda x: x['left']))
            cur_row = [e]
    rows.append(sorted(cur_row, key=lambda x: x['left']))

    return rows


def build_cover_components(manifest_path):
    """shapes_manifest.json 슬라이드 1-2에서 커버 컴포넌트 생성."""
    with open(manifest_path, encoding='utf-8') as f:
        mf = json.load(f)

    slides = mf.get('slides', [])
    if len(slides) < 2:
        return []

    components = []

    # ── 슬라이드 1 ──
    slide1 = slides[0]
    textbox_shape = None
    table_shape = None
    group_shapes = []

    for shape in slide1['shapes']:
        if shape['type'] == 'textbox':
            textbox_shape = shape
        elif shape['type'] == 'table':
            table_shape = shape
        elif shape['type'] == 'group':
            group_shapes.append(shape)

    if textbox_shape and 'text' in textbox_shape:
        paras = textbox_shape['text'].get('paragraphs', [])
        components.extend(_parse_paragraphs(paras))

    if table_shape and 'table' in table_shape:
        tbl = table_shape['table']
        rows = []
        for row in tbl['rows']:
            cells = []
            for ci, cell in enumerate(row['cells']):
                v = cell.get('v', '').replace('\xa0', ' ').strip()
                s = 'H' if ci == 0 else 'V'
                cells.append({'v': v, 's': s, 'algn': 'l'})
            rows.append({'cells': cells})

        insert_idx = None
        for idx, c in enumerate(components):
            if c.get('type') == 'heading' and c.get('level') == 'subsection':
                insert_idx = idx + 1
                break

        table_comp = {
            'type': 'table',
            'rows': rows,
            'col_widths_cm': tbl.get('col_widths_cm', []),
        }
        if insert_idx is not None:
            components.insert(insert_idx, table_comp)
        else:
            components.append(table_comp)

    group_shapes.sort(key=lambda s: s['position']['top'])
    for gs in group_shapes:
        rows = _build_structured_diagram(gs)
        if rows:
            components.append({
                'type': 'diagram',
                'rows': [[{'text': e['text'], 'height': e['height']}
                          for e in row] for row in rows],
            })

    # ── 슬라이드 2 ──
    slide2 = slides[1]
    for shape in slide2['shapes']:
        if shape['type'] != 'textbox' or 'text' not in shape:
            continue
        paras = shape['text'].get('paragraphs', [])
        components.extend(_parse_paragraphs(paras))

    return components


# ═══════════════════════════════════════════════════════════════════
# HTML 생성
# ═══════════════════════════════════════════════════════════════════

CSS = r"""
@page {
  size: A4 portrait;
  margin: 15mm 18mm 15mm 18mm;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
  font-size: 10pt;
  line-height: 1.5;
  color: #111;
}

/* ── 타이틀 ── */
.doc-title {
  font-size: 16pt;
  font-weight: bold;
  text-align: center;
  margin-bottom: 12pt;
  padding: 8pt 0;
}

/* ── 섹션 heading ── */
.heading-section {
  font-size: 14pt;
  font-weight: bold;
  margin-top: 18pt;
  margin-bottom: 6pt;
  padding-bottom: 3pt;
  border-bottom: 2px solid #333;
  break-after: avoid;
}

.heading-subsection {
  font-size: 12pt;
  font-weight: bold;
  margin-top: 14pt;
  margin-bottom: 5pt;
  break-after: avoid;
}

.heading-note {
  font-size: 10pt;
  font-weight: normal;
  margin-top: 10pt;
  margin-bottom: 4pt;
  break-after: avoid;
}

.heading-sub_heading {
  font-size: 11pt;
  font-weight: bold;
  margin-top: 10pt;
  margin-bottom: 4pt;
  break-after: avoid;
}

/* ── 텍스트 블록 ── */
.text-block {
  margin-top: 4pt;
  margin-bottom: 8pt;
  font-size: 10pt;
  line-height: 1.6;
}
.text-block p {
  margin-bottom: 2pt;
}
.text-block p.empty-line {
  height: 6pt;
}
.footnote {
  font-size: 9pt;
  color: #555;
  margin-top: 4pt;
  margin-bottom: 4pt;
}

/* ── 테이블 ── */
table.data-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 4pt;
  margin-bottom: 10pt;
  font-size: 10pt;
  break-inside: auto;
}
table.data-table thead {
  display: table-header-group;
}
table.data-table tr {
  break-inside: avoid;
}
table.data-table th,
table.data-table td {
  border: 1px solid #999;
  padding: 4pt 6pt;
  text-align: center;
  vertical-align: middle;
  min-height: 24pt;
}
table.data-table th {
  background: #d9d9d9;
  font-weight: bold;
  color: #111;
}
td.cell-R {
  background: #cc0000;
  color: #fff;
  font-weight: bold;
}
td.align-left,
th.align-left {
  text-align: left;
}

/* ── 다이어그램 (Graphviz SVG) ── */
.diagram-container {
  margin: 8pt 0 12pt 0;
  text-align: center;
}
.diagram-container svg {
  max-width: 100%;
  height: auto;
}

/* ── 단계 리스트 ── */
.step-list {
  margin: 6pt 0 10pt 0;
  font-size: 10pt;
}
.step-list .step-item {
  margin-bottom: 3pt;
}
.step-list .step-label {
  font-weight: bold;
}
.step-list .step-desc {
  margin-left: 8pt;
  color: #333;
}

/* ── 첫 컴포넌트 여백 제거 ── */
.content-body > :first-child {
  margin-top: 0;
}
"""


def _esc(text):
    """HTML 이스케이프 + 줄바꿈 → <br>."""
    return html.escape(str(text)).replace('\n', '<br>')


def _build_table_html(comp):
    """테이블 컴포넌트 → HTML <table>."""
    rows = comp.get('rows', [])
    if not rows:
        return ''

    skip = set()
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row.get('cells', [])):
            merge = cell.get('merge', {})
            cs = merge.get('cs', 1)
            rs = merge.get('rs', 1)
            if cs > 1 or rs > 1:
                for dr in range(rs):
                    for dc in range(cs):
                        if dr == 0 and dc == 0:
                            continue
                        skip.add((ri + dr, ci + dc))

    parts = ['<table class="data-table">']

    col_widths = comp.get('col_widths_cm', [])
    if col_widths:
        total = sum(col_widths)
        parts.append('<colgroup>')
        for w in col_widths:
            pct = w / total * 100
            parts.append(f'<col style="width:{pct:.1f}%">')
        parts.append('</colgroup>')

    for ri, row in enumerate(rows):
        cells = row.get('cells', [])
        parts.append('<tr>')

        for ci, cell in enumerate(cells):
            if (ri, ci) in skip:
                continue

            v = cell.get('v', '')
            s = cell.get('s', 'V')
            merge = cell.get('merge', {})
            algn = cell.get('algn', '')

            cs = merge.get('cs', 1)
            rs = merge.get('rs', 1)

            tag = 'th' if s == 'H' else 'td'
            classes = []
            if s == 'R':
                classes.append('cell-R')
            if algn == 'l':
                classes.append('align-left')

            attrs = ''
            if cs > 1:
                attrs += f' colspan="{cs}"'
            if rs > 1:
                attrs += f' rowspan="{rs}"'
            if classes:
                attrs += f' class="{" ".join(classes)}"'

            parts.append(f'<{tag}{attrs}>{_esc(v)}</{tag}>')

        parts.append('</tr>')

    parts.append('</table>')
    return '\n'.join(parts)


def _build_text_html(comp):
    """텍스트 컴포넌트 → HTML."""
    lines = comp.get('lines', [])
    parts = ['<div class="text-block">']
    for line in lines:
        if not line.strip():
            parts.append('<p class="empty-line">&nbsp;</p>')
        else:
            parts.append(f'<p>{_esc(line)}</p>')
    parts.append('</div>')
    return '\n'.join(parts)


def _build_heading_html(comp):
    """heading 컴포넌트 → HTML."""
    level = comp.get('level', 'subsection')
    text = comp.get('text', '')
    return f'<div class="heading-{level}">{_esc(text)}</div>'


def _build_footnote_html(comp):
    """각주 컴포넌트 → HTML."""
    text = comp.get('text', '')
    return f'<div class="footnote">{_esc(text)}</div>'


def _build_title_html(comp):
    """타이틀 컴포넌트 → HTML."""
    text = comp.get('text', '')
    return f'<div class="doc-title">{_esc(text)}</div>'


def _svg_text_lines(text, x, y, font_size=9, bold=False, color='#333'):
    """멀티라인 텍스트 → SVG <text> 요소."""
    lines = text.replace('\x0b', '\n').split('\n')
    weight = 'bold' if bold else 'normal'
    parts = []
    line_h = font_size * 1.3
    start_y = y - (len(lines) - 1) * line_h / 2
    for i, line in enumerate(lines):
        ly = start_y + i * line_h
        parts.append(
            f'<text x="{x}" y="{ly}" text-anchor="middle" '
            f'font-family="Malgun Gothic, sans-serif" font-size="{font_size}" '
            f'font-weight="{weight}" fill="{color}">{html.escape(line)}</text>')
    return '\n'.join(parts)


def _svg_box(x, y, w, h, rx=6, fill='#fff', stroke='#333', sw=1.2):
    """둥근 사각형 SVG."""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _svg_arrow(x1, y1, x2, y2, color='#333'):
    """화살표 SVG (마커 사용)."""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="1.2" marker-end="url(#arrowhead)"/>')


def _build_diagram_html(comp):
    """다이어그램 컴포넌트 → 직접 생성 SVG."""
    rows = comp.get('rows', [])
    if not rows:
        return ''

    connectors = {'+', '...', '···', '→', '=>'}
    has_connectors = any(
        e['text'] in connectors for row in rows for e in row
    )

    if has_connectors:
        return _build_combine_diagram_svg(rows, connectors)
    else:
        return _build_flow_diagram_svg(rows)


def _build_flow_diagram_svg(rows):
    """포트폴리오 구성 플로우 다이어그램 → 직접 SVG.

    원본 레이아웃:
    ┌─────────────────── Portfolio 1 ───────────────────┐
    │  [메인1] ──→ [메인2] ──→ [메인3] ──→ [메인4]      │
    │   서브1       서브2       서브3       서브4        │
    └──────────────────────────────────────────────────┘
    """
    main_row = rows[0] if rows else []
    sub_row = rows[1] if len(rows) >= 2 else []

    # title 분리 (높이가 메인 박스의 50% 미만)
    title_text = None
    main_els = main_row
    if main_row:
        avg_h = sum(e.get('height', 1) for e in main_row) / len(main_row)
        title_els = [e for e in main_row if e.get('height', avg_h) < avg_h * 0.6]
        main_els = [e for e in main_row if e.get('height', avg_h) >= avg_h * 0.6]
        if title_els:
            title_text = title_els[0]['text']

    n = len(main_els)
    if n == 0:
        return ''

    # 레이아웃 계산
    bw, bh = 130, 56         # 메인 박스 크기
    gap = 40                  # 박스 간 간격
    sub_h = 28                # 서브 레이블 높이
    sub_gap = 10              # 메인 → 서브 간격
    pad = 22                  # 클러스터 패딩
    title_h = 28 if title_text else 0

    total_w = n * bw + (n - 1) * gap + pad * 2
    total_h = title_h + bh + sub_gap + sub_h + pad * 2
    svg_w = total_w + 20
    svg_h = total_h + 20

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">']
    # 화살표 마커
    parts.append('<defs><marker id="arrowhead" markerWidth="8" markerHeight="6" '
                 'refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" '
                 'fill="#333"/></marker></defs>')

    # 클러스터 배경
    cx, cy = 10, 10
    parts.append(_svg_box(cx, cy, total_w, total_h, rx=8,
                          fill='#fafafa', stroke='#333', sw=1.5))

    # 타이틀
    if title_text:
        parts.append(_svg_text_lines(title_text,
                                     cx + total_w / 2, cy + title_h / 2 + 4,
                                     font_size=12, bold=True))

    # 메인 박스
    start_x = cx + pad
    start_y = cy + pad + title_h
    for i, e in enumerate(main_els):
        bx = start_x + i * (bw + gap)
        by = start_y
        parts.append(_svg_box(bx, by, bw, bh, rx=6))
        label = e['text'].replace('\x0b', '\n')
        parts.append(_svg_text_lines(label, bx + bw / 2, by + bh / 2 + 3,
                                     font_size=11))
        # 화살표
        if i < n - 1:
            parts.append(_svg_arrow(bx + bw + 2, by + bh / 2,
                                    bx + bw + gap - 2, by + bh / 2))

    # 서브 레이블
    for i, e in enumerate(sub_row):
        if i >= n:
            break
        bx = start_x + i * (bw + gap)
        sy = start_y + bh + sub_gap
        sbw = bw
        parts.append(_svg_box(bx, sy, sbw, sub_h, rx=3,
                              fill='#f0f0f0', stroke='#bbb', sw=0.8))
        parts.append(_svg_text_lines(e['text'],
                                     bx + sbw / 2, sy + sub_h / 2 + 3,
                                     font_size=10, color='#555'))

    parts.append('</svg>')
    return f'<div class="diagram-container">{"".join(parts)}</div>'


def _build_combine_diagram_svg(rows, connectors):
    """포트폴리오 결합 다이어그램 → 직접 SVG.

    원본 레이아웃:
    [Port1]  +  [Port2]  +  [Port3]  ···  →  [Combined Portfolio]
    weight%     weight%     weight%              100 %
    """
    ports = []
    weights = []
    result_node = None

    if len(rows) >= 2:
        for e in rows[0]:
            text = e['text']
            if text in connectors:
                continue
            if 'Combined' in text or 'combined' in text:
                result_node = text
            else:
                ports.append(text)
        for e in rows[1]:
            weights.append(e['text'])
    else:
        for e in rows[0]:
            text = e['text']
            if text in connectors:
                continue
            if 'Combined' in text:
                result_node = text
            else:
                ports.append(text)

    n_ports = len(ports)
    bw, bh = 100, 52         # 포트 박스 크기
    rw, rh = 130, 52         # 결과 박스 크기
    conn_w = 34               # + 커넥터 폭
    dots_w = 34               # ... 폭
    arrow_w = 44              # 화살표 영역
    wt_h = 22                 # weight 높이
    wt_gap = 8

    total_w = (n_ports * bw + (n_ports - 1) * conn_w
               + dots_w + arrow_w + rw + 20)
    total_h = bh + wt_gap + wt_h + 10
    svg_w = total_w
    svg_h = total_h + 10

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">']
    parts.append('<defs><marker id="arrowhead2" markerWidth="8" markerHeight="6" '
                 'refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" '
                 'fill="#333"/></marker></defs>')

    x = 10
    y = 5
    port_centers = []

    for i in range(n_ports):
        # 포트 박스
        parts.append(_svg_box(x, y, bw, bh, rx=6))
        label = ports[i]
        parts.append(_svg_text_lines(label, x + bw / 2, y + bh / 2 + 3,
                                     font_size=12, bold=True))
        # weight 레이블
        if i < len(weights):
            parts.append(_svg_text_lines(weights[i],
                                         x + bw / 2, y + bh + wt_gap + wt_h / 2 + 2,
                                         font_size=10, color='#666'))
        port_centers.append(x + bw / 2)
        x += bw

        # + 커넥터
        if i < n_ports - 1:
            parts.append(_svg_text_lines('+', x + conn_w / 2, y + bh / 2 + 3,
                                         font_size=16, bold=True))
            x += conn_w

    # ...
    parts.append(_svg_text_lines('···', x + dots_w / 2, y + bh / 2 + 3,
                                 font_size=18, bold=True))
    x += dots_w

    # 화살표
    parts.append(f'<line x1="{x}" y1="{y + bh / 2}" '
                 f'x2="{x + arrow_w - 4}" y2="{y + bh / 2}" '
                 f'stroke="#333" stroke-width="1.5" '
                 f'marker-end="url(#arrowhead2)"/>')
    x += arrow_w

    # 결과 박스
    if result_node:
        parts.append(_svg_box(x, y, rw, rh, rx=6, fill='#f0f0f0'))
        rlabel = result_node
        parts.append(_svg_text_lines(rlabel, x + rw / 2, y + rh / 2 + 3,
                                     font_size=12, bold=True))
        # 100% weight
        rw_text = weights[-1] if weights and len(weights) > n_ports else ''
        if not rw_text and weights:
            rw_text = weights[-1]
        if rw_text:
            parts.append(_svg_text_lines(rw_text,
                                         x + rw / 2, y + rh + wt_gap + wt_h / 2 + 2,
                                         font_size=10, color='#666'))

    parts.append('</svg>')
    return f'<div class="diagram-container">{"".join(parts)}</div>'


def _build_step_list_html(comp):
    """단계 리스트 컴포넌트 → HTML."""
    steps = comp.get('steps', [])
    parts = ['<div class="step-list">']
    for step in steps:
        label = step.get('label', '')
        desc = step.get('desc', '')
        parts.append(f'<div class="step-item">')
        parts.append(f'  <span class="step-label">{_esc(label)}</span>')
        if desc:
            parts.append(f'  <span class="step-desc">{_esc(desc)}</span>')
        parts.append(f'</div>')
    parts.append('</div>')
    return '\n'.join(parts)


def generate_html(components):
    """컴포넌트 리스트 → 완성 HTML 문자열."""
    parts = [f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
{CSS}
</style>
</head>
<body>
<div class="content-body">
"""]

    for comp in components:
        ctype = comp.get('type', '')
        if ctype == 'title':
            parts.append(_build_title_html(comp))
        elif ctype == 'heading':
            parts.append(_build_heading_html(comp))
        elif ctype == 'table':
            parts.append(_build_table_html(comp))
        elif ctype == 'text':
            parts.append(_build_text_html(comp))
        elif ctype == 'footnote':
            parts.append(_build_footnote_html(comp))
        elif ctype == 'diagram':
            parts.append(_build_diagram_html(comp))
        elif ctype == 'step_list':
            parts.append(_build_step_list_html(comp))

    parts.append('</div>')
    parts.append('</body></html>')
    return '\n'.join(parts)


# ═══════════════════════════════════════════════════════════════════
# PDF 생성 (Playwright)
# ═══════════════════════════════════════════════════════════════════

async def html_to_pdf(html_path, pdf_path):
    """Playwright로 HTML → PDF 변환."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=True)
        page = await browser.new_page()
        await page.goto(Path(html_path).resolve().as_uri())
        await page.pdf(
            path=pdf_path,
            format='A4',
            print_background=True,
            margin={'top': '15mm', 'right': '18mm',
                    'bottom': '15mm', 'left': '18mm'},
        )
        await browser.close()


# ═══════════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print('Usage: python render_pdf.py <render_input_v2.json>',
              file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding='utf-8') as f:
        config = json.load(f)

    work_dir = config.get('work_dir', os.path.dirname(os.path.abspath(sys.argv[1])))
    os.chdir(work_dir)

    # manifest에서 커버 컴포넌트 생성 (슬라이드 1-2)
    cover_components = []
    manifest_path = config.get('manifest_path', '')
    if manifest_path:
        if not os.path.isabs(manifest_path):
            manifest_path = os.path.join(work_dir, manifest_path)
        if os.path.exists(manifest_path):
            cover_components = build_cover_components(manifest_path)
            print(f'[cover] manifest에서 {len(cover_components)}개 커버 컴포넌트 생성')

    # 컴포넌트 로드 (슬라이드 3+)
    comp_path = config['components_path']
    if not os.path.isabs(comp_path):
        comp_path = os.path.join(work_dir, comp_path)
    with open(comp_path, encoding='utf-8') as f:
        body_components = json.load(f)

    print(f'[load] {len(body_components)}개 본문 컴포넌트')

    # 커버 + 본문 병합
    all_components = cover_components + body_components
    print(f'[merge] 총 {len(all_components)}개 컴포넌트')

    # HTML 생성
    html_str = generate_html(all_components)
    html_path = os.path.join(work_dir, '_report.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_str)
    print(f'[html] → {html_path}')

    # PDF 생성
    out_path = config.get('output_path', 'output.pdf')
    if not os.path.isabs(out_path):
        out_path = os.path.join(work_dir, out_path)

    print(f'[pdf] Playwright로 렌더링...')
    asyncio.run(html_to_pdf(html_path, out_path))
    print(f'[pdf] → {out_path}')


if __name__ == '__main__':
    main()
