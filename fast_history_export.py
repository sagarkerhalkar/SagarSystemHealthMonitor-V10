import sqlite3, csv, io, zipfile, urllib.parse, datetime, json
from pathlib import Path

BASE_DIR = None
OLD_GET = None

def db_path():
    candidates = [
        Path(r"D:\SagarSystemHealthMonitor\data\monitor.db"),
        Path(BASE_DIR) / "data" / "monitor.db",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[-1]

def s(v):
    return "" if v is None else str(v).strip()

def parse_date(v, fallback):
    v = s(v)
    if not v:
        return fallback
    return datetime.date.fromisoformat(v[:10])

def range_from_qs(qs):
    today = datetime.date.today()
    d1 = parse_date((qs.get("date_from") or [""])[0], today)
    d2 = parse_date((qs.get("date_to") or [""])[0], d1)
    # UI date_to is inclusive; SQL end is exclusive.
    start = datetime.datetime.combine(d1, datetime.time.min, tzinfo=datetime.timezone.utc).isoformat()
    end = datetime.datetime.combine(d2 + datetime.timedelta(days=1), datetime.time.min, tzinfo=datetime.timezone.utc).isoformat()
    return d1.isoformat(), d2.isoformat(), start, end

def connect_ro():
    p = db_path()
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    con.execute("PRAGMA temp_store=MEMORY")
    return con

def csv_bytes(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(dict(r))
    return buf.getvalue().encode("utf-8-sig")

def query_daily(qs):
    d1, d2, start, end = range_from_qs(qs)
    mid = s((qs.get("machine_id") or [""])[0])
    params = [start, end]
    where_mid = ""
    if mid:
        where_mid = " AND machine_id=? "
        params.append(mid)
    sql = f"""
    SELECT
      substr(received_at,1,10) AS day,
      COUNT(*) AS heartbeat_count,
      COUNT(DISTINCT machine_id) AS machine_count,
      MIN(received_at) AS first_seen,
      MAX(received_at) AS last_seen
    FROM heartbeats
    WHERE received_at>=? AND received_at<? {where_mid}
    GROUP BY substr(received_at,1,10)
    ORDER BY day ASC
    """
    with connect_ro() as con:
        return con.execute(sql, params).fetchall()

def query_machine_daily(qs):
    d1, d2, start, end = range_from_qs(qs)
    mid = s((qs.get("machine_id") or [""])[0])
    params = [start, end]
    where_mid = ""
    if mid:
        where_mid = " AND machine_id=? "
        params.append(mid)
    sql = f"""
    SELECT
      substr(received_at,1,10) AS day,
      machine_id,
      MAX(hostname) AS hostname,
      COUNT(*) AS heartbeat_count,
      MIN(received_at) AS first_seen,
      MAX(received_at) AS last_seen
    FROM heartbeats
    WHERE received_at>=? AND received_at<? {where_mid}
    GROUP BY substr(received_at,1,10), machine_id
    ORDER BY day ASC, hostname ASC, machine_id ASC
    """
    with connect_ro() as con:
        return con.execute(sql, params).fetchall()

def query_raw(qs):
    d1, d2, start, end = range_from_qs(qs)
    mid = s((qs.get("machine_id") or [""])[0])
    limit = int(s((qs.get("limit") or ["200000"])[0]) or "200000")
    if limit < 1000:
        limit = 1000
    if limit > 1000000:
        limit = 1000000
    params = [start, end]
    where_mid = ""
    if mid:
        where_mid = " AND machine_id=? "
        params.append(mid)
    params.append(limit)
    sql = f"""
    SELECT
      received_at,
      machine_id,
      hostname
    FROM heartbeats
    WHERE received_at>=? AND received_at<? {where_mid}
    ORDER BY received_at ASC
    LIMIT ?
    """
    with connect_ro() as con:
        return con.execute(sql, params).fetchall()

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
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("FAST_HISTORY_DAILY.csv", csv_bytes(query_daily(qs), ["day","heartbeat_count","machine_count","first_seen","last_seen"]))
        z.writestr("FAST_HISTORY_MACHINE_DAILY.csv", csv_bytes(query_machine_daily(qs), ["day","machine_id","hostname","heartbeat_count","first_seen","last_seen"]))
        z.writestr("README.txt", "Fast history export: does not parse payload_json. Use raw export only when required.")
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

            if path == "/api/fast-history/daily.csv":
                return send(h, csv_bytes(query_daily(qs), ["day","heartbeat_count","machine_count","first_seen","last_seen"]), "text/csv; charset=utf-8", "FAST_HISTORY_DAILY.csv")

            if path == "/api/fast-history/machine-daily.csv":
                return send(h, csv_bytes(query_machine_daily(qs), ["day","machine_id","hostname","heartbeat_count","first_seen","last_seen"]), "text/csv; charset=utf-8", "FAST_HISTORY_MACHINE_DAILY.csv")

            if path == "/api/fast-history/raw.csv":
                return send(h, csv_bytes(query_raw(qs), ["received_at","machine_id","hostname"]), "text/csv; charset=utf-8", "FAST_HISTORY_RAW_HEARTBEATS_LIMITED.csv")

            if path == "/api/fast-history/export.zip":
                return send(h, zip_pack(qs), "application/zip", "FAST_HISTORY_EXPORT.zip")

            if path == "/api/fast-history/ping":
                return send_json(h, {"ok": True, "db": str(db_path()), "note": "Fast history avoids payload_json parsing."})

            return OLD_GET(h)
        except Exception as e:
            return send_json(h, {"ok": False, "error": str(e)}, 500)

    Handler.do_GET = do_GET