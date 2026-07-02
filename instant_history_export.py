import sqlite3, csv, io, zipfile, urllib.parse, datetime, json
from pathlib import Path
from collections import defaultdict

BASE_DIR = None
OLD_GET = None

def s(v):
    return "" if v is None else str(v).strip()

def db_path():
    candidates = [
        Path(r"D:\SagarSystemHealthMonitor\data\monitor.db"),
        Path(BASE_DIR) / "data" / "monitor.db",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[-1]

def connect_ro():
    p = db_path()
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    con.execute("PRAGMA temp_store=MEMORY")
    return con

def parse_day(v, fallback):
    v = s(v)
    if not v:
        return fallback
    return datetime.date.fromisoformat(v[:10])

def params(qs):
    today = datetime.date.today()
    d1 = parse_day((qs.get("date_from") or [""])[0], today)
    d2 = parse_day((qs.get("date_to") or [""])[0], d1)
    mid = s((qs.get("machine_id") or [""])[0])
    limit = int(s((qs.get("limit") or ["300000"])[0]) or "300000")
    if limit < 50000:
        limit = 50000
    if limit > 1500000:
        limit = 1500000
    return d1.isoformat(), d2.isoformat(), mid, limit

def latest_rows(qs):
    d1, d2, mid, limit = params(qs)
    rows = []
    with connect_ro() as con:
        # rowid DESC avoids full date scan. Very fast for recent data.
        sql = "SELECT rowid, received_at, machine_id, hostname FROM heartbeats ORDER BY rowid DESC LIMIT ?"
        for r in con.execute(sql, (limit,)):
            day = s(r["received_at"])[:10]
            if day < d1 or day > d2:
                continue
            if mid and s(r["machine_id"]) != mid:
                continue
            rows.append(dict(r))
    rows.reverse()
    return rows

def daily(rows):
    d = {}
    machines = defaultdict(set)
    for r in rows:
        day = s(r.get("received_at"))[:10]
        if not day:
            continue
        if day not in d:
            d[day] = {"day":day,"heartbeat_count":0,"machine_count":0,"first_seen":s(r.get("received_at")),"last_seen":s(r.get("received_at"))}
        d[day]["heartbeat_count"] += 1
        d[day]["first_seen"] = min(d[day]["first_seen"], s(r.get("received_at")))
        d[day]["last_seen"] = max(d[day]["last_seen"], s(r.get("received_at")))
        machines[day].add(s(r.get("machine_id")))
    out = []
    for day in sorted(d):
        d[day]["machine_count"] = len([x for x in machines[day] if x])
        out.append(d[day])
    return out

def machine_daily(rows):
    d = {}
    for r in rows:
        day = s(r.get("received_at"))[:10]
        mid = s(r.get("machine_id"))
        key = (day, mid)
        if not day or not mid:
            continue
        if key not in d:
            d[key] = {"day":day,"machine_id":mid,"hostname":s(r.get("hostname")),"heartbeat_count":0,"first_seen":s(r.get("received_at")),"last_seen":s(r.get("received_at"))}
        d[key]["heartbeat_count"] += 1
        if s(r.get("hostname")):
            d[key]["hostname"] = s(r.get("hostname"))
        d[key]["first_seen"] = min(d[key]["first_seen"], s(r.get("received_at")))
        d[key]["last_seen"] = max(d[key]["last_seen"], s(r.get("received_at")))
    return [d[k] for k in sorted(d)]

def csv_bytes(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
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
    rows = latest_rows(qs)
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("INSTANT_HISTORY_DAILY.csv", csv_bytes(daily(rows), ["day","heartbeat_count","machine_count","first_seen","last_seen"]))
        z.writestr("INSTANT_HISTORY_MACHINE_DAILY.csv", csv_bytes(machine_daily(rows), ["day","machine_id","hostname","heartbeat_count","first_seen","last_seen"]))
        z.writestr("INSTANT_HISTORY_RAW_LIMITED.csv", csv_bytes(rows, ["rowid","received_at","machine_id","hostname"]))
        z.writestr("README.txt", "Instant history uses latest rowid records from live DB to avoid full date scan. Best for recent/day history.")
    return b.getvalue()

def install(Handler, base_dir):
    global BASE_DIR, OLD_GET
    BASE_DIR = base_dir
    OLD_GET = Handler.do_GET

    def do_GET(h):
        try:
            u = urllib.parse.urlparse(h.path)
            path = u.path.rstrip("/") or "/"
            qs = urllib.parse.parse_qs(u.query)

            if path == "/api/instant-history/ping":
                rows = latest_rows({"limit":["1000"]})
                return send_json(h, {"ok": True, "db": str(db_path()), "sample_rows": len(rows), "note": "Uses rowid DESC, avoids full received_at scan."})

            if path == "/api/instant-history/daily.csv":
                rows = latest_rows(qs)
                return send(h, csv_bytes(daily(rows), ["day","heartbeat_count","machine_count","first_seen","last_seen"]), "text/csv; charset=utf-8", "INSTANT_HISTORY_DAILY.csv")

            if path == "/api/instant-history/machine-daily.csv":
                rows = latest_rows(qs)
                return send(h, csv_bytes(machine_daily(rows), ["day","machine_id","hostname","heartbeat_count","first_seen","last_seen"]), "text/csv; charset=utf-8", "INSTANT_HISTORY_MACHINE_DAILY.csv")

            if path == "/api/instant-history/raw.csv":
                rows = latest_rows(qs)
                return send(h, csv_bytes(rows, ["rowid","received_at","machine_id","hostname"]), "text/csv; charset=utf-8", "INSTANT_HISTORY_RAW_LIMITED.csv")

            if path == "/api/instant-history/export.zip":
                return send(h, zip_pack(qs), "application/zip", "INSTANT_HISTORY_EXPORT.zip")

            return OLD_GET(h)
        except Exception as e:
            return send_json(h, {"ok": False, "error": str(e)}, 500)

    Handler.do_GET = do_GET