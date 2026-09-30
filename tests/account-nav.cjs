const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');
const code=fs.readFileSync('assets/account.js','utf8');
const account={dataset:{account:'账户',login:'登录 / 注册'},textContent:'',href:''};
const upload={hidden:true,href:''};const events={};let session={authenticated:true,canPublish:true,username:'Sunny'};
const queue=[];let deferred=false;
const context={AbortController,setTimeout,clearTimeout,document:{hidden:false,querySelectorAll(selector){return selector==='[data-account-link]'?[account]:[upload]},addEventListener(name,callback){events[name]=callback}},window:{addEventListener(name,callback){events[name]=callback}},fetch(){if(deferred)return new Promise(resolve=>queue.push(resolve));return Promise.resolve({ok:true,json:async()=>session})}};
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 vm.runInNewContext(code,context);await flush();
 assert.equal(account.href,'https://global.residualinertia.com/account');assert.equal(account.textContent,'账户');assert.equal(upload.hidden,false);
 session={authenticated:true,canPublish:false,username:'Reader'};events.focus();await flush();assert.equal(account.href,'https://global.residualinertia.com/account');assert.equal(upload.hidden,true);
 session={authenticated:false,canPublish:false};events.pageshow();await flush();assert.equal(account.textContent,'登录 / 注册');assert.equal(upload.hidden,true);
 deferred=true;events.focus();events.focus();
 queue[1]({ok:true,json:async()=>({authenticated:false,canPublish:false})});await flush();
 queue[0]({ok:true,json:async()=>({authenticated:true,canPublish:true,username:'Sunny'})});await flush();
 assert.equal(account.textContent,'登录 / 注册');assert.equal(upload.hidden,true);
 console.log('PASS: stable account link, owner-only import, logout refresh and stale response protection.');
})();
