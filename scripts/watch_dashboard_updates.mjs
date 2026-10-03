// Publish after a completed dashboard update, never while a transaction is running.
import { appendFileSync, existsSync, mkdirSync, readFileSync, renameSync, watch, writeFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export function completedMarketUpdate(record, processedId) {
  return Boolean(record?.dashboardId === 'marketResearch' && record.action === 'update'
    && record.status === 'success' && record.transaction?.status === 'committed'
    && ['pass', 'warning'].includes(record.after?.quality?.status)
    && record.runId && record.runId !== processedId);
}

export function latestMarketRecord(text) {
  // Ignore an incomplete final JSONL write; the next filesystem event will retry it.
  const records = text.split(/\r?\n/).flatMap(line => {
    try { return [JSON.parse(line)]; } catch { return []; }
  });
  return records.reverse().find(r => r.dashboardId === 'marketResearch') ?? null;
}

export function createCompletionQueue({ readEvent, publish, save, isBusy, log = () => {}, retryMs = 300000 }) {
  let running = false;
  let timer;
  const notify = (delay = 1200) => {
    clearTimeout(timer);
    timer = setTimeout(flush, delay);
  };
  const flush = async () => {
    if (running) { notify(); return; }
    const event = readEvent();
    if (!event) return;
    if (isBusy()) { notify(3000); return; }
    running = true;
    try {
      await publish(event);
      save(event);
      log('Completed dashboard update exported and pushed: ' + event.id);
      // Check for an update that finished while publication was running.
      notify();
    } catch (error) {
      log('Publication pending; retrying completed update: ' + error.message);
      notify(retryMs);
    } finally {
      running = false;
    }
  };
  return { notify, flush, close: () => clearTimeout(timer) };
}

async function main() {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const portal = resolve(root, '..', 'quant_research_portal');
  const runtime = resolve(root, '.runtime', 'website-sync');
  const historyDir = resolve(portal, '.runtime', 'updates');
  const requests = resolve(runtime, 'requests');
  const statePath = resolve(runtime, 'completed.json');
  [runtime, historyDir, requests].forEach(p => mkdirSync(p, { recursive: true }));
  const load = path => { try { return JSON.parse(readFileSync(path, 'utf8').replace(/^\uFEFF/, '')); } catch { return null; } };
  let processed = load(statePath) ?? {};
  const log = line => appendFileSync(resolve(runtime, 'events.log'), `[${new Date().toISOString()}] ${line}\n`, 'utf8');
  const { readDailyArchiveRunLock } = await import(pathToFileURL(resolve(portal, 'scripts', 'daily-archive-lock.mjs')).href);
  const queue = createCompletionQueue({
    readEvent() {
      // A successful direct dashboard UI update can also request publication.
      const direct = load(resolve(requests, 'latest.json'));
      if (direct?.status === 'success' && direct.id && direct.id !== processed.directId) return { id: direct.id, type: 'direct' };
      const path = resolve(historyDir, 'history.jsonl');
      if (!existsSync(path)) return null;
      const record = latestMarketRecord(readFileSync(path, 'utf8'));
      return completedMarketUpdate(record, processed.runId) ? { id: record.runId, type: 'portal' } : null;
    },
    isBusy: () => readDailyArchiveRunLock(resolve(portal, '.runtime', 'daily-archive', 'run.lock')).active,
    publish: () => new Promise((resolveRun, rejectRun) => {
      const shell = resolve(process.env.SystemRoot ?? 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
      const child = spawn(shell, ['-NoLogo', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File', resolve(root, 'Run Website Sync.ps1')], { cwd: root, windowsHide: true, stdio: 'ignore' });
      child.once('error', rejectRun);
      child.once('close', code => code === 0 ? resolveRun() : rejectRun(new Error('Sync exited ' + code + '; see sync.log')));
    }),
    save(event) {
      processed = { ...processed, [event.type === 'direct' ? 'directId' : 'runId']: event.id, pushedAt: new Date().toISOString() };
      writeFileSync(statePath + '.tmp', JSON.stringify(processed, null, 2) + '\n', 'utf8');
      renameSync(statePath + '.tmp', statePath);
    },
    log,
  });
  // Directory watches survive history rotation and atomic marker replacement.
  const observers = [historyDir, requests].map(path => watch(path, () => queue.notify()));
  for (const observer of observers) observer.on('error', error => { log('Completion listener failed: ' + error.message); process.exitCode = 1; queue.close(); observers.forEach(o => o.close()); });
  process.on('SIGTERM', () => { queue.close(); observers.forEach(o => o.close()); });
  log('Listening for completed market updates. No periodic publication.');
  queue.notify(100);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
}
