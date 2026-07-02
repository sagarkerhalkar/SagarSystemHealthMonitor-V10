import sqlite3, csv, io, zipfile, urllib.parse, datetime, json, threading, time
from pathlib import Path

BASE_DIR = None
OLD_GET = None
BUILD_LOCK = threading.Lock()
BUILDING = False

def s(v):
    return "" if v is None else str(v).strip()

def live_db():
    candidates = [Path(r"D:\SagarSystemHealthMonitor\data\monitor.db"), Path(BASE_DIR) / "data" / "monitor.db"]
    for p in candidates:
        if p.exists():
            return p
    return candidates[-1]

def cache_db():
    p = Path(BASE_DIR) / "data" / "history_summary_cache.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def live_con():
    con = sqlite3.connect(f"file:{live_db()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    con.execute("PRAGMA temp_store=MEMORY")
    return con

def cache_con():
    con = sqlite3.connect(str(cache_db()), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con

def init_cache():
    with cache_con() as con:
        con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
        con.execute("""CREATE TABLE IF NOT EXISTS machine_daily(
            day TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            hostname TEXT,
            heartbeat_count INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT,
            last_seen TEXT,
            public_ip TEXT,
            isp TEXT,
            day_download_gb REAL NOT NULL DEFAULT 0,
            day_upload_gb REAL NOT NULL DEFAULT 0,
            max_down_mbps REAL NOT NULL DEFAULT 0,
            max_up_mbps REAL NOT NULL DEFAULT 0,
            cpu_sum REAL NOT NULL DEFAULT 0,
            cpu_count INTEGER NOT NULL DEFAULT 0,
            ram_sum REAL NOT NULL DEFAULT 0,
            ram_count INTEGER NOT NULL DEFAULT 0,
            ram_total_gb REAL NOT NULL DEFAULT 0,
            usb_max INTEGER NOT NULL DEFAULT 0,
            apps_max INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(day,machine_id)
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_machine_daily_day ON machine_daily(day)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_machine_daily_machine ON machine_daily(machine_id)")
        con.commit()

def meta_get(con, k, default=""):
    r = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return s(r["v"]) if r else default

def meta_set(con, k, v):
    con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (k, str(v)))

def max_live_rowid():
    try:
        with live_con() as con:
            r = con.execute("SELECT MAX(rowid) AS mx FROM heartbeats").fetchone()
            return int(r["mx"] or 0)
    except Exception:
        return 0

def num(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def nested(d, path, default=None):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur.get(part)
    return cur

def first_num(d, paths, default=0.0):
    for p in paths:
        v = nested(d, p, None) if "." in p else (d.get(p) if isinstance(d, dict) else None)
        if v not in (None, ""):
            return num(v, default)
    return default

def first_str(d, paths, default=""):
    for p in paths:
        v = nested(d, p, None) if "." in p else (d.get(p) if isinstance(d, dict) else None)
        if s(v):
            return s(v)
    return default

def parse_payload(raw):
    try:
        p = json.loads(raw or "{}")
        return p if isinstance(p, dict) else {}
    except Exception:
        return {}

def count_list(v):
    return len(v) if isinstance(v, list) else 0

def metrics_from_payload(p):
    usb = p.get("usb") if isinstance(p.get("usb"), dict) else {}
    sw = p.get("software") if isinstance(p.get("software"), dict) else {}
    return {
        "public_ip": first_str(p, ["public_ip","internet.public_ip","network.public_ip","server_public_ip"]),
        "isp": first_str(p, ["isp","internet.isp","network.isp","public_isp"]),
        "day_download_gb": first_num(p, ["today_download_gb","day_download_gb","network.today_download_gb","network.day_download_gb","traffic.today_download_gb","traffic.day_download_gb"]),
        "day_upload_gb": first_num(p, ["today_upload_gb","day_upload_gb","network.today_upload_gb","network.day_upload_gb","traffic.today_upload_gb","traffic.day_upload_gb"]),
        "max_down_mbps": first_num(p, ["wan_download_mbps","current_download_mbps","download_mbps","network.wan_download_mbps","network.current_download_mbps","speed.download_mbps"]),
        "max_up_mbps": first_num(p, ["wan_upload_mbps","current_upload_mbps","upload_mbps","network.wan_upload_mbps","network.current_upload_mbps","speed.upload_mbps"]),
        "cpu_percent": first_num(p, ["cpu_percent","hardware.cpu.percent","hardware.cpu.usage_percent","cpu.usage_percent"]),
        "ram_percent": first_num(p, ["ram_percent","hardware.memory.percent","hardware.memory.usage_percent","memory.usage_percent"]),
        "ram_total_gb": first_num(p, ["ram_total_gb","hardware.memory.total_gb","memory.total_gb"]),
        "usb_count": count_list(usb.get("devices")),
        "apps_count": count_list(sw.get("installed") or sw.get("apps")),
    }

def build_chunk(chunk=50000):
    init_cache()
    with cache_con() as cc:
        last = int(meta_get(cc, "last_rowid", "0") or "0")

    with live_con() as lc:
        rows = [dict(r) for r in lc.execute(
            "SELECT rowid, received_at, machine_id, hostname, payload_json FROM heartbeats WHERE rowid>? ORDER BY rowid ASC LIMIT ?",
            (last, int(chunk))
        ).fetchall()]

    if not rows:
        with cache_con() as cc:
            meta_set(cc, "complete", "1")
            meta_set(cc, "updated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
            cc.commit()
        return {"done": True, "rows": 0, "last_rowid": last}

    agg = {}
    max_rowid = last

    for r in rows:
        max_rowid = max(max_rowid, int(r.get("rowid") or 0))
        day = s(r.get("received_at"))[:10]
        mid = s(r.get("machine_id"))
        if not day or not mid:
            continue

        key = (day, mid)
        if key not in agg:
            agg[key] = {
                "day": day, "machine_id": mid, "hostname": s(r.get("hostname")),
                "heartbeat_count": 0, "first_seen": s(r.get("received_at")), "last_seen": s(r.get("received_at")),
                "public_ip": "", "isp": "", "day_download_gb": 0.0, "day_upload_gb": 0.0,
                "max_down_mbps": 0.0, "max_up_mbps": 0.0, "cpu_sum": 0.0, "cpu_count": 0,
                "ram_sum": 0.0, "ram_count": 0, "ram_total_gb": 0.0, "usb_max": 0, "apps_max": 0
            }

        a = agg[key]
        a["heartbeat_count"] += 1
        ts = s(r.get("received_at"))

        if ts:
            a["first_seen"] = min(a["first_seen"], ts)
            a["last_seen"] = max(a["last_seen"], ts)
        if s(r.get("hostname")):
            a["hostname"] = s(r.get("hostname"))

        m = metrics_from_payload(parse_payload(r.get("payload_json")))

        if m["public_ip"]:
            a["public_ip"] = m["public_ip"]
        if m["isp"]:
            a["isp"] = m["isp"]

        a["day_download_gb"] = max(a["day_download_gb"], m["day_download_gb"])
        a["day_upload_gb"] = max(a["day_upload_gb"], m["day_upload_gb"])
        a["max_down_mbps"] = max(a["max_down_mbps"], m["max_down_mbps"])
        a["max_up_mbps"] = max(a["max_up_mbps"], m["max_up_mbps"])

        if m["cpu_percent"] > 0:
            a["cpu_sum"] += m["cpu_percent"]
            a["cpu_count"] += 1
        if m["ram_percent"] > 0:
            a["ram_sum"] += m["ram_percent"]
            a["ram_count"] += 1

        a["ram_total_gb"] = max(a["ram_total_gb"], m["ram_total_gb"])
        a["usb_max"] = max(a["usb_max"], int(m["usb_count"] or 0))
        a["apps_max"] = max(a["apps_max"], int(m["apps_count"] or 0))

    with cache_con() as cc:
        for a in agg.values():
            cc.execute("""
            INSERT INTO machine_daily(day,machine_id,hostname,heartbeat_count,first_seen,last_seen,public_ip,isp,day_download_gb,day_upload_gb,max_down_mbps,max_up_mbps,cpu_sum,cpu_count,ram_sum,ram_count,ram_total_gb,usb_max,apps_max)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(day,machine_id) DO UPDATE SET
              hostname=CASE WHEN excluded.hostname!='' THEN excluded.hostname ELSE machine_daily.hostname END,
              heartbeat_count=machine_daily.heartbeat_count + excluded.heartbeat_count,
              first_seen=MIN(machine_daily.first_seen, excluded.first_seen),
              last_seen=MAX(machine_daily.last_seen, excluded.last_seen),
              public_ip=CASE WHEN excluded.public_ip!='' THEN excluded.public_ip ELSE machine_daily.public_ip END,
              isp=CASE WHEN excluded.isp!='' THEN excluded.isp ELSE machine_daily.isp END,
              day_download_gb=MAX(machine_daily.day_download_gb, excluded.day_download_gb),
              day_upload_gb=MAX(machine_daily.day_upload_gb, excluded.day_upload_gb),
              max_down_mbps=MAX(machine_daily.max_down_mbps, excluded.max_down_mbps),
              max_up_mbps=MAX(machine_daily.max_up_mbps, excluded.max_up_mbps),
              cpu_sum=machine_daily.cpu_sum + excluded.cpu_sum,
              cpu_count=machine_daily.cpu_count + excluded.cpu_count,
              ram_sum=machine_daily.ram_sum + excluded.ram_sum,
              ram_count=machine_daily.ram_count + excluded.ram_count,
              ram_total_gb=MAX(machine_daily.ram_total_gb, excluded.ram_total_gb),
              usb_max=MAX(machine_daily.usb_max, excluded.usb_max),
              apps_max=MAX(machine_daily.apps_max, excluded.apps_max)
            """, (
                a["day"], a["machine_id"], a["hostname"], a["heartbeat_count"], a["first_seen"], a["last_seen"],
                a["public_ip"], a["isp"], a["day_download_gb"], a["day_upload_gb"], a["max_down_mbps"], a["max_up_mbps"],
                a["cpu_sum"], a["cpu_count"], a["ram_sum"], a["ram_count"], a["ram_total_gb"], a["usb_max"], a["apps_max"]
            ))

        meta_set(cc, "last_rowid", max_rowid)
        meta_set(cc, "complete", "0")
        meta_set(cc, "updated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
        cc.commit()

    return {"done": False, "rows": len(rows), "last_rowid": max_rowid}

def builder_loop():
    global BUILDING
    try:
        while True:
            res = build_chunk()
            if res.get("done"):
                break
            time.sleep(0.05)
    finally:
        BUILDING = False

def start_build():
    global BUILDING
    init_cache()
    with BUILD_LOCK:
        if BUILDING:
            return False
        BUILDING = True
        threading.Thread(target=builder_loop, daemon=True).start()
        return True

def status():
    init_cache()
    mx = max_live_rowid()
    with cache_con() as con:
        last = int(meta_get(con, "last_rowid", "0") or "0")
        complete = meta_get(con, "complete", "0")
        days = con.execute("SELECT COUNT(DISTINCT day) AS c FROM machine_daily").fetchone()["c"]
        machine_days = con.execute("SELECT COUNT(*) AS c FROM machine_daily").fetchone()["c"]
    pct = round((last / mx * 100), 2) if mx else 0
    return {
        "ok": True, "building": BUILDING, "live_max_rowid": mx, "cached_last_rowid": last,
        "percent": pct, "complete": complete == "1" and last >= mx,
        "cached_days": days, "cached_machine_days": machine_days,
        "cache_db": str(cache_db()), "live_db": str(live_db())
    }

def date_range(qs):
    today = datetime.date.today()
    df = s((qs.get("date_from") or [""])[0]) or (today - datetime.timedelta(days=7)).isoformat()
    dt = s((qs.get("date_to") or [""])[0]) or today.isoformat()
    mid = s((qs.get("machine_id") or [""])[0])
    return df[:10], dt[:10], mid

def daily_rows(qs):
    df, dt, mid = date_range(qs)
    where_mid = ""
    params = [df, dt]
    if mid:
        where_mid = " AND machine_id=? "
        params.append(mid)

    with cache_con() as con:
        return con.execute(f"""
        SELECT day AS date,
               COUNT(machine_id) AS machines,
               SUM(heartbeat_count) AS heartbeats,
               ROUND(SUM(day_download_gb), 2) AS day_download_gb,
               ROUND(SUM(day_upload_gb), 2) AS day_upload_gb,
               ROUND(MAX(max_down_mbps), 2) AS max_down_mbps,
               ROUND(MAX(max_up_mbps), 2) AS max_up_mbps,
               ROUND(SUM(cpu_sum) / NULLIF(SUM(cpu_count),0), 2) AS avg_cpu,
               ROUND(SUM(ram_sum) / NULLIF(SUM(ram_count),0), 2) AS avg_ram,
               MAX(usb_max) AS usb_max,
               MAX(apps_max) AS apps_max,
               MIN(first_seen) AS first_seen,
               MAX(last_seen) AS last_seen
        FROM machine_daily
        WHERE day>=? AND day<=? {where_mid}
        GROUP BY day
        ORDER BY day ASC
        """, params).fetchall()

def machine_rows(qs):
    df, dt, mid = date_range(qs)
    where_mid = ""
    params = [df, dt]
    if mid:
        where_mid = " AND machine_id=? "
        params.append(mid)

    with cache_con() as con:
        return con.execute(f"""
        SELECT day AS date,
               machine_id,
               hostname,
               heartbeat_count AS heartbeats,
               public_ip,
               isp,
               ROUND(day_download_gb, 2) AS download_gb,
               ROUND(day_upload_gb, 2) AS upload_gb,
               ROUND(max_down_mbps, 2) AS max_down_mbps,
               ROUND(max_up_mbps, 2) AS max_up_mbps,
               ROUND(cpu_sum / NULLIF(cpu_count,0), 2) AS cpu_max,
               ROUND(ram_sum / NULLIF(ram_count,0), 2) AS ram_max,
               ROUND(ram_total_gb, 2) AS ram_total_gb,
               usb_max,
               apps_max,
               last_seen
        FROM machine_daily
        WHERE day>=? AND day<=? {where_mid}
        ORDER BY day ASC, hostname ASC, machine_id ASC
        LIMIT 20000
        """, params).fetchall()

def csv_bytes(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(dict(r))
    return buf.getvalue().encode("utf-8-sig")

def send(h, b, ctype, filename=None):
    h.send_response(200)
    h.send_header("Content-Type", ctype)
    h.send_header("Content-Length", str(len(b)))
    if filename:
        h.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    h.end_headers()
    h.wfile.write(b)

def send_json(h, obj, status=200):
    b = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(b)))
    h.end_headers()
    h.wfile.write(b)

def zip_pack(qs):
    daily_fields = ["date","machines","heartbeats","day_download_gb","day_upload_gb","max_down_mbps","max_up_mbps","avg_cpu","avg_ram","usb_max","apps_max","first_seen","last_seen"]
    machine_fields = ["date","machine_id","hostname","heartbeats","public_ip","isp","download_gb","upload_gb","max_down_mbps","max_up_mbps","cpu_max","ram_max","ram_total_gb","usb_max","apps_max","last_seen"]

    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("HISTORY_DAILY.csv", csv_bytes(daily_rows(qs), daily_fields))
        z.writestr("HISTORY_MACHINE_DAILY.csv", csv_bytes(machine_rows(qs), machine_fields))
        z.writestr("HISTORY_CACHE_STATUS.json", json.dumps(status(), indent=2, ensure_ascii=False))
    return b.getvalue()

def install(Handler, base_dir):
    global BASE_DIR, OLD_GET
    BASE_DIR = base_dir
    init_cache()
    OLD_GET = Handler.do_GET

    def do_GET(h):
        try:
            u = urllib.parse.urlparse(h.path)
            path = u.path.rstrip("/") or "/"
            qs = urllib.parse.parse_qs(u.query)

            if path == "/api/history-cache/start":
                started = start_build()
                return send_json(h, {"ok": True, "started": started, "status": status()})

            if path == "/api/history-cache/status":
                return send_json(h, status())

            if path == "/api/history-cache/view":
                return send_json(h, {
                    "ok": True,
                    "status": status(),
                    "daily": [dict(r) for r in daily_rows(qs)],
                    "per_machine": [dict(r) for r in machine_rows(qs)],
                    "samples": []
                })

            if path == "/api/history-cache/daily.csv":
                fields = ["date","machines","heartbeats","day_download_gb","day_upload_gb","max_down_mbps","max_up_mbps","avg_cpu","avg_ram","usb_max","apps_max","first_seen","last_seen"]
                return send(h, csv_bytes(daily_rows(qs), fields), "text/csv; charset=utf-8", "HISTORY_DAILY.csv")

            if path == "/api/history-cache/machine-daily.csv":
                fields = ["date","machine_id","hostname","heartbeats","public_ip","isp","download_gb","upload_gb","max_down_mbps","max_up_mbps","cpu_max","ram_max","ram_total_gb","usb_max","apps_max","last_seen"]
                return send(h, csv_bytes(machine_rows(qs), fields), "text/csv; charset=utf-8", "HISTORY_MACHINE_DAILY.csv")

            if path == "/api/history-cache/export.zip":
                return send(h, zip_pack(qs), "application/zip", "HISTORY_EXPORT.zip")

            return OLD_GET(h)
        except Exception as e:
            return send_json(h, {"ok": False, "error": str(e)}, 500)

    Handler.do_GET = do_GET