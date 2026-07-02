from pathlib import Path

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

addon = r'''

# ================= COMPACT OLD IMPORTED INVENTORY UI V2 =================
import json as _ci_json, csv as _ci_csv, io as _ci_io, zipfile as _ci_zip, urllib.parse as _ci_url
from pathlib import Path as _ci_Path
from collections import Counter as _ci_Counter

try:
    _CI_BASE = _ci_Path(BASE_DIR)
except Exception:
    _CI_BASE = _ci_Path(__file__).resolve().parent

_CI_HW = _CI_BASE / "data" / "inventory_assets.json"
_CI_SW = _CI_BASE / "data" / "software_asset_register_2294.json"

def _ci_s(v):
    return "" if v is None else str(v).strip()

def _ci_load(p):
    try:
        if _ci_Path(p).exists():
            x = _ci_json.loads(_ci_Path(p).read_text(encoding="utf-8-sig"))
            return x if isinstance(x, list) else []
    except Exception:
        return []
    return []

def _ci_pick(r, *keys):
    if not isinstance(r, dict): return ""
    low = {str(k).lower().replace(" ","").replace("_","").replace("/",""): k for k in r.keys()}
    for k in keys:
        if k in r and _ci_s(r.get(k)): return _ci_s(r.get(k))
        kk = str(k).lower().replace(" ","").replace("_","").replace("/","")
        if kk in low and _ci_s(r.get(low[kk])): return _ci_s(r.get(low[kk]))
    return ""

def _ci_asset(r):
    x = dict(r or {})
    x["asset_code"] = _ci_pick(x,"asset_code","Code","Tag Name","tag_name","asset_uid","id")
    x["asset_name"] = _ci_pick(x,"asset_name","Name","Assets Name","asset_type","Item Name")
    x["category"] = _ci_pick(x,"category","Asset Type","Assets Type","asset_type") or "Uncategorized"
    x["quantity"] = _ci_pick(x,"quantity","Quantity") or "1"
    x["rate"] = _ci_pick(x,"rate","Rate","Amount")
    x["serial_number"] = _ci_pick(x,"serial_number","SerialNumber","Serial Number","Sr. No","Sr. No.")
    x["hostname_or_tag"] = _ci_pick(x,"hostname_or_tag","Host Name","Tag Name","device_name")
    x["employee_name"] = _ci_pick(x,"employee_name","assigned_user","Person Name","Employee Name","Custodian","Owner")
    x["asset_location"] = _ci_pick(x,"asset_location","location_room","Room No","Hall","Location","source_sheet")
    x["vendor"] = _ci_pick(x,"vendor","Vendor","VendorName","Company Name")
    x["Bill/Invoice/PO No"] = _ci_pick(x,"Bill/Invoice/PO No","bill_invoice_po_no","PO No","Bill No","Invoice No","po_no")
    x["lifecycle_status"] = _ci_pick(x,"lifecycle_status","status","Status") or "Review"
    x["source_sheet"] = _ci_pick(x,"source_sheet")
    return x

def _ci_assets():
    rows = [_ci_asset(r) for r in _ci_load(_CI_HW)]
    bad = ("company total","count summary","assets sheets details","total assets details")
    return [r for r in rows if not any(b in _ci_json.dumps(r, default=str).lower() for b in bad)]

def _ci_sw():
    rows=[]
    for r in _ci_load(_CI_SW):
        x=dict(r or {})
        x["product_name"]=_ci_pick(x,"product_name","software_name","name")
        x["vendor"]=_ci_pick(x,"vendor","publisher")
        x["license_type"]=_ci_pick(x,"license_type") or "Review"
        x["license_count"]=_ci_pick(x,"license_count","seats") or "1"
        x["assigned_to_employee"]=_ci_pick(x,"assigned_to_employee","employee_name","assigned_user")
        x["assigned_to_machine"]=_ci_pick(x,"assigned_to_machine","hostname","machine_hostname")
        x["login_username"]=_ci_pick(x,"login_username","username","account")
        x["Bill/Invoice/PO No"]=_ci_pick(x,"Bill/Invoice/PO No","bill_invoice_po_no","po_no","bill_no")
        x["renewal_date"]=_ci_pick(x,"renewal_date","expiry_date")
        rows.append(x)
    return rows

def _ci_summary():
    a=_ci_assets(); sw=_ci_sw()
    def miss(k): return sum(1 for r in a if not _ci_s(r.get(k)))
    cats=dict(_ci_Counter([_ci_s(r.get("category")) or "Uncategorized" for r in a]).most_common(20))
    return {
        "ok": True,
        "imported_assets": len(a),
        "software_rows": len(sw),
        "missing_owner": miss("employee_name"),
        "missing_location": miss("asset_location"),
        "missing_serial": sum(1 for r in a if not _ci_s(r.get("serial_number")) and not _ci_s(r.get("hostname_or_tag"))),
        "missing_bill": sum(1 for r in a if not _ci_s(r.get("Bill/Invoice/PO No"))),
        "categories": cats,
        "source_file": str(_CI_HW),
        "software_file": str(_CI_SW)
    }

def _ci_filter(rows, qs):
    q=_ci_s((qs.get("q") or [""])[0]).lower()
    if not q: return rows
    return [r for r in rows if q in _ci_json.dumps(r, ensure_ascii=False, default=str).lower()]

def _ci_csv_bytes(rows):
    fields=[]
    for r in rows:
        for k in r.keys():
            if k not in fields: fields.append(k)
    if not fields: fields=["empty"]
    buf=_ci_io.StringIO()
    w=_ci_csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows: w.writerow(r)
    return buf.getvalue().encode("utf-8-sig")

def _ci_download(self, rows, name):
    return self._send(200, _ci_csv_bytes(rows), "text/csv; charset=utf-8", {"Content-Disposition": f'attachment; filename="{name}"'})

def _ci_html():
    return '''<!doctype html><html><head><meta charset="utf-8"><title>Imported Inventory</title>
<style>body{font-family:Segoe UI,Arial;margin:0;background:#07111f;color:#eaf1ff}header{padding:18px;background:#0f2550}main{padding:18px}.card{display:inline-block;background:#101b31;border:1px solid #264163;border-radius:14px;padding:14px;margin:8px;min-width:160px}.v{font-size:26px;font-weight:800}.btn,button{background:#1d4ed8;color:#fff;border:0;border-radius:10px;padding:10px 12px;margin:5px;text-decoration:none;cursor:pointer}input{padding:10px;border-radius:10px;border:1px solid #334155;background:#0f172a;color:#fff;width:360px}table{width:100%;border-collapse:collapse;background:#10182f;margin-top:12px}th,td{padding:8px;border-bottom:1px solid #22314f;font-size:13px}th{background:#172447;text-align:left}</style></head>
<body><header><h1>Imported H/W + S/W Inventory</h1><div>Old working imported inventory inside V10 test UI</div></header><main>
<a class="btn" href="/">Back Dashboard</a><div id="cards"></div>
<input id="q" placeholder="Search"><button onclick="loadAll()">Search</button>
<div><button onclick="tab('hw')">H/W Register</button><button onclick="tab('sw')">S/W Register</button><button onclick="tab('download')">Downloads</button></div>
<section id="hw"></section><section id="sw" style="display:none"></section><section id="download" style="display:none"></section>
<script>
function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function api(u){let r=await fetch(u); if(!r.ok)throw new Error(await r.text()); return r.json()}
function tab(id){for(let s of document.querySelectorAll('section'))s.style.display='none';document.getElementById(id).style.display='block'}
function tbl(rows,cols){return '<table><thead><tr>'+cols.map(c=>'<th>'+esc(c[0])+'</th>').join('')+'</tr></thead><tbody>'+(rows.map(r=>'<tr>'+cols.map(c=>'<td>'+esc(r[c[1]]||'')+'</td>').join('')+'</tr>').join('')||'<tr><td>No rows</td></tr>')+'</tbody></table>'}
async function loadAll(){let q=encodeURIComponent(document.getElementById('q').value||'');let s=await api('/api/imported-inventory/summary');cards.innerHTML=[['Imported Assets',s.imported_assets],['Software Rows',s.software_rows],['Missing Owner',s.missing_owner],['Missing Location',s.missing_location],['Missing Bill',s.missing_bill]].map(x=>'<div class=card><div>'+x[0]+'</div><div class=v>'+esc(x[1])+'</div></div>').join('');
let a=await api('/api/imported-inventory/assets?q='+q);hw.innerHTML='<h2>H/W Asset Register</h2>'+tbl(a.rows,[['Asset Code','asset_code'],['Name','asset_name'],['Category','category'],['Qty','quantity'],['Serial','serial_number'],['Host/Tag','hostname_or_tag'],['Employee','employee_name'],['Location','asset_location'],['Status','lifecycle_status'],['Bill/PO','Bill/Invoice/PO No']]);
let w=await api('/api/imported-inventory/software?q='+q);sw.innerHTML='<h2>S/W License Register</h2>'+tbl(w.rows,[['Product','product_name'],['Vendor','vendor'],['License','license_type'],['Seats','license_count'],['Employee','assigned_to_employee'],['Machine','assigned_to_machine'],['Username','login_username'],['Bill/PO','Bill/Invoice/PO No'],['Renewal','renewal_date']]);
download.innerHTML='<h2>Downloads</h2><a class=btn href="/api/imported-inventory/download/hardware.csv">Download H/W CSV</a><a class=btn href="/api/imported-inventory/download/software.csv">Download S/W CSV</a>'}
loadAll().catch(e=>document.body.innerHTML='<pre>'+esc(e.message)+'</pre>')
</script></main></body></html>'''

_ci_old_get = Handler.do_GET
_ci_old_send = Handler._send

def _ci_get(self):
    try:
        u=_ci_url.urlparse(self.path); path=u.path; qs=_ci_url.parse_qs(u.query)
        if path == "/inventory-manager":
            return self._send(200, _ci_html().encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/imported-inventory/summary":
            return self.send_json(_ci_summary())
        if path == "/api/imported-inventory/assets":
            rows=_ci_filter(_ci_assets(), qs)
            return self.send_json({"ok":True,"count":len(rows),"rows":rows})
        if path == "/api/imported-inventory/software":
            rows=_ci_filter(_ci_sw(), qs)
            return self.send_json({"ok":True,"count":len(rows),"rows":rows})
        if path == "/api/imported-inventory/download/hardware.csv":
            return _ci_download(self, _ci_assets(), "imported_hardware_inventory.csv")
        if path == "/api/imported-inventory/download/software.csv":
            return _ci_download(self, _ci_sw(), "imported_software_inventory.csv")
        return _ci_old_get(self)
    except Exception as e:
        return self.send_json({"ok":False,"error":str(e)},500)

def _ci_send(self, status, body, *args, **kwargs):
    try:
        ctype = str(args[0]) if args else ""
        if status == 200 and isinstance(body,(bytes,bytearray)) and b"Command Center" in body[:300000] and b"inventory-manager" not in body:
            html=bytes(body).decode("utf-8","ignore")
            js='''<script>(function(){function f(){if(document.getElementById("invMgrNav"))return;var refs=[...document.querySelectorAll("button,a,div,span")].filter(x=>(x.textContent||"").trim()=="Software");var ref=refs[0];var n=document.createElement("div");n.id="invMgrNav";n.textContent="ISO ITAM Inventory";n.onclick=function(){location.href="/inventory-manager"};n.style.cssText="cursor:pointer;margin:8px 0;padding:12px 14px;border-radius:12px;font-weight:800;color:#dce8ff;background:linear-gradient(135deg,#1d4ed8,#0e7490);border:1px solid rgba(45,212,191,.4)";if(ref&&ref.parentNode)ref.parentNode.insertBefore(n,ref.nextSibling);else document.body.prepend(n)}if(document.readyState=="loading")document.addEventListener("DOMContentLoaded",f);else f()})();</script>'''
            body=html.replace("</body>",js+"</body>").encode("utf-8")
        return _ci_old_send(self,status,body,*args,**kwargs)
    except Exception:
        return _ci_old_send(self,status,body,*args,**kwargs)

Handler.do_GET = _ci_get
Handler._send = _ci_send
# ================= END COMPACT OLD IMPORTED INVENTORY UI V2 =================
'''

if "COMPACT OLD IMPORTED INVENTORY UI V2" not in code:
    marker = "def main()"
    if marker not in code:
        raise SystemExit("def main() marker not found")
    code = code.replace(marker, addon + "\n" + marker, 1)

server.write_text(code, encoding="utf-8")
print("compact old imported inventory UI added")