import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';
const source=readFileSync(new URL('../assets/factor-access.js',import.meta.url),'utf8');
for(const lang of ['zh','en']){
 for(const scenario of ['owner','reader','guest','network','server','invalid']){
  test(lang+' '+scenario,async()=>{
   const nodes=Object.fromEntries(['title','message','denied','login','retry'].map(key=>[key,{hidden:['denied','login','retry'].includes(key),textContent:'',addEventListener(type,fn){this.click=fn;}}]));
   let resolve,reject,redirect;
   const pending=new Promise((a,b)=>{resolve=a;reject=b;});
   const root={querySelector:sel=>nodes[sel.match(/data-factor-(.*)\]/)[1]],setAttribute(){}};
   vm.runInNewContext(source,{document:{querySelector:()=>root,documentElement:{lang}},AbortController,setTimeout,clearTimeout,fetch:()=>pending,window:{location:{replace:url=>{redirect=url;}}}});
   assert.equal(nodes.denied.hidden,true,'No denial while session is pending');
   if(scenario==='network')reject(new Error('offline'));
   else resolve({ok:scenario!=='server',json:async()=>scenario==='invalid'?{}:{authenticated:scenario!=='guest',canQueryFactors:scenario==='owner'}});
   await new Promise(done=>setImmediate(done));
   if(scenario==='owner'){
    assert.equal(redirect,'/account?view=factors&lang='+lang);
    assert.equal(nodes.denied.hidden,true);
   }else if(scenario==='guest'){
    assert.equal(nodes.denied.hidden,true);
    assert.equal(nodes.login.hidden,false);
    assert.equal(nodes.title.textContent,lang==='en'?'Please log in':'请先登录账户');
    assert.equal(redirect,undefined);
   }else if(scenario==='reader'){
    assert.equal(nodes.denied.hidden,false);
    assert.equal(nodes.login.hidden,scenario==='reader');
    assert.equal(redirect,undefined);
   }else{
    assert.equal(nodes.denied.hidden,true,'Failures must not claim access denied');
    assert.equal(nodes.retry.hidden,false);
    nodes.retry.click();
    assert.equal(nodes.denied.hidden,true);
    await new Promise(done=>setImmediate(done));
   }
  });
 }
}
