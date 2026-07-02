from pathlib import Path

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

addon = r'''

# ================= V10 IMPORTED ISO INVENTORY UI =================
# Correct source: imported Nexttoppers hardware inventory + ISO/ITAM register.
# No client change. No Ubuntu change. No live 2278 change.

import io as _iso_io
import csv as _iso_csv
import zipfile as _iso_zipfile
from collections import Counter as _iso_Counter

ISO_IMPORTED_INVENTORY_PATH = Path(BASE_DIR) / "data" / "inventory_assets.json"
ISO_SOFTWARE_REGISTER_PATH = Path(BASE_DIR) / "data" / "software_asset_register_2294.json"

def _iso_clean(v):
    if v is None:
        return ""
    return str(v).strip()

def _iso_num(v, default=0.0):
    try:
        s = _iso_clean(v).replace(",", "")
        if not s:
            return default
        return float(s)
    except Exception:
        return default

def _iso_qty(r):
    q = int(_iso_num(r.get("quantity") or 1, 1))
    return q if q > 0 else 1

def _iso_load_json(path, default):
    try:
        if Path(path).exists():
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            return data if isinstance(data, list) else default
    except Exception:
        pass
    return default

def _iso_write_json(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    Path(tmp).write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    Path(tmp).replace(path)

def _iso_pick(r, *keys):
    if not isinstance(r, dict):
        return ""
    for k in keys:
        if k in r and _iso_clean(r.get(k)):
            return _iso_clean(r.get(k))
    loose = {re.sub(r"[^a-z0-9]", "", str(k).lower()): k for k in r.keys()}
    for k in keys:
        kk = re.sub(r"[^a-z0-9]", "", str(k).lower())
        if kk in loose and _iso_clean(r.get(loose[kk])):
            return _iso_clean(r.get(loose[kk]))
    return ""

def _iso_assets_raw():
    return _iso_load_json(ISO_IMPORTED_INVENTORY_PATH, [])

def _iso_sw_raw():
    return _iso_load_json(ISO_SOFTWARE_REGISTER_PATH, [])

def _iso_is_summary_row(r):
    txt = " ".join([
        _iso_pick(r, "asset_name", "asset_type", "category", "source_sheet", "record_type"),
        _iso_pick(r, "asset_code", "hostname_or_tag")
    ]).lower()
    bad = ["company total", "count summary", "total assets details", "sheet reference", "assets sheets details"]
    return any(x in txt for x in bad)

def _iso_asset_row(r):
    out = dict(r or {})
    out["asset_code"] = _iso_pick(out, "asset_code", "Code", "Tag Name", "tag_name", "id", "asset_uid")
    out["asset_name"] = _iso_pick(out, "asset_name", "Name", "Assets Name", "asset_type", "asset_type_raw") or _iso_pick(out, "asset_type")
    out["category"] = _iso_pick(out, "category", "Asset Type", "Assets Type", "asset_type")
    out["model_or_config"] = _iso_pick(out, "model_or_config", "Configuration", "Details", "Laptop Model")
    out["quantity"] = _iso_pick(out, "quantity", "Quantity") or "1"
    out["rate"] = _iso_pick(out, "rate", "Rate")
    out["serial_number"] = _iso_pick(out, "serial_number", "SerialNumber", "Serial Number", "Sr. No", "Sr. No.")
    out["hostname_or_tag"] = _iso_pick(out, "hostname_or_tag", "Host Name", "Tag Name", "device_name")
    out["employee_name"] = _iso_pick(out, "employee_name", "assigned_user", "Person Name", "Employee Name", "Custodian", "Owner")
    out["asset_location"] = _iso_pick(out, "asset_location", "location_room", "Room No", "Hall", "Location", "source_sheet")
    out["vendor"] = _iso_pick(out, "vendor", "Vendor", "VendorName", "Company Name")
    out["purchase_date"] = _iso_pick(out, "purchase_date", "PurchaseDate")
    out["warranty_date"] = _iso_pick(out, "warranty_date", "WarrantyDate")
    out["Bill/Invoice/PO No"] = _iso_pick(out, "Bill/Invoice/PO No", "bill_invoice_po_no", "PO No", "Bill No", "Invoice No")
    out["bill_link"] = _iso_pick(out, "bill_link", "proof_link", "bill_photo", "photo_link")
    out["lifecycle_status"] = _iso_pick(out, "lifecycle_status", "status", "Status") or "Review"
    out["asset_condition"] = _iso_pick(out, "asset_condition", "condition") or "Needs Check"
    out["remark"] = _iso_pick(out, "remark", "Remark", "remarks")
    out["source_sheet"] = _iso_pick(out, "source_sheet")
    out["source_row"] = _iso_pick(out, "source_row")
    out["id"] = _iso_pick(out, "id", "asset_uid", "asset_code") or ("ISO-" + hashlib.sha1(json.dumps(out, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:10].upper())
    return out

def _iso_assets():
    rows = [_iso_asset_row(r) for r in _iso_assets_raw()]
    return [r for r in rows if not _iso_is_summary_row(r)]

def _iso_live_machines():
    try:
        return load_latest()
    except Exception:
        return []

def _iso_machine_tokens(m):
    p = m.get("payload") if isinstance(m, dict) else {}
    vals = [
        m.get("hostname"), m.get("machine_id"), m.get("real_machine_id"),
        m.get("primary_ip"), m.get("public_ip")
    ]
    if isinstance(p, dict):
        ident = p.get("identity") if isinstance(p.get("identity"), dict) else {}
        vals += [ident.get("hostname"), ident.get("serial"), ident.get("uuid"), ident.get("machine_uuid")]
    return set([_iso_clean(x).lower() for x in vals if _iso_clean(x)])

def _iso_sync_rows():
    machines = _iso_live_machines()
    machine_tokens = []
    for m in machines:
        machine_tokens.append((m, _iso_machine_tokens(m)))

    rows = []
    for a in _iso_assets():
        search_tokens = set()
        for k in ["serial_number", "hostname_or_tag", "asset_code"]:
            v = _iso_clean(a.get(k)).lower()
            if v:
                search_tokens.add(v)

        match = None
        by = ""
        for m, toks in machine_tokens:
            common = search_tokens.intersection(toks)
            if common:
                match = m
                by = ", ".join(sorted(common))
                break

        x = dict(a)
        if match:
            x["live_match_status"] = "matched"
            x["live_match_by"] = by
            x["live_hostname"] = match.get("hostname", "")
            x["live_machine_id"] = match.get("machine_id", "")
            x["live_primary_ip"] = match.get("primary_ip", "")
            x["live_online"] = match.get("online", "")
            x["live_last_seen"] = match.get("updated_at", "")
        else:
            x["live_match_status"] = "not_matched"
            x["live_match_by"] = ""
            x["live_hostname"] = ""
            x["live_machine_id"] = ""
            x["live_primary_ip"] = ""
            x["live_online"] = ""
            x["live_last_seen"] = ""
        rows.append(x)
    return rows

def _iso_summary():
    rows = _iso_sync_rows()
    qty = sum(_iso_qty(r) for r in rows)
    value = sum(_iso_qty(r) * _iso_num(r.get("rate"), 0) for r in rows)
    matched = [r for r in rows if r.get("live_match_status") == "matched"]
    missing_owner = sum(_iso_qty(r) for r in rows if not _iso_clean(r.get("employee_name")))
    missing_location = sum(_iso_qty(r) for r in rows if not _iso_clean(r.get("asset_location")))
    missing_serial = sum(_iso_qty(r) for r in rows if not _iso_clean(r.get("serial_number")))
    missing_bill = sum(_iso_qty(r) for r in rows if not _iso_clean(r.get("Bill/Invoice/PO No")) and not _iso_clean(r.get("bill_link")))

    keys = []
    for r in rows:
        for k in ["serial_number", "hostname_or_tag", "asset_code"]:
            v = _iso_clean(r.get(k)).lower()
            if v:
                keys.append(k + ":" + v)
                break
    dup_groups = sum(1 for k,v in _iso_Counter(keys).items() if v > 1)

    return {
        "ok": True,
        "source_file": str(ISO_IMPORTED_INVENTORY_PATH),
        "software_register_file": str(ISO_SOFTWARE_REGISTER_PATH),
        "imported_assets": len(rows),
        "total_quantity": qty,
        "total_value": round(value, 2),
        "live_machines": len(_iso_live_machines()),
        "live_matched_assets": len(matched),
        "live_not_matched_assets": len(rows) - len(matched),
        "software_license_rows": len(_iso_sw_raw()),
        "missing_owner_qty": missing_owner,
        "missing_location_qty": missing_location,
        "missing_serial_qty": missing_serial,
        "missing_bill_or_proof_qty": missing_bill,
        "duplicate_groups": dup_groups,
        "categories": dict(_iso_Counter([_iso_clean(r.get("category")) or "Uncategorized" for r in rows]).most_common(20)),
        "locations": dict(_iso_Counter([_iso_clean(r.get("asset_location")) or "Missing Location" for r in rows]).most_common(20)),
        "statuses": dict(_iso_Counter([_iso_clean(r.get("lifecycle_status")) or "Review" for r in rows]).most_common(20)),
        "note": "Imported ISO/ITAM inventory from yesterday source. Live client data is used only for sync check."
    }

def _iso_filter(rows, qs):
    q = _iso_clean((qs.get("q") or [""])[0]).lower()
    category = _iso_clean((qs.get("category") or [""])[0]).lower()
    location = _iso_clean((qs.get("location") or [""])[0]).lower()
    status = _iso_clean((qs.get("status") or [""])[0]).lower()
    out = []
    for r in rows:
        txt = json.dumps(r, ensure_ascii=False, default=str).lower()
        if q and q not in txt: continue
        if category and category not in _iso_clean(r.get("category")).lower(): continue
        if location and location not in _iso_clean(r.get("asset_location")).lower(): continue
        if status and status not in _iso_clean(r.get("lifecycle_status")).lower(): continue
        out.append(r)
    return out

def _iso_csv_bytes(rows):
    buf = _iso_io.StringIO()
    fields = []
    for r in rows:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    if not fields:
        fields = ["empty"]
    w = _iso_csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8-sig")

def _iso_download(self, rows, filename):
    body = _iso_csv_bytes(rows)
    return self._send(200, body, "text/csv; charset=utf-8", {"Content-Disposition": f'attachment; filename="{filename}"'})

def _iso_gap_rows():
    out = []
    for r in _iso_sync_rows():
        issues = []
        if not _iso_clean(r.get("employee_name")): issues.append("Missing owner/custodian")
        if not _iso_clean(r.get("asset_location")): issues.append("Missing location")
        if not _iso_clean(r.get("serial_number")) and not _iso_clean(r.get("hostname_or_tag")): issues.append("Missing serial/hostname identity")
        if not _iso_clean(r.get("Bill/Invoice/PO No")) and not _iso_clean(r.get("bill_link")): issues.append("Missing bill/proof")
        if r.get("live_match_status") != "matched": issues.append("Not matched with live monitor client")
        for issue in issues:
            x = dict(r)
            x["audit_issue"] = issue
            out.append(x)
    return out

def _iso_sw_normalize(r):
    out = dict(r or {})
    out["id"] = _iso_pick(out, "id") or ("SWA-" + hashlib.sha1(json.dumps(out, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:10].upper())
    out["product_name"] = _iso_pick(out, "product_name", "software_name")
    out["vendor"] = _iso_pick(out, "vendor", "publisher")
    out["license_type"] = _iso_pick(out, "license_type") or "Review"
    out["license_count"] = _iso_pick(out, "license_count", "seats") or "1"
    out["assigned_to_employee"] = _iso_pick(out, "assigned_to_employee", "employee_name")
    out["assigned_to_machine"] = _iso_pick(out, "assigned_to_machine", "hostname")
    out["login_username"] = _iso_pick(out, "login_username", "username", "account")
    out["password_vault_ref"] = _iso_pick(out, "password_vault_ref", "password_ref")
    out["Bill/Invoice/PO No"] = _iso_pick(out, "Bill/Invoice/PO No", "bill_invoice_po_no", "po_no", "bill_no", "invoice_no")
    out["bill_link"] = _iso_pick(out, "bill_link", "proof_link")
    out["renewal_date"] = _iso_pick(out, "renewal_date", "expiry_date")
    out["lifecycle_status"] = _iso_pick(out, "lifecycle_status", "status") or "Active"
    out["remarks"] = _iso_pick(out, "remarks", "remark")
    return out

def _iso_mapping_rows():
    return [
        {"standard":"ISO/IEC 27001", "area":"Asset inventory", "evidence":"Asset code, owner, location, lifecycle, live monitor sync", "status":"Evidence supported"},
        {"standard":"ISO/IEC 19770", "area":"IT asset management", "evidence":"Hardware register, software license register, bill/proof fields", "status":"Evidence supported"},
        {"standard":"Finance audit", "area":"Fixed asset register", "evidence":"Rate, quantity, total value, vendor, purchase/warranty, Bill/Invoice/PO No", "status":"Evidence supported"},
        {"standard":"Internal IT audit", "area":"Gaps and action list", "evidence":"Missing owner/location/serial/bill/live-sync checks", "status":"Evidence supported"},
    ]

def _iso_audit_pack(self):
    buf = _iso_io.BytesIO()
    with _iso_zipfile.ZipFile(buf, "w", compression=_iso_zipfile.ZIP_DEFLATED) as z:
        z.writestr("00_CEO_SUMMARY.json", json.dumps(_iso_summary(), indent=2, ensure_ascii=False, default=str))
        z.writestr("01_FULL_ITAM_REGISTER.csv", _iso_csv_bytes(_iso_assets()))
        z.writestr("02_FINANCE_FIXED_ASSET_REGISTER.csv", _iso_csv_bytes(_iso_assets()))
        z.writestr("03_LIVE_CLIENT_SYNC_REGISTER.csv", _iso_csv_bytes(_iso_sync_rows()))
        z.writestr("04_AUDIT_GAPS_AND_ACTIONS.csv", _iso_csv_bytes(_iso_gap_rows()))
        z.writestr("05_SOFTWARE_LICENSE_REGISTER.csv", _iso_csv_bytes([_iso_sw_normalize(r) for r in _iso_sw_raw()]))
        z.writestr("06_ISO_EVIDENCE_MAPPING.csv", _iso_csv_bytes(_iso_mapping_rows()))
        z.writestr("README.txt", "This is ISO/ITAM/finance evidence support, not ISO certification. Final audit depends on real proof, policy, approval and auditor decision.")
    data = buf.getvalue()
    return self._send(200, data, "application/zip", {"Content-Disposition": 'attachment; filename="ISO_ITAM_AUDIT_PACK.zip"'})

def _iso_html():
    return r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ISO ITAM Inventory</title>
<style>
body{margin:0;font-family:Inter,Segoe UI,Arial;background:#0b1020;color:#eaf0ff}
header{padding:18px 22px;background:linear-gradient(135deg,#111b3d,#152b57);position:sticky;top:0;z-index:5}
h1{margin:0;font-size:22px}.sub{color:#aab7d4;font-size:13px}
.wrap{padding:18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.card{background:#121b34;border:1px solid #24365f;border-radius:16px;padding:14px;box-shadow:0 10px 30px #0005}
.k{font-size:12px;color:#99a9c9}.v{font-size:24px;font-weight:800;margin-top:5px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.tabs button,.btn{background:#2563eb;color:white;border:0;border-radius:12px;padding:10px 13px;cursor:pointer}.tabs button.alt,.btn.alt{background:#334155}
input,select{background:#0f172a;color:#eaf0ff;border:1px solid #334155;border-radius:10px;padding:10px;margin:4px}
table{width:100%;border-collapse:collapse;background:#10182f;border-radius:14px;overflow:hidden}th,td{padding:9px;border-bottom:1px solid #22314f;font-size:13px;vertical-align:top}th{background:#172447;color:#bcd0ff;text-align:left}
.bad{color:#fb7185}.good{color:#4ade80}.warn{color:#facc15}.mono{font-family:Consolas,monospace}
</style></head><body>
<header><h1>ISO / ITAM Imported Inventory</h1><div class="sub">Imported H/W inventory + software license register + ISO evidence downloads. V10 test only.</div></header>
<div class="wrap">
<div id="cards" class="grid"></div>
<div class="tabs">
<button onclick="show('assets')">Hardware Asset Register</button>
<button onclick="show('sync')">Live Sync</button>
<button onclick="show('gaps')">Audit Gaps</button>
<button onclick="show('software')">Software License Register</button>
<button onclick="show('downloads')">Downloads</button>
<button onclick="show('iso')">ISO Mapping</button>
<a class="btn alt" href="/">Back Dashboard</a>
</div>
<div><input id="q" placeholder="Search asset / serial / employee / room" style="width:360px;max-width:90%"><button class="btn" onclick="loadAll()">Search</button></div>
<section id="assets"></section><section id="sync" style="display:none"></section><section id="gaps" style="display:none"></section><section id="software" style="display:none"></section><section id="downloads" style="display:none"></section><section id="iso" style="display:none"></section>
</div>
<script>
let S={};
function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function api(u,opt){let r=await fetch(u,opt); if(!r.ok) throw new Error(await r.text()); return r.json()}
function show(id){for(let s of document.querySelectorAll('section'))s.style.display='none';document.getElementById(id).style.display='block'}
function table(rows,cols){return `<table><thead><tr>${cols.map(c=>`<th>${esc(c[0])}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${esc(r[c[1]]??'')}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${cols.length}">No rows</td></tr>`}</tbody></table>`}
async function loadAll(){
 const q=encodeURIComponent(document.getElementById('q').value||'');
 S=await api('/api/iso-inventory/summary');
 document.getElementById('cards').innerHTML=[
 ['Imported Assets',S.imported_assets],['Total Qty',S.total_quantity],['Value',S.total_value],['Live Matched',S.live_matched_assets],
 ['Missing Owner Qty',S.missing_owner_qty],['Missing Location Qty',S.missing_location_qty],['Missing Bill/Proof Qty',S.missing_bill_or_proof_qty],['Software Licenses',S.software_license_rows]
 ].map(x=>`<div class="card"><div class="k">${x[0]}</div><div class="v">${esc(x[1])}</div></div>`).join('');
 let a=await api('/api/iso-inventory/assets?q='+q);
 document.getElementById('assets').innerHTML='<h2>Hardware Asset Register</h2>'+table(a.rows,['Asset Code,asset_code'.split(','),'Name,asset_name'.split(','),'Category,category'.split(','),'Qty,quantity'.split(','),'Serial,serial_number'.split(','),'Host/Tag,hostname_or_tag'.split(','),'Employee,employee_name'.split(','),'Location,asset_location'.split(','),'Status,lifecycle_status'.split(','),'Vendor,vendor'.split(','),'Bill/PO,Bill/Invoice/PO No'.split(',')]);
 let sync=await api('/api/iso-inventory/live-sync?q='+q);
 document.getElementById('sync').innerHTML='<h2>Live Client Sync</h2>'+table(sync.rows,['Asset,asset_code'.split(','),'Name,asset_name'.split(','),'Serial,serial_number'.split(','),'Host/Tag,hostname_or_tag'.split(','),'Match,live_match_status'.split(','),'By,live_match_by'.split(','),'Live Host,live_hostname'.split(','),'Machine ID,live_machine_id'.split(','),'IP,live_primary_ip'.split(','),'Online,live_online'.split(',')]);
 let gaps=await api('/api/iso-inventory/gaps?q='+q);
 document.getElementById('gaps').innerHTML='<h2>Audit Gaps & Actions</h2>'+table(gaps.rows,['Issue,audit_issue'.split(','),'Asset,asset_code'.split(','),'Name,asset_name'.split(','),'Category,category'.split(','),'Employee,employee_name'.split(','),'Location,asset_location'.split(','),'Serial,serial_number'.split(','),'Bill/PO,Bill/Invoice/PO No'.split(','),'Live Match,live_match_status'.split(',')]);
 let sw=await api('/api/iso-inventory/software-register');
 document.getElementById('software').innerHTML='<h2>Software / License Register</h2><p class="sub">Passwords are vault/reference only, not plaintext export.</p>'+table(sw.rows,['Product,product_name'.split(','),'Vendor,vendor'.split(','),'License,license_type'.split(','),'Seats,license_count'.split(','),'Employee,assigned_to_employee'.split(','),'Machine,assigned_to_machine'.split(','),'Username,login_username'.split(','),'Vault Ref,password_vault_ref'.split(','),'Bill/PO,Bill/Invoice/PO No'.split(','),'Renewal,renewal_date'.split(',')]);
 document.getElementById('downloads').innerHTML='<h2>Downloads</h2><p><a class="btn" href="/api/iso-inventory/download/audit-pack.zip">Full ZIP Audit Pack</a> <a class="btn alt" href="/api/iso-inventory/download/assets.csv">Full ITAM CSV</a> <a class="btn alt" href="/api/iso-inventory/download/live-sync.csv">Live Sync CSV</a> <a class="btn alt" href="/api/iso-inventory/download/gaps.csv">Audit Gaps CSV</a> <a class="btn alt" href="/api/iso-inventory/download/software.csv">Software License CSV</a></p>';
 let iso=await api('/api/iso-inventory/iso-mapping');
 document.getElementById('iso').innerHTML='<h2>ISO Evidence Mapping</h2>'+table(iso.rows,['Standard,standard'.split(','),'Area,area'.split(','),'Evidence,evidence'.split(','),'Status,status'.split(',')]);
}
loadAll().catch(e=>document.body.innerHTML='<pre>'+esc(e.message)+'</pre>');
</script></body></html>'''

_iso_old_get = Handler.do_GET
_iso_old_post = Handler.do_POST

def _iso_do_GET(self):
    path = self.path.split("?", 1)[0]
    qs = {}
    if "?" in self.path:
        from urllib.parse import parse_qs
        qs = parse_qs(self.path.split("?", 1)[1])

    try:
        if path == "/iso-inventory":
            return self._send(200, _iso_html().encode("utf-8"), "text/html; charset=utf-8")

        if path.startswith("/api/iso-inventory"):
            if hasattr(self, "require_auth") and not self.require_auth(path, "GET"):
                return

            if path == "/api/iso-inventory/summary":
                return self.send_json(_iso_summary())
            if path == "/api/iso-inventory/assets":
                rows = _iso_filter(_iso_assets(), qs)
                return self.send_json({"ok": True, "count": len(rows), "rows": rows})
            if path == "/api/iso-inventory/live-sync":
                rows = _iso_filter(_iso_sync_rows(), qs)
                return self.send_json({"ok": True, "count": len(rows), "rows": rows})
            if path == "/api/iso-inventory/gaps":
                rows = _iso_filter(_iso_gap_rows(), qs)
                return self.send_json({"ok": True, "count": len(rows), "rows": rows})
            if path == "/api/iso-inventory/software-register":
                rows = [_iso_sw_normalize(r) for r in _iso_sw_raw()]
                return self.send_json({"ok": True, "count": len(rows), "rows": rows})
            if path == "/api/iso-inventory/iso-mapping":
                return self.send_json({"ok": True, "rows": _iso_mapping_rows()})

            if path == "/api/iso-inventory/download/audit-pack.zip":
                return _iso_audit_pack(self)
            if path == "/api/iso-inventory/download/assets.csv":
                return _iso_download(self, _iso_assets(), "01_FULL_ITAM_REGISTER.csv")
            if path == "/api/iso-inventory/download/live-sync.csv":
                return _iso_download(self, _iso_sync_rows(), "03_LIVE_CLIENT_SYNC_REGISTER.csv")
            if path == "/api/iso-inventory/download/gaps.csv":
                return _iso_download(self, _iso_gap_rows(), "04_AUDIT_GAPS_AND_ACTIONS.csv")
            if path == "/api/iso-inventory/download/software.csv":
                return _iso_download(self, [_iso_sw_normalize(r) for r in _iso_sw_raw()], "05_SOFTWARE_LICENSE_REGISTER.csv")

        return _iso_old_get(self)
    except Exception as e:
        return self.send_json({"ok": False, "error": str(e)}, 500)

def _iso_do_POST(self):
    path = self.path.split("?", 1)[0]
    try:
        if path == "/api/iso-inventory/assets/save":
            if hasattr(self, "require_auth") and not self.require_auth(path, "POST"):
                return
            body = self.read_json()
            row = _iso_asset_row(body)
            rows = _iso_assets_raw()
            rid = _iso_clean(row.get("id"))
            found = False
            out = []
            for r in rows:
                rr = _iso_asset_row(r)
                if _iso_clean(rr.get("id")) == rid:
                    out.append(row); found = True
                else:
                    out.append(r)
            if not found:
                out.append(row)
            _iso_write_json(ISO_IMPORTED_INVENTORY_PATH, out)
            return self.send_json({"ok": True, "saved": row})

        if path == "/api/iso-inventory/software-register/save":
            if hasattr(self, "require_auth") and not self.require_auth(path, "POST"):
                return
            body = _iso_sw_normalize(self.read_json())
            rows = [_iso_sw_normalize(r) for r in _iso_sw_raw()]
            found = False
            out = []
            for r in rows:
                if _iso_clean(r.get("id")) == _iso_clean(body.get("id")):
                    out.append(body); found = True
                else:
                    out.append(r)
            if not found:
                out.append(body)
            _iso_write_json(ISO_SOFTWARE_REGISTER_PATH, out)
            return self.send_json({"ok": True, "saved": body})

        return _iso_old_post(self)
    except Exception as e:
        return self.send_json({"ok": False, "error": str(e)}, 500)

Handler.do_GET = _iso_do_GET
Handler.do_POST = _iso_do_POST

# ================= END V10 IMPORTED ISO INVENTORY UI =================
'''

if "V10 IMPORTED ISO INVENTORY UI" not in code:
    marker = "def main()"
    if marker not in code:
        raise SystemExit("def main() marker not found")
    code = code.replace(marker, addon + "\n" + marker, 1)

server.write_text(code, encoding="utf-8")
print("Imported ISO inventory UI/API added")