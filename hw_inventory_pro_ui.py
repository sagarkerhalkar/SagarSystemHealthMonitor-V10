import json, csv, io, hashlib, urllib.parse, re
from pathlib import Path
from collections import Counter

DATA_FILE = None
LOAD_LATEST = None
OLD_GET = None
OLD_POST = None

COLS = [
    "asset_uid","asset_code","make_name","model_name","asset_name","asset_type",
    "configuration_details","quantity","rate","vendor_name","warranty_end_date",
    "warranty_end_year","purchase_date","po_invoice_bill_no","po_invoice_bill_path",
    "tagname_hostname","serial_number","assigned_to","asset_location","status",
    "remarks","source_sheet","source_row","live_sync_status","live_hostname",
    "live_machine_id","live_ip","live_online","live_last_seen"
]

def s(v):
    return "" if v is None else str(v).strip()

def uid(r):
    base = s(r.get("asset_uid") or r.get("serial_number") or r.get("tagname_hostname") or r.get("asset_code"))
    if base:
        return base
    raw = json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)
    return "HW-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()

def norm(r):
    x = dict(r or {})
    mapping = {
        "Code":"asset_code","Name":"asset_name","AssetType":"asset_type","Details":"configuration_details",
        "Quantity":"quantity","Rate":"rate","WarrantyDate":"warranty_end_date","PurchaseDate":"purchase_date",
        "SerialNumber":"serial_number","VendorName":"vendor_name","Vendor Name":"vendor_name",
        "Make Name":"make_name","Model Name":"model_name",
        "PO / Invoice / Bill No":"po_invoice_bill_no","PO / Invoice / Bill Path":"po_invoice_bill_path",
        "Tagname / Hostname":"tagname_hostname","Assigned To":"assigned_to","Location":"asset_location",
        "Status":"status","Remarks":"remarks"
    }
    for old, new in mapping.items():
        if not s(x.get(new)) and s(x.get(old)):
            x[new] = s(x.get(old))

    if not s(x.get("asset_name")):
        x["asset_name"] = s(x.get("model_name") or x.get("asset_type") or "Asset")
    if not s(x.get("asset_type")):
        x["asset_type"] = s(x.get("category") or "Uncategorized")
    if not s(x.get("model_name")):
        x["model_name"] = s(x.get("asset_name"))
    if not s(x.get("quantity")):
        x["quantity"] = "1"
    if not s(x.get("status")):
        x["status"] = "Review"

    if not s(x.get("warranty_end_year")) and s(x.get("warranty_end_date")):
        m = re.search(r"(20\d{2}|19\d{2})", s(x.get("warranty_end_date")))
        if m:
            x["warranty_end_year"] = m.group(1)

    x["asset_uid"] = uid(x)
    for c in COLS:
        x.setdefault(c, "")
    return x

def load_rows():
    try:
        data = json.loads(Path(DATA_FILE).read_text(encoding="utf-8-sig"))
        if not isinstance(data, list):
            return []
    except Exception:
        return []
    return [norm(r) for r in data if isinstance(r, dict)]

def write_rows(rows):
    out = [norm(r) for r in rows if isinstance(r, dict)]
    tmp = Path(DATA_FILE).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(DATA_FILE)

def opts(rows, key):
    return sorted(set(s(r.get(key)) for r in rows if s(r.get(key))))

def summary():
    rows = load_rows()
    def miss(k):
        return sum(1 for r in rows if not s(r.get(k)))
    return {
        "ok": True,
        "assets": len(rows),
        "missing_vendor": miss("vendor_name"),
        "missing_make": miss("make_name"),
        "missing_model": miss("model_name"),
        "missing_serial": miss("serial_number"),
        "missing_tag": miss("tagname_hostname"),
        "missing_person": miss("assigned_to"),
        "missing_room": miss("asset_location"),
        "missing_bill": miss("po_invoice_bill_no"),
        "categories": opts(rows, "asset_type"),
        "rooms": opts(rows, "asset_location"),
        "persons": opts(rows, "assigned_to"),
        "vendors": opts(rows, "vendor_name"),
        "statuses": opts(rows, "status"),
        "category_count": dict(Counter([s(r.get("asset_type")) or "Uncategorized" for r in rows]).most_common(30)),
        "source_file": str(DATA_FILE)
    }

def filtered(qs):
    rows = load_rows()
    q = s((qs.get("q") or [""])[0]).lower()
    cat = s((qs.get("category") or [""])[0]).lower()
    room = s((qs.get("room") or [""])[0]).lower()
    person = s((qs.get("person") or [""])[0]).lower()
    vendor = s((qs.get("vendor") or [""])[0]).lower()
    status = s((qs.get("status") or [""])[0]).lower()

    out = []
    for r in rows:
        if cat and s(r.get("asset_type")).lower() != cat: continue
        if room and s(r.get("asset_location")).lower() != room: continue
        if person and s(r.get("assigned_to")).lower() != person: continue
        if vendor and s(r.get("vendor_name")).lower() != vendor: continue
        if status and s(r.get("status")).lower() != status: continue
        if q and q not in json.dumps(r, ensure_ascii=False, default=str).lower(): continue
        out.append(r)
    return out

def csv_bytes(rows):
    fields = list(COLS)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8-sig")

def body_json(h):
    n = int(h.headers.get("Content-Length") or 0)
    raw = h.rfile.read(n) if n else b"{}"
    return json.loads(raw.decode("utf-8-sig") or "{}")

def tokens(m):
    vals = []
    if isinstance(m, dict):
        vals += [m.get("hostname"), m.get("machine_id"), m.get("real_machine_id"), m.get("primary_ip"), m.get("public_ip")]
        p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        ident = p.get("identity") if isinstance(p.get("identity"), dict) else {}
        vals += [ident.get("serial"), ident.get("bios_serial"), ident.get("uuid"), ident.get("system_uuid"), ident.get("hostname")]
    return set(s(v).lower() for v in vals if s(v))

def sync_live():
    rows = load_rows()
    try:
        machines = LOAD_LATEST()
    except Exception:
        machines = []
    mt = [(m, tokens(m)) for m in machines]
    out, matched = [], 0

    for r in rows:
        x = dict(r)
        keys = [s(x.get(k)).lower() for k in ["serial_number","tagname_hostname","asset_code"] if s(x.get(k))]
        match = None
        for m, toks in mt:
            if any(k in toks for k in keys):
                match = m
                break
        if match:
            matched += 1
            x["live_sync_status"] = "matched"
            x["live_hostname"] = s(match.get("hostname"))
            x["live_machine_id"] = s(match.get("machine_id"))
            x["live_ip"] = s(match.get("primary_ip"))
            x["live_online"] = s(match.get("online"))
            x["live_last_seen"] = s(match.get("updated_at"))
        else:
            x["live_sync_status"] = "not_matched"
            x["live_hostname"] = ""
            x["live_machine_id"] = ""
            x["live_ip"] = ""
            x["live_online"] = ""
            x["live_last_seen"] = ""
        out.append(norm(x))
    write_rows(out)
    return len(out), matched

def send_json(h, obj, status=200):
    b = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(b)))
    h.end_headers()
    h.wfile.write(b)

def send_bytes(h, b, ctype, filename=None):
    h.send_response(200)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(b)))
    if filename:
        h.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    h.end_headers()
    h.wfile.write(b)

def html():
    return """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>H/W Inventory</title>
<style>
body{margin:0;font-family:Segoe UI,Arial;background:#edf5fb;color:#0f172a}
.layout{display:flex;min-height:100vh}
.side{width:250px;background:#071426;color:#dbeafe;padding:22px 14px;box-sizing:border-box;position:sticky;top:0;height:100vh}
.logo{width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#2563eb,#14b8a6);display:grid;place-items:center;font-weight:900}
.brand{display:flex;gap:12px;align-items:center;margin-bottom:28px}
.nav a{display:block;color:#dbeafe;text-decoration:none;padding:13px 14px;border-radius:12px;font-weight:800;margin:7px 0}
.nav a.active{background:linear-gradient(135deg,#0f766e,#1d4ed8);box-shadow:inset 4px 0 #2dd4bf}
.main{flex:1;padding:24px;overflow:hidden}
.hero,.panel,.card{background:white;border-radius:22px;box-shadow:0 18px 50px rgba(30,58,138,.13)}
.hero{padding:22px;margin-bottom:18px}
.hero h1{margin:0;font-size:32px;color:#0f254a}
.sub{color:#64748b;margin-top:6px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0}
.card{padding:14px;border:1px solid #d9e7f7}
.k{font-size:11px;color:#64748b;font-weight:900;text-transform:uppercase}
.v{font-size:25px;font-weight:950}
.panel{padding:16px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0;align-items:center}
input,select{border:1px solid #cbd5e1;border-radius:12px;padding:10px;background:white;min-height:38px}
.search{width:360px;max-width:95%}
button,.btn{border:0;border-radius:12px;padding:10px 13px;background:#2563eb;color:white;font-weight:900;cursor:pointer;text-decoration:none}
.dark{background:#0f172a}.green{background:#0f766e}.red{background:#dc2626}
.form{display:none;background:#f8fbff;border:1px solid #cfe0f5;border-radius:18px;padding:14px;margin:12px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.grid label{font-size:12px;font-weight:900;color:#334155}
.grid input{width:100%;box-sizing:border-box;margin-top:4px}
.tablewrap{overflow:auto;max-height:62vh;border:1px solid #d9e7f7;border-radius:16px;background:white}
table{border-collapse:collapse;width:100%;min-width:2100px}
th,td{padding:9px;border-bottom:1px solid #e2e8f0;font-size:13px;vertical-align:top}
th{position:sticky;top:0;background:#eaf2ff;color:#1e3a8a;text-align:left;z-index:1}
td.action{position:sticky;left:0;background:white;z-index:1;min-width:95px}
th.action{position:sticky;left:0;z-index:2}
</style>
</head>
<body>
<div class="layout">
<aside class="side">
  <div class="brand"><div class="logo">SK</div><div><b>Sagar Kerhalkar</b><br><small>System Health Monitor</small></div></div>
  <nav class="nav">
    <a href="/">Command Center</a>
    <a href="/">Machine Fleet</a>
    <a href="/">Machine 360</a>
    <a href="/">Network + VPN</a>
    <a href="/">Hardware</a>
    <a href="/">Software</a>
    <a class="active" href="/hw-inventory-v2">H/W Inventory</a>
    <a href="/">Deploy</a>
    <a href="/">Settings</a>
  </nav>
</aside>
<main class="main">
  <div class="hero">
    <h1>H/W Inventory</h1>
    <div class="sub">Merged inventory view with category, room, person, vendor and status filters.</div>
  </div>
  <div class="cards" id="cards"></div>
  <div class="panel">
    <div class="toolbar">
      <input id="q" class="search" placeholder="Search serial, tag, model, make, vendor, person, room...">
      <select id="category"><option value="">Category</option></select>
      <select id="room"><option value="">Room</option></select>
      <select id="person"><option value="">Person</option></select>
      <select id="vendor"><option value="">Vendor</option></select>
      <select id="status"><option value="">Status</option></select>
      <button onclick="loadRows()">Search</button>
      <button class="green" onclick="openForm({})">Add New Asset</button>
      <button class="dark" onclick="syncLive()">Sync With Live Data</button>
      <a class="btn dark" id="csvBtn" href="/api/hw-inventory-v2/export.csv">Download CSV</a>
      <a class="btn dark" href="/">Back Dashboard</a>
    </div>
    <div class="form" id="form">
      <h3 id="formTitle">Edit Asset</h3>
      <div class="grid" id="formgrid"></div>
      <div class="toolbar"><button class="green" onclick="saveForm()">Save</button><button class="dark" onclick="closeForm()">Cancel</button></div>
    </div>
    <div class="tablewrap">
      <table><thead><tr id="thead"></tr></thead><tbody id="tbody"></tbody></table>
    </div>
  </div>
</main>
</div>
<script>
const API="/api/hw-inventory-v2";
const COLS=[
["Asset UID","asset_uid"],["Asset Code","asset_code"],["Make Name","make_name"],["Model Name","model_name"],
["Asset Name","asset_name"],["Category","asset_type"],["Details","configuration_details"],["Qty","quantity"],
["Vendor","vendor_name"],["Warranty End","warranty_end_date"],["Warranty Year","warranty_end_year"],
["Purchase Date","purchase_date"],["Bill/PO No","po_invoice_bill_no"],["Bill Path","po_invoice_bill_path"],
["Tag/Hostname","tagname_hostname"],["Serial","serial_number"],["Person","assigned_to"],["Room","asset_location"],
["Status","status"],["Remarks","remarks"],["Live Sync","live_sync_status"],["Live Host","live_hostname"],["Live IP","live_ip"]
];
const EDIT=["asset_uid","asset_code","make_name","model_name","asset_name","asset_type","configuration_details","quantity","rate","vendor_name","warranty_end_date","warranty_end_year","purchase_date","po_invoice_bill_no","po_invoice_bill_path","tagname_hostname","serial_number","assigned_to","asset_location","status","remarks"];
let rows=[];
function esc(x){return String(x??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[m]))}
async function api(u,o){let r=await fetch(u,o);if(!r.ok)throw new Error(await r.text());return r.json()}
function opt(id,arr){let el=document.getElementById(id);let first=el.options[0].textContent;el.innerHTML='<option value="">'+first+'</option>'+(arr||[]).map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join("")}
function card(k,v){return '<div class="card"><div class="k">'+esc(k)+'</div><div class="v">'+esc(v)+'</div></div>'}
async function loadSummary(){let s=await api(API+"/summary");cards.innerHTML=card("Assets",s.assets)+card("Missing Vendor",s.missing_vendor)+card("Missing Make",s.missing_make)+card("Missing Serial",s.missing_serial)+card("Missing Tag/Host",s.missing_tag)+card("Missing Person",s.missing_person)+card("Missing Room",s.missing_room)+card("Missing Bill/PO",s.missing_bill);opt("category",s.categories);opt("room",s.rooms);opt("person",s.persons);opt("vendor",s.vendors);opt("status",s.statuses)}
function qs(){let p=new URLSearchParams();["q","category","room","person","vendor","status"].forEach(id=>{let v=document.getElementById(id).value;if(v)p.set(id,v)});return p.toString()}
async function loadRows(){let q=qs();csvBtn.href=API+"/export.csv"+(q?"?"+q:"");let j=await api(API+"/assets"+(q?"?"+q:""));rows=j.rows||[];thead.innerHTML='<th class="action">Action</th>'+COLS.map(c=>'<th>'+esc(c[0])+'</th>').join("");tbody.innerHTML=rows.map((r,i)=>'<tr><td class="action"><button onclick="editRow('+i+')">Edit</button><br><button class="red" onclick="delRow('+i+')">Delete</button></td>'+COLS.map(c=>'<td>'+esc(r[c[1]]||"")+'</td>').join("")+'</tr>').join("")||'<tr><td>No rows</td></tr>'}
function openForm(r){form.style.display="block";formTitle.textContent=r.asset_uid?"Edit Asset":"Add Asset";formgrid.innerHTML=EDIT.map(k=>'<label>'+esc(k.replaceAll("_"," ").toUpperCase())+'<input id="f_'+k+'" value="'+esc(r[k]||"")+'"></label>').join("");window.current=r;form.scrollIntoView({behavior:"smooth"})}
function closeForm(){form.style.display="none";window.current=null}
function editRow(i){openForm(rows[i])}
async function saveForm(){let r={};EDIT.forEach(k=>r[k]=document.getElementById("f_"+k).value);await api(API+"/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(r)});closeForm();await loadSummary();await loadRows()}
async function delRow(i){if(!confirm("Delete this asset?"))return;await api(API+"/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({asset_uid:rows[i].asset_uid})});await loadSummary();await loadRows()}
async function syncLive(){let j=await api(API+"/sync-save",{method:"POST"});alert("Sync done. matched="+j.matched+" / rows="+j.rows);await loadSummary();await loadRows()}
loadSummary().then(loadRows).catch(e=>document.body.innerHTML='<pre style="padding:20px;color:red">'+esc(e.message)+'</pre>');
</script>
</body>
</html>"""

def install(Handler, base_dir, load_latest_func):
    global DATA_FILE, LOAD_LATEST, OLD_GET, OLD_POST
    DATA_FILE = Path(base_dir) / "data" / "fresh_hw_inventory_v2.json"
    LOAD_LATEST = load_latest_func
    OLD_GET = Handler.do_GET
    OLD_POST = getattr(Handler, "do_POST", None)

    def do_GET(h):
        try:
            u = urllib.parse.urlparse(h.path)
            path = u.path.rstrip("/") or "/"
            qs = urllib.parse.parse_qs(u.query)

            if path in ["/hw-inventory-v2", "/inventory-manager"]:
                return send_bytes(h, html().encode("utf-8"), "text/html; charset=utf-8")

            if path == "/api/hw-inventory-v2/summary":
                return send_json(h, summary())

            if path == "/api/hw-inventory-v2/assets":
                rows = filtered(qs)
                return send_json(h, {"ok": True, "count": len(rows), "rows": rows})

            if path == "/api/hw-inventory-v2/export.csv":
                return send_bytes(h, csv_bytes(filtered(qs)), "text/csv; charset=utf-8", "hw_inventory.csv")

            return OLD_GET(h)
        except Exception as e:
            return send_json(h, {"ok": False, "error": str(e)}, 500)

    def do_POST(h):
        try:
            u = urllib.parse.urlparse(h.path)
            path = u.path.rstrip("/") or "/"

            if path == "/api/hw-inventory-v2/save":
                row = norm(body_json(h))
                rows = load_rows()
                rid = s(row.get("asset_uid"))
                out, found = [], False
                for r in rows:
                    if s(r.get("asset_uid")) == rid:
                        out.append(row); found = True
                    else:
                        out.append(r)
                if not found:
                    out.append(row)
                write_rows(out)
                return send_json(h, {"ok": True, "rows": len(out), "saved": row})

            if path == "/api/hw-inventory-v2/delete":
                req = body_json(h)
                rid = s(req.get("asset_uid"))
                rows = [r for r in load_rows() if s(r.get("asset_uid")) != rid]
                write_rows(rows)
                return send_json(h, {"ok": True, "deleted": rid, "rows": len(rows)})

            if path == "/api/hw-inventory-v2/sync-save":
                total, matched = sync_live()
                return send_json(h, {"ok": True, "rows": total, "matched": matched})

            if OLD_POST:
                return OLD_POST(h)
            return send_json(h, {"ok": False, "error": "not_found"}, 404)
        except Exception as e:
            return send_json(h, {"ok": False, "error": str(e)}, 500)

    Handler.do_GET = do_GET
    Handler.do_POST = do_POST