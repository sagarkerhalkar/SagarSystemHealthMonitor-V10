import json, csv, io, zipfile, hashlib, urllib.parse, re, datetime
from pathlib import Path
from collections import Counter

BASE_DIR = None
LOAD_LATEST = None
OLD_GET = None
OLD_POST = None
HW_FILE = None
SW_FILE = None

HW_COLS = [
    "asset_uid","asset_code","make_name","model_name","asset_name","asset_type",
    "configuration_details","quantity","rate","vendor_name","warranty_end_date",
    "warranty_end_year","purchase_date","po_invoice_bill_no","po_invoice_bill_path",
    "tagname_hostname","serial_number","assigned_to","asset_location","status",
    "remarks","source_sheet","source_row","live_sync_status","live_hostname",
    "live_machine_id","live_ip","live_online","live_last_seen"
]

SW_COLS = [
    "license_uid","software_name","vendor_name","publisher","version","license_type",
    "license_count","assigned_to","assigned_machine","login_username","password_vault_ref",
    "license_key_ref","purchase_date","renewal_date","expiry_date","po_invoice_bill_no",
    "po_invoice_bill_path","status","remarks"
]

def s(v):
    return "" if v is None else str(v).strip()

def jload(path):
    try:
        p = Path(path)
        if p.exists():
            x = json.loads(p.read_text(encoding="utf-8-sig"))
            return x if isinstance(x, list) else []
    except Exception:
        return []
    return []

def jwrite(path, rows):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(p)

def pick(d, *keys):
    if not isinstance(d, dict):
        return ""
    loose = {re.sub(r"[^a-z0-9]", "", str(k).lower()): k for k in d.keys()}
    for k in keys:
        if k in d and s(d.get(k)):
            return s(d.get(k))
        kk = re.sub(r"[^a-z0-9]", "", str(k).lower())
        if kk in loose and s(d.get(loose[kk])):
            return s(d.get(loose[kk]))
    return ""

def hw_uid(r):
    base = s(r.get("asset_uid") or r.get("serial_number") or r.get("tagname_hostname") or r.get("asset_code"))
    if base:
        return base
    raw = json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)
    return "HW-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()

def hw_norm(r):
    x = dict(r or {})
    mapping = {
        "Code":"asset_code","Name":"asset_name","AssetType":"asset_type",
        "Details":"configuration_details","Quantity":"quantity","Rate":"rate",
        "WarrantyDate":"warranty_end_date","PurchaseDate":"purchase_date",
        "SerialNumber":"serial_number","VendorName":"vendor_name",
        "Vendor Name":"vendor_name","Make Name":"make_name","Model Name":"model_name",
        "PO / Invoice / Bill No":"po_invoice_bill_no",
        "PO / Invoice / Bill Path":"po_invoice_bill_path",
        "Tagname / Hostname":"tagname_hostname","Assigned To":"assigned_to",
        "Location":"asset_location","Status":"status","Remarks":"remarks"
    }
    for old, new in mapping.items():
        if not s(x.get(new)) and s(x.get(old)):
            x[new] = s(x.get(old))

    x["asset_code"] = s(x.get("asset_code") or pick(x,"Code","Tag Name"))
    x["asset_name"] = s(x.get("asset_name") or pick(x,"Name","Assets Name","Item Name") or "Asset")
    x["asset_type"] = s(x.get("asset_type") or pick(x,"AssetType","Asset Type","category") or "Uncategorized")
    x["configuration_details"] = s(x.get("configuration_details") or pick(x,"Details","Configuration"))
    x["vendor_name"] = s(x.get("vendor_name") or pick(x,"VendorName","Vendor Name","Vendor"))
    x["serial_number"] = s(x.get("serial_number") or pick(x,"SerialNumber","Serial Number","Sr. No","Sr. No."))
    x["tagname_hostname"] = s(x.get("tagname_hostname") or pick(x,"Host Name","Tag Name"))
    x["assigned_to"] = s(x.get("assigned_to") or pick(x,"Person Name","Employee Name","assigned_user","Owner"))
    x["asset_location"] = s(x.get("asset_location") or pick(x,"Room No","Hall","Location","source_sheet"))
    x["quantity"] = s(x.get("quantity") or "1")
    x["status"] = s(x.get("status") or "Review")
    x["model_name"] = s(x.get("model_name") or x.get("asset_name"))
    x["make_name"] = s(x.get("make_name"))

    if not s(x.get("warranty_end_year")) and s(x.get("warranty_end_date")):
        m = re.search(r"(20\d{2}|19\d{2})", s(x.get("warranty_end_date")))
        if m:
            x["warranty_end_year"] = m.group(1)

    x["asset_uid"] = hw_uid(x)
    for c in HW_COLS:
        x.setdefault(c, "")
    return x

def hw_rows():
    rows = [hw_norm(r) for r in jload(HW_FILE) if isinstance(r, dict)]
    seen = set()
    out = []
    for r in rows:
        key = s(r.get("serial_number")).lower() or s(r.get("tagname_hostname")).lower() or s(r.get("asset_code")).lower() or s(r.get("asset_uid")).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def hw_write(rows):
    jwrite(HW_FILE, [hw_norm(r) for r in rows])

def sw_uid(r):
    base = s(r.get("license_uid") or r.get("software_name") + "|" + r.get("assigned_machine") + "|" + r.get("assigned_to"))
    if base and base != "||":
        return base
    raw = json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)
    return "SW-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()

def sw_norm(r):
    x = dict(r or {})
    x["software_name"] = s(x.get("software_name") or x.get("product_name") or x.get("name"))
    x["vendor_name"] = s(x.get("vendor_name") or x.get("vendor") or x.get("publisher"))
    x["publisher"] = s(x.get("publisher") or x.get("vendor_name"))
    x["version"] = s(x.get("version"))
    x["license_type"] = s(x.get("license_type") or "Review")
    x["license_count"] = s(x.get("license_count") or x.get("seats") or "1")
    x["assigned_to"] = s(x.get("assigned_to") or x.get("assigned_to_employee") or x.get("employee_name"))
    x["assigned_machine"] = s(x.get("assigned_machine") or x.get("assigned_to_machine") or x.get("hostname"))
    x["login_username"] = s(x.get("login_username") or x.get("username") or x.get("account"))
    x["password_vault_ref"] = s(x.get("password_vault_ref") or x.get("password_ref"))
    x["license_key_ref"] = s(x.get("license_key_ref") or x.get("license_key") or x.get("serial_key") or x.get("product_key"))
    x["po_invoice_bill_no"] = s(x.get("po_invoice_bill_no") or x.get("Bill/Invoice/PO No") or x.get("bill_invoice_po_no") or x.get("po_no") or x.get("invoice_no"))
    x["po_invoice_bill_path"] = s(x.get("po_invoice_bill_path") or x.get("bill_link") or x.get("proof_link"))
    x["purchase_date"] = s(x.get("purchase_date"))
    x["renewal_date"] = s(x.get("renewal_date"))
    x["expiry_date"] = s(x.get("expiry_date") or x.get("subscription_end"))
    x["status"] = s(x.get("status") or x.get("lifecycle_status") or "Review")
    x["remarks"] = s(x.get("remarks") or x.get("remark"))
    x["license_uid"] = sw_uid(x)
    for c in SW_COLS:
        x.setdefault(c, "")
    return x

def sw_rows():
    return [sw_norm(r) for r in jload(SW_FILE) if isinstance(r, dict)]

def sw_write(rows):
    jwrite(SW_FILE, [sw_norm(r) for r in rows])

def opts(rows, key):
    return sorted(set(s(r.get(key)) for r in rows if s(r.get(key))))

def hw_summary():
    rows = hw_rows()
    def miss(k): return sum(1 for r in rows if not s(r.get(k)))
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
        "categories": opts(rows,"asset_type"),
        "rooms": opts(rows,"asset_location"),
        "persons": opts(rows,"assigned_to"),
        "vendors": opts(rows,"vendor_name"),
        "statuses": opts(rows,"status")
    }

def hw_filter(qs):
    rows = hw_rows()
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

def live_software_rows():
    rows = []
    try:
        machines = LOAD_LATEST()
    except Exception:
        machines = []
    for m in machines:
        p = m.get("payload") if isinstance(m, dict) else {}
        apps = []
        if isinstance(p, dict):
            sw = p.get("software") if isinstance(p.get("software"), dict) else {}
            apps = sw.get("installed") or sw.get("apps") or []
        if not isinstance(apps, list):
            apps = []
        for a in apps:
            if isinstance(a, str):
                a = {"name": a}
            if not isinstance(a, dict):
                continue
            rows.append({
                "hostname": s(m.get("hostname")),
                "machine_id": s(m.get("machine_id")),
                "ip": s(m.get("primary_ip")),
                "os": s(m.get("os")),
                "software_name": s(a.get("name") or a.get("display_name")),
                "publisher": s(a.get("publisher") or a.get("vendor")),
                "version": s(a.get("version")),
                "install_date": s(a.get("install_date") or a.get("installDate")),
                "source": s(a.get("source"))
            })
    return rows

def sw_summary():
    lic = sw_rows()
    live = live_software_rows()
    def miss(rows,k): return sum(1 for r in rows if not s(r.get(k)))
    return {
        "ok": True,
        "license_rows": len(lic),
        "live_software_rows": len(live),
        "missing_license_bill": miss(lic,"po_invoice_bill_no"),
        "missing_assigned_machine": miss(lic,"assigned_machine"),
        "vendors": opts(lic, "vendor_name"),
        "statuses": opts(lic, "status"),
        "machines": sorted(set(s(r.get("hostname")) for r in live if s(r.get("hostname")))),
        "publishers": sorted(set(s(r.get("publisher")) for r in live if s(r.get("publisher"))))[:500]
    }

def sw_license_filter(qs):
    rows = sw_rows()
    q = s((qs.get("q") or [""])[0]).lower()
    vendor = s((qs.get("vendor") or [""])[0]).lower()
    status = s((qs.get("status") or [""])[0]).lower()
    out = []
    for r in rows:
        if vendor and s(r.get("vendor_name")).lower() != vendor: continue
        if status and s(r.get("status")).lower() != status: continue
        if q and q not in json.dumps(r, ensure_ascii=False, default=str).lower(): continue
        out.append(r)
    return out

def live_sw_filter(qs):
    rows = live_software_rows()
    q = s((qs.get("q") or [""])[0]).lower()
    machine = s((qs.get("machine") or [""])[0]).lower()
    publisher = s((qs.get("publisher") or [""])[0]).lower()
    out = []
    for r in rows:
        if machine and s(r.get("hostname")).lower() != machine: continue
        if publisher and s(r.get("publisher")).lower() != publisher: continue
        if q and q not in json.dumps(r, ensure_ascii=False, default=str).lower(): continue
        out.append(r)
    return out

def csv_bytes(rows, cols=None):
    fields = list(cols or [])
    for r in rows:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    if not fields:
        fields = ["empty"]
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

def hw_gap_rows():
    out = []
    for r in hw_rows():
        checks = [
            ("Missing Make Name","make_name"),("Missing Vendor Name","vendor_name"),
            ("Missing Serial Number","serial_number"),("Missing Tagname / Hostname","tagname_hostname"),
            ("Missing Assigned Person","assigned_to"),("Missing Room / Location","asset_location"),
            ("Missing Bill / PO No","po_invoice_bill_no")
        ]
        for issue, key in checks:
            if not s(r.get(key)):
                x = dict(r); x["audit_issue"] = issue; out.append(x)
    return out

def hw_duplicate_rows():
    keys = {}
    for r in hw_rows():
        key = s(r.get("serial_number")).lower() or s(r.get("tagname_hostname")).lower() or s(r.get("asset_code")).lower()
        if not key: continue
        keys.setdefault(key, []).append(r)
    out = []
    for key, group in keys.items():
        if len(group) > 1:
            for r in group:
                x = dict(r); x["duplicate_key"] = key; out.append(x)
    return out

def warranty_rows():
    out = []
    today = datetime.date.today()
    for r in hw_rows():
        y = s(r.get("warranty_end_year"))
        issue = ""
        if not y:
            issue = "Missing warranty end year"
        else:
            try:
                yy = int(y)
                if yy < today.year:
                    issue = "Warranty expired"
                elif yy == today.year:
                    issue = "Warranty ending this year"
            except Exception:
                issue = "Invalid warranty year"
        if issue:
            x = dict(r); x["warranty_issue"] = issue; out.append(x)
    return out

def iso_summary():
    return {
        "ok": True,
        "hardware_assets": len(hw_rows()),
        "software_license_rows": len(sw_rows()),
        "live_software_rows": len(live_software_rows()),
        "hardware_gap_rows": len(hw_gap_rows()),
        "duplicate_rows": len(hw_duplicate_rows()),
        "warranty_issue_rows": len(warranty_rows()),
        "note": "Audit evidence export only; final ISO compliance depends on real proof, policy and auditor."
    }

def audit_pack():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("00_ISO_AUDIT_SUMMARY.json", json.dumps(iso_summary(), indent=2, ensure_ascii=False, default=str))
        z.writestr("01_HW_ASSET_REGISTER.csv", csv_bytes(hw_rows(), HW_COLS))
        z.writestr("02_HW_MISSING_DATA_GAPS.csv", csv_bytes(hw_gap_rows()))
        z.writestr("03_HW_DUPLICATES.csv", csv_bytes(hw_duplicate_rows()))
        z.writestr("04_HW_WARRANTY_REPORT.csv", csv_bytes(warranty_rows()))
        z.writestr("05_SW_LICENSE_REGISTER.csv", csv_bytes(sw_rows(), SW_COLS))
        z.writestr("06_LIVE_INSTALLED_SOFTWARE.csv", csv_bytes(live_software_rows()))
        z.writestr("README.txt", "ISO/ITAM audit evidence pack. This supports H/W and S/W audit review; it is not ISO certification by itself.")
    return buf.getvalue()

def install(Handler, base_dir, load_latest_func):
    global BASE_DIR, LOAD_LATEST, OLD_GET, OLD_POST, HW_FILE, SW_FILE
    BASE_DIR = Path(base_dir)
    LOAD_LATEST = load_latest_func
    HW_FILE = BASE_DIR / "data" / "fresh_hw_inventory_v2.json"
    SW_FILE = BASE_DIR / "data" / "software_asset_register_2294.json"
    if not SW_FILE.exists():
        SW_FILE.write_text("[]", encoding="utf-8")
    OLD_GET = Handler.do_GET
    OLD_POST = getattr(Handler, "do_POST", None)

    def do_GET(h):
        try:
            u = urllib.parse.urlparse(h.path)
            path = u.path.rstrip("/") or "/"
            qs = urllib.parse.parse_qs(u.query)

            if path == "/api/native-inventory/hw/summary": return send_json(h, hw_summary())
            if path == "/api/native-inventory/hw/assets": return send_json(h, {"ok": True, "rows": hw_filter(qs), "count": len(hw_filter(qs))})
            if path == "/api/native-inventory/hw/export.csv": return send_bytes(h, csv_bytes(hw_filter(qs), HW_COLS), "text/csv; charset=utf-8", "HW_ASSET_REGISTER.csv")
            if path == "/api/native-inventory/hw/gaps.csv": return send_bytes(h, csv_bytes(hw_gap_rows()), "text/csv; charset=utf-8", "HW_MISSING_DATA_GAPS.csv")
            if path == "/api/native-inventory/hw/duplicates.csv": return send_bytes(h, csv_bytes(hw_duplicate_rows()), "text/csv; charset=utf-8", "HW_DUPLICATES.csv")
            if path == "/api/native-inventory/hw/warranty.csv": return send_bytes(h, csv_bytes(warranty_rows()), "text/csv; charset=utf-8", "HW_WARRANTY_REPORT.csv")

            if path == "/api/native-inventory/sw/summary": return send_json(h, sw_summary())
            if path == "/api/native-inventory/sw/live": return send_json(h, {"ok": True, "rows": live_sw_filter(qs), "count": len(live_sw_filter(qs))})
            if path == "/api/native-inventory/sw/licenses": return send_json(h, {"ok": True, "rows": sw_license_filter(qs), "count": len(sw_license_filter(qs))})
            if path == "/api/native-inventory/sw/live.csv": return send_bytes(h, csv_bytes(live_sw_filter(qs)), "text/csv; charset=utf-8", "LIVE_INSTALLED_SOFTWARE.csv")
            if path == "/api/native-inventory/sw/licenses.csv": return send_bytes(h, csv_bytes(sw_license_filter(qs), SW_COLS), "text/csv; charset=utf-8", "SW_LICENSE_REGISTER.csv")

            if path == "/api/native-inventory/iso/summary": return send_json(h, iso_summary())
            if path == "/api/native-inventory/iso/audit-pack.zip": return send_bytes(h, audit_pack(), "application/zip", "ISO_ITAM_HW_SW_AUDIT_PACK.zip")

            return OLD_GET(h)
        except Exception as e:
            return send_json(h, {"ok": False, "error": str(e)}, 500)

    def do_POST(h):
        try:
            u = urllib.parse.urlparse(h.path)
            path = u.path.rstrip("/") or "/"

            if path == "/api/native-inventory/hw/save":
                row = hw_norm(body_json(h))
                rows = hw_rows()
                rid = s(row.get("asset_uid"))
                out, found = [], False
                for r in rows:
                    if s(r.get("asset_uid")) == rid:
                        out.append(row); found = True
                    else:
                        out.append(r)
                if not found: out.append(row)
                hw_write(out)
                return send_json(h, {"ok": True, "rows": len(out), "saved": row})

            if path == "/api/native-inventory/hw/delete":
                rid = s(body_json(h).get("asset_uid"))
                rows = [r for r in hw_rows() if s(r.get("asset_uid")) != rid]
                hw_write(rows)
                return send_json(h, {"ok": True, "deleted": rid, "rows": len(rows)})

            if path == "/api/native-inventory/sw/save":
                row = sw_norm(body_json(h))
                rows = sw_rows()
                rid = s(row.get("license_uid"))
                out, found = [], False
                for r in rows:
                    if s(r.get("license_uid")) == rid:
                        out.append(row); found = True
                    else:
                        out.append(r)
                if not found: out.append(row)
                sw_write(out)
                return send_json(h, {"ok": True, "rows": len(out), "saved": row})

            if path == "/api/native-inventory/sw/delete":
                rid = s(body_json(h).get("license_uid"))
                rows = [r for r in sw_rows() if s(r.get("license_uid")) != rid]
                sw_write(rows)
                return send_json(h, {"ok": True, "deleted": rid, "rows": len(rows)})

            if OLD_POST:
                return OLD_POST(h)
            return send_json(h, {"ok": False, "error": "not_found"}, 404)
        except Exception as e:
            return send_json(h, {"ok": False, "error": str(e)}, 500)

    Handler.do_GET = do_GET
    Handler.do_POST = do_POST