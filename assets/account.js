'use strict';
(() => {
 const origin='https://global.residualinertia.com';
 async function updateAccount(){
  try{
   const response=await fetch(origin+'/api/research/session',{credentials:'include',cache:'no-store'});
   if(!response.ok)return;
   const session=await response.json();
   for(const link of document.querySelectorAll('[data-account-link]')){
    link.textContent=session.canPublish?link.dataset.manage:(session.authenticated?session.username:link.dataset.login);
    link.href=origin+(session.canPublish?'/research/manage':(session.authenticated?'/account':'/auth/login?next=/account'));
   }
   for(const link of document.querySelectorAll('[data-import-report]')){
    link.hidden=!session.canPublish;link.href=origin+'/research/manage';
   }
  }catch{}
 }
 updateAccount();
 window.addEventListener('pageshow',updateAccount);
 window.addEventListener('focus',updateAccount);
})();
