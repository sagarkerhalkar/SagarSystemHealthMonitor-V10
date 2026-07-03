from __future__ import annotations

import csv
import datetime as dt
import io
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR: Path = Path('.')
DB_PATH: Path = Path('data/monitor_v10_notify.db')


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH), timeout=20)
    con.row_factory = sqlite3.Row
    return con


def _safe_json(v: Any, default: Any = None) -> Any:
    if default is None:
        default = {}
    if isinstance(v, (dict, list)):
        return v
    try:
        if v is None:
            return default
        return json.loads(str(v))
    except Exception:
        return default


def _first(*vals: Any) -> Any:
    for v in vals:
        if v is not None and v != '' and v != 'None':
            return v
    return None


def _get(d: Any, path: str, default: Any = None) -> Any:
    cur = d
    for p in path.split('.'):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def _float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == '':
            return default
        if isinstance(v, str):
            v = v.strip().replace(',', '')
            if v.lower().endswith('gb'):
                v = v[:-2].strip()
            if v.lower().endswith('mbps'):
                v = v[:-4].strip()
            if v.lower().endswith('%'):
                v = v[:-1].strip()
        return float(v)
    except Exception:
        return default


def _iso_to_date(s: Any) -> str:
    if not s:
        return ''
    txt = str(s)
    try:
        return dt.datetime.fromisoformat(txt.replace('Z', '+00:00')).astimezone().date().isoformat()
    except Exception:
        return txt[:10]


def _summary_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    data = _safe_json(row['summary_json'] if 'summary_json' in row.keys() else {}, {})
    payload = _safe_json(row['payload_json'] if 'payload_json' in row.keys() else {}, {})
    traffic = _get(payload, 'network.traffic', {}) or payload.get('traffic') or {}
    if not isinstance(traffic, dict):
        traffic = {}
    hw = payload.get('hardware') if isinstance(payload, dict) else {}
    if not isinstance(hw, dict):
        hw = {}
    mem = hw.get('memory') or payload.get('memory') or {}
    if not isinstance(mem, dict):
        mem = {}
    machine_id = _first(data.get('machine_id'), row['machine_id'] if 'machine_id' in row.keys() else None, payload.get('machine_id'))
    hostname = _first(data.get('hostname'), row['hostname'] if 'hostname' in row.keys() else None, payload.get('hostname'), machine_id)
    updated_at = _first(row['updated_at'] if 'updated_at' in row.keys() else None, data.get('updated_at'), payload.get('timestamp'))
    return {
        'machine_id': machine_id or '',
        'hostname': hostname or '',
        'updated_at': updated_at or '',
        'updated_date': _iso_to_date(updated_at),
        'today_download_gb': _float(_first(data.get('today_download_gb'), traffic.get('today_download_gb'), _get(payload, 'network.today_download_gb'), payload.get('today_download_gb')), 0),
        'today_upload_gb': _float(_first(data.get('today_upload_gb'), traffic.get('today_upload_gb'), _get(payload, 'network.today_upload_gb'), payload.get('today_upload_gb')), 0),
        'current_download_mbps': _float(_first(data.get('current_download_mbps'), data.get('wan_download_mbps'), traffic.get('current_download_mbps'), _get(payload, 'network.current_download_mbps'), payload.get('download_mbps'), payload.get('wan_download_mbps')), 0),
        'current_upload_mbps': _float(_first(data.get('current_upload_mbps'), data.get('wan_upload_mbps'), traffic.get('current_upload_mbps'), _get(payload, 'network.current_upload_mbps'), payload.get('upload_mbps'), payload.get('wan_upload_mbps')), 0),
        'primary_ip': _first(data.get('primary_ip'), data.get('ip'), _get(payload, 'network.primary_ip'), payload.get('primary_ip')) or '',
        'status': _first(data.get('status'), data.get('online_status'), 'online') or '',
        'source': 'latest.summary_json + latest.payload_json'
    }


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute("select name from sqlite_master where type='table' and name=?", (name,)).fetchone()
    return bool(row)


def traffic_kpi() -> Dict[str, Any]:
    today = dt.datetime.now().astimezone().date().isoformat()
    rows: List[Dict[str, Any]] = []
    db_exists = DB_PATH.exists()
    if db_exists:
        try:
            with _connect() as con:
                if _table_exists(con, 'latest'):
                    qrows = con.execute('SELECT * FROM latest').fetchall()
                    rows = [_summary_from_row(r) for r in qrows]
        except Exception as e:
            return {'ok': False, 'error': str(e), 'db_path': str(DB_PATH), 'today': today}
    # Treat latest table as current truth. If dates are absent/stale, still show latest but flag it.
    fresh_rows = []
    stale_rows = []
    for r in rows:
        d = r.get('updated_date') or ''
        if d == today or not d:
            fresh_rows.append(r)
        else:
            stale_rows.append(r)
    use_rows = fresh_rows or rows
    total_down = round(sum(_float(r.get('today_download_gb'), 0) for r in use_rows), 2)
    total_up = round(sum(_float(r.get('today_upload_gb'), 0) for r in use_rows), 2)
    cur_down = round(sum(_float(r.get('current_download_mbps'), 0) for r in use_rows), 2)
    cur_up = round(sum(_float(r.get('current_upload_mbps'), 0) for r in use_rows), 2)
    active_clients = len([r for r in use_rows if _float(r.get('current_download_mbps'),0) > 0 or _float(r.get('current_upload_mbps'),0) > 0])
    return {
        'ok': True,
        'source': 'live_latest_client_traffic_no_dummy',
        'db_path': str(DB_PATH),
        'today': today,
        'clients_count': len(use_rows),
        'active_traffic_clients': active_clients,
        'stale_rows_excluded': len(stale_rows) if fresh_rows else 0,
        'today_download_gb': total_down,
        'today_upload_gb': total_up,
        'current_download_mbps': cur_down,
        'current_upload_mbps': cur_up,
        'cards': [
            {'label': 'Today Download', 'value': total_down, 'unit': 'GB', 'sub': 'All clients'},
            {'label': 'Today Upload', 'value': total_up, 'unit': 'GB', 'sub': 'All clients'},
            {'label': 'Current Download', 'value': cur_down, 'unit': 'Mbps', 'sub': 'Live client traffic'},
            {'label': 'Current Upload', 'value': cur_up, 'unit': 'Mbps', 'sub': 'Live client traffic'},
        ],
        'per_machine': use_rows,
        'note': 'Calculated from the V10 latest table. No dummy values are used. If clients do not report traffic counters, values remain 0/Not reported.'
    }


def export_csv(data: Dict[str, Any]) -> bytes:
    out = io.StringIO()
    fields = ['machine_id','hostname','primary_ip','status','updated_at','today_download_gb','today_upload_gb','current_download_mbps','current_upload_mbps','source']
    w = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    for r in data.get('per_machine') or []:
        w.writerow(r)
    return out.getvalue().encode('utf-8-sig')


def _send_csv(handler: Any, body: bytes, filename: str) -> None:
    handler._send(200, body, 'text/csv; charset=utf-8', {'Content-Disposition': f'attachment; filename={filename}'})


def install(Handler: Any, base_dir: Any) -> None:
    global BASE_DIR, DB_PATH
    BASE_DIR = Path(base_dir)
    DB_PATH = BASE_DIR / 'data' / 'monitor_v10_notify.db'
    old_get = Handler.do_GET

    def new_get(self):
        path = self.path.split('?', 1)[0]
        try:
            if path in ('/api/v10/home/traffic-kpi', '/api/v10final/home/traffic-kpi', '/api/v10/traffic/summary'):
                return self.send_json(traffic_kpi())
            if path in ('/api/v10/home/traffic-kpi/export.csv', '/api/v10final/home/traffic-kpi/export.csv'):
                return _send_csv(self, export_csv(traffic_kpi()), 'home_traffic_kpi_live_clients.csv')
        except Exception as e:
            try:
                return self.send_json({'ok': False, 'error': str(e)}, 500)
            except Exception:
                raise
        return old_get(self)

    Handler.do_GET = new_get
