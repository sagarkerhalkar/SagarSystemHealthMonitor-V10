from pathlib import Path

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

markers = [
    ("# ================= HW INVENTORY V2 FROM GOOGLE SHEET =================", "# ================= END HW INVENTORY V2 FROM GOOGLE SHEET ================="),
    ("# ================= COMPACT OLD IMPORTED INVENTORY UI V2 =================", "# ================= END COMPACT OLD IMPORTED INVENTORY UI V2 ================="),
    ("# ================= REAL OLD IMPORTED HW/SW INVENTORY UI =================", "# ================= END REAL OLD IMPORTED HW/SW INVENTORY UI ================="),
    ("# ================= V10 IMPORTED ISO INVENTORY UI =================", "# ================= END V10 IMPORTED ISO INVENTORY UI ================="),
    ("# ================= HW INVENTORY V3 FORCE ROUTE =================", "# ================= END HW INVENTORY V3 FORCE ROUTE ================="),
]
for start, end in markers:
    while start in code:
        s = code.find(start)
        e = code.find(end, s)
        if e < 0:
            break
        code = code[:s] + "\n" + code[e + len(end):]

addon = r'''
# ================= HW INVENTORY V3 FORCE ROUTE =================
import json as _hwi3_json, csv as _hwi3_csv, io as _hwi3_io, urllib.parse as _hwi3_url, hashlib as _hwi3_hash, re as _hwi3_re
from pathlib import Path as _hwi3_Path
from collections import Counter as _hwi3_Counter

try:
    _HWI3_BASE = _hwi3_Path(BASE_DIR)
except Exception:
    _HWI3_BASE = _hwi3_Path(__file__).resolve().parent
_HWI3_FILE = _HWI3_BASE / "data" / "fresh_hw_inventory_v2.json"
_HWI3_COLUMNS = ["asset_uid","asset_code","make_name","model_name","asset_name","asset_type","category","configuration_details","quantity","rate","vendor_name","warranty_end_date","warranty_end_year","purchase_date","po_invoice_bill_no","po_invoice_bill_path","tagname_hostname","serial_number","assigned_to","asset_location","status","remarks","source_sheet","source_row","duplicate_removed_count","live_sync_status","live_hostname","live_machine_id","live_ip","live_online","live_last_seen"]

def _hwi3_s(v): return "" if v is None else str(v).strip()
def _hwi3_load():
    try:
        if _HWI3_FILE.exists():
            x = _hwi3_json.loads(_HWI3_FILE.read_text(encoding="utf-8-sig"))
            return x if isinstance(x, list) else []
    except Exception: pass
    return []
def _hwi3_save(rows):
    _HWI3_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(_HWI3_FILE) + ".tmp"
    _hwi3_Path(tmp).write_text(_hwi3_json.dumps(rows, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    _hwi3_Path(tmp).replace(_HWI3_FILE)
def _hwi3_uid(row):
    base = "|".join([_hwi3_s(row.get(k)) for k in ["asset_code","serial_number","tagname_hostname","asset_name","asset_location"]])
    return "HW-" + _hwi3_hash.sha1(base.encode("utf-8")).hexdigest()[:10].upper()
def _hwi3_norm(row):
    row = dict(row or {})
    out = {c: _hwi3_s(row.get(c, "")) for c in _HWI3_COLUMNS}
    if not out["asset_uid"]: out["asset_uid"] = _hwi3_uid(out)
    if not out["quantity"]: out["quantity"] = "1"
    if out["warranty_end_date"] and not out["warranty_end_year"]:
        m = _hwi3_re.search(r"(20\d{2}|19\d{2})", out["warranty_end_date"])
        if m: out["warranty_end_year"] = m.group(1)
    if not out["live_sync_status"]: out["live_sync_status"] = "not_synced"
    return out
def _hwi3_rows(): return [_hwi3_norm(r) for r in _hwi3_load()]
def _hwi3_filter(rows, qs):
    q = _hwi3_s((qs.get("q") or [""])[0]).lower()
    return rows if not q else [r for r in rows if q in _hwi3_json.dumps(r, ensure_ascii=False, default=str).lower()]
def _hwi3_summary():
    rows = _hwi3_rows()
    def miss(c): return sum(1 for r in rows if not _hwi3_s(r.get(c)))
    return {"ok": True, "source_file": str(_HWI3_FILE), "assets": len(rows), "missing_make": miss("make_name"), "missing_model": miss("model_name"), "missing_vendor": miss("vendor_name"), "missing_warranty": miss("warranty_end_date"), "missing_purchase": miss("purchase_date"), "missing_bill": miss("po_invoice_bill_no"), "missing_bill_path": miss("po_invoice_bill_path"), "missing_tag_hostname": miss("tagname_hostname"), "missing_serial": miss("serial_number"), "missing_assigned": miss("assigned_to"), "missing_location": miss("asset_location"), "synced_live": sum(1 for r in rows if r.get("live_sync_status") == "matched"), "not_synced_live": sum(1 for r in rows if r.get("live_sync_status") != "matched"), "category_counts": dict(_hwi3_Counter([_hwi3_s(r.get("category")) or "Uncategorized" for r in rows]).most_common(30))}
def _hwi3_machine_tokens(m):
    vals=[]
    if isinstance(m,dict):
        vals += [m.get("hostname"), m.get("machine_id"), m.get("real_machine_id"), m.get("primary_ip")]
        p = m.get("payload") if isinstance(m.get("payload"),dict) else {}
        ident = p.get("identity") if isinstance(p.get("identity"),dict) else {}
        vals += [ident.get("hostname"), ident.get("serial"), ident.get("bios_serial"), ident.get("uuid"), ident.get("system_uuid"), ident.get("machine_uuid")]
    return set([_hwi3_s(x).lower() for x in vals if _hwi3_s(x)])
def _hwi3_sync_live():
    rows = _hwi3_rows()
    try: machines = load_latest()
    except Exception: machines = []
    mt = [(m, _hwi3_machine_tokens(m)) for m in machines]
    matched = 0
    for r in rows:
        keys = set()
        for k in ["serial_number","tagname_hostname","asset_code"]:
            v = _hwi3_s(r.get(k)).lower()
            if v and v not in {"na","n/a","-","none"}: keys.add(v)
        hit = None
        for m,toks in mt:
            if keys.intersection(toks): hit = m; break
        if hit:
            matched += 1; r["live_sync_status"]="matched"; r["live_hostname"]=_hwi3_s(hit.get("hostname")); r["live_machine_id"]=_hwi3_s(hit.get("machine_id")); r["live_ip"]=_hwi3_s(hit.get("primary_ip")); r["live_online"]=_hwi3_s(hit.get("online")); r["live_last_seen"]=_hwi3_s(hit.get("updated_at"))
        else:
            r["live_sync_status"]="not_matched"; r["live_hostname"]=r["live_machine_id"]=r["live_ip"]=r["live_online"]=r["live_last_seen"]=""
    _hwi3_save(rows)
    return {"ok": True, "assets": len(rows), "matched": matched, "not_matched": len(rows)-matched}
def _hwi3_body(self):
    try:
        if hasattr(self,"read_json"): return self.read_json()
    except Exception: pass
    ln = int(self.headers.get("Content-Length", "0") or 0)
    raw = self.rfile.read(ln) if ln else b"{}"
    return _hwi3_json.loads(raw.decode("utf-8") or "{}")
def _hwi3_csv_bytes(rows):
    buf = _hwi3_io.StringIO(); w = _hwi3_csv.DictWriter(buf, fieldnames=_HWI3_COLUMNS, extrasaction="ignore"); w.writeheader()
    for r in rows: w.writerow(_hwi3_norm(r))
    return buf.getvalue().encode("utf-8-sig")
def _hwi3_page():
    cols = _HWI3_COLUMNS
    labels = {"asset_code":"Asset Code","make_name":"Make Name","model_name":"Model Name","asset_name":"Asset Name","asset_type":"Asset Type","configuration_details":"Configuration / Details","quantity":"Qty","vendor_name":"Vendor Name","warranty_end_date":"Warranty End Date","warranty_end_year":"Warranty End Year","purchase_date":"Purchase Date","po_invoice_bill_no":"PO / Invoice / Bill No","po_invoice_bill_path":"PO / Invoice / Bill Path","tagname_hostname":"Tagname / Hostname","serial_number":"Serial Number","assigned_to":"Assigned To","asset_location":"Location","status":"Status","remarks":"Remarks","live_sync_status":"Live Sync Status","live_hostname":"Live Hostname","live_online":"Live Online","live_last_seen":"Live Last Seen"}
    return """<!doctype html><html><head><meta charset='utf-8'><title>H/W Inventory V3</title><style>body{font-family:Segoe UI,Arial;margin:0;background:#07111f;color:#eaf1ff}header{padding:18px;background:linear-gradient(135deg,#0c244d,#0f766e)}main{padding:18px}.btn,button{background:#1d4ed8;color:white;border:0;border-radius:10px;padding:9px 11px;margin:4px;text-decoration:none;cursor:pointer}.danger{background:#dc2626}.card{display:inline-block;background:#101b31;border:1px solid #294264;border-radius:15px;padding:12px;margin:6px;min-width:140px}.v{font-size:22px;font-weight:900}input{background:#0f172a;color:white;border:1px solid #334155;border-radius:8px;padding:7px}table{width:100%;border-collapse:collapse;background:#10182f}th,td{padding:7px;border-bottom:1px solid #22314f;font-size:12px}th{background:#172447;position:sticky;top:0}.scroll{overflow:auto;max-height:72vh}.ok{color:#4ade80}.bad{color:#fb7185}</style></head><body><header><h1>Fresh H/W Inventory from Google Sheet</h1><div>Make Name, Model Name, Vendor, Warranty, Purchase, PO/Bill, Bill Path, Tag/Hostname, Serial, Assigned To, Location, Status, Remarks, Live Sync</div></header><main><a class='btn' href='/'>Back Dashboard</a><button onclick='syncLive()'>Sync with Live Monitor</button><a class='btn' href='/api/hw-inventory-v2/export.csv'>Download CSV</a><button onclick='newRow()'>Add New Asset</button><input id='q' placeholder='Search' style='width:340px'><button onclick='loadAll()'>Search</button><div id='cards'></div><div id='msg'></div><div class='scroll'><table id='tbl'></table></div></main><script>const cols=""" + _hwi3_json.dumps(cols) + ";const labels=" + _hwi3_json.dumps(labels) + r""";let rows=[];function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}async function api(u,opt){let r=await fetch(u,opt);if(!r.ok)throw new Error(await r.text());return r.json()}function card(k,v){return `<div class=card><div>${esc(k)}</div><div class=v>${esc(v)}</div></div>`}async function loadAll(){let s=await api('/api/hw-inventory-v2/summary');cards.innerHTML=card('Assets',s.assets)+card('Missing Make',s.missing_make)+card('Missing Model',s.missing_model)+card('Missing Vendor',s.missing_vendor)+card('Missing Bill',s.missing_bill)+card('Synced Live',s.synced_live);let q=encodeURIComponent(document.getElementById('q').value||'');let d=await api('/api/hw-inventory-v2/assets?q='+q);rows=d.rows;render()}function render(){tbl.innerHTML='<thead><tr><th>Action</th>'+cols.map(c=>`<th>${esc(labels[c]||c)}</th>`).join('')+'</tr></thead><tbody>'+rows.map((r,i)=>'<tr><td><button onclick="save('+i+')">Save</button><button class=danger onclick="delRow('+i+')">Delete</button></td>'+cols.map(c=>`<td><input data-i="${i}" data-k="${c}" value="${esc(r[c]||'')}" ${c.startsWith('live_')?'readonly':''}></td>`).join('')+'</tr>').join('')+'</tbody>'}function collect(i){let r={...rows[i]};document.querySelectorAll(`input[data-i="${i}"]`).forEach(x=>r[x.dataset.k]=x.value);return r}async function save(i){let out=await api('/api/hw-inventory-v2/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(collect(i))});msg.innerHTML='<span class=ok>Saved '+esc(out.row.asset_uid)+'</span>';loadAll()}async function delRow(i){if(!confirm('Delete this asset?'))return;await api('/api/hw-inventory-v2/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_uid:rows[i].asset_uid})});msg.innerHTML='<span class=bad>Deleted</span>';loadAll()}async function syncLive(){let r=await api('/api/hw-inventory-v2/sync-save',{method:'POST'});msg.innerHTML='<span class=ok>Live sync: '+r.matched+' / '+r.assets+'</span>';loadAll()}function newRow(){rows.unshift({asset_uid:'',asset_code:'',make_name:'',model_name:'',asset_name:'',asset_type:'',configuration_details:'',quantity:'1',vendor_name:'',warranty_end_date:'',warranty_end_year:'',purchase_date:'',po_invoice_bill_no:'',po_invoice_bill_path:'',tagname_hostname:'',serial_number:'',assigned_to:'',asset_location:'',status:'Review',remarks:'',live_sync_status:'not_synced'});render()}loadAll().catch(e=>document.body.innerHTML='<pre>'+esc(e.message)+'</pre>')</script></body></html>"""

_hwi3_old_get = Handler.do_GET
_hwi3_old_post = getattr(Handler, "do_POST", None)
_hwi3_old_send = Handler._send

def _hwi3_get(self):
    try:
        u = _hwi3_url.urlparse(self.path); path = u.path; qs = _hwi3_url.parse_qs(u.query)
        if path in ("/hw-inventory-v2", "/inventory-manager"):
            return self._send(200, _hwi3_page().encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/hw-inventory-v2/summary": return self.send_json(_hwi3_summary())
        if path == "/api/hw-inventory-v2/assets":
            rows = _hwi3_filter(_hwi3_rows(), qs)
            return self.send_json({"ok": True, "count": len(rows), "rows": rows})
        if path == "/api/hw-inventory-v2/export.csv": return self._send(200, _hwi3_csv_bytes(_hwi3_rows()), "text/csv; charset=utf-8", {"Content-Disposition": 'attachment; filename="fresh_hw_inventory_v2_export.csv"'})
        return _hwi3_old_get(self)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError): return None
    except Exception as e: return self.send_json({"ok": False, "error": str(e)}, 500)

def _hwi3_post(self):
    try:
        u = _hwi3_url.urlparse(self.path); path = u.path
        if path == "/api/hw-inventory-v2/save":
            body = _hwi3_norm(_hwi3_body(self)); rows = _hwi3_rows(); found=False
            for i,r in enumerate(rows):
                if _hwi3_s(r.get("asset_uid")) == _hwi3_s(body.get("asset_uid")) and _hwi3_s(body.get("asset_uid")): rows[i]=body; found=True; break
            if not found:
                if not body.get("asset_uid"): body["asset_uid"]=_hwi3_uid(body)
                rows.insert(0, body)
            _hwi3_save(rows); return self.send_json({"ok": True, "row": body})
        if path == "/api/hw-inventory-v2/delete":
            body = _hwi3_body(self); uid = _hwi3_s(body.get("asset_uid")); rows = [r for r in _hwi3_rows() if _hwi3_s(r.get("asset_uid")) != uid]; _hwi3_save(rows); return self.send_json({"ok": True, "deleted": uid, "remaining": len(rows)})
        if path == "/api/hw-inventory-v2/sync-save": return self.send_json(_hwi3_sync_live())
        if _hwi3_old_post: return _hwi3_old_post(self)
        return self.send_json({"error":"not_found"},404)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError): return None
    except Exception as e: return self.send_json({"ok": False, "error": str(e)}, 500)

def _hwi3_send(self, status, body, *args, **kwargs):
    try:
        ctype = str(args[0]) if args else str(kwargs.get("content_type", ""))
        if status == 200 and isinstance(body,(bytes,bytearray)) and (("text/html" in ctype) or b"Command Center" in body[:300000]) and b"/hw-inventory-v2" not in body:
            html = bytes(body).decode("utf-8", "ignore")
            if "Command Center" in html:
                js = '''<script>(function(){function add(){if(document.getElementById('hwInvV3Nav'))return;var ref=[...document.querySelectorAll('button,a,div,span')].find(x=>(x.textContent||'').trim()==='Hardware')||[...document.querySelectorAll('button,a,div,span')].find(x=>(x.textContent||'').trim()==='Software');var n=document.createElement('div');n.id='hwInvV3Nav';n.textContent='H/W Inventory';n.onclick=function(){location.href='/hw-inventory-v2'};n.style.cssText='cursor:pointer;margin:8px 0;padding:12px 14px;border-radius:12px;font-weight:900;color:#dce8ff;background:linear-gradient(135deg,#1d4ed8,#0e7490);border:1px solid rgba(45,212,191,.45)';if(ref&&ref.parentNode)ref.parentNode.insertBefore(n,ref.nextSibling);else document.body.prepend(n)}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',add);else add()})();</script>'''
                body = html.replace("</body>", js + "</body>").encode("utf-8")
        return _hwi3_old_send(self, status, body, *args, **kwargs)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError): return None

Handler.do_GET = _hwi3_get
Handler.do_POST = _hwi3_post
Handler._send = _hwi3_send
# ================= END HW INVENTORY V3 FORCE ROUTE =================
'''

marker = "def main()"
if marker not in code:
    raise SystemExit("def main() marker not found")
code = code.replace(marker, addon + "\n" + marker, 1)
server.write_text(code, encoding="utf-8")
print("HW inventory V3 force route installed")