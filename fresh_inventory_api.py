import json, csv, io, hashlib, urllib.parse, re
from pathlib import Path
from collections import Counter

BASE_DIR = None
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
    "live_machine_id","live_ip","liveasset_location","status",
    "remarks","source_sheet","source_row","live_sync_status","live_hostname",
    "live_machine_id","live_ip","live_online","live_last_seen"
]

def s(v):
    return "" if v is None else str(v).strip()

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

def uid(r):
    base = s(r.get("asset_uid") or r.get("serial_number") or r.get("tagname_hostname") or r.get("asset_code"))
    if base:
        return base
    raw = json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)
    return "HW-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()

def norm(r):
    x = dict(r or {})
    mapping = {
        "Code":"asset_code",
        "Name":"asset_name",
        "AssetType":"asset_type",
        "Details":"configuration_details",
        "Quantity":"quantity",
        "Rate":"rate",
        "WarrantyDate":"warranty_end_date",
        "PurchaseDate":"purchase_date",
        "SerialNumber":"serial_number",
        "VendorName":"vendor_name",
        "Vendor Name":"vendor_name",
        "Make Name":"make_name",
        "Model Name":"model_name",
        "PO / Invoice / Bill No":"po_invoice_bill_no",
        "PO / Invoice / Bill Path":"po_invoice_bill_path",
        "Tagname / Hostname":"tagname_hostname",
        "Assigned To":"assigned_to",
        "Location":"asset_location",
        "Status":"status",
        "Remarks":"remarks"
    }
    for old, new in mapping.items():
        if not s(x.get(new)) and s(x.get(old)):
            x[new] = s(x.get(old))

    x["asset_code"] = s(x.get("asset_code") or pick(x, "Code", "Tag Name"))
    x["asset_name"] = s(x.get("asset_name") or pick(x, "Name", "Assets Name", "Item Name") or "Asset")
    x["asset_type"] = s(x.get("asset_type") or pick(x, "AssetType", "Asset Type", "category") or "Uncategorized")
    x["configuration_details"] = s(x.get("configuration_details") or pick(x, "Details", "Configuration"))
    x["vendor_name"] = s(x.get("vendor_name") or pick(x, "VendorName", "Vendor Name", "Vendor"))
    x["serial_number"] = s(x.get("serial_number") or pick(x, "SerialNumber", "Serial Number", "Sr. No", "Sr. No."))
    x["tagname_hostname"] = s(x.get("tagname_hostname") or pick(x, "Tagname / Hostname", "Host Name", "Tag Name"))
    x["assigned_to"] = s(x.get("assigned_to") or pick(x, "Person Name", "Employee Name", "assigned_user", "Owner"))
    x["asset_location"] = s(x.get("asset_location") or pick(x, "Room No", "Hall", "Location", "source_sheet"))
    x["quantity"] = s(x.get("quantity") or "1")
    x["status"] = s(x.get("status") or "Review")
    x["model_name"] = s(x.get("model_name") or x.get("asset_name"))
    x["make_name"] = s(x.get("make_name"))

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
    rows = [norm(r) for r in data if isinstance(r, dict)]

    # duplicate remove by serial -> tag/host -> asset_code -> uid
    seen = set()
    out = []
    for r in rows:
        key = s(r.get("serial_number")).lower() or s(r.get("tagname_hostname")).lower() or s(r.get("asset_code")).lower() or s(r.get("asset_uid")).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def write_rows(rows):
    out = [norm(r) for r in rows if isinstance(r, dict)]
    tmp = Path(DATA_FILE).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(DATA_FILE)

def options(rows):
    def vals(k):
        return sorted(set(s(r.get(k)) for r in rows if s(r.get(k))))
    return {
        "categories": vals("asset_type"),
        "rooms": vals("asset_location"),
        "persons": vals("assigned_to"),
        "vendors": vals("vendor_name"),
        "statuses": vals("status")
    }

def summary():
    rows = load_rows()
    def miss(k):
        return sum(1 for r in rows if not s(r.get(k)))
    return {
        "ok": True,
        "imported_assets": len(rows),
        "missing_make_name": miss("make_name"),
        "missing_model_name": miss("model_name"),
        "missing_vendor_name": miss("vendor_name"),
        "missing_serial_number": miss("serial_number"),
        "missing_tagname_hostname": miss("tagname_hostname"),
        "missing_assigned_to": miss("assigned_to"),
        "missing_location": miss("asset_location"),
        "missing_po_invoice_bill_no": miss("po_invoice_bill_no"),
        "categories_count": dict(Counter([s(r.get("asset_type")) or "Uncategorized" for r in rows]).most_common(30)),
        "source_file": str(DATA_FILE),
        "options": options(rows)
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
    for r in rows:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8-sig")

def body_json(handler):
    n = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(n) if n else b"{}"
    return json.loads(raw.decode("utf-8-sig") or "{}")

def tokens(m):
    vals = []
    if isinstance(m, dict):
        vals += [m.get("hostname"), m.get("machine_id"), m.get("real_machine_id"), m.get("primary_ip"), m.get("public_ip")]
        p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        ident = p.get("identity") if isinstance(p.get("identity"), dict) else {}
        vals += [ident.get("serial"), ident.get("bios_serial"), ident.get("uuid"), ident.get("system_uuid"), ident.get("hostname")]
    return set(s(v).lower() for v in vals if s(v))

def sync_live(save=True):
    rows = load_rows()
    try:
        machines = LOAD_LATEST()
    except Exception:
        machines = []
    mt = [(m, tokens(m)) for m in machines]
    matched = 0
    out = []
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
    if save:
        write_rows(out)
    return out, matched

def send_json(handler, obj, status=200):
    data = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def send_bytes(handler, data, ctype, filename=None):
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(data)))
    if filename:
        handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.end_headers()
    handler.wfile.write(data)

def install(Handler, base_dir, load_latest_func):
    global BASE_DIR, DATA_FILE, LOAD_LATEST, OLD_GET, OLD_POST
    BASE_DIR = Path(base_dir)
    DATA_FILE = BASE_DIR / "data" / "fresh_hw_inventory_v2.json"
    LOAD_LATEST = load_latest_func
    OLD_GET = Handler.do_GET
    OLD_POST = getattr(Handler, "do_POST", None)

    def do_GET(self):
        try:
            u = urllib.parse.urlparse(self.path)
            path = u.path.rstrip("/") or "/"
            qs = urllib.parse.parse_qs(u.query)

            if path == "/api/hw-inventory-main/summary":
                return send_json(self, summary())

            if path == "/api/hw-inventory-main/assets":
                rows = filtered(qs)
                return send_json(self, {"ok": True, "count": len(rows), "rows": rows})

            if path == "/api/hw-inventory-main/export.csv":
                rows = filtered(qs)
                return send_bytes(self, csv_bytes(rows), "text/csv; charset=utf-8", "hw_inventory_main.csv")

            return OLD_GET(self)
        except Exception as e:
            return send_json(self, {"ok": False, "error": str(e)}, 500)

    def do_POST(self):
        try:
            u = urllib.parse.urlparse(self.path)
            path = u.path.rstrip("/") or "/"

            if path == "/api/hw-inventory-main/save":
                row = norm(body_json(self))
                rows = load_rows()
                rid = s(row.get("asset_uid"))
                out = []
                found = False
                for r in rows:
                    if s(r.get("asset_uid")) == rid:
                        out.append(row)
                        found = True
                    else:
                        out.append(r)
                if not found:
                    out.append(row)
                write_rows(out)
                return send_json(self, {"ok": True, "saved": row, "rows": len(out)})

            if path == "/api/hw-inventory-main/delete":
                req = body_json(self)
                rid = s(req.get("asset_uid"))
                rows = [r for r in load_rows() if s(r.get("asset_uid")) != rid]
                write_rows(rows)
                return send_json(self, {"ok": True, "deleted": rid, "rows": len(rows)})

            if path == "/api/hw-inventory-main/sync-save":
                rows, matched = sync_live(save=True)
                return send_json(self, {"ok": True, "rows": len(rows), "matched": matched})

            if path == "/api/hw-inventory-main/dedupe-save":
                rows = load_rows()
                write_rows(rows)
                return send_json(self, {"ok": True, "rows": len(rows)})

            if OLD_POST:
                return OLD_POST(self)
            return send_json(self, {"error": "not_found"}, 404)
        except Exception as e:
            return send_json(self, {"ok": False, "error": str(e)}, 500)

    Handler.do_GET = do_GET
    Handler.do_POST = do_POST