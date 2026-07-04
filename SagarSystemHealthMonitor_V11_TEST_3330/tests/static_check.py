#!/usr/bin/env python3
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def check(cond, msg):
    if not cond:
        errors.append(msg)
        print('FAIL:', msg)
    else:
        print('OK  :', msg)

server = ROOT / 'server.py'
app = ROOT / 'public' / 'app.js'
index = ROOT / 'public' / 'index.html'
css = ROOT / 'public' / 'styles.css'

try:
    py_compile.compile(str(server), doraise=True)
    check(True, 'server.py compiles')
except Exception as exc:
    check(False, f'server.py compile failed: {exc}')

for f in [index, app, css]:
    check(f.exists() and f.stat().st_size > 500, f'{f.relative_to(ROOT)} exists and is not empty')

server_text = server.read_text(encoding='utf-8')
app_text = app.read_text(encoding='utf-8')
css_text = css.read_text(encoding='utf-8')
index_text = index.read_text(encoding='utf-8')

for endpoint in [
    '/api/heartbeat','/api/overview','/api/machines','/api/machine','/api/history','/api/changes',
    '/api/assets/hardware','/api/assets/software','/api/iso-audit','/api/v11/snapshot',
    '/api/messages','/api/notifications','/api/export/machines.csv'
]:
    check(endpoint in server_text or endpoint in app_text, f'endpoint present: {endpoint}')

for page in [
    'Home / Command Center','Machine Fleet','Machine 360','Network + VPN','Hardware Intelligence','Software Intelligence',
    'Hardware Asset Register','Software Asset Register','ISO Audit Center','USB + Peripherals','Human Change Log',
    'Day History','Client Messages','Notifications','Deploy Center','Settings'
]:
    check(page in app_text or page in index_text, f'page present: {page}')

for rule in ['@media (max-width:1200px)','@media (max-width:820px)','@media (max-width:520px)']:
    check(rule in css_text, f'responsive CSS rule present: {rule}')

node = shutil.which('node')
if node:
    cp = subprocess.run([node, '--check', str(app)], text=True, capture_output=True)
    check(cp.returncode == 0, 'app.js passes node --check')
    if cp.returncode != 0:
        print(cp.stderr)
else:
    print('WARN: node not installed; skipped JS syntax check')

check('localStorage.v11SelectedMachine' in app_text, 'selected-machine persistence implemented')
check('Not reported by client' in app_text, 'N/A / not-reported display implemented')
check('hardware_assets' in server_text and 'software_assets' in server_text and 'iso_audit_evidence' in server_text, 'asset + ISO DB tables implemented')

if errors:
    print('\nStatic check failed:')
    for e in errors:
        print('-', e)
    sys.exit(1)
print('\nAll V11 static checks passed.')
