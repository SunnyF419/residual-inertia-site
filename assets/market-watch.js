(()=>{'use strict';
const root=document.querySelector('[data-market-watch]');if(!root)return;
const en=document.documentElement.lang==='en',T=(zh,eng)=>en?eng:zh;
const api=root.dataset.api||'https://global.residualinertia.com/api/market-watch';
const esc=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=n=>n==null?'—':Number(n).toLocaleString(en?'en-US':'zh-CN',{maximumFractionDigits:2});
const time=s=>s?new Date(s).toLocaleString(en?'en-US':'zh-CN'):T('尚未完成','Not yet completed');
const safeLink=u=>{try{let x=new URL(u);return x.protocol==='https:'&&x.hostname==='www.sec.gov'?esc(x.href):'#'}catch{return '#'}};
const code=c=>({P:T('买入','Purchase'),S:T('卖出','Sale'),A:T('授予','Grant'),M:T('行权／转换','Exercise / conversion'),F:T('缴税／费用','Tax / exercise payment'),G:T('赠与','Gift')}[c]||c);
function ownerRole(owner) {
  const roles = [
    owner.officer_title || (owner.officer && T('高管','Officer')),
    owner.director && T('董事','Director'),
    owner.ten_percent && T('10% 股东','10% owner')
  ];
  return roles.filter(Boolean).join(' · ');
}
function chartBuyer(buyer) {
  const role = ownerRole(buyer)
    .replace(/\bChief Executive Officer\b/gi, 'CEO')
    .replace(/\bChief Technology Officer\b/gi, 'CTO')
    .replace(/\bChief Financial Officer\b/gi, 'CFO')
    .replace(/\bChief Operating Officer\b/gi, 'COO');
  return esc(buyer.name) + (role ? '<span class="mw-chart-role">'+esc(role)+'</span>' : '');
}
function ownerLine(owner) {
  return [owner.name, ownerRole(owner)].filter(Boolean).map(esc).join(' · ');
}
let mode='insider',page=1,query='',form='all',version=0,lastStatus=null;
root.innerHTML=`<h1>${T('市场追踪','Market Watch')}</h1><p class="mw-intro">${T('近期内部人披露与交割观察。数据直接来自 SEC。','Recent insider filings and settlement observations, sourced directly from the SEC.')}</p><div class="mw-tabs" role="tablist" aria-label="${T('市场追踪栏目','Market Watch sections')}"><button role="tab" aria-selected="true" data-tab="insider">${T('内部人交易','Insider filings')}</button><button role="tab" aria-selected="false" data-tab="ftd">${T('FTD 交割观察','Fails to deliver')}</button></div><div class="mw-status" aria-live="polite"></div><div class="mw-stats"></div><form class="mw-toolbar"><div class="mw-search"><input aria-label="${T('查询公司','Search companies')}" placeholder="${T('股票代码、公司或内部人姓名','Ticker, company or insider name')}"><button type="submit">${T('搜索','Search')}</button></div><select aria-label="${T('申报类型','Filing type')}"><option value="all">${T('全部申报','All filings')}</option>${['3','4','5','3/A','4/A','5/A'].map(f=>`<option value="${f}">Form ${f}</option>`).join('')}</select><button type="button" class="mw-refresh">${T('刷新','Refresh')}</button></form><div class="mw-list" aria-live="polite"></div><div class="mw-pager"></div><p class="mw-footnote"></p>`;
const dateFilter = document.createElement('details');
dateFilter.className = 'mw-calendar';
dateFilter.innerHTML = '<summary></summary><div class="mw-calendar-panel"></div>';
root.querySelector('.mw-refresh').before(dateFilter);
const calendarLabel = dateFilter.querySelector('summary');
const calendarPanel = dateFilter.querySelector('.mw-calendar-panel');
let selectedDay = new URLSearchParams(location.search).get('day') || '';
let firstDay = '', lastDay = '', month = '';
const isoDay = date => date.toISOString().slice(0,10);
function updateDates(start) {
  if (start === firstDay) return;
  firstDay = start;
  const end = new Date(start+'T00:00:00Z');
  end.setUTCDate(end.getUTCDate()+29);
  lastDay = isoDay(end);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(selectedDay) || selectedDay < start || selectedDay > lastDay) selectedDay = '';
  calendarLabel.textContent = selectedDay || T('全部申报日','All filing dates');
  month = (selectedDay || lastDay).slice(0,7);
  renderCalendar();
}
function renderCalendar() {
  const first = new Date(month+'-01T00:00:00Z');
  const caption = first.toLocaleDateString(en?'en-US':'zh-CN',{timeZone:'UTC',month:'long',year:'numeric'});
  const weekdays = en ? ['M','T','W','T','F','S','S'] : [...'一二三四五六日'];
  const days = [];
  const cursor = new Date(first);
  cursor.setUTCDate(1-(first.getUTCDay()+6)%7);
  for (let i=0; i<42; i++, cursor.setUTCDate(cursor.getUTCDate()+1)) {
    const day = isoDay(cursor);
    const active = day >= firstDay && day <= lastDay && day.startsWith(month);
    days.push(`<button type="button" data-day="${day}" aria-label="${day}" aria-pressed="${selectedDay===day}" ${active?'':'disabled'}>${cursor.getUTCDate()}</button>`);
  }
  calendarPanel.innerHTML = `<div class="mw-month"><strong aria-live="polite">${caption}</strong><button type="button" data-step="-1" aria-label="${T('上个月','Previous month')}" ${month<=firstDay.slice(0,7)?'disabled':''}>‹</button><button type="button" data-step="1" aria-label="${T('下个月','Next month')}" ${month>=lastDay.slice(0,7)?'disabled':''}>›</button></div><div class="mw-days">${weekdays.map(x=>'<span>'+x+'</span>').join('')}${days.join('')}</div><div class="mw-calendar-actions"><button type="button" data-day="">${T('清除','Clear')}</button><button type="button" data-day="${lastDay}">${T('今天','Today')}</button></div>`;
}
dateFilter.ontoggle = () => {
  if (dateFilter.open) { month=(selectedDay || lastDay).slice(0,7); renderCalendar(); }
};
calendarPanel.onclick = event => {
  const button = event.target.closest('button');
  if (!button || button.disabled) return;
  if (button.dataset.step) {
    const next = new Date(month+'-01T00:00:00Z');
    next.setUTCMonth(next.getUTCMonth()+Number(button.dataset.step));
    month=isoDay(next).slice(0,7);
    renderCalendar();
    calendarPanel.querySelector('[data-step]:not(:disabled)')?.focus();
    return;
  }
  selectedDay = button.dataset.day;
  calendarLabel.textContent = selectedDay || T('全部申报日','All filing dates');
  dateFilter.open = false;
  calendarLabel.focus();
  page=1;
  load();
};
document.addEventListener('click',event=>{if (!dateFilter.contains(event.target)) dateFilter.open=false;});
dateFilter.onkeydown = event => {
  if (event.key==='Escape') { dateFilter.open=false; calendarLabel.focus(); }
};
const parts = new Intl.DateTimeFormat('en-US', {
  timeZone:'America/New_York', year:'numeric', month:'2-digit', day:'2-digit'
}).formatToParts(new Date());
const todayET = Object.fromEntries(parts.map(({type,value})=>[type,value]));
const firstDate = new Date(Date.UTC(+todayET.year,+todayET.month-1,+todayET.day));
firstDate.setUTCDate(firstDate.getUTCDate()-29);
updateDates(isoDay(firstDate));
async function get(path){const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),20000);try{let r=await fetch(api+path,{signal:ctrl.signal,credentials:'omit'});if(!r.ok)throw Error(String(r.status));return await r.json()}finally{clearTimeout(timer)}}
function showStatus(s){lastStatus=s;updateDates(s.window_start);const error=mode==='insider'?(s.feed_error||s.index_error):s.ftd_error;
root.querySelector('.mw-status').innerHTML=`${mode==='insider'?T('披露窗口：','Filing window: ')+esc(s.window_start)+T(' 至今 · 每分钟检查 SEC',' to present · SEC checked every minute'):T('最新可得窗口：','Latest available window: ')+esc(s.ftd_start)+' — '+esc(s.ftd_end)+T(' · 每 6 小时检查新批次',' · New batches checked every 6 hours')}<br>${T('最近成功检查：','Last successful check: ')}${esc(time(mode==='insider'?s.checked:s.ftd_checked))}${mode==='insider'&&s.pending?`<br>${T('近期索引已收录','Recent index contains')} ${num(s.filings)} ${T('份披露；详情已解析','filings; details parsed for')} ${num(s.parsed)}${T('份，其余待补录。搜索覆盖会随解析进度完善。','; the remainder are pending. Search coverage expands as parsing completes.')}`:''}`;
root.querySelector('.mw-stats').innerHTML=mode==='insider'?`<div><span>${T('近期申报','Recent filings')}</span><strong>${num(s.filings)}</strong></div><div><span>${T('已解析详情','Parsed filings')}</span><strong>${num(s.parsed)}</strong></div><div><span>${T('展示窗口','Display window')}</span><strong>${T('最近 30 天','Last 30 days')}</strong></div>`:`<div><span>${T('数据截至','Data through')}</span><strong>${esc(s.ftd_end)}</strong></div><div><span>${T('官方批次','Official batches')}</span><strong>${s.batches.length}</strong></div><div><span>${T('更新方式','Publication cadence')}</span><strong>${T('半月批次','Half-month batches')}</strong></div>`;
}
async function load(quiet=false){const v=++version;
if(!quiet){const list=root.querySelector('.mw-list');list.style.minHeight=list.getBoundingClientRect().height+'px';}if(!quiet)root.querySelector('.mw-list').innerHTML=`<p>${T('正在读取 SEC 披露…','Loading SEC disclosures…')}</p>`;
try{const data=await get((mode==='insider'?'/insider/days':'/ftd')+'?'+new URLSearchParams({q:query,form,page,day:selectedDay}));if(v!==version)return;showStatus(data.status);draw(data)}catch(e){if(v!==version)return;if(quiet){root.querySelector('.mw-status').textContent=T('刷新暂未成功，保留当前数据。','Refresh failed; keeping current data.');return}root.querySelector('.mw-list').innerHTML=`<p class="mw-error">${T('暂时无法读取数据，请稍后点击刷新。','Data is temporarily unavailable. Please try Refresh shortly.')}</p>`}}
function draw(data){const insider=mode==='insider';root.querySelector('.mw-list').style.minHeight='';root.querySelector('.mw-list').classList.toggle('mw-panel',true);
const headers=insider?[T('申报日','Filed'),T('公司','Company'),T('申报数','Filings'),T('申报类型','Forms')]:[T('股票／CUSIP','Ticker / CUSIP'),T('结算日','Settlement date'),T('未交割股数','FTD shares'),T('参考价格','Reference price'),T('参考金额','Reference value'),T('来源','Source')];
root.querySelector('.mw-list').innerHTML=`<table><thead><tr>${headers.map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${data.rows.length?data.rows.map((r,i)=>`<tr class="mw-record"><td>${insider?esc(r.filed):`<button class="mw-link" aria-expanded="false" data-detail="${esc(r.cusip)}" data-row="${i}">${esc(r.ticker)}</button><small>${esc(r.cusip)}</small>`}</td>${insider?`<td><button class="mw-link" aria-expanded="false" data-detail="${esc(r.accession)}" data-row="${i}">${esc(r.ticker||r.issuer)}</button>${r.ticker?`<small>${esc(r.issuer)}</small>`:''}${!r.parsed?`<small>${T('公司身份待解析','Issuer pending')}</small>`:''}</td><td>${num(r.filings)}</td><td>${r.forms.split(',').map(f=>'Form '+esc(f)).join(' · ')}</td>`:`<td>${esc(r.day)}<small>${esc(r.name)}</small></td><td class="mw-number">${num(r.quantity)}</td><td class="mw-number">${r.price==null?'—':'$'+num(r.price)}</td><td class="mw-number">${r.price==null?'—':'$'+num(r.price*r.quantity)}</td><td><a href="${safeLink(r.batch)}" target="_blank" rel="noopener">SEC ↗</a></td>`}</tr><tr class="mw-detail-row"><td colspan="${headers.length}"><div class="mw-detail" id="mw-detail-${i}"><div><div class="mw-detail-content"></div></div></div></td></tr>`).join(''):`<tr><td colspan="${headers.length}" class="mw-empty">${T('当前条件下暂无已收录记录。','No collected records match these filters.')}</td></tr>`}</tbody></table>`;
const pages=Math.max(1,Math.ceil(data.total/data.page_size));root.querySelector('.mw-pager').innerHTML=`<span>${num(data.total)} ${T('条','records')} · ${page} / ${pages}</span><button data-page="${page-1}" ${page<=1?'disabled':''}>${T('上一页','Previous')}</button><button data-page="${page+1}" ${page>=pages?'disabled':''}>${T('下一页','Next')}</button>`;
root.querySelector('.mw-footnote').innerHTML=insider?T('Form 3 是初始持股申报；Form 4 是持股变动；Form 5 是年度补充申报。窗口按申报日期筛选，交易可能发生在更早日期。P / S 可包含公开市场或私人买卖；授予、行权、缴税和赠与单独展示。修订申报保留 /A 标记，不与原申报合并统计交易金额。','Form 3 reports initial ownership; Form 4 reports changes; Form 5 is an annual supplemental filing. The window uses filing dates; transactions may be earlier. P / S can include open-market or private purchases and sales. Grants, exercises, tax payments and gifts remain separate. Amendments retain /A and are not added to original filings as transaction totals.'):T('FTD 是某结算日尚未交割的累计净余额，并非当日新增量，也不等于裸卖空。不同日期的余额不可相加。列表展示最新可得结算日，展开查看最近两个官方半月批次；参考金额为股数 × SEC 文件参考价，并非成交额或空头仓位。缺失日期不自动补零。','FTD is the aggregate net outstanding balance on a settlement date, not new daily failures or evidence of naked short selling. Do not sum balances across dates. The list shows the latest available settlement date; expand for the latest two official half-month batches. Reference value is shares × the SEC reference price, not turnover or a short position. Missing dates are not filled with zeros.');
root.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{page=Number(b.dataset.page);load()});
root.querySelectorAll('.mw-record').forEach(row=>{const button=row.querySelector('[data-detail]');button.setAttribute('aria-controls','mw-detail-'+button.dataset.row);row.onclick=e=>{if(e.target.closest('a'))return;if(window.getSelection()?.toString())return;detail(button)};});}
const buyerHint = () => T('点击色块或买家姓名，查看金额与占比。','Select a slice or buyer to see the amount and share.');
document.addEventListener('click', event => {
  const hit = event.target.closest?.('[data-slice],[data-buyer],.mw-mix-info.open');
  for (const card of root.querySelectorAll('.mw-mix-info.open')) {
    const panel = card.closest('.mw-buyers');
    if (hit && panel.contains(hit)) continue;
    panel.querySelector('.selected')?.classList.remove('selected');
    panel.querySelector('[aria-pressed="true"]')?.setAttribute('aria-pressed','false');
    card.getAnimations().forEach(anim=>anim.cancel());
    card.classList.remove('open');
    card.textContent = buyerHint();
  }
}, true);
function drawBuyerMix(body, mix, filings) {
  if (!mix) return;
  if (!mix.buyers.length) {
    const types = new Set();
    for (const {payload} of filings) {
      if (!payload) continue;
      if (payload.form.split('/')[0] === '3') types.add(T('初始持仓','initial holdings'));
    }
    for (const {payload} of filings) {
      for (const trade of payload?.transactions || []) {
        if (trade.transaction && trade.code) types.add(trade.code === 'A' ? T('股权授予','equity grants') : code(trade.code));
      }
    }
    const note = document.createElement('p');
    note.textContent = T('近 30 天未查到可统计的买入。','No qualifying purchases found in the past 30 days.');
    if (types.size) {
      const labels = new Intl.ListFormat(en ? 'en' : 'zh-CN').format([...types]);
      note.textContent += T('本日披露包括',' This day’s filings include ') + labels + T('。','.');
    }
    body.append(note);
    return;
  }
  const panel = document.createElement('section');
  panel.className = 'mw-buyers';
  body.querySelector('h3').after(panel);
  const heading = T('近 30 天买入金额占比', 'Share of purchases over 30 days');
  panel.innerHTML = '<h4>'+heading+'</h4><small>'+esc(mix.start)+' — '+esc(mix.end)+'</small>';
  const colors = ['#184b46','#65988b','#b08240','#467b9b','#a46160','#687655'];
  const buyers = mix.buyers;
  const total = buyers.reduce((sum, buyer) => sum + buyer.amount, 0);
  const money = amount => new Intl.NumberFormat(en?'en-US':'zh-CN',{style:'currency',currency:'USD',currencyDisplay:'narrowSymbol'}).format(amount);
  const percent = amount => new Intl.NumberFormat(en?'en-US':'zh-CN',{style:'percent',maximumFractionDigits:2}).format(amount / total);
  const point = (r, angle) => [100+r*Math.sin(angle),100-r*Math.cos(angle)].join(' ');
  let angle = 0;
  const slices = buyers.map((buyer, i) => {
    const start = angle;
    angle += buyer.amount / total * Math.PI * 2;
    const color = colors[i % colors.length];
    if (buyers.length === 1) return '<circle data-slice="0" cx="100" cy="100" r="69" fill="none" stroke="'+color+'" stroke-width="34"/>';
    const large = angle-start > Math.PI ? 1 : 0;
    const path = 'M '+point(86,start)+' A86 86 0 '+large+' 1 '+point(86,angle)+' L '+point(52,angle)+' A52 52 0 '+large+' 0 '+point(52,start)+' Z';
    return '<path data-slice="'+i+'" fill="'+color+'" d="'+path+'"/>';
  }).join('');
  panel.insertAdjacentHTML('beforeend','<div class="mw-mix-layout"><svg viewBox="0 0 200 200" aria-hidden="true">'+slices+'<text x="100" y="99">'+buyers.length+'</text><text x="100" y="116" class="mw-ring-label">'+T('位买家','buyers')+'</text></svg><div class="mw-mix-info" aria-live="polite"></div></div><div class="mw-mix-key">'+buyers.map((b,i)=>'<button type="button" aria-pressed="false" data-buyer="'+i+'"><i style="background:'+colors[i%colors.length]+'"></i>'+chartBuyer(b)+'</button>').join('')+'</div><small>'+T('按交易日汇总已解析的非衍生证券 P 类买入；仅计单一申报人、金额已知的原始申报。涉及修订的同人同报告期记录暂不计入。','Based on parsed, priced non-derivative P purchases by transaction date. Single-filer original reports only; amended owner-periods are excluded.')+'</small>');
  const card = panel.querySelector('.mw-mix-info');
  const select = index => {
    const buyer = buyers[index];
    card.classList.add('open');
    panel.querySelectorAll('[data-slice]').forEach(el=>el.classList.toggle('selected',Number(el.dataset.slice)===index));
    panel.querySelectorAll('[data-buyer]').forEach(el=>el.setAttribute('aria-pressed',String(Number(el.dataset.buyer)===index)));
    card.innerHTML = '<small>'+T('买家','Buyer')+'</small><strong>'+ownerLine(buyer)+'</strong><b>'+money(buyer.amount)+'</b><span>'+T('占已计入金额的 ','Share of included value: ')+percent(buyer.amount)+'</span>';
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
      card.getAnimations().forEach(anim=>anim.cancel());
      card.animate([{opacity:.65,transform:'translateY(5px)'},{opacity:1,transform:'none'}],{duration:220,easing:'ease-out'});
    }
  };
  panel.onclick = event => {
    const hit = event.target.closest('[data-slice],[data-buyer]');
    if (hit) select(Number(hit.dataset.slice ?? hit.dataset.buyer));
  };
  card.textContent = buyerHint();
}
async function detail(button){const detailMode=mode,detailVersion=version;const box=root.querySelector('#mw-detail-'+button.dataset.row),body=box.querySelector('.mw-detail-content');if(box.classList.contains('open')){box.classList.remove('open');button.setAttribute('aria-expanded','false');return}box.classList.add('open');button.setAttribute('aria-expanded','true');body.textContent=T('正在读取详情…','Loading details…');
try{const params = new URLSearchParams({id:button.dataset.detail, form, q:query});
const path = detailMode === 'insider' ? '/insider/days/detail' : '/ftd/detail';
const d = await get(path+'?'+params);
if(detailVersion!==version||!box.isConnected)return;
if(detailMode==='insider'){
  body.innerHTML = '<h3>'+esc(button.textContent)+'</h3>';
  drawBuyerMix(body,d.buyer_mix,d.filings);
  for (const filing of d.filings) {
    const disclosure = document.createElement('details');
    disclosure.className = 'mw-filing';
    const summary = document.createElement('summary');
    const filingData = filing.payload;
    summary.textContent = filingData
      ? ['Form '+filingData.form, ...filingData.owners.map(owner=>owner.name)].join(' · ')
      : T('申报','Filing')+' · '+filing.accession;
    const content = document.createElement('div');
    disclosure.append(summary, content);
    body.append(disclosure);
    disclosure.addEventListener('toggle', () => {
      if (disclosure.open && !content.hasChildNodes()) renderFiling(content,filing);
    });
  }
}else{const h=d.history,max=Math.max(...h.map(r=>r.quantity),1);body.innerHTML=`<h3>${esc(h[0].ticker)} · ${esc(d.cusip)}</h3><p>${T('各结算日未交割余额；仅展示文件中存在的记录。','Outstanding balance by settlement date; only reported records are shown.')}</p><svg viewBox="0 0 800 160" role="img" aria-label="${T('未交割余额柱状图','FTD balance bar chart')}">${h.map((r,i)=>`<rect x="${i*780/h.length+10}" y="${130-r.quantity/max*115}" width="${Math.max(2,780/h.length-4)}" height="${r.quantity/max*115}" fill="#5d8f7e"><title>${esc(r.day)}: ${num(r.quantity)}</title></rect>`).join('')}<text x="10" y="155" font-size="12" fill="#526260">${esc(h[0].day)}</text><text x="690" y="155" font-size="12" fill="#526260">${esc(h.at(-1).day)}</text></svg><p>${T('窗口内单日峰值','Highest daily balance in window')}: ${num(max)} · ${T('最近记录','Latest record')}: ${esc(h.at(-1).day)}</p><a href="${safeLink(h.at(-1).batch)}" target="_blank" rel="noopener">${T('SEC 来源批次','SEC source batch')} ↗</a>`}
}catch{body.textContent=T('详情暂不可用，请稍后重试。','Details unavailable. Please try again shortly.')}}
function renderFiling(body,d){
if(!d.payload){body.innerHTML=`<p>${T('该披露已收录，结构化详情正在补录。现在可以直接查看 SEC 原文。','This filing is indexed; structured details are still being processed. You can read the SEC original now.')}</p><a href="${safeLink(d.source)}" target="_blank" rel="noopener">SEC ↗</a>`;return}const p=d.payload;
body.innerHTML=`<h3>${esc(p.issuer)} · Form ${esc(p.form)}</h3><p>${p.owners.map(ownerLine).join(' / ')}</p><p>${T('报告期','Report period')}: ${esc(p.period)} · ${esc(d.accession)}<br>10b5-1: ${p.plan_10b5_1==='1'||p.plan_10b5_1==='true'?T('已勾选','Checked'):T('未勾选或未披露','Not checked or not disclosed')}</p><div class="mw-list"><table><thead><tr>${[T('证券／日期','Security / date'),T('代码','Code'),T('股数','Shares'),T('每股价格','Price'),T('金额','Value'),T('交易后持有','Held after'),T('持有方式','Ownership')].map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${p.transactions.map(t=>`<tr><td>${esc(t.security)}<small>${esc(t.date||p.period)} · ${t.derivative?T('衍生证券','Derivative'):T('非衍生证券','Non-derivative')}</small></td><td>${esc(t.code||T('持仓','Holding'))}<small>${esc(code(t.code))}</small></td><td class="mw-number">${num(t.shares)}</td><td class="mw-number">${t.price==null?'—':'$'+num(t.price)}</td><td class="mw-number">${t.value==null?'—':'$'+num(t.value)}</td><td class="mw-number">${num(t.held_after)}</td><td>${esc(t.ownership)}<small>${esc(t.nature)}</small></td></tr>`).join('')}</tbody></table></div><p>${T('英文原始脚注（自动翻译暂未启用）','Original footnotes')}</p>${Object.entries(p.footnotes).map(([id,text])=>`<p><b>${esc(id)}</b> ${esc(text)}</p>`).join('')}<p>${esc(p.remarks||'')}</p><a href="${safeLink(d.source)}" target="_blank" rel="noopener">${T('查看 SEC 原始申报','Read original SEC filing')} ↗</a>`;
}

root.querySelector('form').onsubmit=e=>{e.preventDefault();query=root.querySelector('input').value;page=1;load()};root.querySelector('select').onchange=e=>{form=e.target.value;page=1;load()};root.querySelector('.mw-refresh').onclick=()=>load();
root.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{if(mode===b.dataset.tab)return;mode=b.dataset.tab;dateFilter.hidden=mode==='ftd';if(lastStatus)showStatus(lastStatus);page=1;query='';form='all';root.querySelector('input').value='';root.querySelector('select').value='all';root.querySelector('select').style.visibility=mode==='ftd'?'hidden':'';root.querySelector('select').disabled=mode==='ftd';root.querySelector('input').placeholder=mode==='ftd'?T('股票代码、公司或 CUSIP','Ticker, company or CUSIP'):T('股票代码、公司或内部人姓名','Ticker, company or insider name');root.querySelectorAll('[data-tab]').forEach(x=>x.setAttribute('aria-selected',String(x===b)));load()});
query = (new URLSearchParams(location.search).get('company') || '').trim().slice(0, 100);
root.querySelector('.mw-search input').value = query;
load();setInterval(()=>{if(!document.hidden&&!root.querySelector('.mw-detail.open'))load(true)},60000);
})();
