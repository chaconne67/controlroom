# -*- coding: utf-8 -*-
"""서버 Django shell 스크립트 — 투자유니버스 후보 + DB 자산분류 + 계좌정보 + extra 분류.
실행(SSH):
  scp fetch_universe.py {HOST}:/tmp/
  ssh {HOST} "cd {PROJECT} && SCHEDULE_ID=33 GROUP=svr EXTRA_TICKERS=069500,091160 .venv/bin/python manage.py shell < /tmp/fetch_universe.py" > out.txt
  로컬: out.txt의 ===JSON=== 이후를 파싱 → universe→uni_full.json, extra→extra_db.json, accounts 검증.

환경변수:
  SCHEDULE_ID  회차 PK (필수)
  GROUP        kr|svr|us (기본 kr)
  EXTRA_TICKERS  기존 투자유니버스 티커 CSV (prepare_local_data의 existing_uni.json에서, 후보에 없는 종목 분류 보강용)

출력(stdout, ===JSON=== 다음 줄):
  {universe:[...], accounts:[...], extra:[...], parents:[...]}
  universe/extra[]: ticker,isin,name,market,asset_class,asset_type,dscore,is_danger,attack,defense,watch
  accounts[]: pk,desc,account_no,start_money,value,group(안정/중립/적극),idx(1~3)

★ 투자유니버스 = 레시피의 모든 서브전략(매운맛=적극/중간맛=중립/순한맛=안전) BacktestTicker 합집합.
  데이터모델: MyAccount.myportfolio → 부모MP → MyPortfolioManager(subportfolio) → Backtest → BacktestTicker.
  적극=accounts[0:3]→부모MP, 중립=[3:6], 안정=[6:9]. safe_asset=미국 BIL 프록시(실거래는 KR 안전자산 대체)→무관.
  해외상장(market!=KRX/KOSPI/KOSDAQ, 예 SPY/EFA/AGG/EEM)은 watch-only → 빌더가 is_domestic으로 제외.
"""
import os, json
from myaccount.models import MyAccount
from myportfolio.models import MyPortfolioManager, Backtest, BacktestTicker
from xmodules.test_bed.test_bed import TestBed2

SCHEDULE_ID = int(os.environ['SCHEDULE_ID'])
GROUP = os.environ.get('GROUP', 'kr')
EXTRA = [t.strip() for t in os.environ.get('EXTRA_TICKERS', '').split(',') if t.strip()]

tb = TestBed2(schedule_id=SCHEDULE_ID)
pks = {'kr': tb.accounts_kr, 'svr': tb.accounts_svr, 'us': tb.accounts_us}[GROUP]
grp_of = {pk: (('적극' if i < 3 else '중립' if i < 6 else '안정'), (i % 3) + 1) for i, pk in enumerate(pks)}

accounts, parents = [], set()
for pk in pks:
    a = MyAccount.objects.get(id=pk)
    accounts.append({'pk': pk, 'desc': a.description, 'account_no': a.account_no,
                     'start_money': a.start_money, 'value': a.value,
                     'group': grp_of[pk][0], 'idx': grp_of[pk][1]})
    parents.add(a.myportfolio_id)

def cls(a):
    return {'ticker': a.ticker, 'isin': a.isin_code, 'name': a.description, 'market': a.market,
            'asset_class': a.asset_class, 'asset_type': a.asset_type, 'dscore': a.dscore, 'is_danger': a.is_danger}

universe = {}
for pid in parents:
    for m in MyPortfolioManager.objects.filter(myportfolio_id=pid):
        sub = m.subportfolio
        if not sub:
            continue
        for bt in Backtest.objects.filter(myportfolio=sub):
            for btt in BacktestTicker.objects.filter(backtest=bt).select_related('ticker'):
                a = btt.ticker
                d = universe.setdefault(a.ticker, dict(cls(a), attack=0, defense=0, watch=0))
                d['attack'] += 1 if btt.attack else 0
                d['defense'] += 1 if btt.defense else 0
                d['watch'] += 1 if btt.watch else 0

from simulation.models import Asset
extra = []
for tk in EXTRA:
    if tk in universe or tk in ('None', 'CASH', ''):
        continue
    a = Asset.objects.filter(ticker=tk).first()
    if a:
        extra.append(dict(cls(a), attack=0, defense=0, watch=0))

print('===JSON===')
print(json.dumps({'universe': list(universe.values()), 'accounts': accounts,
                  'extra': extra, 'parents': sorted(parents)}, ensure_ascii=False))
