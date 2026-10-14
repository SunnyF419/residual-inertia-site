"""Exercise the PowerShell publisher against a real, entirely local Git origin."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELL = Path(os.environ.get('SystemRoot', 'C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
ORIGIN = 'https://github.com/SunnyF419/residual-inertia-site.git'


@unittest.skipUnless(os.name == 'nt' and SHELL.exists() and shutil.which('git'), 'Windows PowerShell and Git required')
class MarketPublication(unittest.TestCase):
    def setUp(self):
        temp_root = Path(tempfile.gettempdir()).resolve()
        self.temp = tempfile.TemporaryDirectory(prefix='ri-market-publish-', dir=temp_root)
        self.base = Path(self.temp.name).resolve()
        self.assertTrue(self.base.is_relative_to(temp_root))
        self.addCleanup(self.temp.cleanup)
        self.remote = self.base/'origin.git'
        self.source = self.base/'website'
        self.portal = self.base/'quant_research_portal'
        self.clone = self.source/'.runtime/website-sync/publication'
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith('GIT_CONFIG_'):
                del self.env[key]
        # The verified public URL resolves ONLY to this test's local bare repo.
        config = self.base/'git-test-config'
        config.write_text(f'[user]\n name = Publication Test\n email = test@example.invalid\n[url "{self.remote.as_posix()}"]\n insteadOf = {ORIGIN}\n', encoding='utf-8')
        self.env['GIT_CONFIG_GLOBAL'] = str(config)
        self.env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + self.env['PATH']
        self.git(self.base, 'init', '--bare', '--initial-branch=main', str(self.remote))
        seed = self.base/'seed'
        self.git(self.base, 'init', '--initial-branch=main', str(seed))
        for name in ['Update Website.ps1', 'Run Website Sync.ps1', 'scripts/publish_market.ps1']:
            destination = seed/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, destination)
        (seed/'.gitignore').write_text('.runtime/\ndist/\n__pycache__/\n', encoding='utf-8')
        (seed/'README.md').write_text('Committed documentation\n', encoding='utf-8')
        (seed/'content/market').mkdir(parents=True)
        (seed/'content/snapshots').mkdir(parents=True)
        (seed/'content/snapshots/2026-10-09.json').write_text('{}\n', encoding='utf-8')
        self.old = {'market': {'regimeDate': '2026-10-09', 'regimeScore': 65.8}}
        (seed/'content/market/latest.json').write_text(json.dumps(self.old), encoding='utf-8')
        (seed/'scripts/import_portal.py').write_text('''from pathlib import Path
import argparse,json,sys
p=argparse.ArgumentParser();p.add_argument('--portal',type=Path,required=True);a=p.parse_args()
if (a.portal/'IMPORT_FAIL').exists():sys.exit(1)
v=json.loads((a.portal/'latest.json').read_text())
Path('content/market/latest.json').write_text(json.dumps(v))
Path('content/snapshots/2026-10-14.json').write_text(json.dumps(v))
''', encoding='utf-8')
        (seed/'scripts/build.py').write_text('''from pathlib import Path
import subprocess,json
Path('.runtime').mkdir(exist_ok=True)
with Path('.runtime/builds.txt').open('a') as f:f.write('build\\n')
flag=Path(__file__).resolve().parents[5]/'concurrent.json'
if flag.exists():
 d=json.loads(flag.read_text());flag.unlink();repo=Path(d['repo']);p=repo/'content/research/new-report.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{"title":"Uploaded concurrently"}')
 for args in [('add','content/research/new-report.json'),('commit','-m','author report'),('push','origin','main')]:subprocess.run(['git','-C',str(repo),*args],check=True)
''', encoding='utf-8')
        # Validation failure is controlled by a local test marker, not real data.
        (seed/'scripts/check.py').write_text("from pathlib import Path\nimport sys\nmarker=Path(__file__).resolve().parents[5]/'CHECK_FAIL'\nsys.exit(1 if marker.exists() else 0)\n", encoding='utf-8')
        self.git(seed, 'add', '.')
        self.git(seed, 'commit', '-m', 'fixture baseline')
        self.git(seed, 'remote', 'add', 'origin', ORIGIN)
        self.git(seed, 'push', 'origin', 'main')
        self.git(self.base, 'clone', '--branch', 'main', ORIGIN, str(self.source))
        self.portal.mkdir()
        self.latest = {'market': {'regimeDate': '2026-10-13', 'regimeScore': 66.3}}
        (self.portal/'latest.json').write_text(json.dumps(self.latest), encoding='utf-8')
        self.before = self.git(self.remote, 'rev-parse', 'main')

    def git(self, cwd, *args):
        result = subprocess.run(['git', '-C', str(cwd), *args], env=self.env, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def publish(self, expected=0, script='Update Website.ps1', extra=()):
        args = ['-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(self.source/script)]
        if script == 'Update Website.ps1':
            args += ['-PortalPath', '../quant_research_portal', '-Publish']
        result = subprocess.run([str(SHELL), *args, *extra], cwd=self.source, env=self.env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        if expected == 0:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_dirty_and_unpushed_development_are_preserved_and_never_published(self):
        (self.source/'development.py').write_text('unreviewed\n')
        self.git(self.source, 'add', 'development.py')
        self.git(self.source, 'commit', '-m', 'local development')
        (self.source/'README.md').write_text('Uncommitted draft\n')
        self.git(self.source, 'add', 'README.md')
        (self.source/'untracked.txt').write_text('keep me\n')
        status = self.git(self.source, 'status', '--porcelain')
        head = self.git(self.source, 'rev-parse', 'HEAD')
        self.publish()
        self.assertEqual(self.git(self.source, 'status', '--porcelain'), status)
        self.assertEqual(self.git(self.source, 'rev-parse', 'HEAD'), head)
        self.assertEqual(json.loads((self.source/'content/market/latest.json').read_text()), self.old)
        changed = self.git(self.remote, 'diff', '--name-only', self.before, 'main').splitlines()
        self.assertTrue(changed)
        self.assertTrue(all(path.startswith(('content/market/', 'content/snapshots/')) for path in changed))
        result = json.loads((self.source/'.runtime/website-sync/publication-result.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(result['dataAsOf'], '2026-10-13')

    def test_unrelated_clone_changes_and_staging_are_rejected(self):
        self.publish()
        head = self.git(self.remote, 'rev-parse', 'main')
        (self.clone/'README.md').write_text('unreviewed clone change\n')
        self.git(self.clone, 'add', 'README.md')
        self.publish(expected=1)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), head)
        self.assertEqual((self.clone/'README.md').read_text(), 'unreviewed clone change\n')

    def test_unrelated_unpushed_clone_commits_are_rejected(self):
        self.publish()
        head = self.git(self.remote, 'rev-parse', 'main')
        (self.clone/'README.md').write_text('unreviewed clone commit\n')
        self.git(self.clone, 'add', 'README.md')
        self.git(self.clone, 'commit', '-m', 'unreviewed')
        self.publish(expected=1)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), head)

    def test_untracked_clone_code_is_preserved_and_rejected(self):
        self.publish()
        head = self.git(self.remote, 'rev-parse', 'main')
        draft = self.clone/'unreviewed.py'
        draft.write_text('keep this draft\n')
        self.publish(expected=1)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), head)
        self.assertEqual(draft.read_text(), 'keep this draft\n')

    def test_existing_publication_mutex_blocks_second_publisher(self):
        ready = self.base/'mutex-held'
        literal = str(ready).replace("'", "''")
        command = "$m=New-Object System.Threading.Mutex($false,'Local\\ResidualInertiaWebsitePublish');if(-not $m.WaitOne(0)){exit 9};try{Set-Content -LiteralPath '" + literal + "' -Value ready;Start-Sleep -Seconds 5}finally{$m.ReleaseMutex();$m.Dispose()}"
        child = subprocess.Popen([str(SHELL), '-NoProfile', '-NonInteractive', '-Command', command], env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists(), 'Unable to acquire publication test mutex')
            result = self.publish(expected=1)
            self.assertIn('Another website publication', result.stderr)
            self.assertFalse(self.clone.exists())
            self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), self.before)
        finally:
            child.wait(timeout=8)

    def test_pending_data_commits_are_recovered(self):
        self.publish()
        (self.clone/'content/snapshots/pending.json').write_text('{}\n')
        self.git(self.clone, 'add', 'content/snapshots/pending.json')
        self.git(self.clone, 'commit', '-m', 'pending data')
        self.publish()
        self.assertEqual(self.git(self.remote, 'show', 'main:content/snapshots/pending.json'), '{}')

    def test_pending_data_merge_with_known_author_upload_is_recovered(self):
        self.publish()
        (self.clone/'content/snapshots/pending.json').write_text('{}\n')
        self.git(self.clone, 'add', 'content/snapshots/pending.json')
        self.git(self.clone, 'commit', '-m', 'pending data')
        uploader = self.base/'uploader'
        self.git(self.base, 'clone', '--branch', 'main', ORIGIN, str(uploader))
        (uploader/'content/research').mkdir()
        (uploader/'content/research/new-report.json').write_text('{"title":"Known author upload"}')
        self.git(uploader, 'add', 'content/research/new-report.json')
        self.git(uploader, 'commit', '-m', 'author upload')
        self.git(uploader, 'push', 'origin', 'main')
        self.git(self.clone, 'fetch', 'origin', 'main')
        self.git(self.clone, 'merge', '--no-edit', 'origin/main')
        self.publish()
        self.assertEqual(self.git(self.remote, 'show', 'main:content/snapshots/pending.json'), '{}')
        self.assertIn('Known author upload', self.git(self.remote, 'show', 'main:content/research/new-report.json'))

    def test_unreviewed_code_added_only_to_a_local_merge_is_rejected(self):
        self.publish()
        head = self.git(self.remote, 'rev-parse', 'main')
        self.git(self.clone, 'checkout', '-b', 'data-side')
        (self.clone/'content/snapshots/side.json').write_text('{}\n')
        self.git(self.clone, 'add', 'content/snapshots/side.json')
        self.git(self.clone, 'commit', '-m', 'side data')
        self.git(self.clone, 'checkout', 'main')
        (self.clone/'content/snapshots/pending.json').write_text('{}\n')
        self.git(self.clone, 'add', 'content/snapshots/pending.json')
        self.git(self.clone, 'commit', '-m', 'pending data')
        self.git(self.clone, 'merge', '--no-commit', 'data-side')
        (self.clone/'README.md').write_text('Unreviewed merge-only change\n')
        self.git(self.clone, 'add', 'README.md')
        self.git(self.clone, 'commit', '-m', 'merge with unreviewed code')
        self.publish(expected=1)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), head)

    def test_import_failure_does_not_publish(self):
        (self.portal/'IMPORT_FAIL').write_text('fail\n')
        self.publish(expected=1)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), self.before)
        self.assertFalse((self.source/'.runtime/website-sync/publication-result.json').exists())

    def test_validation_failure_does_not_publish(self):
        (self.base/'CHECK_FAIL').write_text('fail\n')
        self.publish(expected=1)
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), self.before)

    def test_concurrently_uploaded_report_is_merged_and_revalidated(self):
        uploader = self.base/'uploader'
        self.git(self.base, 'clone', '--branch', 'main', ORIGIN, str(uploader))
        (self.base/'concurrent.json').write_text(json.dumps({'repo': str(uploader)}))
        self.publish()
        self.assertIn('Uploaded concurrently', self.git(self.remote, 'show', 'main:content/research/new-report.json'))
        self.assertEqual(len((self.clone/'.runtime/builds.txt').read_text().splitlines()), 2)

    def test_repeat_without_new_data_does_not_create_a_commit(self):
        self.publish()
        head = self.git(self.remote, 'rev-parse', 'main')
        self.publish()
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), head)

    def test_windows_line_ending_warnings_are_not_changed_file_paths(self):
        # Match production: Git requires LF JSON, while Python writes CRLF.
        config = self.base/'git-test-config'
        with config.open('a', encoding='utf-8') as output:
            output.write('[core]\n autocrlf = true\n')
        (self.source/'.gitattributes').write_text('*.json text eol=lf\n', encoding='utf-8')
        importer = self.source/'scripts/import_portal.py'
        importer.write_text(importer.read_text(encoding='utf-8').replace(
            '.write_text(json.dumps(v))', '.write_text(json.dumps(v, indent=2) + "\\n")'), encoding='utf-8')
        self.git(self.source, 'add', '.gitattributes', 'scripts/import_portal.py')
        self.git(self.source, 'commit', '-m', 'fixture LF JSON export policy')
        self.git(self.source, 'push', 'origin', 'main')
        result = self.publish()
        self.assertIn('warning:', result.stdout)
        published = json.loads(self.git(self.remote, 'show', 'main:content/market/latest.json'))
        self.assertEqual(published, self.latest)
        head = self.git(self.remote, 'rev-parse', 'main')
        self.publish()
        self.assertEqual(self.git(self.remote, 'rev-parse', 'main'), head)

    def test_run_status_reads_published_clone_not_stale_development_copy(self):
        node = shutil.which('node') or str(Path(os.environ.get('USERPROFILE', 'C:/Users/THINKBOOK'))/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
        if not Path(node).exists():
            self.skipTest('Node required for Run Website Sync')
        (self.portal/'scripts').mkdir()
        (self.portal/'scripts/sync-portal-data.mjs').write_text('// No-op local fixture\n')
        runtime = self.source/'.runtime/website-sync'
        runtime.mkdir(parents=True)
        (runtime/'paths.json').write_text(json.dumps({'node': node, 'python': sys.executable, 'git': shutil.which('git')}))
        self.publish(script='Run Website Sync.ps1')
        status = json.loads((runtime/'latest.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(status['status'], 'pushed')
        self.assertEqual(status['dataAsOf'], '2026-10-13')
        self.assertEqual(status['publishedCommit'], self.git(self.remote, 'rev-parse', 'main'))
        self.assertEqual(json.loads((self.source/'content/market/latest.json').read_text()), self.old)


if __name__ == '__main__':
    unittest.main()
