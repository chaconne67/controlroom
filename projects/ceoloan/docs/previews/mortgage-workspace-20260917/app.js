/* Synthetic review only. Existing listing and company modal presentation are preserved.
   No application requests, real messages, DB writes, or underwriting calculations. */
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const companies=[
 {id:'hotel',name:'주식회사 예시호텔',rep:'김○○',region:'경기 수원시',industry:'호텔업',address:'경기 수원시 · 예시로 120',phone:'031-000-0000',mobile:'010-••••-1200',contact:'재무 담당자',sms:true,relation:'법인 지분 3/10 확인',status:'verified',properties:['hotel-building','hotel-land'],agent:'김담당',sales:'이영업',revenue:'48.2억원',credit:'BB+',memo:'운영자금 확보를 위한 담보 조건 비교 희망',sourceDate:'2026.09.17'},
 {id:'trust',name:'주식회사 예시리조트',rep:'박○○',region:'인천 중구',industry:'휴양 숙박업',address:'인천 중구 · 샘플해안로 38',phone:'032-000-0000',mobile:'010-••••-2300',contact:'재무 담당자',sms:true,relation:'위탁자 확인',status:'verified',properties:['trust-building'],agent:'김담당',sales:'정영업',revenue:'63.4억원',credit:'BB',memo:'신탁 계약과 우선수익권 조건 확인 필요',sourceDate:'2026.09.16'},
 {id:'draft',name:'주식회사 예시스테이',rep:'이○○',region:'서울 강서구',industry:'숙박업',address:'서울 강서구 · 예시길 27',phone:'02-000-0000',mobile:'010-••••-3400',contact:'회사 담당자',sms:true,relation:'주소로 연결',status:'draft',properties:['draft-building','draft-land'],agent:'박담당',sales:'미배정',revenue:'19.7억원',credit:'확인 자료 없음',memo:'공유자와 공동담보목록 원문 검토 필요',sourceDate:'2026.09.17'},
 {id:'unit',name:'주식회사 예시산업',rep:'최○○',region:'서울 금천구',industry:'제조업',address:'서울 금천구 · 샘플산업로 12',phone:'02-000-0001',mobile:'010-••••-4500',contact:'재무 담당자',sms:true,relation:'법인 소유 확인',status:'verified',properties:['unit-room'],agent:'박담당',sales:'미배정',revenue:'82.1억원',credit:'BBB-',memo:'전유부분과 대지권의 담보 범위 확인',sourceDate:'2026.09.15'},
 {id:'empty',name:'주식회사 예시관광',rep:'정○○',region:'경기 가평군',industry:'숙박업',address:'경기 가평군 · 예시호수길 8',phone:'031-000-0002',mobile:'',contact:'회사 일반전화',sms:false,relation:'연결 확인 전',status:'missing',properties:[],agent:'김담당',sales:'미배정',revenue:'자료 수집 대기',credit:'자료 수집 대기',memo:'문자 수신 연락처 확인 필요',sourceDate:''},
 {id:'linked',name:'주식회사 예시파트너스',rep:'윤○○',region:'경기 시흥시',industry:'숙박업',address:'경기 시흥시 · 샘플중앙로 44',phone:'031-000-0003',mobile:'',contact:'회사 일반전화',sms:false,relation:'주소로 연결',status:'verified',properties:['linked-building'],agent:'박담당',sales:'미배정',revenue:'12.6억원',credit:'B+',memo:'회사와 등기 소유자의 관계 확인 필요',sourceDate:'2026.09.14'}
];
const properties={
 'hotel-building':{code:'A-01',type:'건물',name:'예시호텔 본관',address:'경기 수원시 · 예시로 120',kind:'숙박시설 · 지상 5층 / 지하 1층',area:'연면적 1,842.60㎡',group:'공동담보 A',pages:8,source:'2026.09.17'},
 'hotel-land':{code:'A-02',type:'토지',name:'예시호텔 대지',address:'경기 수원시 · 예시동 120-1',kind:'대 · 소유권',area:'토지면적 622.40㎡',group:'공동담보 A',pages:6,source:'2026.09.17'},
 'trust-building':{code:'B-01',type:'건물',name:'예시리조트 본관',address:'인천 중구 · 샘플해안로 38',kind:'숙박시설 · 신탁 부동산',area:'연면적 2,610.20㎡',group:'공동 1순위',pages:28,source:'2026.09.16',trust:true},
 'draft-building':{code:'C-01',type:'건물',name:'예시스테이 건물',address:'서울 강서구 · 예시길 27',kind:'숙박시설',area:'검토 대기',pages:10,source:'2026.09.17',draft:true},
 'draft-land':{code:'C-02',type:'토지',name:'예시스테이 대지',address:'서울 강서구 · 예시동 27-3',kind:'대',area:'검토 대기',pages:7,source:'2026.09.17',draft:true},
 'unit-room':{code:'D-01',type:'호실',name:'예시산업센터 501호',address:'서울 금천구 · 샘플산업로 12, 501호',kind:'집합건물 · 업무시설',area:'전유면적 61.78㎡',group:'본 호실만',pages:3,source:'2026.09.15',unit:true},
 'linked-building':{code:'E-01',type:'건물',name:'주소로 연결된 건물',address:'경기 시흥시 · 샘플중앙로 44',kind:'숙박시설',area:'연면적 921.00㎡',group:'본건 부동산',pages:5,source:'2026.09.14',linked:true}
};

// Fictional display examples. Each row is an explicit fact; no inferred owners,
// loan balances, dates, or per-property allocations.
const commonHotelOwners=[
 {name:'주식회사 예시호텔',share:'3/10',relation:'회사 지분',kind:'매매',cause:'2021.06.18',receipt:'2021.07.02',page:3},
 {name:'공유자 박○○',share:'5/10',relation:'회사와 관계 미확인',kind:'매매',cause:'2021.06.18',receipt:'2021.07.02',page:3},
 {name:'공유자 이○○',share:'2/10',relation:'회사와 관계 미확인',kind:'매매',cause:'2021.06.18',receipt:'2021.07.02',page:4}
];
const commonHotelTransactions=[
 {kind:'매매',buyer:'예시호텔 외 2명',seller:'종전 소유자 최○○',cause:'2021.06.18',receipt:'2021.07.02',amount:'48억원',scope:'본관 + 대지 2개 물건의 전체 계약금액',allocation:'물건별 배분금액 미기재',list:'매매목록 예시 2021-001',page:6}
];
const commonHotelMortgage={rank:'을구 2',kind:'근저당권',party:'가상은행',debtor:'주식회사 예시호텔',amountLabel:'채권최고액',amount:'36억원',scope:'공동담보 A · 본관 + 대지',status:'현재 기재',cause:'2023.04.10',receipt:'2023.04.12',page:5};
const commonHotelHistory=[
 {cause:'2023.04.10',receipt:'2023.04.12',target:'을구 1 근저당권',change:'해지에 따른 말소',detail:'말소 전 채권최고액 24억원 · 현재 권리에서 제외',page:5},
 {cause:'2023.04.10',receipt:'2023.04.12',target:'을구 2 근저당권',change:'설정',detail:'공동담보 A · 채권최고액 36억원',page:5}
];
Object.assign(properties['hotel-building'],{
 owners:commonHotelOwners,transactions:commonHotelTransactions,
 rights:[commonHotelMortgage,{rank:'을구 3',kind:'전세권',party:'예시임차 주식회사',debtor:'해당 없음',amountLabel:'전세금',amount:'1억원',scope:'본관 1층 일부 · 120㎡',status:'현재 기재',cause:'2024.01.15',receipt:'2024.01.18',page:5}],
 events:commonHotelHistory,history:'말소사항 포함 · 현재 등기기록 범위',linkBasis:'법인 식별정보와 지분 대조 완료',
 references:[{name:'공동담보목록 A',state:'수령 · 현재 구성 대조 완료',page:7},{name:'매매목록 예시 2021-001',state:'수령 · 전체 계약 범위 확인',page:6}]
});
Object.assign(properties['hotel-land'],{
 owners:commonHotelOwners,transactions:commonHotelTransactions,rights:[commonHotelMortgage],
 events:commonHotelHistory,history:'말소사항 포함 · 현재 등기기록 범위',linkBasis:'법인 식별정보와 지분 대조 완료',
 references:[{name:'공동담보목록 A',state:'수령 · 현재 구성 대조 완료',page:6}]
});
Object.assign(properties['trust-building'],{
 owners:[{name:'가상신탁 주식회사',share:'1/1',relation:'수탁자 · 회사는 위탁자',kind:'신탁',cause:'2025.07.21',receipt:'2025.07.22',page:3}],
 transactions:[],rights:[],events:[{cause:'2025.07.21',receipt:'2025.07.22',target:'갑구 3 소유권',change:'신탁 이전',detail:'수탁자 명의로 이전 · 매매로 분류하지 않음',page:3}],
 history:'이기 후 등기기록 · 이전 등기 전체 이력은 별도 확인',linkBasis:'신탁원부의 회사 식별정보와 위탁자 대조 완료',
 references:[{name:'신탁원부 예시 2025-010',state:'수령 · 등기와 함께 보관',page:8}],
 trustRoles:[['위탁자','주식회사 예시리조트'],['수탁자','가상신탁 주식회사'],['수익자','주식회사 예시리조트']],
 benefits:[{rank:'공동 1순위',party:'가상금융 A',amount:'30억원',scope:'원부에 기재된 채권 A',page:9},{rank:'공동 1순위',party:'가상금융 B',amount:'12억원',scope:'원부에 기재된 채권 B',page:9},{rank:'공동 1순위',party:'가상금융 C',amount:'18억원',scope:'원부에 기재된 채권 C',page:9}]
});
for(const id of ['draft-building','draft-land'])Object.assign(properties[id],{
 history:'말소사항 포함 · 이기 이전 이력 확인 필요',linkBasis:'회사 주소로 조회 · 회사 소유 여부 미확인',
 references:[{name:'공동담보목록',state:'미수령 · 담보 전체 범위 미확인'}]
});
Object.assign(properties['unit-room'],{
 owners:[{name:'주식회사 예시산업',share:'1/1',relation:'법인 소유 확인',kind:'매매',cause:'2017.09.28',receipt:'2017.09.29',page:2}],
 transactions:[],rights:[{rank:'을구 1',kind:'근저당권',party:'가상은행',debtor:'주식회사 예시산업',amountLabel:'채권최고액',amount:'5.04억원',scope:'건물만 담보 · 대지권 제외',status:'현재 기재',cause:'2017.09.28',receipt:'2017.09.29',page:2}],
 events:[{cause:'확인 자료 없음',receipt:'2022.02.21 (주기 등기일)',target:'을구 1 근저당권',change:'담보 범위 주기',detail:'건물만에 관한 등기임 · 신규 대출 발생으로 해석하지 않음',page:3}],
 history:'말소사항 포함 · 현재 등기기록 범위',linkBasis:'법인 식별정보 대조 완료',references:[]
});
Object.assign(properties['linked-building'],{
 owners:[{name:'개인 소유자 이○○',share:'1/1',relation:'회사와 관계 미확인',kind:'매매',cause:'2008.04.12',receipt:'2008.04.16',page:2}],
 transactions:[],rights:[{rank:'갑구 6',kind:'가압류',party:'가상채권 주식회사',debtor:'개인 소유자 이○○',amountLabel:'청구금액',amount:'2억원',scope:'등기명의자의 본건 부동산',status:'현재 기재',cause:'2025.01.09',receipt:'2025.01.13',page:4}],
 events:[],history:'말소사항 포함 · 현재 등기기록 범위',linkBasis:'회사 주소로 조회 · 회사 소유로 확인되지 않았습니다.',references:[]
});
const financials={
 hotel:{years:[2023,2024,2025],rating:'BB+',ratio:'184.2',rows:[
  ['매출액','백만원',[4100,4460,4820]],['영업이익','백만원',[440,520,610]],['당기순이익','백만원',[210,280,330]],
  ['자산총계','천원',[7800000,8180000,8600000]],['부채총계','천원',[5260000,5400000,5574000]],['자본총계','천원',[2540000,2780000,3026000]],
  ['납입자본금','천원',[500000,500000,500000]],['단기차입금','천원',[620000,580000,500000]],['장기차입금','천원',[3100000,3000000,2800000]]]},
 unit:{years:[2023,2024,2025],rating:'BBB-',ratio:'121.0',rows:[
  ['매출액','백만원',[7210,7650,8210]],['영업이익','백만원',[590,670,730]],['당기순이익','백만원',[360,420,460]],
  ['자산총계','천원',[9210000,9890000,10210000]],['부채총계','천원',[5150000,5500000,5590000]],['자본총계','천원',[4060000,4390000,4620000]],
  ['납입자본금','천원',[800000,800000,800000]],['단기차입금','천원',[null,450000,400000]],['장기차입금','천원',[2100000,2000000,1800000]]]}
};
const menus=[['today','오늘 할 일','list-check'],['sms','문자 발송','paper-plane'],['tm','TM 상담','headset'],['audio','통화 녹음 올리기','microphone-lines'],['history','TM 진행 내역','clipboard-list'],['sales','영업 현황','chart-line']];
const channelNames={funding:'기업자금',mortgage:'모기지'};
let mode='mortgage',page='sms',selectedCompany=null,selectedProperty=null,opener=null;
const channels={funding:{search:'',selected:new Set()},mortgage:{search:'',selected:new Set()}};
const modal=$('#company-modal'),sourceModal=$('#source-modal');
function note(text){$('#preview-status').textContent=text;$('#preview-status').hidden=false;clearTimeout(note.timer);note.timer=setTimeout(()=>$('#preview-status').hidden=true,5000);}
function navigation(){
  $('#navigation').innerHTML=Object.entries(channelNames).map(([key,label])=>`<details class="nav-section" data-channel="${key}" ${key===mode?'open':''}><summary>${label}</summary><div class="nav-links">${menus.map(([id,text,icon])=>`<button type="button" data-menu="${id}" data-mode="${key}" ${mode===key&&page===id?'aria-current="page"':''}><i class="fa-solid fa-${icon}" aria-hidden="true"></i>${text}</button>`).join('')}</div></details>`).join('');
  document.querySelectorAll('.nav-section').forEach(group=>group.addEventListener('toggle',()=>{
    if(group.open)document.querySelectorAll('.nav-section').forEach(other=>{if(other!==group)other.open=false;});
  }));
}
function renderPage(){
  const label=menus.find(m=>m[0]===page)?.[1]||'문자 발송';
  const start=`<div class="w-full max-w-screen-2xl px-6 py-8 lg:px-10 lg:py-10 text-ink-mid"><nav class="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-ink-faint"><span class="text-ink-mid">${channelNames[mode]}</span></nav><h1 class="mb-8 text-2xl font-extrabold tracking-tight text-ink">${label}</h1>`;
  if(page!=='sms'){
    $('#screen').innerHTML=start+`<div class="border border-dashed border-line-strong rounded-lg p-6 text-sm text-ink-soft"><p>이 영역은 기존 ${label} 화면을 그대로 사용합니다.</p><p class="mt-2">이번 시안은 메뉴 묶음과 회사 정보 모달의 부동산 추가 부분만 보여드립니다.</p><button class="btn btn-quiet mt-4" data-menu="sms" data-mode="${mode}">문자 발송 목록에서 모달 확인</button></div></div>`;
    return;
  }
  $('#screen').innerHTML=start+`
    <p class="mb-5 text-sm text-ink-mid">보낼 회사를 고른 뒤 예약합니다. 문자가 나간 회사만 TM 담당자 화면에 나타납니다.</p>
    <section class="mb-6"><h2 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-faint">예약 현황</h2><p class="rounded-lg border border-dashed border-line-strong bg-white p-4 text-sm text-ink-faint">예약된 발송이 없습니다. 아래 목록에서 대상을 고르거나, 조건만 걸고 바로 예약할 수 있습니다.</p></section>
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <input id="company-search" type="search" aria-label="회사·대표·사업자번호·전화 검색" placeholder="회사·대표·사업자번호·전화" class="w-64 h-10 rounded-lg border border-line-strong bg-white px-3 text-sm text-ink focus:border-accent focus:outline-none" value="${esc(channels[mode].search)}">
      <select class="select" aria-label="담당 TM" data-filter="agent"><option value="">담당 TM 전체</option><option>김담당</option><option>박담당</option></select>
      <select class="select" aria-label="발송 상태" disabled title="기존 필터 유지"><option>발송 전체</option></select>
      <select class="select" aria-label="자격" disabled title="기존 필터 유지"><option>자격 전체</option></select>
      <select class="select" aria-label="매출" disabled title="기존 필터 유지"><option>매출 전체</option></select>
      <select class="select" aria-label="신용등급" disabled title="기존 필터 유지"><option>등급 전체</option></select>
      <select class="select" aria-label="부채비율" disabled title="기존 필터 유지"><option>부채비율 전체</option></select>
      <button class="btn btn-primary ml-2" data-preview="문자 예약은 기존 화면의 동작을 유지합니다. 이 시안에서는 발송·예약을 실행하지 않습니다.">문자 예약하기</button>
    </div>
    <div class="list-scroll" id="admin-rows"></div></div>`;
  renderRows();
}
function renderRows(){
  const query=channels[mode].search.trim().toLowerCase();
  const agent=$('[data-filter=agent]')?.value||'';
  const visible=companies.filter(c=>(mode==='mortgage'||['hotel','unit','empty','linked'].includes(c.id))&&(!agent||c.agent===agent)&&[c.name,c.rep,c.address,c.phone,c.mobile].join(' ').toLowerCase().includes(query));
  $('#admin-rows').innerHTML=`<p class="text-xs text-ink-soft mb-2">리스트 ${visible.length}개 · 선택 <span id="selected-count">${channels[mode].selected.size}</span>개</p>
    <table class="darkhead-table"><thead><tr><th class="w-8"><input type="checkbox" id="pick-all" aria-label="화면에 보이는 목록 전체 선택" ${visible.length&&visible.every(c=>channels[mode].selected.has(c.id))?'checked':''}></th><th>회사명</th><th>대표</th><th class="text-right">매출</th><th>등급</th>${mode==='mortgage'?'<th>부동산 자료</th>':''}<th>담당 TM</th><th>최근 통화</th><th>반응도</th><th class="text-right">통화</th><th>상태</th></tr></thead>
    <tbody>${visible.map(c=>`<tr class="cursor-pointer" data-company="${c.id}"><td><input type="checkbox" data-pick="${c.id}" aria-label="${esc(c.name)} 선택" ${channels[mode].selected.has(c.id)?'checked':''}></td><td class="font-medium text-ink"><button type="button" class="text-left" data-open="${c.id}">${esc(c.name)}</button></td><td>${c.rep}</td><td class="text-right tabular-nums">${financials[c.id]?c.revenue:'—'}</td><td>${financials[c.id]?c.credit:'—'}</td>${mode==='mortgage'?`<td>${c.properties.length?'연결 '+c.properties.length+'개':'미수집'}<br><span class="text-ink-faint">${c.properties.length?(c.status==='draft'?'검토 대기':'검토 완료 예시'):'—'}</span></td>`:''}<td>${c.agent}</td><td>—</td><td>—</td><td class="text-right">0</td><td><span class="text-ink-faint">미발송</span></td></tr>`).join('')||`<tr><td colspan="${mode==='mortgage'?11:10}" class="py-12 text-center text-sm text-ink-faint">조건에 맞는 회사가 없습니다.</td></tr>`}</tbody></table>`;
}
function financeBody(c){
  const f=financials[c.id];
  return `<div class="grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
    <div><h4 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-soft">대출 가능 금액</h4><p class="text-sm text-ink-faint">${f?'기업자금 산정 결과가 없습니다.':'기준 매출 또는 업종 코드가 없어 산정할 수 없습니다.'}</p></div>
    <div><h4 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-soft">자격 판정</h4><ul class="space-y-1 text-sm"><li class="text-ink-soft">? 자격 판정 자료 미확정</li><li class="text-ink-soft">? 휴폐업·회생: 원천 데이터 미확정 (판정 보류)</li></ul></div></div>
    <div class="border-t border-line px-5 py-4"><h4 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-soft">재무 3개년 ${f?`<span class="ml-2 normal-case tracking-normal text-ink-mid">신용등급 <b class="text-ink">${f.rating}</b> (2026-06-30)</span><span class="ml-2 normal-case tracking-normal text-ink-mid">부채비율 <b class="text-ink">${f.ratio}%</b></span>`:''}</h4>
    ${f?`<div class="overflow-x-auto"><table class="darkhead-table"><thead><tr><th>계정</th>${f.years.map(y=>`<th class="text-right">${y}</th>`).join('')}</tr></thead><tbody>${f.rows.map(([label,unit,values])=>`<tr><td class="text-ink-mid">${label} <span class="text-ink-faint">(${unit})</span></td>${values.map(v=>`<td class="text-right tabular-nums text-ink">${v==null?'—':v.toLocaleString('ko-KR')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<p class="text-sm text-ink-faint">재무 데이터가 없습니다.</p>'}</div>`;
}
function openCompany(id,trigger){
  const c=companies.find(c=>c.id===id);if(!c)return;
  selectedCompany=c;selectedProperty=c.properties[0]||null;opener=trigger||document.activeElement;
  const finance=financeBody(c);
  $('#company-dialog-content').innerHTML=`
    <div class="company-dialog-header"><div class="flex flex-wrap items-baseline gap-3"><h2 id="company-modal-title" class="text-lg font-extrabold text-ink">${c.rep}</h2><span class="text-sm font-semibold tabular-nums text-ink-mid">${esc(c.mobile||c.phone)}</span></div><button type="button" data-close="company" aria-label="회사 정보 닫기" class="text-ink-faint hover:text-ink">✕</button></div>
    <div class="company-dialog-body">
      ${mode==='mortgage'?'<p class="text-xs text-ink-soft mb-4" data-review-only>시안용 가상 자료 · 검토 완료 표본은 향후 표시 예시입니다.</p>':''}
      <div class="rounded-lg border border-line bg-white shadow-sm">
        <div class="flex items-start justify-between gap-3 border-b border-line px-5 py-3">
          <div class="min-w-0"><div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5"><h3 class="text-base font-bold text-ink">${c.name}</h3><span class="text-xs text-ink-soft">사업자번호 예시</span></div><p class="mt-1 text-xs leading-relaxed text-ink-soft">${c.address}</p></div>
          <button type="button" class="btn btn-quiet" data-preview="경영진단 내려받기는 기존 기능을 유지합니다. 이 시안에서는 파일을 생성하지 않습니다."><i class="fa-solid fa-file-excel text-accent-dark" aria-hidden="true"></i><span>경영진단</span></button>
        </div>
        ${mode==='mortgage'?`<details id="finance-section" class="company-info-section"><summary>재무정보 <span class="section-state">${financials[id]?'재무 3개년':'자료 없음'}</span></summary>${finance}</details>
        <details id="estate-section" class="company-info-section" open><summary>부동산 정보 <span class="section-state">${c.properties.length?'연결 '+c.properties.length+'개':'미수집'}</span></summary><div class="estate-content" id="estate-content"></div></details>`:finance}
        <div class="border-t border-line px-5 py-3 text-xs text-ink-soft">대표 ${c.rep} · 설립 — · 직원 —명 · ${c.industry}</div>
      </div>
    </div>`;
  if(mode==='mortgage')renderEstate();
  if(!modal.open)modal.showModal();
  $('.company-dialog-body').scrollTop=0;
  modal.querySelector('[data-close=company]').focus({preventScroll:true});
}
const fact=(label,value,note='')=>`<div><dt>${label}</dt><dd>${esc(value)}${note?`<small>${esc(note)}</small>`:''}</dd></div>`;
const sourceButton=(page,label='근거')=>`<button class="source-link" data-source="original" data-source-page="${page||''}" aria-label="${esc(label)}${page?' '+page+'쪽':''} 보기">${esc(label)}${page?' '+page+'쪽':''}</button>`;
function renderEstate(){
  const c=selectedCompany,p=properties[selectedProperty];
  if(!p){$('#estate-content').innerHTML='<p class="text-sm text-ink-faint py-4">수집된 부동산 정보가 없습니다.</p><p class="text-xs text-ink-soft pb-4">자료가 없다는 뜻이며, 부동산 미보유를 뜻하지 않습니다.</p>';return;}
  const selection=`<label for="property-select">확인할 부동산</label><select id="property-select" class="select">${c.properties.map(id=>`<option value="${id}" ${id===selectedProperty?'selected':''}>[${properties[id].type}] ${properties[id].name} · ${properties[id].address}</option>`).join('')}</select>
    <p class="text-xs text-ink-soft mt-2">${p.code} · 열람 ${p.source} 기준 · ${p.draft?'판독 검토 대기':'판독 검토 완료 예시'} ${sourceButton(null,'원문')}</p>
    <p class="text-xs text-ink-soft mt-2">회사 연결: ${esc(p.linkBasis)}</p>`;
  if(p.draft){
    $('#estate-content').innerHTML=selection+`<div class="estate-note"><b>원문 검토가 필요합니다.</b><p>소유자·지분·거래금액·채권최고액은 아직 확정하지 않았습니다.</p><p>회사 주소로 찾은 물건이며 회사 소유 여부도 확인 전입니다.</p></div>${documentsTable(p)}`;
    return;
  }
  $('#estate-content').innerHTML=selection+`<dl class="estate-facts">${fact('물건 종류·용도',p.type+' · '+p.kind)}${fact('면적',p.area,p.unit?'대지권: 3,221.2분의 13.76 · 전유면적과 별개':'')}</dl>
    <h4>소유·취득</h4><div class="table-scroll"><table class="darkhead-table" data-table="owners"><thead><tr><th>등기명의자 / 회사 관계</th><th>현재 지분</th><th>취득 원인</th><th>원인일 / 접수일</th><th>근거</th></tr></thead><tbody>${p.owners.map(o=>`<tr><td>${esc(o.name)}<br><span class="text-ink-faint">${esc(o.relation)}</span></td><td>${esc(o.share)}</td><td>${esc(o.kind)}</td><td>${esc(o.cause)}<br>${esc(o.receipt)}</td><td>${sourceButton(o.page)}</td></tr>`).join('')}</tbody></table></div>
    <h4>거래금액·적용 범위</h4>${p.transactions.length?`<div class="table-scroll"><table class="darkhead-table" data-table="transactions"><thead><tr><th>거래 당사자</th><th>계약일 / 접수일</th><th>거래금액</th><th>적용 범위 / 근거</th></tr></thead><tbody>${p.transactions.map(t=>`<tr><td>매수 ${esc(t.buyer)}<br>매도 ${esc(t.seller)}</td><td>${esc(t.cause)}<br>${esc(t.receipt)}</td><td>${esc(t.amount)}<br><span class="text-ink-faint">전체 계약</span></td><td>${esc(t.scope)}<br>${esc(t.allocation)}<br>${esc(t.list)} · ${sourceButton(t.page)}</td></tr>`).join('')}</tbody></table></div><p class="text-xs text-ink-soft mt-2">같은 거래금액이 다른 물건에 반복되어도 합산하지 않습니다. 이 물건의 단독 매매가격으로 배분하지 않습니다.</p>`:`<p class="text-sm text-ink-soft">${p.trust?'최근 소유권 변동은 신탁입니다. 매매로 처리하거나 매매가격을 만들지 않습니다.':'확인된 거래금액 자료가 없습니다. 0원으로 표시하지 않습니다.'}</p>`}
    ${rightsTable(p)}${p.trust?trustTable(p):''}
    <p class="estate-note">${p.group==='공동담보 A'?'본관과 대지는 같은 공동담보 A입니다. 두 등기에 같은 36억원이 기재되어 있으며 중복 합산하지 않습니다.<br>':''}실제 대출 잔액·금리·만기: 확인 자료 없음<br>재무정보의 단기·장기차입금은 회사 전체 금액이며 이 물건의 대출 잔액과 다릅니다.</p>
    <h4>변경·말소 이력</h4><p class="text-xs text-ink-soft mb-2">${esc(p.history)} · 열람일 이후 변동은 반영되지 않습니다.</p>
    ${p.events.length?`<div class="table-scroll"><table class="darkhead-table" data-table="history"><thead><tr><th>원인일 / 접수·주기일</th><th>대상 / 변경</th><th>내용</th><th>근거</th></tr></thead><tbody>${p.events.map(e=>`<tr><td>${esc(e.cause)}<br>${esc(e.receipt)}</td><td>${esc(e.target)}<br>${esc(e.change)}</td><td>${esc(e.detail)}</td><td>${sourceButton(e.page)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="text-sm text-ink-soft">이 예시에서 추가로 표시할 변경·말소 내역이 없습니다.</p>'}
    ${documentsTable(p)}`;
}
function rightsTable(p){
  return `<h4>현재 권리·담보 <span class="text-ink-faint">(${p.rights.length}건 · 열람일 기준)</span></h4>${p.rights.length?`<div class="table-scroll"><table class="darkhead-table" data-table="rights"><thead><tr><th>순위 / 종류</th><th>권리자 / 채무자</th><th>등기 금액</th><th>담보·권리 범위</th><th>상태 / 원인·접수일 / 근거</th></tr></thead><tbody>${p.rights.map(r=>`<tr><td>${esc(r.rank)}<br>${esc(r.kind)}</td><td>권리자 ${esc(r.party)}<br>채무자 ${esc(r.debtor)}</td><td>${esc(r.amountLabel)}<br>${esc(r.amount)}</td><td>${esc(r.scope)}</td><td>${esc(r.status)}<br>원인 ${esc(r.cause)}<br>접수 ${esc(r.receipt)}<br>${sourceButton(r.page)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="text-sm text-ink-soft">이 검토 완료 예시에는 현재 기재된 근저당·전세권·압류가 없습니다. 신탁 내용은 아래에 표시합니다.</p>'}`;
}
function trustTable(p){
  return `<h4>신탁 관계</h4><dl class="estate-facts">${p.trustRoles.map(([role,name])=>fact(role,name)).join('')}</dl>
    <h4>우선수익권</h4><div class="table-scroll"><table class="darkhead-table" data-table="trust"><thead><tr><th>순위</th><th>우선수익자</th><th>우선수익 한도</th><th>담보 채권 범위 / 근거</th></tr></thead><tbody>${p.benefits.map(b=>`<tr><td>${esc(b.rank)}</td><td>${esc(b.party)}</td><td>${esc(b.amount)}</td><td>${esc(b.scope)}<br>${sourceButton(b.page,'신탁원부')}</td></tr>`).join('')}</tbody></table></div>
    <p class="estate-note">세 기관은 같은 순위입니다. 기관별 한도를 표시하며 동일 채권 중복 여부가 확인되지 않아 합산하지 않습니다.<br>신탁 기간: 2025.07.21 ~ 2027.07.11 · 채무 미상환 시 연장 조항 있음 ${sourceButton(10,'기간 조항')}<br>신탁 기간은 대출 만기를 뜻하지 않습니다. 우선수익 한도는 근저당권 채권최고액과 구분합니다.</p>`;
}
function documentsTable(p){
  return `<h4>원문·연결 목록</h4><p class="text-sm">등기사항전부증명서 ${p.pages}쪽 · 열람 ${p.source} · ${p.draft?'검토 대기':'검토 완료 예시'} ${sourceButton(null,'원문 보기')}</p><p class="text-xs text-ink-soft mt-2">${esc(p.history)}</p>
    ${p.references.map(r=>`<p class="text-sm mt-2">${esc(r.name)} · ${esc(r.state)} ${r.page?sourceButton(r.page,'연결 원문'):''}</p>`).join('')}`;
}
function openSource(button){
  const p=properties[selectedProperty];if(!p)return;
  const page=button?.dataset.sourcePage;
  sourceModal.innerHTML=`<div class="company-dialog-header"><h2 id="source-title" class="text-lg font-extrabold text-ink">원문 연결 예시</h2><button data-close="source" aria-label="원문 예시 닫기">✕</button></div><div class="source-body"><p class="text-sm font-semibold">실제 등기 원문이 아닌 시안 설명입니다.</p><p class="mt-3">${esc(p.name)} · ${p.pages}쪽 · 열람 ${p.source}${page?' · 근거 '+esc(page)+'쪽':''}</p><p class="mt-3">운영에서는 회사·문서 권한을 확인한 기존 인증 다운로드로 마운트 디스크의 원본을 엽니다. 페이지 근거만 있는 데이터는 해당 쪽까지만 안내하고, 문장 위치를 강조한 것처럼 표시하지 않습니다.</p></div>`;
  sourceModal.showModal();
}
function changeMenu(nextMode,nextPage){
  if(modal.open)modal.close();
  mode=nextMode;page=nextPage;
  history.replaceState(null,'',`#${mode}/${page}`);
  navigation();renderPage();
}
document.addEventListener('click',e=>{
  const t=e.target.closest('button,input,tr');if(!t)return;
  if(t.matches('[data-menu]')){changeMenu(t.dataset.mode,t.dataset.menu);return;}
  if(t.matches('[data-scenario]')){changeMenu('mortgage','sms');openCompany(t.dataset.scenario,t);return;}
  if(t.matches('[data-close]')){(t.dataset.close==='source'?sourceModal:modal).close();return;}
  if(t.matches('[data-source]')){openSource(t);return;}
  if(t.matches('[data-preview]')){
    if(modal.open){t.title=t.dataset.preview;let message=modal.querySelector('[data-preview-note]');if(!message){message=document.createElement('p');message.dataset.previewNote='';message.className='text-xs text-ink-soft px-5 py-3';t.closest('.company-dialog-body').append(message);}message.textContent=t.dataset.preview;message.scrollIntoView({block:'nearest'});}
    else note(t.dataset.preview);return;
  }
  if(t.matches('input'))return;
  const row=t.closest('[data-company]');
  if(row){openCompany(row.dataset.company,row.querySelector('[data-open]'));return;}
});
document.addEventListener('input',e=>{if(e.target.id==='company-search'){channels[mode].search=e.target.value;renderRows();}});
document.addEventListener('change',e=>{
  if(e.target.id==='property-select'){selectedProperty=e.target.value;renderEstate();$('#property-select').focus({preventScroll:true});return;}
  if(e.target.matches('[data-filter]')){renderRows();return;}
  if(e.target.matches('[data-pick]')){const set=channels[mode].selected;e.target.checked?set.add(e.target.dataset.pick):set.delete(e.target.dataset.pick);$('#selected-count').textContent=set.size;const picks=[...document.querySelectorAll('[data-pick]')];$('#pick-all').checked=picks.length>0&&picks.every(p=>p.checked);}
  if(e.target.id==='pick-all'){document.querySelectorAll('[data-pick]').forEach(p=>{p.checked=e.target.checked;p.checked?channels[mode].selected.add(p.dataset.pick):channels[mode].selected.delete(p.dataset.pick);});$('#selected-count').textContent=channels[mode].selected.size;}
});
for(const d of [modal,sourceModal])d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});
modal.addEventListener('close',()=>{if(sourceModal.open)sourceModal.close();if(opener?.isConnected)opener.focus({preventScroll:true});});
function route(){
  const parts=location.hash.slice(1).split('/');const nextMode=Object.hasOwn(channelNames,parts[0])?parts[0]:'mortgage';
  const nextPage=menus.some(m=>m[0]===parts[1])?parts[1]:'sms';changeMenu(nextMode,nextPage);
  if(parts[1]==='detail'&&companies.some(c=>c.id===parts[2]))openCompany(parts[2],document.querySelector(`[data-open="${parts[2]}"]`));
}
window.addEventListener('hashchange',route);
route();
