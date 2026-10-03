import assert from 'node:assert/strict';
import { completedMarketUpdate, createCompletionQueue, latestMarketRecord } from '../scripts/watch_dashboard_updates.mjs';
const good = { dashboardId: 'marketResearch', action: 'update', status: 'success', transaction: { status: 'committed' }, after: { quality: { status: 'pass' } }, runId: 'good-1' };
assert.equal(completedMarketUpdate(good, null), true);
assert.equal(completedMarketUpdate(good, 'good-1'), false);
for (const change of [{ status: 'running' }, { status: 'error' }, { action: 'rollback' }, { dashboardId: 'holdings' }, { transaction: { status: 'auto_restored' } }, { after: { quality: { status: 'fail' } } }]) assert.equal(completedMarketUpdate({ ...good, ...change }, null), false);
const error = { ...good, runId: 'error-2', status: 'error' };
assert.equal(latestMarketRecord(JSON.stringify(good) + '\n' + JSON.stringify(error) + '\n').runId, 'error-2');
assert.equal(latestMarketRecord(JSON.stringify(good) + '\n{"incomplete":').runId, 'good-1');
let pending = { id: 'good-1' }, busy = true, attempts = 0, acknowledgements = 0, fail = true;
const queue = createCompletionQueue({ readEvent: () => pending, isBusy: () => busy,
  publish: async () => { attempts++; if (fail) throw new Error('offline'); },
  save: () => { acknowledgements++; pending = null; } });
await queue.flush();
assert.equal(attempts, 0, 'Do not publish while a dashboard transaction is active');
busy = false;
await queue.flush();
assert.equal(acknowledgements, 0, 'Do not acknowledge a failed push');
fail = false;
await queue.flush();
assert.equal(attempts, 2);
assert.equal(acknowledgements, 1);
await queue.flush();
assert.equal(attempts, 2, 'Do not republish the same completion');
queue.close();
console.log('PASS: completed commits only, failure isolation, lock deferral, push retry and event deduplication.');
