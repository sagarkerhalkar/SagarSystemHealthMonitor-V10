from pathlib import Path
import re
server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

helper = r'''

# ================= FRESH GOOGLE SHEET HW INVENTORY UI V3 =================
# Source: Nexttoppers Assets Detail.xlsx Google Sheet import. No client change. No Ubuntu change. No live 2278 change.
import json as _fhw_json
import csv as _fhw_csv
import io as _fhw_io
import urllib.parse as _fhw_url
import hashlib as _fhw_hash
from pathlib import Path as _fhw_Path
from collections import Counter as _fhw_Counter

try:
    _FHW_BASE = _fhw_Path(BASE_DIR)
except Exception:
    _FHW_BASE = _fhw_Path(__file__).resolve().parent
_FHW_DATA = _FHW_BASE / "data" / "fresh_hw_inventory.json"
_FSW_DATA = _FHW_BASE / "data" / "fresh_sw_inventory.json"

_FHW_FIELDS = [
    "asset_uid", "asset_code", "asset_name", "asset_type", "category", "configuration_details", "quantity", "rate",
    "vendor_name", "warranty_end_date", "warranty_end_year", "purchase_date", "po_invoice_bill_no", "po_invoice_bill_path",
    "tagname_hostname", "serial_number", "assigned_to", "asset_location", "status", "remarks",
    "source_sheet", "source_row", "duplicate_warning", "live_sync_status", "live_hostname", "live_machine_id", "live_primary_ip", "live_last_seen"
]

def _fhw_s(v):
    return "" if v is None else str(v).strip()

def _fhw_valid(v):
    return _fhw_s(v).lower() not in ("", "na", "n/a", "-", "none", "null", "0")

def _fhw_load(path):
    try:
        if _fhw_Path(path).exists():
            x = _fhw_json.loads(_fhw_Path(path).read_text(encoding="utf-8-sig"))
            return x if isinstance(x, list) else []
    except Exception:
        return []
    return []

def _fhw_write(path, rows):
    _fhw_Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    _fhw_Path(tmp).write_text(_fhw_json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _fhw_Path(tmp).replace(path)

def _fhw_norm_row(r):
    r = dict(r or {})
    for k in _FHW_FIELDS:
        r.setdefault(k, "")
    if not _fhw_s(r.get("asset_uid")):
        seed = "|".join([_fhw_s(r.get(k)) for k in ["asset_code","tagname_hostname","serial_number","asset_name","asset_type","source_sheet","source_row"]])
        r["asset_uid"] = "HW-" + _fhw_hash.sha1(seed.encode("utf-8", "ignore")).hexdigest()[:10].upper()
    if not _fhw_s(r.get("category")):
        r["category"] = r.get("asset_type") or "Uncategorized"
    if not _fhw_s(r.get("warranty_end_year")) and _fhw_s(r.get("warranty_end_date")):
        m = re.search(r"(20\d{2}|19\d{2})", _fhw_s(r.get("warranty_end_date")))
        if m: r["warranty_end_year"] = m.group(1)
    return r

def _fhw_rows(live=False):
    rows = [_fhw_norm_row(r) for r in _fhw_load(_FHW_DATA)]
    return _fhw_sync(rows) if live else rows

def _fsw_rows():
    return _fhw_load(_FSW_DATA)

def _fhw_live_tokens():
    out=[]
    try:
        machines = load_latest()
    except Exception:
        machines = []
    for m in machines:
        toks=[]
        if isinstance(m, dict):
            toks += [m.get("hostname"), m.get("machine_id"), m.get("real_machine_id"), m.get("primary_ip"), m.get("public_ip")]
            p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
            ident = p.get("identity") if isinstance(p.get("identity"), dict) else {}
            toks += [ident.get("hostname"), ident.get("serial"), ident.get("bios_serial"), ident.get("uuid"), ident.get("system_uuid")]
            hw = p.get("hardware") if isinstance(p.get("hardware"), dict) else {}
            cpu = hw.get("cpu") if isinstance(hw.get("cpu"), dict) else {}
            toks += [cpu.get("processor_id"), cpu.get("serial")]
        tokset = set([_fhw_s(x).lower() for x in toks if _fhw_valid(x)])
        out.append((m, tokset))
    return out

def _fhw_sync(rows):
    machines = _fhw_live_tokens()
    result=[]
    for r in rows:
        x=dict(r)
        keys=[]
        if _fhw_valid(x.get("tagname_hostname")): keys.append(_fhw_s(x.get("tagname_hostname")).lower())
        if _fhw_valid(x.get("serial_number")): keys.append(_fhw_s(x.get("serial_number")).lower())
        if _fhw_valid(x.get("asset_code")): keys.append(_fhw_s(x.get("asset_code")).lower())
        match=None; by=""
        for m,toks in machines:
            common=[k for k in keys if k in toks]
            if common:
                match=m; by=", ".join(common); break
        if match:
            x["live_sync_status"]="matched"
            x["live_match_by"]=by
            x["live_hostname"]=match.get("hostname","")
            x["live_machine_id"]=match.get("machine_id","")
            x["live_primary_ip"]=match.get("primary_ip","")
            x["live_last_seen"]=match.get("updated_at","")
            x["live_online"]=match.get("online","")
        else:
            x.setdefault("live_sync_status", "not_matched")
            x["live_match_by"]=""
            x["live_hostname"]=""
            x["live_machine_id"]=""
            x["live_primary_ip"]=""
            x["live_last_seen"]=""
            x["live_online"]=""
        result.append(x)
    return result

def _fhw_filter(rows, qs):
    q = _fhw_s((qs.get("q") or [""])[0]).lower()
    cat = _fhw_s((qs.get("category") or [""])[0]).lower()
    loc = _fhw_s((qs.get("location") or [""])[0]).lower()
    out=[]
    for r in rows:
        text = _fhw_json.dumps(r, ensure_ascii=False, default=str).lower()
        if q and q not in text: continue
        if cat and cat not in _fhw_s(r.get("category")).lower(): continue
        if loc and loc not in _fhw_s(r.get("asset_location")).lower(): continue
        out.append(r)
    return out

def _fhw_summary():
    rows = _fhw_rows(live=True)
    def missing(k): return sum(1 for r in rows if not _fhw_valid(r.get(k)))
    return {
        "ok": True,
        "imported_assets": len(rows),
        "software_rows": len(_fsw_rows()),
        "live_machines": len(_fhw_live_tokens()),
        "live_matched": sum(1 for r in rows if r.get("live_sync_status") == "matched"),
        "missing_vendor": missing("vendor_name"),
        "missing_warranty": missing("warranty_end_date"),
        "missing_purchase_date": missing("purchase_date"),
        "missing_bill": missing("po_invoice_bill_no"),
        "missing_bill_path": missing("po_invoice_bill_path"),
        "missing_tag_hostname": missing("tagname_hostname"),
        "duplicate_warning_rows": sum(1 for r in rows if _fhw_s(r.get("duplicate_warning"))),
        "categories": dict(_fhw_Counter([_fhw_s(r.get("category")) or "Uncategorized" for r in rows]).most_common(30)),
        "locations": dict(_fhw_Counter([_fhw_s(r.get("asset_location")) or "Unknown" for r in rows]).most_common(30)),
        "source_file": str(_FHW_DATA),
        "software_file": str(_FSW_DATA),
    }

def _fhw_csv_bytes(rows):
    fields=[]
    for k in _FHW_FIELDS:
        if k not in fields: fields.append(k)
    for r in rows:
        for k in r.keys():
            if k not in fields: fields.append(k)
    buf=_fhw_io.StringIO()
    w=_fhw_csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows: w.writerow(r)
    return buf.getvalue().encode("utf-8-sig")

def _fhw_send_csv(self, rows, filename):
    return self._send(200, _fhw_csv_bytes(rows), "text/csv; charset=utf-8", {"Content-Disposition": f'attachment; filename="{filename}"'})

def _fhw_save(body):
    row = _fhw_norm_row(body)
    rows = _fhw_rows(False)
    uid = _fhw_s(row.get("asset_uid"))
    done=False; out=[]
    for r in rows:
        if _fhw_s(r.get("asset_uid")) == uid:
            out.append(row); done=True
        else:
            out.append(r)
    if not done: out.append(row)
    _fhw_write(_FHW_DATA, out)
    return {"ok": True, "saved": row, "count": len(out)}

def _fhw_delete(body):
    uid = _fhw_s(body.get("asset_uid") or body.get("id"))
    rows = _fhw_rows(False)
    out = [r for r in rows if _fhw_s(r.get("asset_uid")) != uid]
    _fhw_write(_FHW_DATA, out)
    return {"ok": True, "deleted": uid, "count": len(out)}

def _fhw_sync_save():
    rows = _fhw_sync(_fhw_rows(False))
    _fhw_write(_FHW_DATA, rows)
    return {"ok": True, "count": len(rows), "live_matched": sum(1 for r in rows if r.get("live_sync_status") == "matched")}

def _fhw_html():
    return r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fresh H/W Inventory</title>
<style>body{margin:0;background:#07111f;color:#eaf1ff;font-family:Inter,Segoe UI,Arial}header{padding:18px 22px;background:linear-gradient(135deg,#0b1f46,#155e75);position:sticky;top:0;z-index:10}main{padding:18px}.card{background:#101b31;border:1px solid #264163;border-radius:16px;padding:14px;margin:10px 0;box-shadow:0 12px 28px #0005}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.metric{background:#0f172a;border:1px solid #334155;border-radius:14px;padding:12px}.metric b{font-size:24px;display:block;margin-top:4px}.btn,button{background:#1d4ed8;color:#fff;border:0;border-radius:10px;padding:10px 12px;margin:4px;text-decoration:none;cursor:pointer;font-weight:700}.alt{background:#334155}.danger{background:#dc2626}input,select,textarea{background:#0f172a;color:#eaf1ff;border:1px solid #334155;border-radius:9px;padding:9px;margin:4px}table{width:100%;border-collapse:collapse;background:#10182f}th,td{padding:8px;border-bottom:1px solid #22314f;font-size:13px;vertical-align:top}th{background:#172447;color:#bcd0ff;text-align:left}.scroll{overflow:auto;max-height:62vh}.good{color:#4ade80}.bad{color:#fb7185}.warn{color:#facc15}</style></head>
<body><header><h1>Fresh H/W Inventory â€” Google Sheet Import</h1><div>Editable asset register + dedupe + live monitor sync. V10 test only.</div></header><main>
<a class="btn alt" href="/">Back Dashboard</a><a class="btn" href="/api/fresh-inventory/export.csv">Download CSV</a><button onclick="syncSave()">Sync Live & Save</button>
<div id="cards" class="grid"></div>
<div class="card"><h2>Add / Edit Asset</h2><div class="grid">
<input id="asset_uid" placeholder="asset_uid auto" readonly><input id="asset_code" placeholder="Asset Code"><input id="asset_name" placeholder="Asset Name"><input id="asset_type" placeholder="Asset Type"><input id="category" placeholder="Category"><input id="configuration_details" placeholder="Configuration / Details"><input id="quantity" placeholder="Quantity"><input id="rate" placeholder="Rate"><input id="vendor_name" placeholder="Vendor Name"><input id="warranty_end_date" placeholder="Warranty End Date"><input id="warranty_end_year" placeholder="Warranty End Year"><input id="purchase_date" placeholder="Purchase Date"><input id="po_invoice_bill_no" placeholder="PO / Invoice / Bill No"><input id="po_invoice_bill_path" placeholder="PO / Invoice / Bill Path"><input id="tagname_hostname" placeholder="Tagname / Hostname"><input id="serial_number" placeholder="Serial Number"><input id="assigned_to" placeholder="Assigned To"><input id="asset_location" placeholder="Location"><input id="status" placeholder="Status"><input id="remarks" placeholder="Remarks"></div><button onclick="saveAsset()">Save</button><button class="alt" onclick="clearForm()">Clear</button></div>
<div class="card"><h2>Inventory List</h2><input id="q" placeholder="Search asset / serial / hostname / vendor / bill" style="width:420px;max-width:90%" oninput="loadRows()"><select id="cat" onchange="loadRows()"><option value="">All categories</option></select><select id="loc" onchange="loadRows()"><option value="">All locations</option></select><div class="scroll"><table><thead><tr><th>Asset</th><th>Type/Config</th><th>Vendor/Warranty/Purchase</th><th>PO/Bill</th><th>Tag/Serial</th><th>Live Sync</th><th>Action</th></tr></thead><tbody id="rows"></tbody></table></div></div>
<script>
let DATA=[]; const F=['asset_uid','asset_code','asset_name','asset_type','category','configuration_details','quantity','rate','vendor_name','warranty_end_date','warranty_end_year','purchase_date','po_invoice_bill_no','po_invoice_bill_path','tagname_hostname','serial_number','assigned_to','asset_location','status','remarks'];
function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function api(u,o){let r=await fetch(u,o); if(!r.ok) throw new Error(await r.text()); return r.json()}
async function loadSummary(){let s=await api('/api/fresh-inventory/summary'); cards.innerHTML=[['Assets',s.imported_assets],['Live Matched',s.live_matched],['Missing Vendor',s.missing_vendor],['Missing Warranty',s.missing_warranty],['Missing Purchase',s.missing_purchase_date],['Missing Bill No',s.missing_bill],['Missing Bill Path',s.missing_bill_path],['Duplicate Warning',s.duplicate_warning_rows]].map(x=>`<div class=metric>${x[0]}<b>${esc(x[1])}</b></div>`).join(''); fillSelect(cat,s.categories); fillSelect(loc,s.locations)}
function fillSelect(el,obj){let cur=el.value; let first=el.options[0].outerHTML; el.innerHTML=first+Object.keys(obj||{}).map(k=>`<option>${esc(k)}</option>`).join(''); el.value=cur}
async function loadRows(){let u='/api/fresh-inventory/assets?live=1&q='+encodeURIComponent(q.value||'')+'&category='+encodeURIComponent(cat.value||'')+'&location='+encodeURIComponent(loc.value||''); let j=await api(u); DATA=j.rows||[]; rows.innerHTML=DATA.map((r,i)=>`<tr><td><b>${esc(r.asset_code)}</b><br>${esc(r.asset_name)}<br><span class=warn>${esc(r.duplicate_warning||'')}</span></td><td>${esc(r.asset_type)} / ${esc(r.category)}<br>${esc(r.configuration_details)}</td><td>${esc(r.vendor_name)}<br>Warranty: ${esc(r.warranty_end_date)} ${esc(r.warranty_end_year)}<br>Purchase: ${esc(r.purchase_date)}</td><td>${esc(r.po_invoice_bill_no)}<br>${esc(r.po_invoice_bill_path)}</td><td>Tag: ${esc(r.tagname_hostname)}<br>Serial: ${esc(r.serial_number)}<br>Loc: ${esc(r.asset_location)} / ${esc(r.assigned_to)}</td><td class=${r.live_sync_status==='matched'?'good':'bad'}>${esc(r.live_sync_status)}<br>${esc(r.live_hostname)}<br>${esc(r.live_primary_ip||'')}</td><td><button onclick="edit(${i})">Edit</button><button class=danger onclick="delAsset('${esc(r.asset_uid)}')">Delete</button></td></tr>`).join('')||'<tr><td colspan=7>No rows</td></tr>'}
function edit(i){let r=DATA[i]; F.forEach(k=>{let e=document.getElementById(k); if(e)e.value=r[k]||''}); scrollTo(0,0)}
function clearForm(){F.forEach(k=>{let e=document.getElementById(k); if(e)e.value=''})}
async function saveAsset(){let b={}; F.forEach(k=>b[k]=document.getElementById(k).value); await api('/api/fresh-inventory/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}); clearForm(); await loadSummary(); await loadRows()}
async function delAsset(id){if(!confirm('Delete this asset?'))return; await api('/api/fresh-inventory/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_uid:id})}); await loadSummary(); await loadRows()}
async function syncSave(){let j=await api('/api/fresh-inventory/sync-save',{method:'POST'}); alert('Live matched: '+j.live_matched+' / '+j.count); await loadSummary(); await loadRows()}
loadSummary().then(loadRows).catch(e=>document.body.innerHTML='<pre>'+esc(e.message)+'</pre>')
</script></main></body></html>'''

# ================= END FRESH GOOGLE SHEET HW INVENTORY UI V3 =================
'''

if "FRESH GOOGLE SHEET HW INVENTORY UI V3" not in code:
    marker = "class Handler"
    if marker not in code:
        raise SystemExit("class Handler marker not found")
    code = code.replace(marker, helper + "\n" + marker, 1)

get_block = '''            if path == "/inventory-manager":
                return self._send(200, _fhw_html().encode("utf-8"), "text/html; charset=utf-8")
            if path == "/api/fresh-inventory/summary":
                return self.send_json(_fhw_summary())
            if path == "/api/fresh-inventory/assets":
                rows = _fhw_filter(_fhw_rows(live=((qs.get("live") or ["1"])[0] in ("1","true","yes"))), qs)
                return self.send_json({"ok": True, "count": len(rows), "rows": rows})
            if path == "/api/fresh-inventory/export.csv":
                return _fhw_send_csv(self, _fhw_rows(live=True), "fresh_hw_inventory_live_synced.csv")
            if path == "/api/fresh-inventory/template.csv":
                return _fhw_send_csv(self, [], "fresh_hw_inventory_template.csv")
'''

post_block = '''            if path == "/api/fresh-inventory/save":
                return self.send_json(_fhw_save(body))
            if path == "/api/fresh-inventory/delete":
                return self.send_json(_fhw_delete(body))
            if path == "/api/fresh-inventory/sync-save":
                return self.send_json(_fhw_sync_save())
'''

if '"/api/fresh-inventory/summary"' not in code:
    # insert GET after GET auth check if possible
    auth_get = '            if not self.require_auth(path, "GET"):\n                return\n'
    if auth_get in code:
        code = code.replace(auth_get, auth_get + get_block, 1)
    else:
        marker = '            if path == "/api/overview":'
        if marker not in code:
            marker = '            if path == "/api/machines":'
        if marker not in code:
            raise SystemExit("GET insertion marker not found")
        code = code.replace(marker, get_block + marker, 1)

    auth_post = '            if not self.require_auth(path, "POST"):\n                return\n'
    if auth_post in code:
        code = code.replace(auth_post, auth_post + post_block, 1)
    else:
        marker = '            if path == "/api/auth/logout":'
        if marker not in code:
            marker = '            if path == "/api/auth/change-password":'
        if marker not in code:
            raise SystemExit("POST insertion marker not found")
        code = code.replace(marker, post_block + marker, 1)
else:
    print("fresh inventory routes already present")

server.write_text(code, encoding="utf-8")
print("fresh Google Sheet inventory UI/API patched")