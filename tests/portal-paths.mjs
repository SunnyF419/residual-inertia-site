import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { resolve } from 'node:path';
import { resolvePortal } from '../scripts/resolve_portal.mjs';
const runtime = resolve('.runtime/website-sync/path-tests');
mkdirSync(runtime,{recursive:true});
const base=mkdtempSync(resolve(runtime,'case-'));
try {
  const site=resolve(base,'04_品牌与发布/01_官网/site');
  const portal=resolve(base,'01_日常看板/00_统一门户/quant_research_portal');
  mkdirSync(site,{recursive:true}); mkdirSync(portal,{recursive:true});
  writeFileSync(resolve(portal,'portal.config.json'),'{}');
  assert.equal(resolvePortal(site),portal);
  assert.throws(()=>resolvePortal(site,resolve(base,'absent')));
  const legacy=resolve(base,'legacy');mkdirSync(resolve(legacy,'site'),{recursive:true});
  mkdirSync(resolve(legacy,'quant_research_portal'),{recursive:true});
  writeFileSync(resolve(legacy,'quant_research_portal/portal.config.json'),'{}');
  assert.equal(resolvePortal(resolve(legacy,'site')),resolve(legacy,'quant_research_portal'));
  console.log('Portal resolution: migrated, explicit failure and legacy paths passed.');
} finally { rmSync(base,{recursive:true,force:true}); }
