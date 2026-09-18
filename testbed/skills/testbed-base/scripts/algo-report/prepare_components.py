"""components.json 생성 — semantic_map + computed + shapes_manifest → components.json.

semantic_map.component_order를 순회하며,
  - heading/text: shapes_manifest에서 텍스트 추출 (after/until 마커 기반)
  - table(deepcopy): shapes_manifest에서 rows/col_widths 추출
  - table(patch): shapes_manifest에서 rows/col_widths 추출 + computed patches 적용
  - table(render): computed에서 rows/col_widths 사용
  - footnote: shapes_manifest에서 prefix 기반 추출

도메인 지식 제로 — 무엇을 조립할지는 입력 JSON이 결정.

사용법:
    python prepare_components.py prepare_input.json

입력 JSON:
    {
      "semantic_map_path": "semantic_map.json",
      "computed_path": "computed.json",
      "manifest_path": "shapes_manifest.json",
      "output_path": "components.json"
    }
"""
import sys, json, os, re

sys.stdout.reconfigure(encoding='utf-8')


def _clean_text(text):
    """PUA 문자(Wingdings 글머리 등)와 양쪽 공백 제거."""
    return re.sub(r'^[\uf000-\uf0ff\s]+', '', text).strip()


# ── manifest 유틸 ──

def _build_shape_index(manifest):
    """manifest에서 shape_id → shape dict 인덱스."""
    idx = {}
    for slide in manifest.get('slides', []):
        for shape in slide.get('shapes', []):
            idx[shape['id']] = shape
    return idx


def _get_paragraphs(shape_index, shape_id):
    """shape_id → paragraphs 리스트."""
    shape = shape_index.get(shape_id)
    if not shape or 'text' not in shape:
        return []
    return shape['text'].get('paragraphs', [])


def _get_table_rows(shape_index, shape_id):
    """shape_id → 테이블 행 데이터 (셀 값 v 키). s는 원본 그대로."""
    shape = shape_index.get(shape_id)
    if not shape or 'table' not in shape:
        return []
    rows = []
    for row in shape['table'].get('rows', []):
        cells = []
        for c in row.get('cells', []):
            cells.append({
                'v': c.get('v', ''),
                's': c.get('s', 'V'),
            })
        rows.append({'cells': cells, 'h': row.get('h_cm', 0.8)})
    return rows


def _apply_thead(rows, thead_rows):
    """semantic_map의 thead_rows 값에 따라 H/V를 재분류.

    - thead_rows 이내 행: 모든 셀 → H
    - thead_rows 이후 행: R은 보존, 나머지 → V
    """
    if thead_rows is None:
        return rows
    for ri, row in enumerate(rows):
        for cell in row['cells']:
            if ri < thead_rows:
                if cell['s'] != 'R':
                    cell['s'] = 'H'
            else:
                if cell['s'] != 'R':
                    cell['s'] = 'V'
    return rows


def _get_table_col_widths(shape_index, shape_id):
    """shape_id → col_widths_cm 리스트."""
    shape = shape_index.get(shape_id)
    if not shape or 'table' not in shape:
        return []
    return shape['table'].get('col_widths_cm', [])


# ── 텍스트 추출 (after/until 마커 기반) ──

def _extract_text_section(paragraphs, after, until):
    """paragraphs에서 after~until 구간의 텍스트를 추출.

    after: 이 텍스트로 시작하는 paragraph을 찾아서 그 줄의 텍스트 반환
    until: 이 텍스트로 시작하는 paragraph 직전까지 (None이면 after 줄만)
    """
    found_start = False
    result_lines = []

    for p in paragraphs:
        text = _clean_text(p.get('text', ''))
        if not text:
            continue

        if not found_start:
            if text.startswith(after):
                found_start = True
                if until is None:
                    return text
                result_lines.append(text)
            continue

        if until and text.startswith(until):
            break
        result_lines.append(text)

    if result_lines:
        return result_lines[0] if len(result_lines) == 1 else result_lines
    return after  # fallback


def _extract_text_lines(paragraphs, after, until):
    """paragraphs에서 after~until 구간의 여러 줄 텍스트를 리스트로 추출."""
    found_start = False
    result_lines = []

    for p in paragraphs:
        text = _clean_text(p.get('text', ''))
        if not text:
            if found_start:
                result_lines.append('')
            continue

        if not found_start:
            if text.startswith(after):
                found_start = True
                result_lines.append(text)
            continue

        if until and text.startswith(until):
            break
        result_lines.append(text)

    return result_lines


def _extract_footnote(paragraphs, prefix):
    """paragraphs에서 prefix로 시작하는 첫 줄을 추출."""
    for p in paragraphs:
        text = _clean_text(p.get('text', ''))
        if text.startswith(prefix):
            return text
    return ''


# ── patch 적용 ──

def _apply_patches(rows, patches):
    """rows에 patches를 적용하여 새 rows 반환."""
    if not patches:
        return rows
    import copy
    patched = copy.deepcopy(rows)
    for patch in patches:
        r, c = patch['row'], patch['col']
        if r < len(patched) and c < len(patched[r]['cells']):
            patched[r]['cells'][c]['v'] = patch['v']
    return patched


# ── 메인 조립 ──

def build(semantic_map, computed, manifest):
    """semantic_map.component_order를 순회하며 컴포넌트 리스트 조립."""
    shape_index = _build_shape_index(manifest)
    shapes = semantic_map.get('shapes', {})
    component_order = semantic_map.get('component_order', [])

    components = []

    for entry in component_order:
        comp_type = entry['type']
        ref = entry['ref']
        shape_info = shapes.get(ref, {})
        shape_id = shape_info.get('shape_id', '')
        tag = shape_info.get('tag', '')

        if comp_type == 'heading':
            level = entry.get('level', 'subsection')
            if tag == 'text_section':
                paragraphs = _get_paragraphs(shape_index, shape_id)
                after = shape_info.get('after', '')
                until = shape_info.get('until')
                text = _extract_text_section(paragraphs, after, until)
                if isinstance(text, list):
                    text = text[0] if text else after
            elif tag == 'heading':
                paragraphs = _get_paragraphs(shape_index, shape_id)
                texts = [p.get('text', '').strip() for p in paragraphs
                         if p.get('text', '').strip()]
                text = texts[0] if texts else ref
            else:
                text = ref

            components.append({
                'type': 'heading',
                'level': level,
                'text': text,
            })

        elif comp_type == 'table':
            action = shape_info.get('action', 'render')
            table_id = shape_info.get('id', ref)
            thead_rows = shape_info.get('thead_rows')

            if action == 'deepcopy':
                rows = _get_table_rows(shape_index, shape_id)
                col_widths = _get_table_col_widths(shape_index, shape_id)

            elif action == 'patch':
                rows = _get_table_rows(shape_index, shape_id)
                col_widths = _get_table_col_widths(shape_index, shape_id)
                patches = computed.get(table_id, {}).get('patches', [])
                rows = _apply_patches(rows, patches)

            elif action == 'render':
                table_data = computed.get(table_id, {})
                rows = table_data.get('rows', [])
                col_widths = table_data.get('col_widths_cm', [])

            else:
                print(f'  [WARN] 알 수 없는 action: {action} (ref={ref})',
                      file=sys.stderr)
                continue

            # semantic_map의 thead_rows에 따라 H/V 재분류
            rows = _apply_thead(rows, thead_rows)

            comp = {
                'type': 'table',
                'rows': rows,
                'col_widths_cm': col_widths,
            }

            # footnote
            footnote_ref = entry.get('footnote_ref')
            if footnote_ref:
                fn_info = shapes.get(footnote_ref, {})
                fn_shape_id = fn_info.get('shape_id', '')
                fn_prefix = fn_info.get('prefix', '*')
                paragraphs = _get_paragraphs(shape_index, fn_shape_id)
                fn_text = _extract_footnote(paragraphs, fn_prefix)
                if fn_text:
                    comp['footnote'] = fn_text

            if 'font_size' in entry:
                comp['font_size'] = entry['font_size']

            components.append(comp)

        elif comp_type == 'text':
            paragraphs = _get_paragraphs(shape_index, shape_id)
            after = shape_info.get('after', '')
            until = shape_info.get('until')
            lines = _extract_text_lines(paragraphs, after, until)

            components.append({
                'type': 'text',
                'lines': lines,
                'size': entry.get('size', 11),
            })

        else:
            print(f'  [WARN] 알 수 없는 컴포넌트 타입: {comp_type} (ref={ref})',
                  file=sys.stderr)

    return components


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python prepare_components.py <prepare_input.json>',
              file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding='utf-8') as f:
        input_data = json.load(f)

    base_dir = os.path.dirname(os.path.abspath(sys.argv[1]))

    def _resolve(p):
        return p if os.path.isabs(p) else os.path.join(base_dir, p)

    with open(_resolve(input_data['semantic_map_path']), encoding='utf-8') as f:
        semantic_map = json.load(f)

    with open(_resolve(input_data['computed_path']), encoding='utf-8') as f:
        computed = json.load(f)

    with open(_resolve(input_data['manifest_path']), encoding='utf-8') as f:
        manifest = json.load(f)

    components = build(semantic_map, computed, manifest)

    out_path = _resolve(input_data.get('output_path', 'components.json'))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(components, f, ensure_ascii=False, indent=2)
    print(f'{len(components)}개 컴포넌트 → {out_path}')
