from pathlib import Path
import re

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

start = "# ================= HW INVENTORY V4 LEFT MENU FORCE START ================="
end = "# ================= HW INVENTORY V4 LEFT MENU FORCE END ================="
# Remove previous V4 block if rerun
while start in code and end in code:
    s = code.find(start)
    e = code.find(end, s) + len(end)
    code = code[:s] + code[e:]

addon = r'''
# ================= HW INVENTORY V4 LEFT MENU FORCE START =================
# Clean H/W inventory from Google Sheet. Injects left menu item into existing dashboard.
# Routes: /hw-inventory-v2 and /inventory-manager. No client/Ubuntu/live2278 change.

import json as _hwv4_json
import csv as _hwv4_csv
import io as _hwv4_io
import hashlib as _hwv4_hashlib
import urllib.parse as _hwv4_url
from pathlib import Path as _hwv4_Path
from collections import Counter as _hwv4_Counter

_HWV4_BASE = _hwv4_Path(BASE_DIR) if 'BASE_DIR' in globals() else _hwv4_Path(__file__).resolve().parent
_HWV4_FILE = _HWV4_BASE / 'data' / 'fresh_hw_inventory_v2.json'
_HWV4_COLS = [
    'asset_uid','asset_code','make_name','model_name','asset_name','asset_type','category','configuration_details',
    'quantity','rate','vendor_name','warranty_end_date','warranty_end_year','purchase_date',
    'po_invoice_bill_no','po_invoice_bill_path','tagname_hostname','serial_number','assigned_to','asset_location',
    'status','remarks','source_sheet','source_row','duplicate_removed_count','live_sync_status','live_hostname','live_machine_id','live_ip','live_online','live_last_seen'
]

def _hwv4_s(v):
    return '' if v is None else str(v).strip()

def _hwv4_load():
    try:
        if _HWV4_FILE.exists():
            x = _hwv4_json.loads(_HWV4_FILE.read_text(encoding='utf-8-sig'))
            if isinstance(x, list):
                return [_hwv4_norm(r) for r in x if isinstance(r, dict)]
    except Exception:
        pass
    return []

def _hwv4_write(rows):
    _HWV4_FILE.parent.mkdir(parents=True, exist_ok=True)
    out = [_hwv4_norm(r) for r in rows if isinstance(r, dict)]
    tmp = _HWV4_FILE.with_suffix('.json.tmp')
    tmp.write_text(_hwv4_json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    tmp.replace(_HWV4_FILE)

def _hwv4_uid(r):
    base = _hwv4_s(r.get('asset_uid') or r.get('asset_code') or r.get('serial_number') or r.get('tagname_hostname'))
    if base:
        return base
    raw = _hwv4_json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)
    return 'HW-' + _hwv4_hashlib.sha1(raw.encode('utf-8')).hexdigest()[:10].upper()

def _hwv4_norm(r):
    x = dict(r or {})
    # compatibility aliases from sheet
    alias = {
        'Code':'asset_code','Name':'asset_name','AssetType':'asset_type','Details':'configuration_details','Quantity':'quantity',
        'Rate':'rate','WarrantyDate':'warranty_end_date','PurchaseDate':'purchase_date','SerialNumber':'serial_number','VendorName':'vendor_name',
        'Vendor Name':'vendor_name','Warranty End Date':'warranty_end_date','Warranty End Year':'warranty_end_year','Purchase Date':'purchase_date',
        'PO / Invoice / Bill No':'po_invoice_bill_no','PO / Invoice / Bill Path':'po_invoice_bill_path','Tagname / Hostname':'tagname_hostname',
        'Serial Number':'serial_number','Assigned To':'assigned_to','Location':'asset_location','Status':'status','Remarks':'remarks',
        'Make Name':'make_name','Model Name':'model_name'
    }
    for k,v in list(alias.items()):
        if not _hwv4_s(x.get(v)) and _hwv4_s(x.get(k)):
            x[v] = _hwv4_s(x.get(k))
    if not _hwv4_s(x.get('asset_type')):
        x['asset_type'] = _hwv4_s(x.get('category'))
    if not _hwv4_s(x.get('category')):
        x['category'] = _hwv4_s(x.get('asset_type')) or 'Uncategorized'
    if not _hwv4_s(x.get('asset_name')):
        x['asset_name'] = _hwv4_s(x.get('model_name') or x.get('asset_type') or x.get('category'))
    if not _hwv4_s(x.get('model_name')):
        # Use sheet Name as model name when explicit model missing.
        x['model_name'] = _hwv4_s(x.get('asset_name'))
    if not _hwv4_s(x.get('make_name')):
        # keep blank if unknown; user can edit
        x['make_name'] = ''
    if not _hwv4_s(x.get('quantity')):
        x['quantity'] = '1'
    if not _hwv4_s(x.get('status')):
        x['status'] = 'Review'
    # derive warranty year
    if not _hwv4_s(x.get('warranty_end_year')) and _hwv4_s(x.get('warranty_end_date')):
        import re as _r
        m = _r.search(r'(20\d{2}|19\d{2})', _hwv4_s(x.get('warranty_end_date')))
        if m: x['warranty_end_year'] = m.group(1)
    x['asset_uid'] = _hwv4_uid(x)
    for c in _HWV4_COLS:
        x.setdefault(c, '')
    return x

def _hwv4_summary():
    rows = _hwv4_load()
    def missing(k): return sum(1 for r in rows if not _hwv4_s(r.get(k)))
    return {
        'ok': True,
        'rows': len(rows),
        'imported_assets': len(rows),
        'missing_vendor_name': missing('vendor_name'),
        'missing_make_name': missing('make_name'),
        'missing_model_name': missing('model_name'),
        'missing_serial_number': missing('serial_number'),
        'missing_tagname_hostname': missing('tagname_hostname'),
        'missing_assigned_to': missing('assigned_to'),
        'missing_location': missing('asset_location'),
        'missing_po_invoice_bill_no': missing('po_invoice_bill_no'),
        'categories': dict(_hwv4_Counter([_hwv4_s(r.get('category')) or 'Uncategorized' for r in rows]).most_common(30)),
        'source_file': str(_HWV4_FILE)
    }

def _hwv4_filter(rows, qs):
    q = _hwv4_s((qs.get('q') or [''])[0]).lower()
    if not q: return rows
    return [r for r in rows if q in _hwv4_json.dumps(r, ensure_ascii=False, default=str).lower()]

def _hwv4_csv_bytes(rows):
    buf = _hwv4_io.StringIO()
    fields = list(_HWV4_COLS)
    for r in rows:
        for k in r.keys():
            if k not in fields: fields.append(k)
    w = _hwv4_csv.DictWriter(buf, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    for r in rows: w.writerow(r)
    return buf.getvalue().encode('utf-8-sig')

def _hwv4_read_json(self):
    try:
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n) if n else b'{}'
        return _hwv4_json.loads(raw.decode('utf-8-sig') or '{}')
    except Exception:
        return {}

def _hwv4_live_tokens(m):
    vals=[]
    if isinstance(m, dict):
        vals += [m.get('hostname'), m.get('machine_id'), m.get('real_machine_id'), m.get('primary_ip'), m.get('public_ip')]
        p = m.get('payload') if isinstance(m.get('payload'), dict) else {}
        ident = p.get('identity') if isinstance(p.get('identity'), dict) else {}
        vals += [ident.get('serial'), ident.get('bios_serial'), ident.get('uuid'), ident.get('system_uuid'), ident.get('hostname')]
    return set([_hwv4_s(v).lower() for v in vals if _hwv4_s(v)])

def _hwv4_sync_rows(save=False):
    rows = _hwv4_load()
    try:
        machines = load_latest()
    except Exception:
        machines = []
    mt = [(m, _hwv4_live_tokens(m)) for m in machines]
    out=[]
    for r in rows:
        x=dict(r)
        keys=[]
        for k in ['serial_number','tagname_hostname','asset_code']:
            v=_hwv4_s(x.get(k)).lower()
            if v: keys.append(v)
        match=None; by=''
        for m,toks in mt:
            common=[k for k in keys if k in toks]
            if common:
                match=m; by=', '.join(common); break
        if match:
            x['live_sync_status']='matched'
            x['live_hostname']=_hwv4_s(match.get('hostname'))
            x['live_machine_id']=_hwv4_s(match.get('machine_id'))
            x['live_ip']=_hwv4_s(match.get('primary_ip'))
            x['live_online']=_hwv4_s(match.get('online'))
            x['live_last_seen']=_hwv4_s(match.get('updated_at'))
        else:
            x['live_sync_status']='not_matched'
            x['live_hostname']=x['live_machine_id']=x['live_ip']=x['live_online']=x['live_last_seen']=''
        out.append(_hwv4_norm(x))
    if save: _hwv4_write(out)
    return out

def _hwv4_html():
    return r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>H/W Inventory V2</title>
<style>
body{margin:0;font-family:Inter,Segoe UI,Arial;background:#eef5fb;color:#0f172a}.layout{display:flex;min-height:100vh}.side{width:250px;background:#071426;color:#dbeafe;padding:22px 14px;position:sticky;top:0;height:100vh;box-sizing:border-box}.brand{display:flex;gap:12px;align-items:center;margin-bottom:24px}.logo{width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#2563eb,#14b8a6);display:grid;place-items:center;font-weight:900}.nav a{display:block;color:#dbeafe;text-decoration:none;padding:13px 14px;border-radius:12px;font-weight:800;margin:7px 0}.nav a.active{background:linear-gradient(135deg,#0f766e,#1d4ed8);box-shadow:inset 3px 0 #2dd4bf}.main{flex:1;padding:24px}.top{background:white;border-radius:26px;padding:22px;box-shadow:0 18px 50px #1e3a8a18;margin-bottom:18px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}.card{background:white;border:1px solid #d9e7f7;border-radius:18px;padding:16px}.k{font-size:12px;color:#64748b;font-weight:900;text-transform:uppercase}.v{font-size:27px;font-weight:900}.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}button,.btn{border:0;border-radius:12px;padding:11px 14px;background:#2563eb;color:white;font-weight:900;cursor:pointer;text-decoration:none}button.alt,.btn.alt{background:#0f172a}button.danger{background:#dc2626}input,select,textarea{border:1px solid #cbd5e1;border-radius:10px;padding:10px;background:white;min-width:160px}.search{width:520px;max-width:95%}.panel{background:white;border-radius:20px;padding:16px;box-shadow:0 18px 50px #1e3a8a12}.tablewrap{overflow:auto;max-height:62vh;border-radius:14px;border:1px solid #d9e7f7}table{border-collapse:collapse;width:100%;min-width:1900px}th,td{padding:9px;border-bottom:1px solid #e2e8f0;font-size:13px;vertical-align:top}th{position:sticky;top:0;background:#eaf2ff;text-align:left;color:#1e3a8a}tr:hover{background:#f8fbff}.form{display:none;background:#f8fbff;border:1px solid #cfe0f5;border-radius:16px;padding:14px;margin:12px 0}.formgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.formgrid label{font-size:12px;font-weight:900;color:#334155}.formgrid input,.formgrid textarea{width:100%;box-sizing:border-box}.bad{color:#dc2626}.good{color:#16a34a}
</style></head><body><div class="layout"><aside class="side"><div class="brand"><div class="logo">SK</div><div><b>Sagar Kerhalkar</b><br><small>System Health Monitor</small></div></div><nav class="nav"><a href="/">Command Center</a><a href="/#fleet">Machine Fleet</a><a href="/#machine360">Machine 360</a><a href="/#hardware">Hardware</a><a href="/#software">Software</a><a class="active" href="/hw-inventory-v2">H/W Inventory</a><a href="/#deploy">Deploy</a></nav></aside><main class="main"><div class="top"><h1>Fresh H/W Inventory</h1><div>Google Sheet cleaned inventory + editable ISO/ITAM columns + live monitor sync.</div></div><div class="cards" id="cards"></div><div class="panel"><div class="toolbar"><input id="q" class="search" placeholder="Search code, serial, tag/hostname, make, model, vendor, location..."><button onclick="loadRows()">Search</button><button onclick="openForm()">Add New Asset</button><button onclick="syncLive()">Sync With Live Data</button><a class="btn alt" href="/api/hw-inventory-v2/export.csv">Download CSV</a><a class="btn alt" href="/">Back Dashboard</a></div><div class="form" id="form"><h3 id="formTitle">Edit Asset</h3><div class="formgrid" id="formgrid"></div><div class="toolbar"><button onclick="saveForm()">Save</button><button class="alt" onclick="closeForm()">Cancel</button></div></div><div class="tablewrap"><table><thead><tr id="thead"></tr></thead><tbody id="tbody"></tbody></table></div></div></main></div>
<script>
const cols=[['Asset UID','asset_uid'],['Asset Code','asset_code'],['Make Name','make_name'],['Model Name','model_name'],['Asset Name','asset_name'],['Asset Type','asset_type'],['Configuration / Details','configuration_details'],['Qty','quantity'],['Rate','rate'],['Vendor Name','vendor_name'],['Warranty End Date','warranty_end_date'],['Warranty End Year','warranty_end_year'],['Purchase Date','purchase_date'],['PO / Invoice / Bill No','po_invoice_bill_no'],['PO / Invoice / Bill Path','po_invoice_bill_path'],['Tagname / Hostname','tagname_hostname'],['Serial Number','serial_number'],['Assigned To','assigned_to'],['Location','asset_location'],['Status','status'],['Remarks','remarks'],['Live Sync Status','live_sync_status'],['Live Host','live_hostname'],['Live IP','live_ip']];
const editCols=['asset_uid','asset_code','make_name','model_name','asset_name','asset_type','category','configuration_details','quantity','rate','vendor_name','warranty_end_date','warranty_end_year','purchase_date','po_invoice_bill_no','po_invoice_bill_path','tagname_hostname','serial_number','assigned_to','asset_location','status','remarks'];
let rows=[], current=null; function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))} async function api(u,o){let r=await fetch(u,o); if(!r.ok)throw new Error(await r.text()); return r.json()}
function card(k,v){return `<div class=card><div class=k>${esc(k)}</div><div class=v>${esc(v)}</div></div>`}
async function loadSummary(){let s=await api('/api/hw-inventory-v2/summary');cards.innerHTML=card('Assets',s.imported_assets)+card('Missing Vendor',s.missing_vendor_name)+card('Missing Make',s.missing_make_name)+card('Missing Model',s.missing_model_name)+card('Missing Serial',s.missing_serial_number)+card('Missing Tag/Host',s.missing_tagname_hostname)+card('Missing Bill/PO',s.missing_po_invoice_bill_no)}
async function loadRows(){await loadSummary(); let q=encodeURIComponent(document.getElementById('q').value||''); let j=await api('/api/hw-inventory-v2/assets?q='+q); rows=j.rows||[]; thead.innerHTML='<th>Action</th>'+cols.map(c=>'<th>'+esc(c[0])+'</th>').join(''); tbody.innerHTML=rows.map((r,i)=>'<tr><td><button onclick="editRow('+i+')">Edit</button> <button class="danger" onclick="delRow('+i+')">Delete</button></td>'+cols.map(c=>'<td>'+esc(r[c[1]]||'')+'</td>').join('')+'</tr>').join('')||'<tr><td>No rows</td></tr>'}
function openForm(r){current=r||{}; form.style.display='block'; formTitle.textContent=current.asset_uid?'Edit Asset':'Add New Asset'; formgrid.innerHTML=editCols.map(k=>`<label>${esc(k.replaceAll('_',' ').toUpperCase())}<input id="f_${k}" value="${esc(current[k]||'')}"></label>`).join(''); window.scrollTo({top:0,behavior:'smooth'})}
function closeForm(){form.style.display='none';current=null} function editRow(i){openForm(rows[i])}
async function saveForm(){let r={}; editCols.forEach(k=>r[k]=document.getElementById('f_'+k).value); await api('/api/hw-inventory-v2/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(r)}); closeForm(); await loadRows()}
async function delRow(i){if(!confirm('Delete this asset?'))return; await api('/api/hw-inventory-v2/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_uid:rows[i].asset_uid})}); await loadRows()}
async function syncLive(){let j=await api('/api/hw-inventory-v2/sync-save',{method:'POST'}); alert('Sync done. matched='+j.matched+' / rows='+j.rows); await loadRows()}
loadRows().catch(e=>{document.body.innerHTML='<pre style="padding:20px;color:red">'+esc(e.message)+'</pre>'})
</script></body></html>'''

def _hwv4_download(self, rows, filename):
    return self._send(200, _hwv4_csv_bytes(rows), 'text/csv; charset=utf-8', {'Content-Disposition': f'attachment; filename="{filename}"'})

_hwv4_prev_get = Handler.do_GET
_hwv4_prev_post = getattr(Handler, 'do_POST', None)
_hwv4_prev_send = Handler._send

def _hwv4_do_GET(self):
    try:
        u = _hwv4_url.urlparse(self.path); path = u.path.rstrip('/') or '/'; qs = _hwv4_url.parse_qs(u.query)
        if path in ['/hw-inventory-v2','/inventory-manager']:
            return self._send(200, _hwv4_html().encode('utf-8'), 'text/html; charset=utf-8')
        if path == '/api/hw-inventory-v2/summary':
            return self.send_json(_hwv4_summary())
        if path == '/api/hw-inventory-v2/assets':
            rows = _hwv4_filter(_hwv4_load(), qs)
            return self.send_json({'ok': True, 'count': len(rows), 'rows': rows})
        if path == '/api/hw-inventory-v2/export.csv':
            return _hwv4_download(self, _hwv4_load(), 'fresh_hw_inventory_v2.csv')
        return _hwv4_prev_get(self)
    except Exception as e:
        try: return self.send_json({'ok': False, 'error': str(e)}, 500)
        except Exception: return None

def _hwv4_do_POST(self):
    try:
        u = _hwv4_url.urlparse(self.path); path = u.path.rstrip('/') or '/'
        if path == '/api/hw-inventory-v2/save':
            row = _hwv4_norm(_hwv4_read_json(self))
            rows = _hwv4_load(); out=[]; found=False
            for r in rows:
                if _hwv4_s(r.get('asset_uid')) == _hwv4_s(row.get('asset_uid')):
                    out.append(row); found=True
                else:
                    out.append(r)
            if not found: out.append(row)
            _hwv4_write(out)
            return self.send_json({'ok': True, 'saved': row})
        if path == '/api/hw-inventory-v2/delete':
            body = _hwv4_read_json(self); uid = _hwv4_s(body.get('asset_uid'))
            rows = [r for r in _hwv4_load() if _hwv4_s(r.get('asset_uid')) != uid]
            _hwv4_write(rows)
            return self.send_json({'ok': True, 'deleted': uid, 'rows': len(rows)})
        if path == '/api/hw-inventory-v2/sync-save':
            rows = _hwv4_sync_rows(save=True)
            matched = sum(1 for r in rows if r.get('live_sync_status') == 'matched')
            return self.send_json({'ok': True, 'rows': len(rows), 'matched': matched})
        if _hwv4_prev_post: return _hwv4_prev_post(self)
        return self.send_json({'error':'not_found'},404)
    except Exception as e:
        try: return self.send_json({'ok': False, 'error': str(e)}, 500)
        except Exception: return None

def _hwv4_send(self, status, body, *args, **kwargs):
    try:
        ctype = str(args[0]) if args else str(kwargs.get('content_type',''))
        if status == 200 and isinstance(body,(bytes,bytearray)) and (b'Command Center' in body[:500000] or b'Sagar Kerhalkar' in body[:500000]):
            html = bytes(body).decode('utf-8','ignore')
            if 'HW_INVENTORY_V4_LEFT_MENU_INJECT' not in html:
                js = r'''<script id="HW_INVENTORY_V4_LEFT_MENU_INJECT">
(function(){
function removeOldInventoryModal(){
  document.querySelectorAll('div,button,a,section').forEach(function(el){
    var t=(el.textContent||'').trim();
    if(t==='Inventory / ISO' || t.indexOf('V10 Inventory / ISO Merge')>=0){
      var p=el; for(var i=0;i<4 && p && p.parentElement;i++){ if(getComputedStyle(p).position==='fixed'){p.remove(); return;} p=p.parentElement; }
      el.style.display='none';
    }
  });
}
function addLeftMenu(){
  if(document.getElementById('hwInventoryV4LeftMenu')) return;
  var items=[].slice.call(document.querySelectorAll('a,button,div,span')).filter(function(x){return (x.textContent||'').trim()==='Software';});
  var ref=items[0] || [].slice.call(document.querySelectorAll('a,button,div,span')).find(function(x){return (x.textContent||'').trim()==='Hardware';});
  var n=document.createElement('div'); n.id='hwInventoryV4LeftMenu'; n.textContent='H/W Inventory';
  n.onclick=function(e){e.preventDefault(); location.href='/hw-inventory-v2';};
  n.style.cssText='cursor:pointer;margin:8px 0;padding:13px 14px;border-radius:12px;font-weight:900;color:#dbeafe;background:linear-gradient(135deg,#1d4ed8,#0e7490);border-left:4px solid #2dd4bf;box-shadow:0 8px 20px rgba(0,0,0,.18)';
  if(ref && ref.parentNode) ref.parentNode.insertBefore(n, ref.nextSibling); else document.body.prepend(n);
}
function run(){removeOldInventoryModal(); addLeftMenu();}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',run); else run();
setInterval(run,1500);
})();</script>'''
                html = html.replace('</body>', js + '</body>') if '</body>' in html else html + js
                body = html.encode('utf-8')
        return _hwv4_prev_send(self, status, body, *args, **kwargs)
    except Exception:
        return _hwv4_prev_send(self, status, body, *args, **kwargs)

Handler.do_GET = _hwv4_do_GET
Handler.do_POST = _hwv4_do_POST
Handler._send = _hwv4_send
# ================= HW INVENTORY V4 LEFT MENU FORCE END =================
'''

marker = 'def main()'
if marker not in code:
    raise SystemExit('def main() marker not found')
# Insert as the final monkeypatch before main so it wins over older broken inventory wrappers.
code = code.replace(marker, addon + "\n" + marker, 1)
server.write_text(code, encoding='utf-8')
print('HW Inventory V4 left menu force patch installed')