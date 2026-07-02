import sqlite3, json, threading, time, urllib.parse, datetime
from pathlib import Path

BASE_DIR = None
OLD_GET = None
BUILDING = False
LOCK = threading.Lock()

def s(v):
    return "" if v is None else str(v).strip()

def live_db():
    p = Path(r"D:\SagarSystemHealthMonitor\data\monitor.db")
    if p.exists():
        return p
    return Path(BASE_DIR) / "data" / "monitor.db"

def cache_db():
    p = Path(BASE_DIR) / "data" / "history_cache_lite.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def live_con():
    con = sqlite3.connect("file:" + str(live_db()) + "?mode=ro", uri=True, timeout=30)
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

def init():
    with cache_con() as con:
        con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
        con.execute("""CREATE TABLE IF NOT EXISTS machine_day(
            day TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            hostname TEXT,
            heartbeats INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT,
            last_seen TEXT,
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
        con.execute("CREATE INDEX IF NOT EXISTS idx_machine_day_day ON machine_day(day)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_machine_day_machine ON machine_day(machine_id)")
        con.commit()

def meta_get(con, k, default="0"):
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

def num(v):
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except Exception:
        return 0.0

def get_nested(d, path):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur

def first_num(p, names):
    for n in names:
        v = get_nested(p, n) if "." in n else p.get(n)
        if v not in (None, ""):
            return num(v)
    return 0.0

def metrics(payload_text):
    try:
        p = json.loads(payload_text or "{}")
        if not isinstance(p, dict):
            p = {}
    except Exception:
        p = {}

    usb = p.get("usb") if isinstance(p.get("usb"), dict) else {}
    sw = p.get("software") if isinstance(p.get("software"), dict) else {}

    apps = sw.get("installed") or sw.get("apps") or []
    devices = usb.get("devices") or []

    return {
        "day_download_gb": first_num(p, ["today_download_gb","day_download_gb","network.today_download_gb","traffic.today_download_gb"]),
        "day_upload_gb": first_num(p, ["today_upload_gb","day_upload_gb","network.today_upload_gb","traffic.today_upload_gb"]),
        "max_down_mbps": first_num(p, ["wan_download_mbps","current_download_mbps","download_mbps","network.wan_download_mbps"]),
        "max_up_mbps": first_num(p, ["wan_upload_mbps","current_upload_mbps","upload_mbps","network.wan_upload_mbps"]),
        "cpu": first_num(p, ["cpu_percent","hardware.cpu.percent","hardware.cpu.usage_percent"]),
        "ram": first_num(p, ["ram_percent","hardware.memory.percent","hardware.memory.usage_percent"]),
        "ram_total_gb": first_num(p, ["ram_total_gb","hardware.memory.total_gb"]),
        "usb_count": len(devices) if isinstance(devices, list) else 0,
        "apps_count": len(apps) if isinstance(apps, list) else 0,
    }

def build_once(chunk=20000):
    init()
    with cache_con() as cc:
        last = int(meta_get(cc, "last_rowid", "0") or "0")

    with live_con() as lc:
        rows = [dict(r) for r in lc.execute(
            "SELECT rowid, received_at, machine_id, hostname, payload_json FROM heartbeats WHERE rowid>? ORDER BY rowid ASC LIMIT ?",
            (last, chunk)
        ).fetchall()]

    if not rows:
        with cache_con() as cc:
            meta_set(cc, "complete", "1")
            meta_set(cc, "updated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
            cc.commit()
        return 0

    maxid = last
    agg = {}

    for r in rows:
        maxid = max(maxid, int(r.get("rowid") or 0))
        ts = s(r.get("received_at"))
        day = ts[:10]
        mid = s(r.get("machine_id"))
        if not day or not mid:
            continue

        key = (day, mid)
        if key not in agg:
            agg[key] = {
                "day": day,
                "machine_id": mid,
                "hostname": s(r.get("hostname")),
                "heartbeats": 0,
                "first_seen": ts,
                "last_seen": ts,
                "day_download_gb": 0.0,
                "day_upload_gb": 0.0,
                "max_down_mbps": 0.0,
                "max_up_mbps": 0.0,
                "cpu_sum": 0.0,
                "cpu_count": 0,
                "ram_sum": 0.0,
                "ram_count": 0,
                "ram_total_gb": 0.0,
                "usb_max": 0,
                "apps_max": 0
            }

        a = agg[key]
        a["heartbeats"] += 1
        if ts:
            a["first_seen"] = min(a["first_seen"], ts)
            a["last_seen"] = max(a["last_seen"], ts)
        if s(r.get("hostname")):
            a["hostname"] = s(r.get("hostname"))

        m = metrics(r.get("payload_json"))

        a["day_download_gb"] = max(a["day_download_gb"], m["day_download_gb"])
        a["day_upload_gb"] = max(a["day_upload_gb"], m["day_upload_gb"])
        a["max_down_mbps"] = max(a["max_down_mbps"], m["max_down_mbps"])
        a["max_up_mbps"] = max(a["max_up_mbps"], m["max_up_mbps"])

        if m["cpu"] > 0:
            a["cpu_sum"] += m["cpu"]
            a["cpu_count"] += 1
        if m["ram"] > 0:
            a["ram_sum"] += m["ram"]
            a["ram_count"] += 1

        a["ram_total_gb"] = max(a["ram_total_gb"], m["ram_total_gb"])
        a["usb_max"] = max(a["usb_max"], int(m["usb_count"]))
        a["apps_max"] = max(a["apps_max"], int(m["apps_count"]))

    with cache_con() as cc:
        for a in agg.values():
            cc.execute("""
            INSERT INTO machine_day(day,machine_id,hostname,heartbeats,first_seen,last_seen,day_download_gb,day_upload_gb,max_down_mbps,max_up_mbps,cpu_sum,cpu_count,ram_sum,ram_count,ram_total_gb,usb_max,apps_max)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(day,machine_id) DO UPDATE SET
              hostname=CASE WHEN excluded.hostname!='' THEN excluded.hostname ELSE machine_day.hostname END,
              heartbeats=machine_day.heartbeats + excluded.heartbeats,
              first_seen=MIN(machine_day.first_seen, excluded.first_seen),
              last_seen=MAX(machine_day.last_seen, excluded.last_seen),
              day_download_gb=MAX(machine_day.day_download_gb, excluded.day_download_gb),
              day_upload_gb=MAX(machine_day.day_upload_gb, excluded.day_upload_gb),
              max_down_mbps=MAX(machine_day.max_down_mbps, excluded.max_down_mbps),
              max_up_mbps=MAX(machine_day.max_up_mbps, excluded.max_up_mbps),
              cpu_sum=machine_day.cpu_sum + excluded.cpu_sum,
              cpu_count=machine_day.cpu_count + excluded.cpu_count,
              ram_sum=machine_day.ram_sum + excluded.ram_sum,
              ram_count=machine_day.ram_count + excluded.ram_count,
              ram_total_gb=MAX(machine_day.ram_total_gb, excluded.ram_total_gb),
              usb_max=MAX(machine_day.usb_max, excluded.usb_max),
              apps_max=MAX(machine_day.apps_max, excluded.apps_max)
            """, (
                a["day"], a["machine_id"], a["hostname"], a["heartbeats"], a["first_seen"], a["last_seen"],
                a["day_download_gb"], a["day_upload_gb"], a["max_down_mbps"], a["max_up_mbps"],
                a["cpu_sum"], a["cpu_count"], a["ram_sum"], a["ram_count"], a["ram_total_gb"], a["usb_max"], a["apps_max"]
            ))

        meta_set(cc, "last_rowid", maxid)
        meta_set(cc, "complete", "0")
        meta_set(cc, "updated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())
        cc.commit()

    return len(rows)

def builder():
    global BUILDING
    try:
        while True:
            n = build_once()
            if n <= 0:
                break
            time.sleep(0.02)
    finally:
        BUILDING = False

def start_build():
    global BUILDING
    init()
    with LOCK:
        if BUILDING:
            return False
        BUILDING = True
        threading.Thread(target=builder, daemon=True).start()
        return True

def status():
    init()
    mx = max_live_rowid()
    with cache_con() as con:
        last = int(meta_get(con, "last_rowid", "0") or "0")
        days = con.execute("SELECT COUNT(DISTINCT day) c FROM machine_day").fetchone()["c"]
        mds = con.execute("SELECT COUNT(*) c FROM machine_day").fetchone()["c"]
    pct = round((last / mx * 100), 2) if mx else 0
    return {"ok": True, "building": BUILDING, "percent": pct, "live_max_rowid": mx, "cached_last_rowid": last, "cached_days": days, "cached_machine_days": mds}

def qs_dates(qs):
    today = datetime.date.today()
    df = s((qs.get("date_from") or [""])[0]) or (today - datetime.timedelta(days=30)).isoformat()
    dt = s((qs.get("date_to") or [""])[0]) or today.isoformat()
    mid = s((qs.get("machine_id") or [""])[0])
    return df[:10], dt[:10], mid

def view(qs):
    df, dt, mid = qs_dates(qs)
    where = ""
    params = [df, dt]
    if mid:
        where = " AND machine_id=? "
        params.append(mid)

    with cache_con() as con:
        daily = [dict(r) for r in con.execute(f"""
        SELECT day AS date,
               COUNT(machine_id) AS machines,
               SUM(heartbeats) AS heartbeats,
               ROUND(SUM(day_download_gb),2) AS day_download_gb,
               ROUND(SUM(day_upload_gb),2) AS day_upload_gb,
               ROUND(MAX(max_down_mbps),2) AS max_down_mbps,
               ROUND(MAX(max_up_mbps),2) AS max_up_mbps,
               ROUND(SUM(cpu_sum)/NULLIF(SUM(cpu_count),0),2) AS avg_cpu,
               ROUND(SUM(ram_sum)/NULLIF(SUM(ram_count),0),2) AS avg_ram,
               MAX(usb_max) AS usb_max,
               MAX(apps_max) AS apps_max
        FROM machine_day
        WHERE day>=? AND day<=? {where}
        GROUP BY day
        ORDER BY day ASC
        """, params).fetchall()]

        machine = [dict(r) for r in con.execute(f"""
        SELECT day AS date, machine_id, hostname,
               heartbeats,
               ROUND(day_download_gb,2) AS download_gb,
               ROUND(day_upload_gb,2) AS upload_gb,
               ROUND(max_down_mbps,2) AS max_down_mbps,
               ROUND(max_up_mbps,2) AS max_up_mbps,
               ROUND(cpu_sum/NULLIF(cpu_count,0),2) AS cpu_max,
               ROUND(ram_sum/NULLIF(ram_count,0),2) AS ram_max,
               ROUND(ram_total_gb,2) AS ram_total_gb,
               usb_max, apps_max, last_seen
        FROM machine_day
        WHERE day>=? AND day<=? {where}
        ORDER BY day ASC, hostname ASC
        LIMIT 20000
        """, params).fetchall()]

    return {"ok": True, "daily": daily, "per_machine": machine, "samples": [], "status": status()}

def send_json(h, obj, status_code=200):
    b = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
    h.send_response(status_code)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(b)))
    h.end_headers()
    h.wfile.write(b)

def install(Handler, base_dir):
    global BASE_DIR, OLD_GET
    BASE_DIR = base_dir
    init()
    start_build()
    OLD_GET = Handler.do_GET

    def do_GET(h):
        try:
            u = urllib.parse.urlparse(h.path)
            path = u.path.rstrip("/") or "/"
            qs = urllib.parse.parse_qs(u.query)

            if path == "/api/history-cache-lite/status":
                return send_json(h, status())

            if path == "/api/history-cache-lite/start":
                return send_json(h, {"ok": True, "started": start_build(), "status": status()})

            if path == "/api/history-cache-lite/view":
                start_build()
                return send_json(h, view(qs))

            return OLD_GET(h)
        except Exception as e:
            return send_json(h, {"ok": False, "error": str(e)}, 500)

    Handler.do_GET = do_GET