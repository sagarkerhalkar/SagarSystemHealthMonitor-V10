from pathlib import Path
import py_compile
root = Path(__file__).resolve().parents[1]
py_compile.compile(str(root / 'server_3330_proxy.py'), doraise=True)
app = (root / 'public' / 'app.js').read_text(encoding='utf-8')
html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
css = (root / 'public' / 'styles.css').read_text(encoding='utf-8')
required_pages = ['Home / Command Center','Machine Fleet','Machine 360','Network + VPN','Hardware Intelligence','Software Intelligence','Hardware Asset Register','Software Asset Register','ISO Audit Center','USB + Peripherals','Human Change Log','Day History','Client Messages','Notifications','Deploy Center','Settings']
missing = [p for p in required_pages if p not in html and p not in app]
if missing:
    raise SystemExit('Missing pages: ' + ', '.join(missing))
for s in ['/api/overview','/api/machine','/api/assets/hardware','/api/assets/software','/api/iso-audit']:
    if s not in app:
        raise SystemExit(f'Missing API in app.js: {s}')
for s in ['3330','2278','source','shadow']:
    if s not in (root / 'server_3330_proxy.py').read_text(encoding='utf-8'):
        raise SystemExit(f'Missing bridge marker: {s}')
if '@media' not in css:
    raise SystemExit('Responsive CSS media query missing')
print('V11 TEST 3330 static checks passed')
