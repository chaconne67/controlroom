/* Synthetic review only. Existing listing and company modal presentation are preserved.
   No application requests, real messages, DB writes, or underwriting calculations. */
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const companies=[
 {id:'hotel',name:'주식회사 예시호텔',rep:'김○○',region:'경기 수원시',industry:'호텔업',address:'경기 수원시 · 예시로 120',phone:'031-000-0000',mobile:'010-••••-1200',contact:'재무 담당자',sms:true,relation:'법인 소유 확인',status:'verified',properties:['hotel-building','hotel-land'],agent:'김담당',sales:'이영업',revenue:'48.2억원',credit:'BB+',memo:'운영자금 확보를 위한 담보 조건 비교 희망',sourceDate:'2026.09.17'},
 {id:'trust',name:'주식회사 예시리조트',rep:'박○○',region:'인천 중구',industry:'휴양 숙박업',address:'인천 중구 · 샘플해안로 38',phone:'032-000-0000',mobile:'010-••••-2300',contact:'재무 담당자',sms:true,relation:'위탁자 확인',status:'verified',properties:['trust-building'],agent:'김담당',sales:'정영업',revenue:'63.4억원',credit:'BB',memo:'신탁 계약과 우선수익권 조건 확인 필요',sourceDate:'2026.09.16'},
 {id:'draft',name:'주식회사 예시스테이',rep:'이○○',region:'서울 강서구',industry:'숙박업',address:'서울 강서구 · 예시길 27',phone:'02-000-0000',mobile:'010-••••-3400',contact:'회사 담당자',sms:true,relation:'주소로 연결',status:'draft',properties:['draft-building','draft-land'],agent:'박담당',sales:'미배정',revenue:'19.7억원',credit:'확인 자료 없음',memo:'공유자와 공동담보목록 원문 검토 필요',sourceDate:'2026.09.17'},
 {id:'unit',name:'주식회사 예시산업',rep:'최○○',region:'서울 금천구',industry:'제조업',address:'서울 금천구 · 샘플산업로 12',phone:'02-000-0001',mobile:'010-••••-4500',contact:'재무 담당자',sms:true,relation:'법인 소유 확인',status:'verified',properties:['unit-room'],agent:'박담당',sales:'미배정',revenue:'82.1억원',credit:'BBB-',memo:'전유부분과 대지권의 담보 범위 확인',sourceDate:'2026.09.15'},
 {id:'empty',name:'주식회사 예시관광',rep:'정○○',region:'경기 가평군',industry:'숙박업',address:'경기 가평군 · 예시호수길 8',phone:'031-000-0002',mobile:'',contact:'회사 일반전화',sms:false,relation:'연결 확인 전',status:'missing',properties:[],agent:'김담당',sales:'미배정',revenue:'자료 수집 대기',credit:'자료 수집 대기',memo:'문자 수신 연락처 확인 필요',sourceDate:''},
 {id:'linked',name:'주식회사 예시파트너스',rep:'윤○○',region:'경기 시흥시',industry:'숙박업',address:'경기 시흥시 · 샘플중앙로 44',phone:'031-000-0003',mobile:'',contact:'회사 일반전화',sms:false,relation:'주소로 연결',status:'verified',properties:['linked-building'],agent:'박담당',sales:'미배정',revenue:'12.6억원',credit:'B+',memo:'회사와 등기 소유자의 관계 확인 필요',sourceDate:'2026.09.14'}
];
const properties={
 'hotel-building':{creditor:'가상은행',debtor:'주식회사 예시호텔',code:'A-01',type:'건물',name:'예시호텔 본관',address:'경기 수원시 · 예시로 120',kind:'숙박시설 · 지상 5층 / 지하 1층',area:'연면적 1,842.60㎡',owner:'주식회사 예시호텔',share:'단독 소유 · 1/1',acquired:'2021.06.18',receipt:'2021.07.02',price:'48억원',priceScope:'본관 + 대지 2개 물건의 전체 계약금액',right:'공동담보',amount:'36억원',group:'공동담보 A',date:'2023.04.12',pages:8,source:'2026.09.17'},
 'hotel-land':{creditor:'가상은행',debtor:'주식회사 예시호텔',code:'A-02',type:'토지',name:'예시호텔 대지',address:'경기 수원시 · 예시동 120-1',kind:'대 · 소유권',area:'토지면적 622.40㎡',owner:'주식회사 예시호텔',share:'단독 소유 · 1/1',acquired:'2021.06.18',receipt:'2021.07.02',price:'48억원',priceScope:'본관 + 대지 2개 물건의 전체 계약금액',right:'공동담보',amount:'36억원',group:'공동담보 A',date:'2023.04.12',pages:6,source:'2026.09.17'},
 'trust-building':{code:'B-01',type:'건물',name:'예시리조트 본관',address:'인천 중구 · 샘플해안로 38',kind:'숙박시설 · 신탁 부동산',area:'연면적 2,610.20㎡',owner:'가상신탁 주식회사',share:'등기명의자 · 수탁자',acquired:'2025.07.21',receipt:'2025.07.22',price:'확인 자료 없음',priceScope:'최근 소유권 변동 원인: 신탁',right:'신탁',amount:'60억원',group:'공동 1순위',date:'2025.07.21',pages:28,source:'2026.09.16',trust:true},
 'draft-building':{code:'C-01',type:'건물',name:'예시스테이 건물',address:'서울 강서구 · 예시길 27',kind:'숙박시설',area:'검토 대기',owner:'검토 대기',share:'공유지분 검토 필요',acquired:'검토 대기',receipt:'검토 대기',price:'검토 대기',priceScope:'가격과 대상 범위 미확정',right:'검토 대기',amount:'검토 대기',pages:10,source:'2026.09.17',draft:true},
 'draft-land':{code:'C-02',type:'토지',name:'예시스테이 대지',address:'서울 강서구 · 예시동 27-3',kind:'대',area:'검토 대기',owner:'검토 대기',share:'공유지분 검토 필요',acquired:'검토 대기',receipt:'검토 대기',price:'검토 대기',priceScope:'가격과 대상 범위 미확정',right:'검토 대기',amount:'검토 대기',pages:7,source:'2026.09.17',draft:true},
 'unit-room':{creditor:'가상은행',debtor:'주식회사 예시산업',code:'D-01',type:'호실',name:'예시산업센터 501호',address:'서울 금천구 · 샘플산업로 12, 501호',kind:'집합건물 · 업무시설',area:'전유면적 61.78㎡',owner:'주식회사 예시산업',share:'전유부분 1/1',acquired:'2017.09.28',receipt:'2017.09.29',price:'확인 자료 없음',priceScope:'이 원문에서 거래금액 확인 불가',right:'건물만 담보',amount:'5.04억원',group:'본 호실만',date:'2017.09.29',pages:3,source:'2026.09.15',unit:true},
 'linked-building':{creditor:'가상은행',debtor:'확인 자료 없음',code:'E-01',type:'건물',name:'주소로 연결된 건물',address:'경기 시흥시 · 샘플중앙로 44',kind:'숙박시설',area:'연면적 921.00㎡',owner:'개인 소유자 이○○',share:'단독 소유 · 1/1',acquired:'2008.04.12',receipt:'2008.04.16',price:'확인 자료 없음',priceScope:'현재 회사의 취득으로 확인되지 않음',right:'근저당권',amount:'9억원',group:'본건 부동산',date:'2020.05.20',pages:5,source:'2026.09.14',linked:true}
};

const financials={
  hotel:{years:[2025,2024,2023],rating:'BB+',ratio:'184.2',rows:[['매출액','백만원',[4820,4460,4100]],['영업이익','백만원',[610,520,440]],['당기순이익','백만원',[330,280,210]],['자산총계','백만원',[8600,8180,7800]],['부채총계','백만원',[5574,5400,5260]],['자본총계','백만원',[3026,2780,2540]]]},
  unit:{years:[2025,2024,2023],rating:'BBB-',ratio:'121.0',rows:[['매출액','백만원',[8210,7650,7210]],['영업이익','백만원',[730,670,590]],['당기순이익','백만원',[460,420,360]],['자산총계','백만원',[10210,9890,9210]],['부채총계','백만원',[5590,5500,5150]],['자본총계','백만원',[4620,4390,4060]]]}
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
    <table class="darkhead-table"><thead><tr><th class="w-8"><input type="checkbox" id="pick-all" aria-label="화면에 보이는 목록 전체 선택" ${visible.length&&visible.every(c=>channels[mode].selected.has(c.id))?'checked':''}></th><th>회사명</th><th>대표</th><th class="text-right">매출</th><th>등급</th><th>담당 TM</th><th>최근 통화</th><th>반응도</th><th class="text-right">통화</th><th>상태</th></tr></thead>
    <tbody>${visible.map(c=>`<tr class="cursor-pointer" data-company="${c.id}"><td><input type="checkbox" data-pick="${c.id}" aria-label="${esc(c.name)} 선택" ${channels[mode].selected.has(c.id)?'checked':''}></td><td class="font-medium text-ink"><button type="button" class="text-left" data-open="${c.id}">${esc(c.name)}</button></td><td>${c.rep}</td><td class="text-right tabular-nums">${financials[c.id]?c.revenue:'—'}</td><td>${financials[c.id]?c.credit:'—'}</td><td>${c.agent}</td><td>—</td><td>—</td><td class="text-right">0</td><td><span class="text-ink-faint">미발송</span></td></tr>`).join('')||'<tr><td colspan="10" class="py-12 text-center text-sm text-ink-faint">조건에 맞는 회사가 없습니다.</td></tr>'}</tbody></table>`;
}
function financeBody(c){
  const f=financials[c.id];
  return `<div class="grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
    <div><h4 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-soft">대출 가능 금액</h4><p class="text-sm text-ink-faint">${f?'기업자금 산정 결과가 없습니다.':'기준 매출 또는 업종 코드가 없어 산정할 수 없습니다.'}</p></div>
    <div><h4 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-soft">자격 판정</h4><ul class="space-y-1 text-sm"><li class="text-ink-soft">? 자격 판정 자료 미확정</li><li class="text-ink-soft">? 휴폐업·회생: 원천 데이터 미확정 (판정 보류)</li></ul></div></div>
    <div class="border-t border-line px-5 py-4"><h4 class="mb-2 text-xs font-bold uppercase tracking-wider text-ink-soft">재무 3개년 ${f?`<span class="ml-2 normal-case tracking-normal text-ink-mid">신용등급 <b class="text-ink">${f.rating}</b> (2026-06-30)</span><span class="ml-2 normal-case tracking-normal text-ink-mid">부채비율 <b class="text-ink">${f.ratio}%</b></span>`:''}</h4>
    ${f?`<div class="overflow-x-auto"><table class="darkhead-table"><thead><tr><th>계정</th>${f.years.map(y=>`<th class="text-right">${y}</th>`).join('')}</tr></thead><tbody>${f.rows.map(([label,unit,values])=>`<tr><td class="text-ink-mid">${label} <span class="text-ink-faint">(${unit})</span></td>${values.map(v=>`<td class="text-right tabular-nums text-ink">${v.toLocaleString('ko-KR')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<p class="text-sm text-ink-faint">재무 데이터가 없습니다.</p>'}</div>`;
}
function openCompany(id,trigger){
  const c=companies.find(c=>c.id===id);if(!c)return;
  selectedCompany=c;selectedProperty=c.properties[0]||null;opener=trigger||document.activeElement;
  const finance=financeBody(c);
  $('#company-dialog-content').innerHTML=`
    <div class="company-dialog-header"><div class="flex flex-wrap items-baseline gap-3"><h2 id="company-modal-title" class="text-lg font-extrabold text-ink">${c.rep}</h2><span class="text-sm font-semibold tabular-nums text-ink-mid">${esc(c.mobile||c.phone)}</span></div><button type="button" data-close="company" aria-label="회사 정보 닫기" class="text-ink-faint hover:text-ink">✕</button></div>
    <div class="company-dialog-body">
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
function renderEstate(){
  const c=selectedCompany,p=properties[selectedProperty];
  if(!p){$('#estate-content').innerHTML='<p class="text-sm text-ink-faint py-4">수집된 부동산 정보가 없습니다.</p><p class="text-xs text-ink-soft pb-4">회사와 연결된 물건을 아직 확인하지 못했습니다.</p>';return;}
  const selection=`<label for="property-select">확인할 부동산</label><select id="property-select" class="select">${c.properties.map(id=>`<option value="${id}" ${id===selectedProperty?'selected':''}>[${properties[id].type}] ${properties[id].name} · ${properties[id].address}</option>`).join('')}</select>
    <p class="text-xs text-ink-soft mt-2">${p.code} · 등기 열람 ${p.source} · ${p.draft?'판독 검토 대기':'확인 완료'} <button class="source-link" data-source="original">원문 보기</button></p>`;
  if(p.draft){$('#estate-content').innerHTML=selection+`<div class="estate-note"><b>원문 검토가 필요합니다.</b><p>소유자·지분·거래금액·채권최고액은 아직 확정하지 않았습니다.</p><p>공동담보목록 미수령 · 등기 이기 관계와 담보 범위 확인 필요</p></div><h4>보관된 원문</h4><p class="text-sm">등기사항전부증명서 ${p.pages}쪽 · ${p.source}</p>`;return;}
  const amount=p.trust?'우선수익 한도 합계': '채권최고액';
  $('#estate-content').innerHTML=selection+`<dl class="estate-facts">
    ${fact('등기명의자',p.owner,p.share)}${fact('회사와의 관계',c.relation,p.trust?'회사: 위탁자 / 등기명의자: 수탁자':p.linked?'회사 소유로 확인되지 않았습니다.':'')}
    ${fact('용도·면적',p.kind,p.area)}${fact('최근 소유권 변동',p.acquired,'원인: '+(p.trust?'신탁':'매매')+' · 접수 '+p.receipt)}
    ${fact('등기에 기재된 거래금액',p.price,p.priceScope)}${fact(amount,p.amount,p.trust?'공동 1순위 세 기관의 합계':'실제 대출 잔액과 다릅니다.')}
    </dl>
    ${p.unit?'<p class="estate-note">대지권: 3,221.2분의 13.76 · 전유부분 면적과 별개입니다. 해당 근저당은 건물만 담보로 기재되어 있습니다.</p>':''}
    ${p.trust?trustTable(p):rightsTable(p)}
    <p class="estate-note">${p.group==='공동담보 A'?'본관과 대지는 같은 공동담보 A입니다. 두 등기에 같은 36억원이 기재되어 있으며 중복 합산하지 않습니다.<br>':''}실제 대출 잔액·금리·만기: 확인 자료 없음</p>
    <h4>변동 이력</h4><div class="table-scroll"><table class="darkhead-table compact"><thead><tr><th>원인일</th><th>접수일</th><th>내용</th><th>상태</th></tr></thead><tbody><tr><td>${p.acquired}</td><td>${p.receipt}</td><td>${p.trust?'신탁 소유권 이전':'매매 소유권 이전'}</td><td>등기 확인</td></tr><tr><td>${p.date}</td><td>${p.date}</td><td>${p.trust?'공동 순위 우선수익권':'근저당권 설정'}</td><td>현재 기재</td></tr></tbody></table></div>
    <h4>원문</h4><p class="text-sm">등기사항전부증명서 · ${p.pages}쪽 · 열람 ${p.source} <button class="source-link" data-source="original">원문 보기</button></p>
    ${p.group==='공동담보 A'?'<p class="text-xs text-ink-soft mt-2">담보 범위: 예시호텔 본관 + 예시호텔 대지</p>':''}`;
}
function rightsTable(p){return `<h4>권리·담보</h4><div class="table-scroll"><table class="darkhead-table"><thead><tr><th>순위</th><th>권리</th><th>권리자 / 채무자</th><th class="text-right">채권최고액</th><th>담보 범위</th></tr></thead><tbody><tr><td>을구 1</td><td>근저당권</td><td>${esc(p.creditor||"확인 자료 없음")} / ${esc(p.debtor||"확인 자료 없음")}</td><td class="text-right">${p.amount}</td><td>${p.group||p.right}</td></tr></tbody></table></div>`;}
function trustTable(p){return `<h4>신탁 · 공동 1순위 우선수익권</h4><div class="table-scroll"><table class="darkhead-table compact"><thead><tr><th>순위</th><th>우선수익자</th><th class="text-right">한도</th></tr></thead><tbody><tr><td>공동 1순위</td><td>가상금융 A</td><td class="text-right">30억원</td></tr><tr><td>공동 1순위</td><td>가상금융 B</td><td class="text-right">12억원</td></tr><tr><td>공동 1순위</td><td>가상금융 C</td><td class="text-right">18억원</td></tr></tbody></table></div><p class="estate-note">신탁 기간: 2025.07.21 ~ 2027.07.11<br>신탁 기간은 대출 만기를 뜻하지 않습니다. 우선수익 한도는 근저당권 채권최고액과 구분합니다.</p>`;}
function openSource(){
  const p=properties[selectedProperty];if(!p)return;
  sourceModal.innerHTML=`<div class="company-dialog-header"><h2 id="source-title" class="text-lg font-extrabold text-ink">원문 연결 예시</h2><button data-close="source" aria-label="원문 예시 닫기">✕</button></div><div class="source-body"><p class="text-sm font-semibold">실제 등기 원문이 아닌 시안 설명입니다.</p><p class="mt-3">${esc(p.name)} · ${p.pages}쪽 · ${p.source}</p><p class="mt-3">운영에서는 이 물건에 연결된 마운트 디스크의 원본을 기존 인증 다운로드 경로로 엽니다. 파일 접근 권한과 검토 상태는 그대로 유지합니다.</p></div>`;
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
  if(t.matches('[data-source]')){openSource();return;}
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
