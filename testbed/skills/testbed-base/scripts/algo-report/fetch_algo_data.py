#!/usr/bin/env python
"""DB → algo_data.json 생성.

서버에서 실행:
    DJANGO_SETTINGS_MODULE=fundkeeper.settings.deploy .venv/bin/python fetch_algo_data.py "국내ETF" /tmp/algo_data.json

종료 코드:
    0: 성공
    1: 0건 매치
    2: 다수 레시피 매치 (base recipe 단위 그룹핑 후 복수 레시피 감지)
"""
import sys, os, json, re

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fundkeeper.settings.deploy')

import django
django.setup()

from myportfolio.models import MyPortfolios, MyPortfolioManager, Backtest, BacktestTicker
from datetime import datetime


def _base_recipe(name):
    """유형명에서 base recipe 추출.
    '모아-국내ETF레시피1매운맛' → '국내ETF레시피'
    '모아-글로벌투자레시피3순한맛' → '글로벌투자레시피'
    """
    # '모아-' prefix 제거
    n = re.sub(r'^모아[-\s]*', '', name)
    # 맛(숫자+맛이름) 제거
    n = re.sub(r'\d+[가-힣]*맛$', '', n)
    return n.strip()


def fetch(keyword):
    """키워드로 포트폴리오를 검색하고 전략 데이터를 수집."""
    portfolios = MyPortfolios.objects.filter(name__icontains=keyword)

    if not portfolios.exists():
        print(f'ERROR: "{keyword}" 매칭 0건', file=sys.stderr)
        sys.exit(1)

    # base recipe 단위 그룹핑 → 여러 레시피가 섞이면 exit 2
    recipes = {}
    for mp in portfolios:
        base = _base_recipe(mp.name)
        recipes.setdefault(base, []).append(mp)

    if len(recipes) > 1:
        print(f'ERROR: 다수 레시피 매치 ({len(recipes)}개):', file=sys.stderr)
        for base, mps in recipes.items():
            names = [mp.name for mp in mps]
            print(f'  {base}: {names}', file=sys.stderr)
        sys.exit(2)

    selected = next(iter(recipes.values()))
    types = []
    for mp in selected:
        managers = MyPortfolioManager.objects.filter(myportfolio=mp)
        strategies = []

        for mgr in managers:
            sub = mgr.subportfolio
            if sub is None:
                continue
            bt = Backtest.objects.filter(myportfolio=sub).first()
            if not bt:
                continue

            tickers = []
            for btk in BacktestTicker.objects.filter(backtest=bt):
                asset = btk.ticker
                tickers.append({
                    'ticker': asset.ticker,
                    'description': asset.description,
                    'asset_type': asset.asset_type,
                    'dscore': asset.dscore,
                    'attack': btk.attack,
                    'defense': btk.defense,
                    'wt': float(btk.wt) if btk.wt is not None else None,
                })

            # type: 동적=dynamic, 정적=전략명(sub.name에서 파생)
            if sub.port_name == 'BAA':
                strat_type = 'dynamic'
            else:
                # sub.name에서 전략명 파생 (예: "퇴직안전자산-TDF(모아)" → "TDF")
                strat_type = sub.name
            strategies.append({
                'type': strat_type,
                'port_name': sub.port_name,
                'mixed_wt': float(mgr.mixed_wt) if mgr.mixed_wt is not None else None,
                'tickers': tickers,
            })

        types.append({
            'name': mp.name,
            'strategies': strategies,
        })

    return {
        'recipe': keyword,
        'fetched_at': datetime.now().isoformat(),
        'types': types,
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python fetch_algo_data.py <keyword> <output.json>',
              file=sys.stderr)
        sys.exit(1)

    keyword = sys.argv[1]
    output_path = sys.argv[2]

    data = fetch(keyword)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    n_types = len(data['types'])
    n_tickers = sum(len(s['tickers']) for tp in data['types']
                    for s in tp['strategies'])
    print(f'{n_types}개 유형, {n_tickers}개 종목 → {output_path}')
