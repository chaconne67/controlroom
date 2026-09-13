# KRX 투자전략 백테스트 프로젝트 계획서

## 프로젝트 개요

### 목표
- KRX 투자전략 문서에 정의된 체계적인 포트폴리오 전략의 백테스트 시스템 구축
- 주간 리밸런싱 기반의 다중 종목 관리 시스템 개발
- 분할 익절/손절 시스템을 포함한 완전한 투자 전략 시뮬레이션

### 현재 상황
- **기존 코드**: `KrxTickerBacktest` 클래스가 단일 종목 백테스트 기능 제공
- **미완성 부분**: 포트폴리오 관리 로직이 주석 처리된 상태
- **요구사항**: 전략 문서의 복합적인 포트폴리오 전략 구현 필요

## 시스템 아키텍처

### 클래스 구조
```
KrxPortfolioBacktest(KrxTickerBacktest)
├── PortfolioManager          # 포트폴리오 관리
├── RebalancingEngine         # 리밸런싱 엔진
├── RiskManager              # 리스크 관리
├── TradeExecutor            # 거래 실행
├── PerformanceAnalyzer      # 성과 분석
└── ReportGenerator          # 리포트 생성
```

### KrxPortfolioBacktest 메인 클래스
```python
class KrxPortfolioBacktest:
    def __init__(self, params):
        self.params = params
        self.start_date = params['start_date']
        self.end_date = params['end_date']
        self.initial_fund = params['fund']
        
        # 컴포넌트 초기화 (모든 컴포넌트에 params 전달)
        self.portfolio_manager = PortfolioManager(params)
        self.rebalancing_engine = RebalancingEngine(params)
        self.risk_manager = RiskManager(params)
        self.trade_executor = TradeExecutor(params)
        self.performance_analyzer = PerformanceAnalyzer(params)
        
    def run_backtest(self):
        # 백테스트 실행 로직
        pass
```

## 개발 단계별 계획

### 1단계: 핵심 포트폴리오 관리 시스템 (1주차)

#### A. PortfolioManager 클래스
- **기능**:
  - params 딕셔너리 기반 설정 관리
  - 최대 종목 수 제한 관리 (params['max_positions'])
  - 균등 자금 배분 로직 (params['fund'])
  - 포지션 상태 추적 (진입/보유/청산)
  - 빈 자리 관리 (손절/익절 후 신규 진입 가능)
  - **전체 데이터 활용**: 멀티인덱스 기반 빠른 데이터 접근

- **주요 메서드**:
  ```python
  def __init__(self, params):
      self.params = params
      # 전체 데이터 로드 및 최적화
      self.krx_data = self.load_and_optimize_data()
      
  def add_position(self, ticker, price, qty, date)
  def remove_position(self, ticker, reason)
  def get_available_slots(self)  # params['max_positions'] 활용
  def calculate_position_size(self)  # params['fund'] 활용
  def update_portfolio_value(self, date)
  def get_market_data(self, ticker, date)  # 최적화된 데이터 접근
  ```

#### B. Position 클래스
- **속성**:
  - ticker, entry_price, qty, entry_date
  - stoploss_price, takeprofit_price
  - status (active, partial_exit, closed)
  - partial_exit_qty (분할 익절용)

### 2단계: 리밸런싱 엔진 (2주차)

#### A. RebalancingEngine 클래스
- **기능**:
  - 매주 지정 요일 (수요일, weekday=2) 리밸런싱 실행
  - 필터링 조건 적용 및 종목 선별
  - 신규 진입 종목 결정

- **필터링 조건**:
  - 정배열: 종가 > 5일선 > 20일선 > 120일선
  - 당일 양봉: 종가 > 시가
  - 최소 거래대금 조건
  - 기관/외국인 순매수 조건

- **주요 메서드**:
  ```python
  def __init__(self, params):
      self.params = params
      
  def is_rebalancing_day(self, date)  # params['rebalance_day'] 활용
  def filter_stocks(self, date)  # params['min_volume'], params['min_value'] 활용
  def score_and_rank(self, filtered_stocks)  # params['ma_short'], params['ma_long'] 활용
  def select_new_positions(self, available_slots)
  ```

### 3단계: 손절/익절 시스템 (3주차)

#### A. RiskManager 클래스
- **손절 시스템**:
  - 최근 n개 봉 최저가 돌파 감지 (params['stoploss_lookback'])
  - 역배열 상황 감지
  - 2% Rule 적용 (params['max_loss_per_position'])

- **익절 시스템**:
  - 손익비 기반 익절가 설정 (params['profit_loss_ratio'])
  - 분할 익절: 1차 익절 후 트레일링 스탑 (params['partial_profit_ratio'])
  - 2차 청산: 잔량의 손절 조건 관리

- **주요 메서드**:
  ```python
  def __init__(self, params):
      self.params = params
      
  def check_stoploss_conditions(self, position, current_data)  # params['stoploss_lookback'] 활용
  def check_takeprofit_conditions(self, position, current_data)  # params['profit_loss_ratio'] 활용
  def calculate_stoploss_price(self, ticker, entry_price, date)
  def calculate_takeprofit_price(self, entry_price, stoploss_price)  # params['profit_loss_ratio'] 활용
  def apply_trailing_stop(self, position, current_price)  # params['partial_profit_ratio'] 활용
  ```

### 4단계: 거래 실행 엔진 (4주차)

#### A. TradeExecutor 클래스
- **기능**:
  - 종가/장중 진입 처리 (params['entry_price_type'])
  - 슬리피지 및 거래비용 반영 (params['commission_rate'], params['slippage'])
  - 갭 상황 처리 (갭 하락/상승 시 시가 거래)

- **주요 메서드**:
  ```python
  def __init__(self, params):
      self.params = params
      
  def execute_entry(self, ticker, date, entry_type='close')  # params['entry_price_type'] 활용
  def execute_exit(self, position, date, exit_reason)  # params['exit_price_type'] 활용
  def calculate_execution_price(self, ticker, date, order_type)  # params 기반 가격 결정
  def handle_gap_situation(self, position, date)
  def calculate_fees(self, trade_value)  # params['commission_rate'] 활용
  ```

### 5단계: 성과 분석 시스템 (5주차)

#### A. PerformanceAnalyzer 클래스
- **분석 지표**:
  - 일별/월별/연별 수익률
  - 최대 낙폭 (MDD)
  - 샤프 비율
  - 승률 및 평균 손익비
  - 거래 통계 (거래 횟수, 평균 보유 기간)
  - 벤치마크 대비 성과 분석

- **주요 메서드**:
  ```python
  def __init__(self, params):
      self.params = params
      
  def calculate_returns(self, portfolio_values)
  def calculate_mdd(self, portfolio_values)
  def calculate_sharpe_ratio(self, returns)  # params['risk_free_rate'] 활용
  def calculate_win_rate(self, trades)
  def generate_trade_statistics(self, trades)
  def compare_to_benchmark(self)  # params['benchmark'] 활용
  ```

## 데이터 구조 설계

### Params 딕셔너리 구조
모든 백테스트 설정을 하나의 딕셔너리로 관리합니다:

```python
params = {
    # 기본 설정
    'start_date': '2020-01-01',
    'end_date': '2024-12-31',
    'fund': 100000000,  # 초기 자금
    
    # 포트폴리오 관리
    'max_positions': 10,  # 최대 보유 종목 수
    
    # 리밸런싱 설정
    'rebalance_day': 'Wednesday',  # 리밸런싱 요일
    'min_volume': 1000000,  # 최소 거래량
    'min_value': 50000000,  # 최소 거래대금
    
    # 기술적 지표
    'ma_short': 5,   # 단기 이동평균
    'ma_long': 20,   # 장기 이동평균
    'volume_ma': 20, # 거래량 이동평균
    
    # 리스크 관리
    'stop_loss_pct': -0.05,      # 손절 비율 (-5%)
    'take_profit_pct': 0.10,     # 익절 비율 (+10%)
    'partial_profit_pct': 0.05,  # 분할 익절 비율 (+5%)
    'partial_ratio': 0.5,        # 분할 익절 비율 (50%)
    'profit_loss_ratio': 2.5,    # 손익비 (1:2.5)
    'max_loss_per_position': 0.02, # 종목당 최대 손실 (2%)
    'stoploss_lookback': 10,     # 손절 기준 봉 수
    
    # 거래 실행
    'buy_price_type': 'open',    # 매수가격 기준 (open/high/low/close)
    'sell_price_type': 'open',   # 매도가격 기준
    'commission_rate': 0.00015,  # 수수료율
    'tax_rate': 0.0025,         # 세금율 (매도시)
    'slippage': 0.001,          # 슬리피지
    
    # 성과 분석
    'risk_free_rate': 0.02,     # 무위험 수익률
    'benchmark': 'KOSPI',       # 벤치마크
}
```

### 전체 데이터 구조
```python
# 전체 KRX 데이터 로드 및 인덱싱
self.krx_data = pd.DataFrame(self.do_query_fast('select * from `stocks`', 'price'))
self.krx_data['Date'] = pd.to_datetime(self.krx_data['Date'])
self.krx_data.set_index(['Date', 'ticker'], inplace=True)
self.krx_data.sort_index(inplace=True)

# 기술적 지표 사전 계산
self.krx_data = self.krx_data.groupby('ticker').apply(self.calculate_technical_indicators)
```

### 백테스트 DataFrame 구조
```python
columns = [
    'Date',           # 날짜
    'weekday',        # 요일
    'is_rebalancing', # 리밸런싱 일 여부
    'positions',      # 보유 포지션 리스트
    'trades',         # 당일 거래 내역
    'portfolio_value', # 포트폴리오 총 가치
    'cash',           # 현금
    'invested_amount', # 투자 금액
    'daily_return',   # 일일 수익률
    'cumulative_return' # 누적 수익률
]
```

### Position 데이터 구조
```python
position = {
    'ticker': str,
    'entry_date': datetime,
    'entry_price': float,
    'qty': int,
    'stoploss_price': float,
    'takeprofit_price': float,
    'status': str,  # 'active', 'partial_exit', 'closed'
    'partial_exit_qty': int,
    'trailing_stop_price': float
}
```

## 구현 우선순위

### Phase 1: 기본 시스템 (1-3주차)
1. PortfolioManager 구현
2. RebalancingEngine 기본 기능
3. RiskManager 손절/익절 로직

### Phase 2: 고도화 (4-5주차)
1. TradeExecutor 완성
2. PerformanceAnalyzer 구현
3. 통합 테스트 및 디버깅

### Phase 3: 확장 기능 (6주차 이후)
1. 파라미터 최적화 기능
2. 시각화 및 리포팅
3. 다양한 전략 변형 테스트

## 기술적 고려사항

### 성능 최적화

#### A. 데이터 로딩 전략
- **전체 데이터 로드**: `krx_data = pd.DataFrame(self.do_query_fast('select * from `stocks`', 'price'))`
- **기존 방식 개선**: 개별 종목별 반복 쿼리 → 전체 데이터 한 번 로드
- **메모리 최적화**: 필요한 기간만 필터링하여 메모리 사용량 제어

#### B. 데이터 구조 최적화
- **멀티인덱스 활용**: (Date, ticker) 기준 인덱싱으로 빠른 데이터 접근
- **벡터화 연산**: pandas groupby 및 transform 활용
- **캐싱 전략**: 계산된 기술적 지표 캐싱

#### C. 쿼리 최적화 비교
```python
# 기존 방식 (비효율적)
def get_ohlc(self, ticker, date):
    q = f'select * from `stocks` where Date="{date}" and ticker="{ticker}"'
    return pd.DataFrame(self.do_query_fast(q, 'price'))

# 개선된 방식 (효율적)
def __init__(self):
    self.krx_data = pd.DataFrame(self.do_query_fast('select * from `stocks`', 'price'))
    self.krx_data.set_index(['Date', 'ticker'], inplace=True)
    
def get_ohlc(self, ticker, date):
    return self.krx_data.loc[(date, ticker)]
```

#### D. 성능 개선 효과
- **쿼리 횟수**: N번 → 1번 (N = 백테스트 일수 × 종목 수)
- **예상 성능**: 5년 백테스트 기준 10분 → 30초 이내
- **메모리 사용**: 예측 가능한 메모리 사용량

### 확장성
- 모듈화된 설계로 새로운 전략 추가 용이
- 설정 파일을 통한 파라미터 관리
- 플러그인 방식의 필터링 조건 추가

### 테스트 전략
- 단위 테스트: 각 클래스별 기능 테스트
- 통합 테스트: 전체 백테스트 시나리오 테스트
- 성능 테스트: 대용량 데이터 처리 테스트

## 예상 결과물

### 1. 완성된 백테스트 시스템
- 전략 문서의 모든 요구사항 구현
- 실제 거래와 유사한 시뮬레이션 환경

### 2. 성과 분석 리포트
- 상세한 백테스트 결과
- 리스크 지표 및 수익성 분석
- 거래 패턴 분석

### 3. 확장 가능한 프레임워크
- 새로운 전략 추가 가능
- 파라미터 최적화 지원
- 실시간 거래 시스템 연동 가능

## 리스크 및 대응방안

### 기술적 리스크
- **데이터 품질 문제**: 데이터 검증 로직 강화
- **성능 이슈**: 프로파일링 및 최적화
- **복잡성 증가**: 모듈화 및 문서화 강화

### 일정 리스크
- **개발 지연**: 단계별 마일스톤 설정
- **요구사항 변경**: 유연한 아키텍처 설계

## 성공 기준

1. **기능적 완성도**: 전략 문서의 모든 요구사항 구현
2. **성능**: 5년 이상 데이터 백테스트 30초 이내 완료
3. **정확성**: 수동 계산 결과와 99% 이상 일치
4. **확장성**: 새로운 필터링 조건 1시간 이내 추가 가능

## 사용 예시

### 기본 백테스트 실행
```python
# params 딕셔너리 설정
params = {
    'start_date': '2020-01-01',
    'end_date': '2024-12-31',
    'fund': 100000000,
    'max_positions': 10,
    'rebalance_day': 'Wednesday',
    'min_volume': 1000000,
    'min_value': 50000000,
    'ma_short': 5,
    'ma_long': 20,
    'stop_loss_pct': -0.05,
    'take_profit_pct': 0.10,
    'commission_rate': 0.00015,
    'tax_rate': 0.0025,
    'risk_free_rate': 0.02,
    'benchmark': 'KOSPI'
}

# 백테스트 실행
backtest = KrxPortfolioBacktest(params)
results = backtest.run_backtest()

# 결과 분석
print(f"총 수익률: {results['total_return']:.2%}")
print(f"연간 수익률: {results['annual_return']:.2%}")
print(f"최대 낙폭: {results['max_drawdown']:.2%}")
print(f"샤프 비율: {results['sharpe_ratio']:.2f}")
```

### 파라미터 최적화 예시
```python
# 여러 파라미터 조합 테스트
parameter_sets = [
    {'ma_short': 5, 'ma_long': 20, 'max_positions': 10},
    {'ma_short': 3, 'ma_long': 15, 'max_positions': 8},
    {'ma_short': 7, 'ma_long': 25, 'max_positions': 12},
]

results = []
for param_set in parameter_sets:
    # 기본 params에 테스트 파라미터 업데이트
    test_params = params.copy()
    test_params.update(param_set)
    
    # 백테스트 실행
    backtest = KrxPortfolioBacktest(test_params)
    result = backtest.run_backtest()
    results.append(result)
    
# 최적 파라미터 선택
best_result = max(results, key=lambda x: x['sharpe_ratio'])
print(f"최적 샤프 비율: {best_result['sharpe_ratio']:.2f}")
```

---

*이 계획서는 KRX 투자전략 백테스트 프로젝트의 전체적인 로드맵을 제시하며, 실제 개발 과정에서 세부사항은 조정될 수 있습니다.*