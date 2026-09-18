"""v2 계산 + 셀 데이터 사전 생성.

shapes_manifest + semantic_map + algo_data + 투자유니버스 → computed.json
ref_data.json 의존 완전 제거. manifest 테이블에서 직접 읽음.

사용법:
    python build_computed.py compute_input.json

입력 JSON (compute_input.json):
    {
      "manifest_path": "shapes_manifest.json",
      "semantic_map_path": "semantic_map.json",
      "universe_path": "투자유니버스.xlsx",
      "algo_data_path": "algo_data.json",
      "output_path": "computed.json"
    }

출력: computed.json — per_type + patch 셀 + render 테이블 데이터
"""
import sys, json, os, re

sys.stdout.reconfigure(encoding='utf-8')

try:
    import openpyxl
except ImportError:
    openpyxl = None

from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════
# Manifest 테이블 읽기
# ═══════════════════════════════════════════════════════════════════

def _build_shape_index(manifest):
    """manifest에서 shape id → shape dict 인덱스 구축."""
    idx = {}
    for slide in manifest.get('slides', []):
        for shape in slide.get('shapes', []):
            idx[shape['id']] = shape
    return idx


def _get_table_rows(shape_index, shape_id):
    """shape_id로 manifest에서 테이블 행 데이터를 가져온다.
    Returns: list of list of str (각 행의 셀 값 목록)
    """
    shape = shape_index.get(shape_id)
    if not shape or 'table' not in shape:
        return []
    rows = []
    for row in shape['table'].get('rows', []):
        cells = [c.get('v', '') for c in row.get('cells', [])]
        rows.append(cells)
    return rows


def _get_table_col_widths(shape_index, shape_id):
    """shape_id로 manifest에서 col_widths_cm을 가져온다."""
    shape = shape_index.get(shape_id)
    if not shape or 'table' not in shape:
        return []
    return shape['table'].get('col_widths_cm', [])


# ═══════════════════════════════════════════════════════════════════
# Manifest에서 도메인 상수 파싱
# ═══════════════════════════════════════════════════════════════════

def _parse_grade_info(t41_rows):
    """t41_table (위험등급 정의)에서 등급명, 점수범위, grade_map 파싱.

    t41_rows:
      row0: ['매우높은위험\\n(1등급)', '높은위험\\n(2등급)', ...]
      row1: ['5.5 이상', '4.5 ~ 5.5 미만', ...]
    """
    gnames = t41_rows[0] if t41_rows else []
    grade_ranges = t41_rows[1] if len(t41_rows) > 1 else []

    grade_map = {}
    gnum_to_grade = {}
    risk_grades = []

    for i, gn in enumerate(gnames):
        gnum = i + 1
        # 등급명: 줄바꿈 전까지
        grade_map[gnum] = gn.split('\n')[0].split('\x0b')[0]

        # "N등급" 패턴 추출
        m = re.search(r'\((\d+)(등급)\)', gn)
        if m:
            gnum_to_grade[int(m.group(1))] = m.group(1) + m.group(2)

    # 점수범위에서 min_score 파싱
    for i, rng in enumerate(grade_ranges):
        gnum = i + 1
        # "5.5 이상" → 5.5, "4.5 ~ 5.5 미만" → 4.5
        nums = re.findall(r'[\d.]+', rng)
        min_score = float(nums[0]) if nums else 0.0
        risk_grades.append({'gnum': gnum, 'min_score': min_score})

    return {
        'gnames': gnames,
        'grade_ranges': grade_ranges,
        'grade_map': grade_map,
        'gnum_to_grade': gnum_to_grade,
        'risk_grades': risk_grades,
    }


def _parse_investor_types(t31_rows):
    """t31_table (투자자성향 구분)에서 투자자유형 목록 파싱.

    t31_rows:
      row0: ['투자자 성향 구분', '', '점수']  (header)
      row1: ['모범 규준', 'XXXレシピ', '']     (sub-header)
      row2: ['공격형', '', '80.0점 ~ 100.0점'] (데이터 시작)
      ...
    Returns: (inv_types, tb_type_map, recipe_name)
    """
    inv_types = []
    tb_type_map = {}
    recipe_name = ''

    if len(t31_rows) > 1:
        recipe_name = t31_rows[1][1] if len(t31_rows[1]) > 1 else ''

    for i, row in enumerate(t31_rows[2:], start=1):
        if row[0]:
            inv_types.append(row[0])
            tb_type_map[i] = row[0]

    return inv_types, tb_type_map, recipe_name


def _parse_types_from_t32(t32_rows):
    """t32_table에서 포트폴리오 유형 목록(매운맛 등) 추출."""
    types = []
    for row in t32_rows[1:]:  # skip header
        if row[0] and not row[0].startswith('*'):
            types.append(row[0])
    return types


def _parse_t44_labels(t44_rows):
    """t44_table (투자자성향별 투자가능상품)에서 라벨 추출.

    Returns: (ok_label, no_label, row_label)
    """
    ok_label = ''
    no_label = ''
    row_label = ''

    for row in t44_rows[2:]:  # skip 2 header rows
        if row[0]:
            row_label = row[0]
        for v in row[2:]:
            v = v.strip() if v else ''
            if '가능' in v and not ok_label:
                ok_label = v
            if '불가' in v and not no_label:
                no_label = v

    return ok_label, no_label, row_label


# ═══════════════════════════════════════════════════════════════════
# 유니버스 + 알고 데이터 로드 (v1과 동일)
# ═══════════════════════════════════════════════════════════════════

def _load_universe(xlsx_path):
    """투자유니버스 엑셀에서 종목 데이터 로드."""
    col_map = {"name": 1, "market": 2, "asset_group": 3,
               "asset_type": 4, "risk_grade": 5, "dscore": 6,
               "risk_asset": 7, "ticker": 8}
    if openpyxl is None:
        raise ImportError('openpyxl 필요: uv pip install openpyxl')
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None and row[col_map['name']] is None:
            continue
        ds = row[col_map['dscore']]
        if isinstance(ds, str):
            ds = int(ds) if ds.strip().isdigit() else 0
        rows.append({
            'name': row[col_map['name']], 'market': row[col_map['market']],
            'asset_group': row[col_map['asset_group']],
            'asset_type': row[col_map['asset_type']],
            'risk_grade': row[col_map['risk_grade']], 'dscore': ds,
            'risk_asset': row[col_map['risk_asset']],
            'ticker': str(row[col_map['ticker']]).strip() if row[col_map['ticker']] else None
        })
    return rows


def _base_name(asset_type, strip_pattern=r'\d+$'):
    """세분류에서 접미 숫자 제거. 국내주식1→국내주식"""
    return re.sub(strip_pattern, '', asset_type)


def _map_ticker_to_asset_type(ticker, tk_asset_type, uni_map, bn_to_types,
                              strip_pattern=r'\d+$'):
    """DB ticker → 유니버스 asset_type 매핑."""
    ticker = str(ticker)
    if ticker in uni_map:
        return uni_map[ticker]
    bn = _base_name(tk_asset_type, strip_pattern)
    at_set = bn_to_types.get(bn, set())
    return sorted(at_set)[0] if at_set else tk_asset_type


def _load_algo_data(json_path, uni, types, strip_pattern=r'\d+$'):
    """algo_data.json에서 전략 데이터 로드."""
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    uni_map = {r['ticker']: r['asset_type'] for r in uni if r.get('ticker')}
    bn_to_types = defaultdict(set)
    for r in uni:
        bn_to_types[_base_name(r['asset_type'], strip_pattern)].add(r['asset_type'])

    strat_data = {}
    for typ in data.get('types', []):
        short = next((t for t in types if t in typ['name']), None)
        if not short:
            continue
        dyn_wt = 0.0
        atk = defaultdict(set)
        dfn = defaultdict(set)
        fixed = []
        seen_fixed = set()
        for strat in typ.get('strategies', []):
            stype = strat.get('type')
            mw = strat.get('mixed_wt', 0)
            if stype == 'dynamic':
                dyn_wt += mw
                for tk in strat.get('tickers', []):
                    at = _map_ticker_to_asset_type(
                        tk['ticker'], tk.get('asset_type', ''), uni_map, bn_to_types,
                        strip_pattern)
                    if not at:
                        continue
                    ds = tk.get('dscore', 0)
                    if tk.get('attack'):
                        atk[ds].add(at)
                    if tk.get('defense'):
                        dfn[ds].add(at)
            elif stype not in seen_fixed:
                seen_fixed.add(stype)
                by_ds = defaultdict(lambda: {'wt': 0, 'assets': set()})
                for tk in strat.get('tickers', []):
                    ds = tk.get('dscore', 0)
                    wt = tk.get('wt', 0) or 0
                    at = _map_ticker_to_asset_type(
                        tk['ticker'], tk.get('asset_type', ''), uni_map, bn_to_types,
                        strip_pattern)
                    by_ds[ds]['wt'] += wt
                    by_ds[ds]['assets'].add(at)
                groups = [{'ds': ds, 'wt_pct': v['wt'], 'assets': sorted(v['assets'])}
                          for ds, v in sorted(by_ds.items(), reverse=True)]
                fixed.append({'type': stype, 'mixed_wt': mw, 'groups': groups})

        all_ds = sorted(set(atk.keys()) | set(dfn.keys()), reverse=True)
        dyn_groups = []
        for ds in all_ds:
            assets = sorted(atk.get(ds, set()) | dfn.get(ds, set()))
            ra = 'Y' if ds in atk else 'N'
            dyn_groups.append({'ds': ds, 'assets': assets, 'ra': ra})

        strat_data[short] = {
            'dynamic_wt': dyn_wt,
            'attack': [{'ds': d, 'assets': sorted(a)}
                       for d, a in sorted(atk.items(), reverse=True)],
            'defense': [{'ds': d, 'assets': sorted(a)}
                        for d, a in sorted(dfn.items(), reverse=True)],
            'dynamic_groups': dyn_groups,
            'fixed': fixed,
        }
    return strat_data


# ═══════════════════════════════════════════════════════════════════
# 위험도 계산
# ═══════════════════════════════════════════════════════════════════

def _calc_risk(sd):
    """위험도 산출. min/max 점수 계산."""
    dyn = sd['dynamic_wt'] / 100
    atk_ds = max((g['ds'] for g in sd['attack']), default=0)
    def_ds = min((g['ds'] for g in sd['defense']), default=0)
    mn = dyn * def_ds
    mx = dyn * atk_ds
    for f in sd['fixed']:
        base_wt = f['mixed_wt'] / 100
        for grp in f['groups']:
            contrib = base_wt * (grp['wt_pct'] / 100) * grp['ds']
            mn += contrib
            mx += contrib
    return round(mn, 2), round(mx, 2)


def _risk_grade(mx, risk_grades, grade_map):
    """위험등급 판정. Returns (grade_name, gnum)."""
    for rg in risk_grades:
        if mx >= rg['min_score']:
            gnum = rg['gnum']
            return grade_map.get(gnum, ''), gnum
    last = risk_grades[-1]
    gnum = last['gnum']
    return grade_map.get(gnum, ''), gnum


def _tb_type(gnum, tb_type_map, inv_types):
    """등급번호 → 테스트베드 투자자유형."""
    return tb_type_map.get(gnum, inv_types[-1] if inv_types else '')


def _compute_per_type(types, strat_data, risk_grades, grade_map, tb_type_map,
                      inv_types, gnum_to_grade):
    """유형별 위험도 정보 계산."""
    result = {}
    for t in types:
        mn, mx = _calc_risk(strat_data[t])
        gn, gnum = _risk_grade(mx, risk_grades, grade_map)
        result[t] = {
            'min': mn, 'max': mx, 'grade': gn, 'gnum': gnum,
            'grade_label': gnum_to_grade.get(gnum, f'{gnum}등급'),
            'tb': _tb_type(gnum, tb_type_map, inv_types),
            'dynamic_wt': int(strat_data[t]['dynamic_wt']),
        }
    return result


# ═══════════════════════════════════════════════════════════════════
# Patch 테이블 빌더 (t31_table, t32_table)
# ═══════════════════════════════════════════════════════════════════

def _build_t31_patches(t31_rows, types, per_type):
    """t31_table patch: 투자자성향에 대응하는 유형의 포트폴리오 이름을 기존 셀에 쓴다.

    t31에서 types에 매칭되는 행의 col 1을 포트폴리오 유형명으로 갱신 불필요.
    이미 레퍼런스에 '매운맛' 등이 들어있으므로, 변경할 필요가 없다.
    → patch 없음 (레퍼런스 그대로 deepcopy)

    하지만 만약 등급이 바뀌었다면? t31은 투자자성향 구분 테이블이므로
    계산 결과와 무관한 고정 테이블이다. patch가 필요한 건 아니다.

    실제로는 t31은 이미 매핑이 맞는 상태일 수 있으니, 확인 후 차이가 있는 셀만 패치.
    """
    patches = []
    # t31_rows: row0=header(투자자 성향 구분, '', 점수)
    #           row1=sub-header(모범 규준, 레시피명, '')
    #           row2~6=data(공격형/적극투자형/위험중립형/안정추구형/안정형)
    # 투자자성향→포트폴리오유형 매핑은 semantic_map에 이미 있으므로
    # per_type에서 각 유형의 투자자성향(tb)을 찾아 해당 행의 col1에 유형명을 넣는다.
    type_to_row = {}
    for ri, row in enumerate(t31_rows[2:], start=2):
        investor_type = row[0]
        for t in types:
            if per_type[t]['tb'] == investor_type:
                type_to_row[t] = ri

    for t in types:
        ri = type_to_row.get(t)
        if ri is not None:
            current_val = t31_rows[ri][1] if len(t31_rows[ri]) > 1 else ''
            if current_val != t:
                patches.append({"row": ri, "col": 1, "v": t})

    return patches


def _build_t32_patches(t32_rows, types, per_type, strat_data):
    """t32_table patch: 포트폴리오 유형별 위험등급 + 운용방식 텍스트의 위험자산비중 갱신.

    t32_rows:
      row0: header
      row1~3: [유형명, 등급, 운용방식]
    """
    patches = []
    for ri, row in enumerate(t32_rows[1:], start=1):
        type_name = row[0]
        if type_name not in per_type:
            continue
        pt = per_type[type_name]

        # col 1: 위험등급
        new_grade = pt['grade_label']
        if row[1] != new_grade:
            patches.append({"row": ri, "col": 1, "v": new_grade})

        # col 2: 운용방식 텍스트에서 위험자산 비중 교체
        dw = pt['dynamic_wt']
        desc = row[2]
        new_desc = re.sub(r'0\s*~\s*\d+\s*%', f'0 ~ {dw}%', desc, count=1)
        if desc != new_desc:
            patches.append({"row": ri, "col": 2, "v": new_desc})

    return patches


# ═══════════════════════════════════════════════════════════════════
# Render 테이블 빌더
# ═══════════════════════════════════════════════════════════════════

def _build_t42_table(uni, grade_info):
    """t42_table (s4_shape3): 자산종류별 위험등급 (7 cols).

    ref: [위험등급, 1등급~6등급] — 유니버스의 dscore별 자산종류 분류.
    """
    gnames = grade_info['gnames']
    by_ds = defaultdict(list)
    for r in uni:
        by_ds[r['dscore']].append(r['asset_type'])

    # header
    rows = [{"cells": [{"v": "위험등급", "s": "H"}] +
                       [{"v": g, "s": "H"} for g in gnames], "h": 1.2}]
    # 자산종류 행
    asset_cells = [{"v": "자산종류", "s": "H"}]
    score_cells = [{"v": "위험도점수", "s": "H"}]
    for ds in [6, 5, 4, 3, 2, 1]:
        ts = sorted(set(by_ds.get(ds, [])))
        asset_cells.append({"v": "\n".join(ts) if ts else "-", "s": "V"})
        score_cells.append({"v": str(ds), "s": "V"})
    rows.append({"cells": asset_cells, "h": 1.8})
    rows.append({"cells": score_cells, "h": 0.8})

    return rows


def _build_t43_table(types, per_type, inv_types, t44_labels):
    """t43_table (s4_shape4): 투자자 성향별 투자적합상품 분류 (5 cols)."""
    ok_label, no_label, row_label = t44_labels
    header0 = [{"v": "구분", "s": "H", "merge": {"cs": 2, "rs": 2}},
               {"v": "", "s": "H"},
               {"v": "포트폴리오 유형", "s": "H", "merge": {"cs": len(types)}}] + \
              [{"v": "", "s": "H"} for _ in range(len(types) - 1)]
    header1 = [{"v": "", "s": "H"}, {"v": "", "s": "H"}] + \
              [{"v": t, "s": "H"} for t in types]

    rows = [{"cells": header0, "h": 0.8},
            {"cells": header1, "h": 0.8}]

    tg = {t: per_type[t]['gnum'] for t in types}
    for i, inv in enumerate(inv_types):
        ig = i + 1
        first_col = ({"v": row_label, "s": "V", "merge": {"rs": len(inv_types)}}
                     if i == 0
                     else {"v": "", "s": "V"})
        cells = [first_col, {"v": inv, "s": "V"}]
        for t in types:
            ok = tg[t] >= ig
            cells.append({"v": ok_label if ok else no_label,
                          "s": "V" if ok else "R"})
        rows.append({"cells": cells, "h": 0.8})
    return rows


def _build_t44_table(uni):
    """t44_table (s4_shape5): 편입자산 종류 및 특징 (7 cols, 유니버스 기반)."""
    bg = defaultdict(lambda: {'c': 0, 'm': '', 'g': '', 'rg': '', 'ra': '', 'ds': 0})
    for r in uni:
        at = r['asset_type']
        bg[at]['c'] += 1
        bg[at]['m'] = r['market']
        bg[at]['g'] = r['asset_group']
        bg[at]['rg'] = r['risk_grade']
        bg[at]['ds'] = r['dscore']
        bg[at]['ra'] = r['risk_asset']

    rows = [{"cells": [
        {"v": "시장구분", "s": "H"}, {"v": "자산군", "s": "H"},
        {"v": "자산종류", "s": "H"}, {"v": "포함 종목수", "s": "H"},
        {"v": "위험등급", "s": "H"}, {"v": "위험자산여부", "s": "H"},
        {"v": "특징", "s": "H"}], "h": 0.8}]

    for at in sorted(bg.keys(), key=lambda x: (-bg[x]['ds'], x)):
        d = bg[at]
        rows.append({"cells": [
            {"v": d['m'], "s": "V"}, {"v": d['g'], "s": "V"},
            {"v": at, "s": "V"}, {"v": str(d['c']), "s": "V"},
            {"v": d['rg'], "s": "V"}, {"v": d['ra'], "s": "V"},
            {"v": "", "s": "V"}], "h": 0.8})
    return rows


def _build_t51_table(types, strat_data, per_type):
    """t51_table (s5_shape2): 포트폴리오 유형별 구분 (4 cols).

    ref: [구분, 매운맛, 중간맛, 순한맛]
         [위험자산 편입 비중, 0~70%, ...]
         [위험도 범위, 1.95~4.75, ...]
    """
    rows = [
        {"cells": [{"v": "구분", "s": "H"}] +
                   [{"v": t, "s": "H"} for t in types], "h": 0.8},
        {"cells": [{"v": "위험자산 편입 비중", "s": "V"}] +
                   [{"v": f"0 ~ {per_type[t]['dynamic_wt']}%", "s": "V"}
                    for t in types], "h": 0.8},
        {"cells": [{"v": "위험도 범위", "s": "V"}] +
                   [{"v": f"{per_type[t]['min']}~{per_type[t]['max']}", "s": "V"}
                    for t in types], "h": 0.8},
    ]
    return rows


def _build_t52_table(types, strat_data, per_type, grade_info):
    """t52_table (s5_shape3): 자산종류별 편입비중 (6 cols).

    ref: [자산종류, 위험등급(점수), 위험자산여부, 매운맛, 중간맛, 순한맛]
    """
    grade_map = grade_info['grade_map']
    sd0 = strat_data[types[0]]

    rows = [{"cells": [
        {"v": "자산종류", "s": "H"}, {"v": "위험등급\n(점수)", "s": "H"},
        {"v": "위험자산\n여부", "s": "H"}] +
        [{"v": t, "s": "H"} for t in types], "h": 1.2}]

    # 공격 자산
    n_atk_rows = len(sd0['attack'])
    for i, grp in enumerate(sd0['attack']):
        cells = [
            {"v": "/".join(grp['assets']), "s": "V"},
            {"v": f"{grade_map.get(7 - grp['ds'], '')}({grp['ds']})", "s": "V"},
            {"v": "Y", "s": "V"},
        ]
        if i == 0:
            for t in types:
                c = {"v": f"0~{int(strat_data[t]['dynamic_wt'])}%", "s": "V"}
                if n_atk_rows > 1:
                    c["merge"] = {"rs": n_atk_rows}
                cells.append(c)
        else:
            cells += [{"v": "", "s": "V"} for _ in types]
        rows.append({"cells": cells,
                     "h": max(0.8, 0.4 * len(grp['assets']))})

    # 방어 자산
    for grp in sd0['defense']:
        ra = "Y" if grp['ds'] >= 4 else "N"
        cells = [
            {"v": "/".join(grp['assets']), "s": "V"},
            {"v": f"{grade_map.get(7 - grp['ds'], '')}({grp['ds']})", "s": "V"},
            {"v": ra, "s": "V"},
        ]
        for t in types:
            cells.append({"v": f"0~{int(strat_data[t]['dynamic_wt'])}%", "s": "V"})
        rows.append({"cells": cells,
                     "h": max(0.8, 0.4 * len(grp['assets']))})

    # 정적전략 자산
    for fs in sd0['fixed']:
        for grp in fs['groups']:
            cells = [
                {"v": "/".join(grp['assets']), "s": "V"},
                {"v": f"{grade_map.get(7 - grp['ds'], '')}({grp['ds']})", "s": "V"},
                {"v": "N", "s": "V"},
            ]
            for t in types:
                matching = next((f for f in strat_data[t]['fixed']
                                 if f['type'] == fs['type']), None)
                if matching:
                    mg = next((g for g in matching['groups']
                               if g['ds'] == grp['ds']), None)
                    alloc = matching['mixed_wt'] * mg['wt_pct'] / 100 if mg else 0
                    cells.append({"v": f"{alloc:.1f}%", "s": "V"})
                else:
                    cells.append({"v": "-", "s": "V"})
            rows.append({"cells": cells,
                         "h": max(0.8, 0.4 * len(grp['assets']))})

    # 합계행
    rows.append({"cells": [
        {"v": "합계", "s": "H", "merge": {"cs": 3}},
        {"v": "", "s": "H"}, {"v": "", "s": "H"}] +
        [{"v": "100%", "s": "V"} for _ in types], "h": 0.8})

    return rows


def _build_t53_table(types, strat_data, per_type, grade_info):
    """t53_table (s5_shape4): 위험도 산출방법 상세 (9 cols).

    ref: [유형, 전략, 비중, 자산종류-소, 최소, 최대, 위험점수, 최소위험도, 최대위험도]
    """
    grade_map = grade_info['grade_map']

    rows = [{"cells": [
        {"v": "유형", "s": "H"}, {"v": "전략", "s": "H"},
        {"v": "비중", "s": "H"}, {"v": "자산종류-소", "s": "H"},
        {"v": "최소", "s": "H"}, {"v": "최대", "s": "H"},
        {"v": "위험점수", "s": "H"},
        {"v": "최소위험도", "s": "H"}, {"v": "최대위험도", "s": "H"}], "h": 0.8}]

    for t in types:
        sd = strat_data[t]
        dw = sd['dynamic_wt']
        dd = dw / 100
        mn, mx = per_type[t]['min'], per_type[t]['max']
        atk_ds = max(g['ds'] for g in sd['attack'])
        def_ds = min(g['ds'] for g in sd['defense'])
        atk_assets = sorted(
            at for g in sd['attack'] if g['ds'] == atk_ds for at in g['assets'])
        def_assets = sorted(
            at for g in sd['defense'] if g['ds'] == def_ds for at in g['assets'])
        atk_label = "/".join(atk_assets)
        def_label = "/".join(def_assets)

        # 전략별 행 수 계산
        awt_rows = sum(len(fs['groups']) for fs in sd['fixed'])
        rows_per_type = 2 + awt_rows + 1  # atk + def + fixed groups + formula

        # 동적전략 공격
        rows.append({"cells": [
            {"v": t, "s": "V", "merge": {"rs": rows_per_type}},
            {"v": "동적", "s": "V", "merge": {"rs": 2}},
            {"v": f"{dw:.2f}%", "s": "V", "merge": {"rs": 2}},
            {"v": atk_label, "s": "V"},
            {"v": "0.0%", "s": "V"},
            {"v": f"{dw:.1f}%", "s": "V"}, {"v": str(atk_ds), "s": "V"},
            {"v": str(mn), "s": "V", "merge": {"rs": rows_per_type - 1}},
            {"v": str(mx), "s": "V", "merge": {"rs": rows_per_type - 1}},
        ], "h": 0.8})

        # 동적전략 방어
        rows.append({"cells": [
            {"v": "", "s": "V"}, {"v": "", "s": "V"}, {"v": "", "s": "V"},
            {"v": def_label, "s": "V"},
            {"v": f"{dw:.1f}%", "s": "V"},
            {"v": "0.0%", "s": "V"}, {"v": str(def_ds), "s": "V"},
            {"v": "", "s": "V"}, {"v": "", "s": "V"},
        ], "h": 0.8})

        # 정적전략
        for fs in sd['fixed']:
            sname = fs['type']
            if '-' in sname:
                sname = sname.split('-')[0]
            if sname == '현금자산':
                sname = '현금'
            base_wt = fs['mixed_wt']
            n_grps = len(fs['groups'])
            for gi, grp in enumerate(fs['groups']):
                alloc = base_wt * grp['wt_pct'] / 100
                label = "/".join(grp['assets'])
                cells = [{"v": "", "s": "V"}]
                if gi == 0:
                    merge_opt = {"merge": {"rs": n_grps}} if n_grps > 1 else {}
                    cells += [{"v": sname, "s": "V", **merge_opt},
                              {"v": f"{base_wt:.2f}%", "s": "V", **merge_opt}]
                else:
                    cells += [{"v": "", "s": "V"}, {"v": "", "s": "V"}]
                cells += [{"v": label, "s": "V"},
                          {"v": f"{alloc:.1f}%", "s": "V"},
                          {"v": f"{alloc:.1f}%", "s": "V"},
                          {"v": str(grp['ds']), "s": "V"},
                          {"v": "", "s": "V"}, {"v": "", "s": "V"}]
                rows.append({"cells": cells, "h": 0.8})

        # 수식행
        parts_min = [f"{dd}*{def_ds}"]
        parts_max = [f"{dd}*{atk_ds}"]
        for fs in sd['fixed']:
            base_pct = fs['mixed_wt'] / 100
            for grp in fs['groups']:
                w = base_pct * grp['wt_pct'] / 100
                parts_min.append(f"{w}*{grp['ds']}")
                parts_max.append(f"{w}*{grp['ds']}")
        mf = f"최소: {'+'.join(parts_min)}={mn}"
        xf = f"최대: {'+'.join(parts_max)}={mx}"
        rows.append({"cells": [
            {"v": "", "s": "V"},
            {"v": f"{mf}\n{xf}", "s": "V", "algn": "l", "merge": {"cs": 8}},
            {"v": "", "s": "V"}, {"v": "", "s": "V"}, {"v": "", "s": "V"},
            {"v": "", "s": "V"}, {"v": "", "s": "V"}, {"v": "", "s": "V"},
            {"v": "", "s": "V"}], "h": 1.2})

    return rows


def _build_t61_table(types, strat_data, per_type):
    """t61_table (s6_shape2): RA테스트베드 참여 포트폴리오 (5 cols)."""
    rows = [{"cells": [
        {"v": "RA테스트베드 기준", "s": "H"},
        {"v": "모멘텀 퇴직연금", "s": "H"},
        {"v": "참여 여부", "s": "H"},
        {"v": "위험자산 \n편입한도", "s": "H"},
        {"v": "위험도 범위", "s": "H"}], "h": 1.2}]
    for t in types:
        pt = per_type[t]
        rows.append({"cells": [
            {"v": pt['tb'], "s": "V"}, {"v": t, "s": "V"},
            {"v": "참여", "s": "V"},
            {"v": f"{pt['dynamic_wt']}%", "s": "V"},
            {"v": f"{pt['min']}~{pt['max']}", "s": "V"}],
            "h": 0.8})
    return rows


def _build_t62_table(types, strat_data, per_type, grade_info):
    """t62_table (s6_shape3): RA테스트베드 자산배분 상세 (7 cols)."""
    rows = [{"cells": [
        {"v": "참여유형", "s": "H"}, {"v": "모멘텀 \n퇴직연금", "s": "H"},
        {"v": "자산 종류", "s": "H"}, {"v": "위험\n등급", "s": "H"},
        {"v": "위험자산\n여부", "s": "H"}, {"v": "비중", "s": "H"},
        {"v": "특징", "s": "H"}], "h": 1.2}]

    for t in types:
        sd = strat_data[t]
        pt = per_type[t]
        tb_label = pt['tb']
        # 줄바꿈 포함 투자자유형 레이블 (4글자 넘으면 중간에 줄바꿈)
        tb_display = tb_label.replace('투자', '\n투자') if len(tb_label) > 4 else tb_label
        dw = int(sd['dynamic_wt'])

        # 자산 그룹 구성
        asset_rows = []
        # 공격 자산 (동적)
        atk_assets = sorted(set(at for g in sd['attack'] for at in g['assets']))
        atk_ds = max(g['ds'] for g in sd['attack'])
        asset_rows.append({
            'asset': "/".join(atk_assets),
            'grade': grade_info['gnum_to_grade'].get(7 - atk_ds, ''),
            'ra': 'Y', 'weight': f'0~{dw}%', 'feature': ''
        })

        # 정적 자산
        for fs in sd['fixed']:
            for grp in fs['groups']:
                alloc = fs['mixed_wt'] * grp['wt_pct'] / 100
                ds = grp['ds']
                grade_label = grade_info['gnum_to_grade'].get(7 - ds, '')
                asset_rows.append({
                    'asset': "/".join(grp['assets']),
                    'grade': grade_label,
                    'ra': 'N',
                    'weight': f'{alloc:.1f}%',
                    'feature': ''
                })

        # 방어 자산 (동적)
        def_assets = sorted(set(at for g in sd['defense'] for at in g['assets']))
        def_ds = min(g['ds'] for g in sd['defense'])
        asset_rows.append({
            'asset': "/".join(def_assets),
            'grade': grade_info['gnum_to_grade'].get(7 - def_ds, ''),
            'ra': 'N', 'weight': f'0~{dw}%', 'feature': ''
        })

        n_rows = len(asset_rows)
        for j, ar in enumerate(asset_rows):
            cells = []
            if j == 0:
                cells += [{"v": tb_display, "s": "V", "merge": {"rs": n_rows}},
                          {"v": t, "s": "V", "merge": {"rs": n_rows}}]
            else:
                cells += [{"v": "", "s": "V"}, {"v": "", "s": "V"}]
            cells += [{"v": ar['asset'], "s": "V"},
                      {"v": ar['grade'], "s": "V"},
                      {"v": ar['ra'], "s": "V"},
                      {"v": ar['weight'], "s": "V"},
                      {"v": ar['feature'], "s": "V"}]
            rows.append({"cells": cells, "h": 0.8})

    return rows


# ═══════════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════════

def compute(input_data, base_dir='.'):
    """입력 dict → computed.json 데이터.

    Args:
        input_data: compute_input.json의 내용 (dict)
        base_dir: 상대경로 해석 기준 디렉토리
    Returns:
        dict: {per_type, patch tables, render tables}
    """

    def _resolve(p):
        return p if os.path.isabs(p) else os.path.join(base_dir, p)

    # ── manifest + semantic_map 로드 ──
    with open(_resolve(input_data['manifest_path']), encoding='utf-8') as f:
        manifest = json.load(f)
    with open(_resolve(input_data['semantic_map_path']), encoding='utf-8') as f:
        semantic_map = json.load(f)

    shape_index = _build_shape_index(manifest)
    shapes = semantic_map.get('shapes', {})

    # ── role 기반 테이블 인덱스 구축 ──
    role_map = {}  # role → table_id
    for tid, info in shapes.items():
        r = info.get('role')
        if r:
            role_map[r] = tid

    def _tbl(table_id):
        """semantic_map의 table_id → manifest 테이블 행 데이터."""
        info = shapes.get(table_id, {})
        sid = info.get('shape_id', '')
        return _get_table_rows(shape_index, sid)

    def _tbl_by_role(role):
        """role → manifest 테이블 행 데이터."""
        tid = role_map.get(role)
        if not tid:
            raise KeyError(f"semantic_map에 role='{role}' 테이블이 없습니다")
        return _tbl(tid), tid

    def _tbl_cw(table_id):
        """semantic_map의 table_id → manifest col_widths_cm."""
        info = shapes.get(table_id, {})
        sid = info.get('shape_id', '')
        return _get_table_col_widths(shape_index, sid)

    def _render_tid(role):
        """render role → semantic_map 테이블 ID (출력 키용)."""
        tid = role_map.get(role)
        if not tid:
            raise KeyError(f"semantic_map에 render role='{role}' 테이블이 없습니다")
        return tid

    # ── 도메인 상수 파싱 (role 기반으로 manifest 테이블에서 직접) ──
    grade_rows, grade_tid = _tbl_by_role('grade_definition')
    grade_info = _parse_grade_info(grade_rows)

    inv_rows, inv_tid = _tbl_by_role('investor_type')
    inv_types, tb_type_map, recipe_name = _parse_investor_types(inv_rows)

    pt_rows, pt_tid = _tbl_by_role('portfolio_type')
    types = _parse_types_from_t32(pt_rows)

    label_rows, label_tid = _tbl_by_role('investable_label')
    t44_labels = _parse_t44_labels(label_rows)

    # ── 유니버스 + 전략 데이터 로드 ──
    uni = _load_universe(_resolve(input_data['universe_path']))
    strat_data = _load_algo_data(
        _resolve(input_data['algo_data_path']), uni, types)

    # ── 유형별 위험도 계산 ──
    per_type = _compute_per_type(
        types, strat_data,
        grade_info['risk_grades'], grade_info['grade_map'],
        tb_type_map, inv_types, grade_info['gnum_to_grade'])

    # ── 결과 구축 ──
    result = {'per_type': per_type}

    # ── Patch 테이블 (deepcopy + 특정 셀 교체) ──
    result[inv_tid] = {"patches": _build_t31_patches(inv_rows, types, per_type)}
    result[pt_tid] = {"patches": _build_t32_patches(pt_rows, types, per_type, strat_data)}

    # ── Render 테이블 (완전 새로 생성, role 기반 출력 키) ──
    render_tables = [
        ('asset_risk_grade',       lambda: _build_t42_table(uni, grade_info)),
        ('investable_label',       lambda: _build_t43_table(types, per_type, inv_types, t44_labels)),
        ('asset_feature',          lambda: _build_t44_table(uni)),
        ('portfolio_summary',      lambda: _build_t51_table(types, strat_data, per_type)),
        ('asset_allocation',       lambda: _build_t52_table(types, strat_data, per_type, grade_info)),
        ('risk_calculation',       lambda: _build_t53_table(types, strat_data, per_type, grade_info)),
        ('testbed_participation',  lambda: _build_t61_table(types, strat_data, per_type)),
        ('testbed_allocation',     lambda: _build_t62_table(types, strat_data, per_type, grade_info)),
    ]
    for role, builder in render_tables:
        tid = _render_tid(role)
        result[tid] = {"rows": builder(), "col_widths_cm": _tbl_cw(tid)}

    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python build_computed.py <compute_input.json>',
              file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding='utf-8') as f:
        input_data = json.load(f)

    base_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
    result = compute(input_data, base_dir)

    out_path = input_data.get('output_path', 'computed.json')
    if not os.path.isabs(out_path):
        out_path = os.path.join(base_dir, out_path)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'computed 데이터 → {out_path}')
