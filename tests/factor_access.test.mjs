import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';
const source=readFileSync(new URL('../assets/factor-access.js',import.meta.url),'utf8');
test('a guest can search without a session check',async()=>{
 const requests=[],events={};
 const node={value:'AAPL',replaceChildren(){},append(){},addEventListener(type,fn){events[type]=fn;}};
 const root={querySelector:()=>node};
 const document={querySelector:()=>root,documentElement:{lang:'en'}};
 vm.runInNewContext(source,{document,URLSearchParams,fetch:async url=>{
  requests.push(url);return {ok:true,json:async()=>({results:[]})};
 }});
 await events.submit({preventDefault(){}});
 assert.equal(requests.length,1);
 assert.match(requests[0],/factor_endpoint=public_search&q=AAPL/);
 assert.equal(node.textContent,'No matching companies.');
});
