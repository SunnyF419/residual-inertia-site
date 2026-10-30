'use strict';
(() => {
 const root=document.querySelector('[data-factor-access]');
 if(!root)return;
 const language=document.documentElement.lang.startsWith('en')?'en':'zh';
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),8000);
 fetch('/api/research/session',{credentials:'same-origin',cache:'no-store',signal:controller.signal})
 .then(response=>response.ok?response.json():null)
 .then(session=>{
  if(session?.authenticated===true&&session.canQueryFactors===true){
   root.querySelector('[data-factor-message]').textContent=language==='en'?'Opening your factor workspace…':'正在打开你的因子查询台…';
   window.location.replace('/account?view=factors');
  }else if(session?.authenticated){root.querySelector('[data-factor-login]').hidden=true;}
 }).catch(()=>{}).finally(()=>clearTimeout(timer));
})();
