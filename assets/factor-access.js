'use strict';
(() => {
 const root=document.querySelector('[data-factor-access]');
 if(!root)return;
 const language=document.documentElement.lang.startsWith('en')?'en':'zh';
 const text=(zh,en)=>language==='en'?en:zh;
 const title=root.querySelector('[data-factor-title]');
 const message=root.querySelector('[data-factor-message]');
 const denied=root.querySelector('[data-factor-denied]');
 const login=root.querySelector('[data-factor-login]');
 const retry=root.querySelector('[data-factor-retry]');
 async function openWorkspace(){
  root.setAttribute('aria-busy','true');
  denied.hidden=login.hidden=retry.hidden=true;
  title.hidden=false;
  title.textContent=text('正在打开因子查询','Opening factor research');
  message.textContent=text('正在确认登录状态…','Checking your session…');
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),8000);
  try{
   const response=await fetch('/api/research/session',{credentials:'same-origin',cache:'no-store',signal:controller.signal});
   if(!response.ok)throw new Error('Session unavailable');
   const session=await response.json();
   if(typeof session?.authenticated!=='boolean'||(session.authenticated&&typeof session.canQueryFactors!=='boolean'))throw new Error('Invalid session');
   if(session.authenticated===true&&session.canQueryFactors===true){
    message.textContent=text('正在打开你的因子查询台…','Opening your factor workspace…');
    window.location.replace('/account?view=factors&lang='+language);
   }else{
    root.setAttribute('aria-busy','false');
    title.hidden=true;
    message.textContent='';
    denied.hidden=false;
    login.hidden=session.authenticated;
   }
  }catch{
   root.setAttribute('aria-busy','false');
   title.textContent=text('暂时无法确认登录状态','Unable to check your session');
   message.textContent=text('请重试，或返回其他页面。','Please try again or return to another page.');
   retry.hidden=false;
  }finally{clearTimeout(timer);}
 }
 retry.addEventListener('click',openWorkspace);
 openWorkspace();
})();
