'use strict';
(() => {
 const origin='https://global.residualinertia.com';
 let pending;
 async function updateAccount(){
  if(pending)pending.abort();
  const controller=new AbortController();pending=controller;
  const timeout=setTimeout(()=>controller.abort(),8000);
  try{
   const response=await fetch(origin+'/api/research/session',{credentials:'include',cache:'no-store',signal:controller.signal});
   if(!response.ok)return;
   const session=await response.json();
   if(pending!==controller)return;
   for(const link of document.querySelectorAll('[data-account-link]')){
    link.textContent=session.authenticated?(link.dataset.account||session.username):link.dataset.login;
    link.href=origin+(session.authenticated?'/account':'/auth/login?next=/account');
   }
   for(const link of document.querySelectorAll('[data-import-report]')){
    link.hidden=!session.canPublish;link.href=origin+'/research/manage';
   }
  }catch{}finally{clearTimeout(timeout);}
 }
 updateAccount();
 window.addEventListener('pageshow',updateAccount);
 window.addEventListener('focus',updateAccount);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)updateAccount();});
})();
