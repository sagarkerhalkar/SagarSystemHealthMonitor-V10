from pathlib import Path
server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")
addon = r'''

# ================= HW INVENTORY V2 FROM GOOGLE SHEET =================
# Fresh inventory made from Google Sheet: Nexttoppers Assets Detail.xlsx
# Route: /hw-inventory-v2
# API: /api/hw-inventory-v2/*
# Editable fields: vendor, warranty, purchase, PO/bill, path, tag/hostname, serial, assigned, location, make/model, status, remarks.
# No client change. No Ubuntu change. No live 2278 change.

import json as _hwi_json, csv as _hwi_csv, io as _hwi_io, urllib.parse as _hwi_url, hashlib as _hwi_hash, re as _hwi_re
from pathlib import Path as _hwi_Path
from collections import Counter as _hwi_Counter

try:
    _HWI_BASE = _hwi_Path(BASE_DIR)
except Exception:
    _HWI_BASE = _hwi_Path(__file__).resolve().parent
_HWI_FILE = _HWI_BASE / "data" / "fresh_hw_inventory_v2.json"

_HWI_COLUMNS = [
    "asset_uid","asset_code","make_name","model_name","asset_name","asset_type","category","configuration_details",
    "quantity","rate","vendor_name","warranty_end_date","warranty_end_year","purchase_date",
    "po_invoice_bill_no","po_invoice_bill_path","tagname_hostname","serial_number","assigned_to","asset_location",
    "status","remarks","source_sheet","source_row","duplicate_removed_count","live_sync_status","live_hostname",
    "live_machine_id","live_ip","live_online","live_last_seen"
]

_HWI_EDITABLE = set(_HWI_COLUMNS)

def _hwi_s(v):
    return "" if v is None else str(v).strip()

def _hwi_load():
    try:
        if _HWI_FILE.exists():
            data = _hwi_json.loads(_HWI_FILE.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, list) else []
    except Exception:
        return []
    return []

def _hwi_save(rows):
    _HWI_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(_HWI_FILE) + ".tmp"
    _hwi_Path(tmp).write_text(_hwi_json.dumps(rows, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    _hwi_Path(tmp).replace(_HWI_FILE)

def _hwi_uid(row):
    base = "|".join([_hwi_s(row.get(k)) for k in ["asset_code","serial_number","tagname_hostname","asset_name","asset_location"]])
    return "HW-" + _hwi_hash.sha1(base.encode("utf-8")).hexdigest()[:10].upper()

def _hwi_normalize(row):
    row = dict(row or {})
    out = {c: _hwi_s(row.get(c, "")) for c in _HWI_COLUMNS}
    if not out["asset_uid"]:
        out["asset_uid"] = _hwi_uid(out)
    if out["warranty_end_date"] and not out["warranty_end_year"]:
        m = _hwi_re.search(r"(20\d{2}|19\d{2})", out["warranty_end_date"])
        if m: out["warranty_end_year"] = m.group(1)
    if not out["quantity"]:
        out["quantity"] = "1"
    if not out["live_sync_status"]:
        out["live_sync_status"] = "not_synced"
    return out

def _hwi_rows():
    return [_hwi_normalize(r) for r in _hwi_load()]

def _hwi_filter(rows, qs):
    q = _hwi_s((qs.get("q") or [""])[0]).lower()
    if not q:
        return rows
    return [r for r in rows if q in _hwi_json.dumps(r, ensure_ascii=False, default=str).lower()]

def _hwi_summary():
    rows = _hwi_rows()
    def miss(col): return sum(1 for r in rows if not _hwi_s(r.get(col)))
    return {
        "ok": True,
        "source_file": str(_HWI_FILE),
        "assets": len(rows),
        "missing_vendor": miss("vendor_name"),
        "missing_warranty": miss("warranty_end_date"),
        "missing_purchase": miss("purchase_date"),
        "missing_bill": miss("po_invoice_bill_no"),
        "missing_bill_path": miss("po_invoice_bill_path"),
        "missing_tag_hostname": miss("tagname_hostname"),
        "missing_serial": miss("serial_number"),
        "missing_assigned": miss("assigned_to"),
        "missing_location": miss("asset_location"),
        "synced_live": sum(1 for r in rows if r.get("live_sync_status") == "matched"),
        "not_synced_live": sum(1 for r in rows if r.get("live_sync_status") != "matched"),
        "category_counts": dict(_hwi_Counter([_hwi_s(r.get("category")) or "Uncategorized" for r in rows]).most_common(30)),
    }

def _hwi_machine_tokens(m):
    vals=[]
    if isinstance(m,dict):
        vals += [m.get("hostname"), m.get("machine_id"), m.get("real_machine_id"), m.get("primary_ip")]
        p = m.get("payload") if isinstance(m.get("payload"),dict) else {}
        ident = p.get("identity") if isinstance(p.get("identity"),dict) else {}
        vals += [ident.get("hostname"), ident.get("serial"), ident.get("bios_serial"), ident.get("uuid"), ident.get("system_uuid"), ident.get("machine_uuid")]
    return set([_hwi_s(x).lower() for x in vals if _hwi_s(x)])

def _hwi_sync_live():
    rows = _hwi_rows()
    try:
        machines = load_latest()
    except Exception:
        machines = []
    mt = [(m, _hwi_machine_tokens(m)) for m in machines]
    matched = 0
    for r in rows:
        keys = set()
        for k in ["serial_number","tagname_hostname","asset_code"]:
            v = _hwi_s(r.get(k)).lower()
            if v and v not in {"na","n/a","-","none"}: keys.add(v)
        hit = None; by = ""
        for m,toks in mt:
            common = keys.intersection(toks)
            if common:
                hit = m; by = ", ".join(sorted(common)); break
        if hit:
            matched += 1
            r["live_sync_status"] = "matched"
            r["live_hostname"] = _hwi_s(hit.get("hostname"))
            r["live_machine_id"] = _hwi_s(hit.get("machine_id"))
            r["live_ip"] = _hwi_s(hit.get("primary_ip"))
            r["live_online"] = _hwi_s(hit.get("online"))
            r["live_last_seen"] = _hwi_s(hit.get("updated_at"))
            r["remarks"] = (r.get("remarks","") + (" | " if r.get("remarks") else "") + "Live matched by: " + by)[:500]
        else:
            r["live_sync_status"] = "not_matched"
            r["live_hostname"] = r["live_machine_id"] = r["live_ip"] = r["live_online"] = r["live_last_seen"] = ""
    _hwi_save(rows)
    return {"ok": True, "assets": len(rows), "matched": matched, "not_matched": len(rows)-matched}

def _hwi_read_body(self):
    try:
        if hasattr(self,"read_json"):
            return self.read_json()
    except Exception:
        pass
    ln = int(self.headers.get("Content-Length", "0") or 0)
    raw = self.rfile.read(ln) if ln else b"{}"
    return _hwi_json.loads(raw.decode("utf-8") or "{}")

def _hwi_csv_bytes(rows):
    buf = _hwi_io.StringIO()
    w = _hwi_csv.DictWriter(buf, fieldnames=_HWI_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for r in rows: w.writerow(_hwi_normalize(r))
    return buf.getvalue().encode("utf-8-sig")

def _hwi_html():
    return r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>H/W Inventory V2</title>
<style>
body{margin:0;font-family:Inter,Segoe UI,Arial;background:#07111f;color:#eaf1ff}header{padding:18px 22px;background:linear-gradient(135deg,#0c244d,#0f766e);position:sticky;top:0;z-index:5}h1{margin:0;font-size:24px}.sub{color:#b7c7e5;font-size:13px}.wrap{padding:18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.card{background:#101b31;border:1px solid #294264;border-radius:15px;padding:12px}.k{font-size:11px;color:#9fb2d1}.v{font-size:22px;font-weight:900}button,.btn{background:#1d4ed8;color:white;border:0;border-radius:10px;padding:9px 11px;margin:4px;cursor:pointer;text-decoration:none;display:inline-block}button.danger{background:#dc2626}.alt{background:#334155}input,select,textarea{background:#0f172a;color:#fff;border:1px solid #334155;border-radius:8px;padding:7px;min-width:120px}table{width:100%;border-collapse:collapse;background:#10182f;margin-top:12px}th,td{padding:7px;border-bottom:1px solid #22314f;font-size:12px;vertical-align:top}th{position:sticky;top:70px;background:#172447;text-align:left;color:#bfdbfe}.scroll{overflow:auto;max-height:72vh;border-radius:14px;border:1px solid #22314f}.small{font-size:12px;color:#9fb2d1}.ok{color:#4ade80}.bad{color:#fb7185}
</style></head><body><header><h1>Fresh H/W Inventory from Google Sheet</h1><div class="sub">Duplicate-cleaned asset register with Make, Model, Vendor, Warranty, Purchase, PO/Bill, Bill Path, Tag/Hostname, Serial, Assigned To, Location, Status, Remarks and Live Sync.</div></header><div class="wrap"><a class="btn alt" href="/">Back Dashboard</a><button onclick="syncLive()">Sync with Live Monitor</button><a class="btn" href="/api/hw-inventory-v2/export.csv">Download CSV</a><button onclick="newRow()">Add New Asset</button><input id="q" placeholder="Search make/model/serial/host/location" style="width:340px"><button onclick="loadAll()">Search</button><div id="cards" class="grid" style="margin-top:12px"></div><div id="msg" class="small"></div><div class="scroll"><table id="tbl"></table></div></div>
<script>
const cols=['asset_code','make_name','model_name','asset_name','asset_type','configuration_details','quantity','vendor_name','warranty_end_date','warranty_end_year','purchase_date','po_invoice_bill_no','po_invoice_bill_path','tagname_hostname','serial_number','assigned_to','asset_location','status','remarks','live_sync_status','live_hostname','live_online','live_last_seen'];
const labels={'asset_code':'Asset Code','make_name':'Make Name','model_name':'Model Name','asset_name':'Asset Name','asset_type':'Asset Type','configuration_details':'Configuration / Details','quantity':'Qty','vendor_name':'Vendor Name','warranty_end_date':'Warranty End Date','warranty_end_year':'Warranty End Year','purchase_date':'Purchase Date','po_invoice_bill_no':'PO / Invoice / Bill No','po_invoice_bill_path':'PO / Invoice / Bill Path','tagname_hostname':'Tagname / Hostname','serial_number':'Serial Number','assigned_to':'Assigned To','asset_location':'Location','status':'Status','remarks':'Remarks','live_sync_status':'Live Sync Status','live_hostname':'Live Hostname','live_online':'Live Online','live_last_seen':'Live Last Seen'};
let rows=[];function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}async function api(u,opt){let r=await fetch(u,opt); if(!r.ok)throw new Error(await r.text()); return r.json()}
function card(k,v){return `<div class=card><div class=k>${esc(k)}</div><div class=v>${esc(v)}</div></div>`}
async function loadAll(){let s=await api('/api/hw-inventory-v2/summary');cards.innerHTML=card('Assets',s.assets)+card('Synced Live',s.synced_live)+card('Missing Vendor',s.missing_vendor)+card('Missing Warranty',s.missing_warranty)+card('Missing Purchase',s.missing_purchase)+card('Missing Bill No',s.missing_bill)+card('Missing Bill Path',s.missing_bill_path)+card('Missing Tag/Host',s.missing_tag_hostname);let q=encodeURIComponent(document.getElementById('q').value||'');let data=await api('/api/hw-inventory-v2/assets?q='+q);rows=data.rows;render()}
function render(){tbl.innerHTML='<thead><tr><th>Action</th>'+cols.map(c=>`<th>${esc(labels[c]||c)}</th>`).join('')+'</tr></thead><tbody>'+rows.map((r,i)=>'<tr><td><button onclick="save('+i+')">Save</button><button class=danger onclick="delRow('+i+')">Delete</button></td>'+cols.map(c=>`<td><input data-i="${i}" data-k="${c}" value="${esc(r[c]||'')}" ${c.startsWith('live_')?'readonly':''}></td>`).join('')+'</tr>').join('')+'</tbody>'}
function collect(i){let r={...rows[i]};document.querySelectorAll(`input[data-i="${i}"]`).forEach(x=>r[x.dataset.k]=x.value);return r}
async function save(i){let r=collect(i);let out=await api('/api/hw-inventory-v2/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(r)});msg.innerHTML='<span class=ok>Saved '+esc(out.row.asset_uid)+'</span>';loadAll()}
async function delRow(i){if(!confirm('Delete this asset?'))return;await api('/api/hw-inventory-v2/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_uid:rows[i].asset_uid})});msg.innerHTML='<span class=bad>Deleted</span>';loadAll()}
async function syncLive(){let r=await api('/api/hw-inventory-v2/sync-save',{method:'POST'});msg.innerHTML='<span class=ok>Live sync done: matched '+r.matched+' / '+r.assets+'</span>';loadAll()}
function newRow(){rows.unshift({asset_uid:'',asset_code:'',make_name:'',model_name:'',asset_name:'',asset_type:'',configuration_details:'',quantity:'1',vendor_name:'',warranty_end_date:'',warranty_end_year:'',purchase_date:'',po_invoice_bill_no:'',po_invoice_bill_path:'',tagname_hostname:'',serial_number:'',assigned_to:'',asset_location:'',status:'Review',remarks:'',live_sync_status:'not_synced'});render()}
loadAll().catch(e=>document.body.innerHTML='<pre>'+esc(e.message)+'</pre>')
</script></body></html>'''

_hwi_old_get = Handler.do_GET
_hwi_old_post = Handler.do_POST if hasattr(Handler, "do_POST") else None
_hwi_old_send = Handler._send

def _hwi_get(self):
    try:
        u = _hwi_url.urlparse(self.path); path = u.path; qs = _hwi_url.parse_qs(u.query)
        if path in ("/hw-inventory-v2", "/inventory-manager"):
            return self._send(200, _hwi_html().encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/hw-inventory-v2/summary":
            return self.send_json(_hwi_summary())
        if path == "/api/hw-inventory-v2/assets":
            rows = _hwi_filter(_hwi_rows(), qs)
            return self.send_json({"ok": True, "count": len(rows), "rows": rows})
        if path == "/api/hw-inventory-v2/export.csv":
            return self._send(200, _hwi_csv_bytes(_hwi_rows()), "text/csv; charset=utf-8", {"Content-Disposition": 'attachment; filename="fresh_hw_inventory_v2.csv"'})
        return _hwi_old_get(self)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
        return None
    except Exception as e:
        return self.send_json({"ok": False, "error": str(e)}, 500)

def _hwi_post(self):
    try:
        u = _hwi_url.urlparse(self.path); path = u.path
        if path == "/api/hw-inventory-v2/save":
            body = _hwi_normalize(_hwi_read_body(self))
            rows = _hwi_rows(); found=False
            for i,r in enumerate(rows):
                if _hwi_s(r.get("asset_uid")) == _hwi_s(body.get("asset_uid")) and _hwi_s(body.get("asset_uid")):
                    rows[i]=body; found=True; break
            if not found:
                if not body.get("asset_uid"): body["asset_uid"]=_hwi_uid(body)
                rows.insert(0, body)
            _hwi_save(rows)
            return self.send_json({"ok": True, "row": body})
        if path == "/api/hw-inventory-v2/delete":
            body = _hwi_read_body(self); uid = _hwi_s(body.get("asset_uid"))
            rows = [r for r in _hwi_rows() if _hwi_s(r.get("asset_uid")) != uid]
            _hwi_save(rows)
            return self.send_json({"ok": True, "deleted": uid, "remaining": len(rows)})
        if path == "/api/hw-inventory-v2/sync-save":
            return self.send_json(_hwi_sync_live())
        if _hwi_old_post:
            return _hwi_old_post(self)
        return self.send_json({"error":"not_found"},404)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
        return None
    except Exception as e:
        return self.send_json({"ok": False, "error": str(e)}, 500)

def _hwi_send(self, status, body, *args, **kwargs):
    try:
        ctype = str(args[0]) if args else str(kwargs.get("content_type", ""))
        if status == 200 and isinstance(body,(bytes,bytearray)) and (("text/html" in ctype) or b"Command Center" in body[:300000]) and b"/hw-inventory-v2" not in body:
            html = bytes(body).decode("utf-8", "ignore")
            if "Command Center" in html:
                js = '''<script>(function(){function add(){if(document.getElementById('hwInvV2Nav'))return;var ref=[...document.querySelectorAll('button,a,div,span')].find(x=>(x.textContent||'').trim()==='Hardware')||[...document.querySelectorAll('button,a,div,span')].find(x=>(x.textContent||'').trim()==='Software');var n=document.createElement('div');n.id='hwInvV2Nav';n.textContent='H/W Inventory';n.onclick=function(){location.href='/hw-inventory-v2'};n.style.cssText='cursor:pointer;margin:8px 0;padding:12px 14px;border-radius:12px;font-weight:900;color:#dce8ff;background:linear-gradient(135deg,#1d4ed8,#0e7490);border:1px solid rgba(45,212,191,.45)';if(ref&&ref.parentNode)ref.parentNode.insertBefore(n,ref.nextSibling);else document.body.prepend(n)}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',add);else add()})();</script>'''
                html = html.replace("</body>", js + "</body>")
                body = html.encode("utf-8")
        return _hwi_old_send(self, status, body, *args, **kwargs)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
        return None

Handler.do_GET = _hwi_get
Handler.do_POST = _hwi_post
Handler._send = _hwi_send
# ================= END HW INVENTORY V2 FROM GOOGLE SHEET =================
'''

if "HW INVENTORY V2 FROM GOOGLE SHEET" not in code:
    marker = "def main()"
    if marker not in code:
        raise SystemExit("def main() marker not found")
    code = code.replace(marker, addon + "\n" + marker, 1)
else:
    print("HW inventory v2 patch already exists; data file refreshed only")
server.write_text(code, encoding="utf-8")
print("HW inventory v2 route/API/UI installed")