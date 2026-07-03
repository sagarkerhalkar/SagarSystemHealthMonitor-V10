#!/usr/bin/env python3
# V10 2-Day Phase 1 DB + API Bridge
# Standard-library only. Does not touch main 2278. Does not overwrite old DB data.
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import sqlite3
import time
import traceback
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Tuple

PHASE_NAME = "V10_2DAY_PHASE1_DB_API_BRIDGE"
PHASE_VERSION = "2026-07-03.1"

HW_COLUMNS = [
    "asset_uid","asset_code","make_name","model_name","asset_name","asset_type",
    "configuration_details","quantity","rate","vendor_name","warranty_end_date",
    "warranty_end_year","purchase_date","po_invoice_bill_no","po_invoice_bill_path",
    "tagname_hostname","serial_number","assigned_to","asset_location","status",
    "remarks","source_sheet","source_row","live_sync_status","live_hostname",
    "live_machine_id","live_ip","live_online","live_last_seen"
]

SW_COLUMNS = [
    "software_uid","machine_id","hostname","software_name","version","publisher",
    "install_date","install_location","license_key","license_type","assigned_to",
    "status","source","remarks","extra_json","created_at","updated_at"
]

def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")

def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()

def _lower(v: Any) -> str:
    return _s(v).lower()

def _json(v: Any) -> str:
    try:
        return json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        return "{}"

def _loads(v: Any, default: Any = None) -> Any:
    if default is None:
        default = {}
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v or "")
    except Exception:
        return default

def _first(*vals: Any) -> str:
    for v in vals:
        x = _s(v)
        if x:
            return x
    return ""

def _float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def _bool_online(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return _lower(v) in ("1","true","yes","online","on")

def _get_nested(d: Any, dotted: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    cur = d
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur.get(part)
        else:
            return default
    return cur

def _listify(v: Any) -> List[Any]:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return [v]
    return []

def _asset_uid(row: Dict[str, Any]) -> str:
    base = _first(row.get("asset_uid"), row.get("asset_code"), row.get("serial_number"), row.get("tagname_hostname"))
    if base:
        return re.sub(r"[^A-Za-z0-9_.:-]+", "-", base)[:120]
    raw = _json(row)
    import hashlib
    return "HW-" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:12].upper()

def _software_uid(row: Dict[str, Any]) -> str:
    base = "|".join([_s(row.get("machine_id")), _s(row.get("hostname")), _s(row.get("software_name")), _s(row.get("version")), _s(row.get("publisher"))])
    if not base.strip("|"):
        base = _json(row)
    import hashlib
    return "SW-" + hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()[:16].upper()

def _norm_hw(row: Dict[str, Any]) -> Dict[str, Any]:
    r = dict(row or {})
    aliases = {
        "Code":"asset_code","Asset Code":"asset_code",
        "Name":"asset_name","Asset Name":"asset_name",
        "AssetType":"asset_type","Asset Type":"asset_type",
        "Details":"configuration_details","Configuration / Details":"configuration_details","Configuration Details":"configuration_details",
        "Quantity":"quantity","Qty":"quantity",
        "Rate":"rate",
        "WarrantyDate":"warranty_end_date","Warranty End Date":"warranty_end_date",
        "Warranty End Year":"warranty_end_year",
        "PurchaseDate":"purchase_date","Purchase Date":"purchase_date",
        "SerialNumber":"serial_number","Serial Number":"serial_number",
        "VendorName":"vendor_name","Vendor Name":"vendor_name",
        "Make Name":"make_name","Make":"make_name",
        "Model Name":"model_name","Model":"model_name",
        "PO / Invoice / Bill No":"po_invoice_bill_no","Invoice No":"po_invoice_bill_no","Bill No":"po_invoice_bill_no",
        "PO / Invoice / Bill Path":"po_invoice_bill_path",
        "Tagname / Hostname":"tagname_hostname","Hostname":"tagname_hostname","Tagname":"tagname_hostname",
        "Assigned To":"assigned_to",
        "Location":"asset_location","Asset Location":"asset_location",
        "Status":"status",
        "Remarks":"remarks",
        "Sheet":"source_sheet","Source Sheet":"source_sheet",
        "Row":"source_row","Source Row":"source_row"
    }
    for old, new in aliases.items():
        if not _s(r.get(new)) and _s(r.get(old)):
            r[new] = _s(r.get(old))
    if not _s(r.get("asset_name")):
        r["asset_name"] = _first(r.get("model_name"), r.get("asset_type"), "Asset")
    if not _s(r.get("asset_type")):
        r["asset_type"] = "Uncategorized"
    if not _s(r.get("quantity")):
        r["quantity"] = "1"
    if not _s(r.get("status")):
        r["status"] = "Review"
    if not _s(r.get("warranty_end_year")) and _s(r.get("warranty_end_date")):
        m = re.search(r"(19\d{2}|20\d{2})", _s(r.get("warranty_end_date")))
        if m:
            r["warranty_end_year"] = m.group(1)
    r["asset_uid"] = _asset_uid(r)
    for c in HW_COLUMNS:
        r.setdefault(c, "")
    return {c: _s(r.get(c)) for c in HW_COLUMNS}

def _norm_sw(row: Dict[str, Any]) -> Dict[str, Any]:
    r = dict(row or {})
    aliases = {
        "name":"software_name","Name":"software_name","DisplayName":"software_name","display_name":"software_name",
        "Software Name":"software_name","app_name":"software_name",
        "Version":"version","DisplayVersion":"version",
        "Publisher":"publisher","vendor":"publisher",
        "InstallDate":"install_date","Install Date":"install_date",
        "InstallLocation":"install_location","Install Location":"install_location",
        "License Key":"license_key","License Type":"license_type",
        "Assigned To":"assigned_to","Status":"status","Remarks":"remarks"
    }
    for old, new in aliases.items():
        if not _s(r.get(new)) and _s(r.get(old)):
            r[new] = _s(r.get(old))
    if not _s(r.get("software_name")):
        r["software_name"] = _first(r.get("name"), r.get("display_name"), "Unknown Software")
    if not _s(r.get("status")):
        r["status"] = "Live" if _s(r.get("machine_id")) else "Review"
    if not _s(r.get("source")):
        r["source"] = "manual"
    r["software_uid"] = _s(r.get("software_uid")) or _software_uid(r)
    now = _now()
    r.setdefault("created_at", now)
    r["updated_at"] = now
    for c in SW_COLUMNS:
        r.setdefault(c, "")
    return {c: _s(r.get(c)) for c in SW_COLUMNS}

def _send_json(handler: Any, obj: Any, status: int = 200) -> None:
    if hasattr(handler, "send_json"):
        return handler.send_json(obj, status)
    body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)

def _read_json(handler: Any) -> Dict[str, Any]:
    if hasattr(handler, "read_json"):
        data = handler.read_json()
        return data if isinstance(data, dict) else {}
    n = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(n) if n else b"{}"
    try:
        data = json.loads(raw.decode("utf-8", errors="replace") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _csv_response(handler: Any, rows: List[Dict[str, Any]], filename: str) -> None:
    fields: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    if not fields:
        fields = ["message"]
        rows = [{"message":"no rows"}]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    body = buf.getvalue().encode("utf-8-sig")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/csv; charset=utf-8")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)

class V10Bridge:
    def __init__(self, Handler: Any, BASE_DIR: Any, load_latest_func: Any):
        self.Handler = Handler
        self.base = Path(BASE_DIR)
        self.data = self.base / "data"
        self.public = self.base / "public"
        self.db_path = self.data / "monitor_v10_notify.db"
        self.load_latest_func = load_latest_func
        self.data.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path), timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def migrate(self) -> Dict[str, Any]:
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS hardware_assets(
                asset_uid TEXT PRIMARY KEY,
                asset_code TEXT, make_name TEXT, model_name TEXT, asset_name TEXT, asset_type TEXT,
                configuration_details TEXT, quantity TEXT, rate TEXT, vendor_name TEXT,
                warranty_end_date TEXT, warranty_end_year TEXT, purchase_date TEXT,
                po_invoice_bill_no TEXT, po_invoice_bill_path TEXT,
                tagname_hostname TEXT, serial_number TEXT, assigned_to TEXT, asset_location TEXT,
                status TEXT, remarks TEXT, source_sheet TEXT, source_row TEXT,
                live_sync_status TEXT, live_hostname TEXT, live_machine_id TEXT, live_ip TEXT,
                live_online TEXT, live_last_seen TEXT,
                extra_json TEXT, created_at TEXT, updated_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS software_assets(
                software_uid TEXT PRIMARY KEY,
                machine_id TEXT, hostname TEXT, software_name TEXT, version TEXT, publisher TEXT,
                install_date TEXT, install_location TEXT, license_key TEXT, license_type TEXT,
                assigned_to TEXT, status TEXT, source TEXT, remarks TEXT, extra_json TEXT,
                created_at TEXT, updated_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS asset_edit_audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_uid TEXT, action TEXT, before_json TEXT, after_json TEXT, actor TEXT, created_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS software_edit_audit_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                software_uid TEXT, action TEXT, before_json TEXT, after_json TEXT, actor TEXT, created_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS inventory_sync_matches(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT, hostname TEXT, asset_uid TEXT, serial_number TEXT, tagname_hostname TEXT,
                match_method TEXT, score INTEGER, matched_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS branding_settings(
                key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS retention_settings(
                key TEXT PRIMARY KEY, value TEXT, updated_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS deploy_profiles(
                id TEXT PRIMARY KEY, name TEXT, os_type TEXT, command TEXT, notes TEXT, enabled INTEGER,
                created_at TEXT, updated_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS history_summary_cache(
                cache_key TEXT PRIMARY KEY, summary_json TEXT, updated_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS iso_audit_results(
                id INTEGER PRIMARY KEY AUTOINCREMENT, audit_type TEXT, summary_json TEXT, created_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS roles(
                role TEXT PRIMARY KEY, description TEXT, created_at TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS user_role_permissions(
                role TEXT, permission TEXT, allowed INTEGER, PRIMARY KEY(role, permission)
            )""")
            for idx in [
                "CREATE INDEX IF NOT EXISTS idx_hw_serial ON hardware_assets(serial_number)",
                "CREATE INDEX IF NOT EXISTS idx_hw_tag ON hardware_assets(tagname_hostname)",
                "CREATE INDEX IF NOT EXISTS idx_hw_status ON hardware_assets(status)",
                "CREATE INDEX IF NOT EXISTS idx_sw_machine ON software_assets(machine_id)",
                "CREATE INDEX IF NOT EXISTS idx_sw_name ON software_assets(software_name)",
                "CREATE INDEX IF NOT EXISTS idx_sync_machine ON inventory_sync_matches(machine_id)",
                "CREATE INDEX IF NOT EXISTS idx_hist_updated ON history_summary_cache(updated_at)"
            ]:
                cur.execute(idx)
            now = _now()
            defaults = {
                "company_name":"Next Toppers",
                "company_website":"https://www.nexttoppers.com/",
                "logo_path":"/assets/brand/nexttoppers_logo.png",
                "login_photo_path":"/assets/brand/nexttoppers_login_photo.png",
                "app_title":"Sagar Kerhalkar System Health Monitor Tool",
                "tagline":"Customer V10 command center"
            }
            for k, v in defaults.items():
                cur.execute("INSERT OR IGNORE INTO branding_settings(key,value,updated_at) VALUES(?,?,?)", (k, v, now))
            for k, v in {"heartbeat_retention_days":"30","history_summary_days":"30","notification_retention_days":"90"}.items():
                cur.execute("INSERT OR IGNORE INTO retention_settings(key,value,updated_at) VALUES(?,?,?)", (k, v, now))
            roles = {"viewer":"Read-only dashboard access","admin":"Admin with edit/download/deploy rights","super_admin":"Full system owner rights"}
            for role, desc in roles.items():
                cur.execute("INSERT OR IGNORE INTO roles(role,description,created_at) VALUES(?,?,?)", (role, desc, now))
            perms = {
                "viewer":["view_dashboard","view_machine","view_inventory"],
                "admin":["view_dashboard","view_machine","view_inventory","edit_inventory","send_message","download","manage_deploy","manage_settings"],
                "super_admin":["view_dashboard","view_machine","view_inventory","edit_inventory","send_message","download","manage_deploy","manage_settings","manage_users","danger_delete"]
            }
            for role, ps in perms.items():
                for p in ps:
                    cur.execute("INSERT OR IGNORE INTO user_role_permissions(role,permission,allowed) VALUES(?,?,1)", (role, p))
            default_deploy = [
                ("windows-client-2294","Windows client 2294","windows","powershell -ExecutionPolicy Bypass -File C:\\Temp\\BOOTSTRAP_WINDOWS_CLIENT_2294.ps1 -ServerUrl http://<SERVER_IP>:2294 -IntervalSeconds 5","Replace <SERVER_IP> with server LAN IP or public domain.",1),
                ("ubuntu-client-2294","Ubuntu client 2294","ubuntu","bash BOOTSTRAP_UBUNTU_CLIENT_2294.sh --server-url http://<SERVER_IP>:2294 --interval 5","Replace <SERVER_IP> with server LAN IP or public domain.",1),
            ]
            for row in default_deploy:
                cur.execute("""INSERT OR IGNORE INTO deploy_profiles(id,name,os_type,command,notes,enabled,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?)""", (*row, now, now))
            con.commit()
        return self.status(import_if_empty=True)

    def table_count(self, table: str) -> int:
        try:
            with self.connect() as con:
                return int(con.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"])
        except Exception:
            return -1

    def existing_tables(self) -> List[str]:
        try:
            with self.connect() as con:
                return [r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        except Exception:
            return []

    def source_hw_rows(self) -> List[Dict[str, Any]]:
        candidates = [
            self.data / "fresh_hw_inventory_v2.json",
            self.data / "fresh_hw_inventory.json",
            self.public / "generated" / "fresh_hw_inventory_v2.json",
            self.public / "generated" / "fresh_hw_inventory.json",
        ]
        for p in candidates:
            try:
                if p.exists():
                    data = json.loads(p.read_text(encoding="utf-8-sig"))
                    if isinstance(data, dict):
                        for k in ("rows","assets","data"):
                            if isinstance(data.get(k), list):
                                data = data[k]
                                break
                    if isinstance(data, list):
                        return [_norm_hw(x) for x in data if isinstance(x, dict)]
            except Exception:
                pass
        csv_candidates = [
            self.data / "fresh_hw_inventory_v2.csv",
            self.data / "fresh_hw_inventory_source.csv",
            self.public / "generated" / "fresh_hw_inventory_v2.csv",
            self.public / "generated" / "fresh_hw_inventory_source.csv",
        ]
        for p in csv_candidates:
            try:
                if p.exists():
                    with p.open("r", encoding="utf-8-sig", newline="") as f:
                        return [_norm_hw(dict(x)) for x in csv.DictReader(f)]
            except Exception:
                pass
        return []

    def import_hw_if_needed(self, force: bool = False) -> Dict[str, Any]:
        self.migrate_no_import()
        current = self.table_count("hardware_assets")
        if current > 0 and not force:
            return {"ok": True, "imported": 0, "existing": current, "source_rows": None}
        rows = self.source_hw_rows()
        now = _now()
        with self.connect() as con:
            if force:
                con.execute("DELETE FROM hardware_assets")
            for r in rows:
                rr = _norm_hw(r)
                vals = [rr.get(c,"") for c in HW_COLUMNS] + [_json(r), now, now]
                con.execute("""INSERT OR REPLACE INTO hardware_assets(
                    asset_uid,asset_code,make_name,model_name,asset_name,asset_type,
                    configuration_details,quantity,rate,vendor_name,warranty_end_date,
                    warranty_end_year,purchase_date,po_invoice_bill_no,po_invoice_bill_path,
                    tagname_hostname,serial_number,assigned_to,asset_location,status,
                    remarks,source_sheet,source_row,live_sync_status,live_hostname,
                    live_machine_id,live_ip,live_online,live_last_seen,extra_json,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
            con.commit()
        return {"ok": True, "imported": len(rows), "existing": self.table_count("hardware_assets"), "source_rows": len(rows)}

    def migrate_no_import(self) -> None:
        # migration without recursive status/import
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS hardware_assets(asset_uid TEXT PRIMARY KEY, asset_code TEXT, make_name TEXT, model_name TEXT, asset_name TEXT, asset_type TEXT, configuration_details TEXT, quantity TEXT, rate TEXT, vendor_name TEXT, warranty_end_date TEXT, warranty_end_year TEXT, purchase_date TEXT, po_invoice_bill_no TEXT, po_invoice_bill_path TEXT, tagname_hostname TEXT, serial_number TEXT, assigned_to TEXT, asset_location TEXT, status TEXT, remarks TEXT, source_sheet TEXT, source_row TEXT, live_sync_status TEXT, live_hostname TEXT, live_machine_id TEXT, live_ip TEXT, live_online TEXT, live_last_seen TEXT, extra_json TEXT, created_at TEXT, updated_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS software_assets(software_uid TEXT PRIMARY KEY, machine_id TEXT, hostname TEXT, software_name TEXT, version TEXT, publisher TEXT, install_date TEXT, install_location TEXT, license_key TEXT, license_type TEXT, assigned_to TEXT, status TEXT, source TEXT, remarks TEXT, extra_json TEXT, created_at TEXT, updated_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS asset_edit_audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, asset_uid TEXT, action TEXT, before_json TEXT, after_json TEXT, actor TEXT, created_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS software_edit_audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, software_uid TEXT, action TEXT, before_json TEXT, after_json TEXT, actor TEXT, created_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS inventory_sync_matches(id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT, hostname TEXT, asset_uid TEXT, serial_number TEXT, tagname_hostname TEXT, match_method TEXT, score INTEGER, matched_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS branding_settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS retention_settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS deploy_profiles(id TEXT PRIMARY KEY, name TEXT, os_type TEXT, command TEXT, notes TEXT, enabled INTEGER, created_at TEXT, updated_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS history_summary_cache(cache_key TEXT PRIMARY KEY, summary_json TEXT, updated_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS iso_audit_results(id INTEGER PRIMARY KEY AUTOINCREMENT, audit_type TEXT, summary_json TEXT, created_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS roles(role TEXT PRIMARY KEY, description TEXT, created_at TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS user_role_permissions(role TEXT, permission TEXT, allowed INTEGER, PRIMARY KEY(role, permission))")
            con.commit()

    def latest(self) -> List[Dict[str, Any]]:
        try:
            rows = self.load_latest_func()
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    def status(self, import_if_empty: bool = False) -> Dict[str, Any]:
        if import_if_empty and self.table_count("hardware_assets") <= 0:
            self.import_hw_if_needed(False)
        machines = self.latest()
        online = [m for m in machines if _bool_online(m.get("online"))]
        return {
            "ok": True,
            "phase": PHASE_NAME,
            "version": PHASE_VERSION,
            "db_path": str(self.db_path),
            "tables": self.existing_tables(),
            "counts": {
                "machines_total": len(machines),
                "machines_online": len(online),
                "machines_offline": max(0, len(machines)-len(online)),
                "hardware_assets": self.table_count("hardware_assets"),
                "software_assets": self.table_count("software_assets"),
                "asset_audit": self.table_count("asset_edit_audit_log"),
                "software_audit": self.table_count("software_edit_audit_log"),
                "notifications": self.table_count("notifications"),
                "notification_rules": self.table_count("notification_rules"),
                "client_messages": self.table_count("client_messages"),
            },
            "truth": {
                "no_fake_data": True,
                "gpu_rule": "show real GPU only; otherwise Not reported",
                "disk_rule": "show real disk only; if client missing then Not reported",
                "protected_2278": True
            },
            "time": _now()
        }

    def settings_dict(self, table: str) -> Dict[str, str]:
        self.migrate_no_import()
        out = {}
        with self.connect() as con:
            try:
                for r in con.execute(f"SELECT key,value FROM {table} ORDER BY key").fetchall():
                    out[r["key"]] = r["value"]
            except Exception:
                pass
        return out

    def set_settings_dict(self, table: str, body: Dict[str, Any]) -> Dict[str, Any]:
        self.migrate_no_import()
        now = _now()
        with self.connect() as con:
            for k, v in body.items():
                if isinstance(v, (dict, list)):
                    v = _json(v)
                con.execute(f"INSERT OR REPLACE INTO {table}(key,value,updated_at) VALUES(?,?,?)", (_s(k), _s(v), now))
            con.commit()
        return {"ok": True, "settings": self.settings_dict(table)}

    def hardware_rows(self, qs: Dict[str, List[str]]) -> Dict[str, Any]:
        self.import_hw_if_needed(False)
        q = _lower((qs.get("q") or [""])[0])
        limit = int(_float((qs.get("limit") or ["500"])[0], 500))
        offset = int(_float((qs.get("offset") or ["0"])[0], 0))
        sql = "SELECT * FROM hardware_assets"
        params: List[Any] = []
        if q:
            likes = " OR ".join([f"LOWER({c}) LIKE ?" for c in ["asset_code","make_name","model_name","asset_name","asset_type","vendor_name","tagname_hostname","serial_number","assigned_to","asset_location","status","remarks"]])
            sql += " WHERE " + likes
            params = [f"%{q}%"] * 11
        sql += " ORDER BY asset_uid LIMIT ? OFFSET ?"
        params += [limit, offset]
        with self.connect() as con:
            rows = [dict(r) for r in con.execute(sql, params).fetchall()]
            total = con.execute("SELECT COUNT(*) c FROM hardware_assets").fetchone()["c"]
        return {"ok": True, "total": total, "count": len(rows), "limit": limit, "offset": offset, "rows": rows}

    def hardware_save(self, body: Dict[str, Any], actor: str = "admin") -> Dict[str, Any]:
        self.migrate_no_import()
        row = _norm_hw(body)
        now = _now()
        with self.connect() as con:
            old = con.execute("SELECT * FROM hardware_assets WHERE asset_uid=?", (row["asset_uid"],)).fetchone()
            oldd = dict(old) if old else None
            vals = [row.get(c,"") for c in HW_COLUMNS] + [_json(body), oldd.get("created_at") if oldd else now, now]
            con.execute("""INSERT OR REPLACE INTO hardware_assets(
                asset_uid,asset_code,make_name,model_name,asset_name,asset_type,
                configuration_details,quantity,rate,vendor_name,warranty_end_date,
                warranty_end_year,purchase_date,po_invoice_bill_no,po_invoice_bill_path,
                tagname_hostname,serial_number,assigned_to,asset_location,status,
                remarks,source_sheet,source_row,live_sync_status,live_hostname,
                live_machine_id,live_ip,live_online,live_last_seen,extra_json,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
            con.execute("INSERT INTO asset_edit_audit_log(asset_uid,action,before_json,after_json,actor,created_at) VALUES(?,?,?,?,?,?)",
                        (row["asset_uid"], "edit" if oldd else "add", _json(oldd), _json(row), actor, now))
            con.commit()
        return {"ok": True, "asset": row, "action": "edit" if oldd else "add"}

    def hardware_delete(self, uid: str, actor: str = "admin") -> Dict[str, Any]:
        self.migrate_no_import()
        with self.connect() as con:
            old = con.execute("SELECT * FROM hardware_assets WHERE asset_uid=?", (uid,)).fetchone()
            if not old:
                return {"ok": False, "error": "asset_not_found", "asset_uid": uid}
            con.execute("DELETE FROM hardware_assets WHERE asset_uid=?", (uid,))
            con.execute("INSERT INTO asset_edit_audit_log(asset_uid,action,before_json,after_json,actor,created_at) VALUES(?,?,?,?,?,?)",
                        (uid, "delete", _json(dict(old)), "{}", actor, _now()))
            con.commit()
        return {"ok": True, "deleted": uid}

    def software_rows(self, qs: Dict[str, List[str]]) -> Dict[str, Any]:
        self.migrate_no_import()
        q = _lower((qs.get("q") or [""])[0])
        machine_id = _s((qs.get("machine_id") or [""])[0])
        rows: List[Dict[str, Any]] = []
        params: List[Any] = []
        where: List[str] = []
        if q:
            where.append("(LOWER(software_name) LIKE ? OR LOWER(version) LIKE ? OR LOWER(publisher) LIKE ? OR LOWER(hostname) LIKE ?)")
            params += [f"%{q}%"]*4
        if machine_id:
            where.append("machine_id=?")
            params.append(machine_id)
        sql = "SELECT * FROM software_assets" + ((" WHERE " + " AND ".join(where)) if where else "") + " ORDER BY software_name LIMIT 1000"
        with self.connect() as con:
            rows = [dict(r) for r in con.execute(sql, params).fetchall()]
        if not rows:
            rows = self.live_software(machine_id)
        return {"ok": True, "count": len(rows), "rows": rows, "source": "db_or_live_fallback"}

    def software_save(self, body: Dict[str, Any], actor: str = "admin") -> Dict[str, Any]:
        self.migrate_no_import()
        row = _norm_sw(body)
        now = _now()
        with self.connect() as con:
            old = con.execute("SELECT * FROM software_assets WHERE software_uid=?", (row["software_uid"],)).fetchone()
            oldd = dict(old) if old else None
            vals = [row.get(c,"") for c in SW_COLUMNS]
            con.execute("""INSERT OR REPLACE INTO software_assets(
                software_uid,machine_id,hostname,software_name,version,publisher,install_date,
                install_location,license_key,license_type,assigned_to,status,source,remarks,
                extra_json,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
            con.execute("INSERT INTO software_edit_audit_log(software_uid,action,before_json,after_json,actor,created_at) VALUES(?,?,?,?,?,?)",
                        (row["software_uid"], "edit" if oldd else "add", _json(oldd), _json(row), actor, now))
            con.commit()
        return {"ok": True, "software": row, "action": "edit" if oldd else "add"}

    def software_delete(self, uid: str, actor: str = "admin") -> Dict[str, Any]:
        self.migrate_no_import()
        with self.connect() as con:
            old = con.execute("SELECT * FROM software_assets WHERE software_uid=?", (uid,)).fetchone()
            if not old:
                return {"ok": False, "error": "software_not_found", "software_uid": uid}
            con.execute("DELETE FROM software_assets WHERE software_uid=?", (uid,))
            con.execute("INSERT INTO software_edit_audit_log(software_uid,action,before_json,after_json,actor,created_at) VALUES(?,?,?,?,?,?)",
                        (uid, "delete", _json(dict(old)), "{}", actor, _now()))
            con.commit()
        return {"ok": True, "deleted": uid}

    def match_machine(self, mid: str) -> Dict[str, Any]:
        machines = self.latest()
        if not mid and machines:
            return machines[0]
        for m in machines:
            if _s(m.get("machine_id")) == mid or _s(m.get("hostname")) == mid or _s(m.get("real_machine_id")) == mid:
                return m
        return {}

    def machine360(self, qs: Dict[str, List[str]]) -> Dict[str, Any]:
        mid = _s((qs.get("id") or qs.get("machine_id") or [""])[0])
        m = self.match_machine(mid)
        if not m:
            return {"ok": False, "error": "machine_not_found", "machine_id": mid}
        payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        disks = _listify(_get_nested(payload, "storage.disks", []) or payload.get("disks") or m.get("disks"))
        gpus = _listify(_get_nested(payload, "hardware.gpus", []) or payload.get("gpus") or payload.get("gpu"))
        software = _listify(_get_nested(payload, "software.installed", []) or payload.get("software") or payload.get("installed_software") or payload.get("apps"))
        usb = _listify(_get_nested(payload, "usb.devices", []) or payload.get("usb") or payload.get("peripherals") or payload.get("devices"))
        adapters = _listify(_get_nested(payload, "network.adapters", []) or payload.get("adapters") or payload.get("network_adapters"))
        summary = {
            "machine_id": _s(m.get("machine_id")),
            "hostname": _s(m.get("hostname")),
            "online": _bool_online(m.get("online")),
            "last_seen": _s(m.get("updated_at") or m.get("last_seen")),
            "os": _s(m.get("os") or _get_nested(payload, "os.name")),
            "primary_ip": _s(m.get("primary_ip")),
            "cpu_percent": m.get("cpu_percent"),
            "cpu_name": _first(m.get("cpu_name"), _get_nested(payload, "hardware.cpu.name"), _get_nested(payload, "cpu.name"), "Not reported"),
            "cpu_temp_c": m.get("cpu_temp_c") if m.get("cpu_temp_c") not in ("", None) else "Not reported",
            "ram_percent": m.get("ram_percent"),
            "ram_total_gb": m.get("ram_total_gb"),
            "ram_used_gb": m.get("ram_used_gb") if m.get("ram_used_gb") not in ("", None, 0, 0.0) else "Not reported",
            "disk_max_percent": m.get("disk_max_percent") if _float(m.get("disk_max_percent"),0)>0 else "Not reported",
            "gpu_names": m.get("gpu_names") or [g.get("name") for g in gpus if isinstance(g, dict) and g.get("name")] or "Not reported",
            "software_count": m.get("software_count") if _float(m.get("software_count"),0)>0 else len(software),
            "usb_count": m.get("usb_count") if _float(m.get("usb_count"),0)>0 else len(usb),
            "vpn_active": m.get("vpn_active"),
            "wan_download_mbps": m.get("wan_download_mbps"),
            "wan_upload_mbps": m.get("wan_upload_mbps"),
            "today_download_gb": m.get("today_download_gb"),
            "today_upload_gb": m.get("today_upload_gb"),
        }
        return {"ok": True, "machine": m, "summary": summary, "hardware": {"disks": disks, "gpus": gpus}, "software": software[:1000], "usb": usb, "network": {"adapters": adapters}}

    def live_software(self, mid: str = "") -> List[Dict[str, Any]]:
        rows = []
        machines = self.latest()
        for m in machines:
            if mid and _s(m.get("machine_id")) != mid and _s(m.get("hostname")) != mid:
                continue
            payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
            software = _listify(_get_nested(payload, "software.installed", []) or payload.get("software") or payload.get("installed_software") or payload.get("apps"))
            for app in software:
                if isinstance(app, dict):
                    r = _norm_sw({**app, "machine_id": m.get("machine_id"), "hostname": m.get("hostname"), "source": "live_client"})
                    rows.append(r)
                elif _s(app):
                    rows.append(_norm_sw({"software_name": _s(app), "machine_id": m.get("machine_id"), "hostname": m.get("hostname"), "source": "live_client"}))
        return rows

    def notifications_rules(self) -> Dict[str, Any]:
        rows = []
        try:
            with self.connect() as con:
                rows = [dict(r) for r in con.execute("SELECT * FROM notification_rules ORDER BY id").fetchall()]
        except Exception:
            pass
        locked = {"cpu_high":"disabled_locked","ram_high":"disabled_locked"}
        return {"ok": True, "rules": rows, "locked_policy": locked, "required_active": ["cpu_ram_critical","disk_high","gpu_temp_high","cpu_temp_high_if_real"]}

    def deploy_profiles(self) -> Dict[str, Any]:
        self.migrate_no_import()
        with self.connect() as con:
            rows = [dict(r) for r in con.execute("SELECT * FROM deploy_profiles ORDER BY os_type,name").fetchall()]
        return {"ok": True, "count": len(rows), "rows": rows}

    def iso_audit(self) -> Dict[str, Any]:
        self.import_hw_if_needed(False)
        with self.connect() as con:
            total = con.execute("SELECT COUNT(*) c FROM hardware_assets").fetchone()["c"]
            missing_serial = con.execute("SELECT COUNT(*) c FROM hardware_assets WHERE serial_number IS NULL OR TRIM(serial_number)=''").fetchone()["c"]
            missing_vendor = con.execute("SELECT COUNT(*) c FROM hardware_assets WHERE vendor_name IS NULL OR TRIM(vendor_name)=''").fetchone()["c"]
            missing_bill = con.execute("SELECT COUNT(*) c FROM hardware_assets WHERE po_invoice_bill_no IS NULL OR TRIM(po_invoice_bill_no)=''").fetchone()["c"]
            unmatched = con.execute("SELECT COUNT(*) c FROM hardware_assets WHERE live_sync_status IS NULL OR live_sync_status='' OR live_sync_status='not_matched'").fetchone()["c"]
        return {"ok": True, "hardware": {"total": total, "missing_serial": missing_serial, "missing_vendor": missing_vendor, "missing_invoice_or_po": missing_bill, "unmatched_live_machine": unmatched}}

    def sync_inventory(self) -> Dict[str, Any]:
        self.import_hw_if_needed(False)
        machines = self.latest()
        tokens: List[Tuple[Dict[str,Any], set]] = []
        for m in machines:
            payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
            vals = [m.get("machine_id"), m.get("hostname"), m.get("primary_ip"), m.get("public_ip"),
                    _get_nested(payload,"identity.serial"), _get_nested(payload,"identity.bios_serial"),
                    _get_nested(payload,"identity.uuid"), _get_nested(payload,"hardware.serial")]
            tokens.append((m, set(_lower(v) for v in vals if _s(v))))
        matched = 0
        now = _now()
        with self.connect() as con:
            rows = [dict(r) for r in con.execute("SELECT * FROM hardware_assets").fetchall()]
            con.execute("DELETE FROM inventory_sync_matches")
            for r in rows:
                keys = [_lower(r.get("serial_number")), _lower(r.get("tagname_hostname")), _lower(r.get("asset_code"))]
                keys = [k for k in keys if k]
                match = None
                method = ""
                for m, toks in tokens:
                    hit = [k for k in keys if k in toks]
                    if hit:
                        match = m
                        method = "serial/tag/asset_code"
                        break
                status = "not_matched"
                if match:
                    matched += 1
                    status = "matched"
                    con.execute("INSERT INTO inventory_sync_matches(machine_id,hostname,asset_uid,serial_number,tagname_hostname,match_method,score,matched_at) VALUES(?,?,?,?,?,?,?,?)",
                                (_s(match.get("machine_id")), _s(match.get("hostname")), r.get("asset_uid"), r.get("serial_number"), r.get("tagname_hostname"), method, 100, now))
                    con.execute("UPDATE hardware_assets SET live_sync_status=?, live_hostname=?, live_machine_id=?, live_ip=?, live_online=?, live_last_seen=?, updated_at=? WHERE asset_uid=?",
                                (status, _s(match.get("hostname")), _s(match.get("machine_id")), _s(match.get("primary_ip")), _s(match.get("online")), _s(match.get("updated_at")), now, r.get("asset_uid")))
                else:
                    con.execute("UPDATE hardware_assets SET live_sync_status=?, live_hostname='', live_machine_id='', live_ip='', live_online='', live_last_seen='', updated_at=? WHERE asset_uid=?",
                                (status, now, r.get("asset_uid")))
            con.commit()
        return {"ok": True, "matched": matched, "total_assets": self.table_count("hardware_assets"), "machines": len(machines)}

def install(Handler: Any, BASE_DIR: Any, load_latest: Any, *args: Any, **kwargs: Any) -> None:
    bridge = V10Bridge(Handler, BASE_DIR, load_latest)
    bridge.migrate()
    bridge.import_hw_if_needed(False)
    old_get = Handler.do_GET
    old_post = Handler.do_POST
    old_delete = getattr(Handler, "do_DELETE", None)

    def parse_qs(handler: Any) -> Tuple[str, Dict[str, List[str]]]:
        raw = handler.path
        path = raw.split("?", 1)[0]
        qs = urllib.parse.parse_qs(raw.split("?", 1)[1]) if "?" in raw else {}
        return path, qs

    def do_GET(self: Any) -> None:
        path, qs = parse_qs(self)
        try:
            if path == "/api/v10final/status":
                return _send_json(self, bridge.status(import_if_empty=True))
            if path == "/api/v10final/db/status":
                return _send_json(self, bridge.status(import_if_empty=True))
            if path == "/api/v10final/migrate":
                return _send_json(self, bridge.migrate())
            if path == "/api/v10final/machines":
                machines = bridge.latest()
                return _send_json(self, {"ok": True, "count": len(machines), "machines": machines})
            if path == "/api/v10final/machine360":
                return _send_json(self, bridge.machine360(qs))
            if path == "/api/v10final/inventory/hardware":
                return _send_json(self, bridge.hardware_rows(qs))
            if path == "/api/v10final/inventory/software":
                return _send_json(self, bridge.software_rows(qs))
            if path == "/api/v10final/notifications/rules":
                return _send_json(self, bridge.notifications_rules())
            if path == "/api/v10final/branding":
                return _send_json(self, {"ok": True, "settings": bridge.settings_dict("branding_settings")})
            if path == "/api/v10final/retention":
                return _send_json(self, {"ok": True, "settings": bridge.settings_dict("retention_settings")})
            if path == "/api/v10final/deploy/profiles":
                return _send_json(self, bridge.deploy_profiles())
            if path == "/api/v10final/iso/audit":
                return _send_json(self, bridge.iso_audit())
            if path == "/api/v10final/inventory/sync":
                return _send_json(self, bridge.sync_inventory())
            if path == "/api/v10final/export/hardware.csv":
                data = bridge.hardware_rows(qs)
                return _csv_response(self, data.get("rows") or [], "v10_hardware_assets.csv")
            if path == "/api/v10final/export/software.csv":
                data = bridge.software_rows(qs)
                return _csv_response(self, data.get("rows") or [], "v10_software_assets.csv")
        except Exception as e:
            return _send_json(self, {"ok": False, "error": str(e), "trace": traceback.format_exc()[-3000:]}, 500)
        return old_get(self)

    def do_POST(self: Any) -> None:
        path, qs = parse_qs(self)
        try:
            if path == "/api/v10final/inventory/hardware/save":
                return _send_json(self, bridge.hardware_save(_read_json(self), getattr(self, "current_username", lambda: "admin")() or "admin"))
            if path == "/api/v10final/inventory/software/save":
                return _send_json(self, bridge.software_save(_read_json(self), getattr(self, "current_username", lambda: "admin")() or "admin"))
            if path == "/api/v10final/branding":
                return _send_json(self, bridge.set_settings_dict("branding_settings", _read_json(self)))
            if path == "/api/v10final/retention":
                return _send_json(self, bridge.set_settings_dict("retention_settings", _read_json(self)))
            if path == "/api/v10final/inventory/sync":
                return _send_json(self, bridge.sync_inventory())
        except Exception as e:
            return _send_json(self, {"ok": False, "error": str(e), "trace": traceback.format_exc()[-3000:]}, 500)
        return old_post(self)

    def do_DELETE(self: Any) -> None:
        path, qs = parse_qs(self)
        try:
            if path == "/api/v10final/inventory/hardware":
                uid = _s((qs.get("asset_uid") or qs.get("id") or [""])[0])
                return _send_json(self, bridge.hardware_delete(uid, getattr(self, "current_username", lambda: "admin")() or "admin"))
            if path == "/api/v10final/inventory/software":
                uid = _s((qs.get("software_uid") or qs.get("id") or [""])[0])
                return _send_json(self, bridge.software_delete(uid, getattr(self, "current_username", lambda: "admin")() or "admin"))
        except Exception as e:
            return _send_json(self, {"ok": False, "error": str(e), "trace": traceback.format_exc()[-3000:]}, 500)
        if old_delete:
            return old_delete(self)
        return _send_json(self, {"error": "not found"}, 404)

    Handler.do_GET = do_GET
    Handler.do_POST = do_POST
    Handler.do_DELETE = do_DELETE
    setattr(Handler, "_v10_final_bridge", bridge)
    print(f"{PHASE_NAME}_LOADED {PHASE_VERSION}")
