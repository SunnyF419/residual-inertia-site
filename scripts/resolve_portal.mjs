import { existsSync, readFileSync, realpathSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export function resolvePortal(root, configured = process.env.RI_PORTAL_PATH) {
  root = realpathSync(root);
  if (!configured) {
    const config = resolve(root, '.runtime/website-sync/paths.json');
    if (existsSync(config)) configured = JSON.parse(readFileSync(config, 'utf8').replace(/^\uFEFF/, '')).portal;
  }
  if (configured) {
    const path = resolve(root, configured);
    if (!existsSync(resolve(path, 'portal.config.json'))) throw new Error('Configured portal is unavailable');
    return realpathSync(path);
  }
  const candidates = [resolve(root, '..', 'quant_research_portal')];
  for (let parent = root; dirname(parent) !== parent; parent = dirname(parent)) {
    candidates.push(resolve(parent, '01_日常看板/00_统一门户/quant_research_portal'));
  }
  const found = candidates.find(p => existsSync(resolve(p, 'portal.config.json')));
  if (!found) throw new Error('Portal not found; configure RI_PORTAL_PATH or website-sync/paths.json portal');
  return realpathSync(found);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log(resolvePortal(process.argv[2] || resolve(dirname(fileURLToPath(import.meta.url)), '..')));
}
