"""Run on the authorized DOCN host after copying the three release files."""
import pathlib
import shutil
import subprocess
import time
import urllib.request

def run(*args):
    subprocess.run(args, check=True)

base = pathlib.Path('/opt/ri-market-watch')
base.mkdir(exist_ok=True)
if subprocess.run(['id', '-u', 'ri-market-watch'], capture_output=True).returncode:
    run('useradd', '--system', '--home', str(base), '--shell', '/usr/sbin/nologin', 'ri-market-watch')
data = pathlib.Path('/var/lib/ri-market-watch')
data.mkdir(exist_ok=True)
run('chown', 'ri-market-watch:ri-market-watch', str(data))
source = pathlib.Path(__file__).parent
shutil.copy2(source/'service.py', base/'service.py')
if not (data/'market-watch.sqlite3').exists():
    shutil.copy2(source/'market-watch.sqlite3', data/'market-watch.sqlite3')
    run('chown', 'ri-market-watch:ri-market-watch', str(data/'market-watch.sqlite3'))
unit = pathlib.Path('/etc/systemd/system/ri-market-watch.service')
unit.write_text('''[Unit]
Description=Residual Inertia SEC Market Watch
After=network-online.target
Wants=network-online.target
[Service]
User=ri-market-watch
Group=ri-market-watch
WorkingDirectory=/opt/ri-market-watch
ExecStart=/usr/bin/python3 /opt/ri-market-watch/service.py --data /var/lib/ri-market-watch --port 8774 --collect
Restart=on-failure
RestartSec=15
Environment=PYTHONUNBUFFERED=1
Environment="SEC_USER_AGENT=Residual Inertia Research data@residualinertia.com"
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/ri-market-watch
MemoryMax=180M
CPUQuota=40%
TasksMax=64
[Install]
WantedBy=multi-user.target
''')
run('systemctl', 'daemon-reload')
run('systemctl', 'enable', '--now', 'ri-market-watch')
for _ in range(20):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8774/api/market-watch/status', timeout=2) as response:
            assert response.status == 200
        break
    except OSError:
        time.sleep(1)
else:
    raise RuntimeError('New service failed health check; nginx was not changed')
nginx = pathlib.Path('/etc/nginx/sites-available/global-pulse')
original = nginx.read_text()
marker = '    location /api/ {'
block = '''    # RI public SEC read-only service; independent of account and globe services.
    location ^~ /api/market-watch/ {
        limit_except GET { deny all; }
        proxy_pass http://127.0.0.1:8774;
        proxy_connect_timeout 5s;
        proxy_read_timeout 25s;
    }
'''
if 'location ^~ /api/market-watch/' not in original:
    assert original.count(marker) == 1, 'Unexpected nginx structure; no edits made'
    backup = nginx.with_name('global-pulse.before-market-watch-'+str(int(time.time())))
    shutil.copy2(nginx, backup)
    nginx.write_text(original.replace(marker, block+marker))
    try:
        run('nginx', '-t')
    except Exception:
        nginx.write_text(original)
        raise
    run('systemctl', 'reload', 'nginx')
print('Market Watch deployed; existing application services were not restarted.')
