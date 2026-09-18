"""build_computed + prepare_components 통합 스크립트.

manifest를 한 번만 읽고, computed 결과를 디스크 I/O 없이 메모리에서 직접 전달.

사용법:
    python build_and_prepare.py pipeline_input.json

입력 JSON (pipeline_input.json):
    {
      "manifest_path": "shapes_manifest.json",
      "semantic_map_path": "semantic_map.json",
      "universe_path": "투자유니버스.xlsx",
      "algo_data_path": "algo_data.json",
      "computed_path": "computed.json",       (optional, 디버깅용 중간 산출물)
      "output_path": "components.json"
    }

출력:
  - components.json (필수)
  - computed.json (computed_path 지정 시)

종료 코드:
  0 = 성공 + 검증 통과
  1 = 입력 파일 누락 또는 파싱 실패
  2 = compute 실패 (semantic_map role 매핑 등)
  3 = prepare 실패 (component 조립)
  4 = 검증 실패 (구조 불일치)
"""
import sys, json, os, time

sys.stdout.reconfigure(encoding='utf-8')

# 같은 디렉토리의 모듈 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_computed
import prepare_components


def validate_computed(computed, semantic_map):
    """computed.json 구조 검증. Returns (ok, errors)."""
    errors = []
    shapes = semantic_map.get('shapes', {})

    # per_type 존재
    if 'per_type' not in computed:
        errors.append('per_type 키 누락')
    else:
        pt = computed['per_type']
        if not pt:
            errors.append('per_type가 비어있음')
        for t, info in pt.items():
            for key in ('min', 'max', 'grade', 'gnum'):
                if key not in info:
                    errors.append(f'per_type[{t}]에 {key} 누락')

    # render/patch 테이블 키 존재
    for tid, info in shapes.items():
        action = info.get('action')
        if action == 'render':
            if tid not in computed:
                errors.append(f'render 테이블 {tid} 누락')
            elif 'rows' not in computed[tid]:
                errors.append(f'{tid}에 rows 키 누락')
        elif action == 'patch':
            if tid not in computed:
                errors.append(f'patch 테이블 {tid} 누락')
            elif 'patches' not in computed[tid]:
                errors.append(f'{tid}에 patches 키 누락')

    return len(errors) == 0, errors


def validate_components(components, semantic_map):
    """components.json 구조 검증. Returns (ok, errors)."""
    errors = []
    component_order = semantic_map.get('component_order', [])

    # 개수 일치
    expected = len(component_order)
    actual = len(components)
    if actual != expected:
        errors.append(f'컴포넌트 수 불일치: expected={expected}, actual={actual}')

    # 타입별 카운트
    types = {}
    for c in components:
        t = c.get('type', 'unknown')
        types[t] = types.get(t, 0) + 1

    # 최소 heading, table 존재
    if types.get('heading', 0) == 0:
        errors.append('heading 컴포넌트가 없음')
    if types.get('table', 0) == 0:
        errors.append('table 컴포넌트가 없음')

    # 빈 테이블 확인
    for i, c in enumerate(components):
        if c.get('type') == 'table' and not c.get('rows'):
            errors.append(f'components[{i}]: 빈 테이블 (rows 없음)')

    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print('Usage: python build_and_prepare.py <pipeline_input.json>',
              file=sys.stderr)
        sys.exit(1)

    # ── 입력 로드 ──
    try:
        with open(sys.argv[1], encoding='utf-8') as f:
            input_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f'[ERROR] 입력 파일 읽기 실패: {e}', file=sys.stderr)
        sys.exit(1)

    base_dir = os.path.dirname(os.path.abspath(sys.argv[1]))

    def _resolve(p):
        return p if os.path.isabs(p) else os.path.join(base_dir, p)

    # 필수 파일 존재 확인
    required = ['manifest_path', 'semantic_map_path', 'universe_path', 'algo_data_path']
    for key in required:
        if key not in input_data:
            print(f'[ERROR] 입력 JSON에 {key} 누락', file=sys.stderr)
            sys.exit(1)
        path = _resolve(input_data[key])
        if not os.path.exists(path):
            print(f'[ERROR] 파일 없음: {path}', file=sys.stderr)
            sys.exit(1)

    # ── Phase 1: compute ──
    t0 = time.time()
    try:
        # build_computed.compute()는 manifest, semantic_map을 내부에서 로드
        computed = build_computed.compute(input_data, base_dir)
    except Exception as e:
        print(f'[ERROR] compute 실패: {e}', file=sys.stderr)
        sys.exit(2)
    t1 = time.time()
    print(f'[Phase 1] compute 완료 ({t1 - t0:.1f}s)')

    # semantic_map 로드 (검증 + prepare용)
    with open(_resolve(input_data['semantic_map_path']), encoding='utf-8') as f:
        semantic_map = json.load(f)

    # computed 검증
    ok, errors = validate_computed(computed, semantic_map)
    if not ok:
        print('[FAIL] computed 검증 실패:', file=sys.stderr)
        for e in errors:
            print(f'  - {e}', file=sys.stderr)
        sys.exit(4)
    print(f'[Phase 1] computed 검증 통과 (per_type: {list(computed.get("per_type", {}).keys())})')

    # computed.json 중간 산출물 저장 (선택)
    computed_path = input_data.get('computed_path')
    if computed_path:
        cp = _resolve(computed_path)
        with open(cp, 'w', encoding='utf-8') as f:
            json.dump(computed, f, ensure_ascii=False, indent=2)
        print(f'[Phase 1] computed → {cp}')

    # ── Phase 2: prepare components ──
    # manifest를 다시 로드 (prepare_components.build가 필요)
    with open(_resolve(input_data['manifest_path']), encoding='utf-8') as f:
        manifest = json.load(f)

    t2 = time.time()
    try:
        components = prepare_components.build(semantic_map, computed, manifest)
    except Exception as e:
        print(f'[ERROR] prepare 실패: {e}', file=sys.stderr)
        sys.exit(3)
    t3 = time.time()
    print(f'[Phase 2] prepare 완료 ({t3 - t2:.1f}s)')

    # components 검증
    ok, errors = validate_components(components, semantic_map)
    if not ok:
        print('[FAIL] components 검증 실패:', file=sys.stderr)
        for e in errors:
            print(f'  - {e}', file=sys.stderr)
        sys.exit(4)

    types = {}
    for c in components:
        t = c.get('type', 'unknown')
        types[t] = types.get(t, 0) + 1
    print(f'[Phase 2] components 검증 통과 ({len(components)}개: {types})')

    # ── 출력 ──
    out_path = _resolve(input_data.get('output_path', 'components.json'))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(components, f, ensure_ascii=False, indent=2)

    total = t3 - t0
    print(f'[완료] {len(components)}개 컴포넌트 → {out_path} (총 {total:.1f}s)')


if __name__ == '__main__':
    main()
