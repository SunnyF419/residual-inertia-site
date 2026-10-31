'use strict';
(() => {
 const root=document.querySelector('[data-factor-access]');
 if(!root)return;
 const find=selector=>root.querySelector(selector);
 const t=(zh,en)=>document.documentElement.lang.startsWith('en')?en:zh;
 const status=find('[data-status]'), results=find('[data-results]'), profile=find('[data-profile]'), date=find('[data-date]');
 const factors={value:t('价值','Value'),growth:t('成长','Growth'),quality:t('质量','Quality'),momentum:t('动量','Momentum'),lowvol:t('低波','Low volatility'),size:t('规模','Size'),investment:t('投资','Investment'),bab:t('低贝塔','Betting against beta')};
 let sequence=0,history=[];
 async function request(endpoint,params){
  const query=new URLSearchParams({factor_endpoint:endpoint,...params});
  const response=await fetch('/api/research/session?'+query,{cache:'no-store'});
  if(!response.ok)throw new Error();
  return response.json();
 }
 function render(){
  const row=history[date.selectedIndex];
  find('tbody').replaceChildren();
  if(!row)return;
  for(const [id,label] of Object.entries(factors)){
   const rank=key=>row[id+'_'+key+'_rank']==null?'—':row[id+'_'+key+'_rank']+' / '+row[id+'_'+key+'_n'];
   const tr=document.createElement('tr');
   for(const value of [label,row[id+'_score']==null?'—':row[id+'_score'].toFixed(2),rank('market'),rank('industry')]){
    const td=document.createElement('td');td.textContent=value;tr.append(td);
   }
   find('tbody').append(tr);
  }
 }
 date.addEventListener('change',render);
 const failure=t('查询暂时不可用，请重试。','The lookup is unavailable. Please try again.');
 async function selectCompany(company){
  const token=++sequence;profile.hidden=true;status.textContent=t('正在读取历史评分…','Loading score history…');
  try{
   const data=await request('public_company',{id:company.permco});
   if(token!==sequence)return;
   history=data.history.slice().reverse();
   if(!history.length){status.textContent=t('暂无历史评分。','No score history available.');return;}
   date.replaceChildren(...history.map(row=>new Option(row.as_of,row.as_of)));
   find('[data-company]').textContent=[data.company.ticker,data.company.company_name].filter(Boolean).join(' · ');
   render();profile.hidden=false;status.textContent='';
  }catch{if(token===sequence)status.textContent=failure;}
 }
 find('[data-search]').addEventListener('submit',async event=>{
  event.preventDefault();const q=find('input').value.trim();if(!q)return;
  const token=++sequence;results.replaceChildren();profile.hidden=true;status.textContent=t('正在查询…','Searching…');
  try{
   const data=await request('public_search',{q});if(token!==sequence)return;
   status.textContent=data.results.length?t('选择公司查看评分。','Select a company to view its scores.'):t('未找到匹配公司。','No matching companies.');
   for(const company of data.results){
    const button=document.createElement('button');button.className='action-link';button.type='button';
    button.textContent=[company.ticker,company.company_name].filter(Boolean).join(' · ');
    button.addEventListener('click',()=>selectCompany(company));results.append(button);
   }
   if(data.results.length===1)selectCompany(data.results[0]);
  }catch{if(token===sequence)status.textContent=failure;}
 });
})();
