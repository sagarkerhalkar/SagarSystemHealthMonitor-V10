from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR: Path = Path('.')
SOURCE_2278_DB: Path = Path(r'D:\SagarSystemHealthMonitor\data\monitor.db')


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _connect_ro() -> sqlite3.Connection:
    # Important: read-only mode, no write lock and no schema change in 2278 DB.
    uri = 'file:' + str(SOURCE_2278_DB).replace('\\', '/') + '?mode=ro'
    con = sqlite3.connect(uri, uri=True, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def _safe_json(v: Any, default: Any = None) -> Any:
    if default is None:
        default = {}
    if isinstance(v, (dict, list)):
        return v
    if v is None:
        return default
    try:
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
            for suf in ['mbps', 'gb', '%', 'c']:
                if v.lower().endswith(suf):
                    v = v[:-len(suf)].strip()
        return float(v)
    except Exception:
        return default


def _int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == '':
            return default
        return int(float(str(v).strip()))
    except Exception:
        return default


def _iso_parse(s: Any) -> Optional[dt.datetime]:
    if not s:
        return None
    txt = str(s).strip()
    try:
        if txt.endswith('Z'):
            txt = txt[:-1] + '+00:00'
        d = dt.datetime.fromisoformat(txt)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


def _age_minutes(s: Any) -> Optional[float]:
    d = _iso_parse(s)
    if not d:
        return None
    return round((_now_utc() - d).total_seconds() / 60, 2)


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    return bool(con.execute("select name from sqlite_master where type='table' and name=?", (name,)).fetchone())


def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    try:
        return [r[1] for r in con.execute(f'PRAGMA table_info({table})').fetchall()]
    except Exception:
        return []


def _rowdict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _machine_from_latest(row: sqlite3.Row) -> Dict[str, Any]:
    rd = _rowdict(row)
    summary = _safe_json(rd.get('summary_json'), {})
    payload = _safe_json(rd.get('payload_json'), {})
    if isinstance(summary.get('payload'), dict) and not payload:
        payload = summary.get('payload') or {}
    hw = payload.get('hardware') if isinstance(payload, dict) else {}
    if not isinstance(hw, dict):
        hw = {}
    storage = payload.get('storage') or hw.get('storage') or payload.get('disks') or []
    network = payload.get('network') if isinstance(payload, dict) else {}
    if not isinstance(network, dict):
        network = {}
    software = payload.get('software') if isinstance(payload, dict) else {}
    usb = payload.get('usb') or payload.get('peripherals') or []
    updated_at = _first(rd.get('updated_at'), summary.get('updated_at'), payload.get('timestamp'), summary.get('timestamp'))
    machine_id = _first(rd.get('machine_id'), summary.get('machine_id'), payload.get('machine_id')) or ''
    hostname = _first(rd.get('hostname'), summary.get('hostname'), payload.get('hostname'), machine_id) or ''
    return {
        'machine_id': machine_id,
        'hostname': hostname,
        'id_source': _first(rd.get('id_source'), summary.get('id_source')) or '',
        'id_value': _first(rd.get('id_value'), summary.get('id_value')) or '',
        'updated_at': updated_at or '',
        'age_minutes': _age_minutes(updated_at),
        'fresh': (_age_minutes(updated_at) is not None and _age_minutes(updated_at) <= 10),
        'os': _first(summary.get('os'), payload.get('os'), _get(payload, 'system.os')) or 'Not reported',
        'primary_ip': _first(summary.get('primary_ip'), summary.get('ip'), network.get('primary_ip'), payload.get('primary_ip')) or 'Not reported',
        'all_ips': _first(summary.get('all_ips'), network.get('all_ips'), payload.get('all_ips')) or [],
        'cpu_percent': _float(_first(summary.get('cpu_percent'), _get(payload, 'cpu.percent'), payload.get('cpu_percent')), 0),
        'cpu_temp_c': _first(summary.get('cpu_temp_c'), _get(payload, 'cpu.temp_c')),
        'ram_percent': _float(_first(summary.get('ram_percent'), _get(payload, 'memory.percent'), payload.get('ram_percent')), 0),
        'ram_total_gb': _float(_first(summary.get('ram_total_gb'), _get(payload, 'memory.total_gb')), 0),
        'ram_used_gb': _float(_first(summary.get('ram_used_gb'), _get(payload, 'memory.used_gb')), 0),
        'ram_free_gb': _float(_first(summary.get('ram_free_gb'), _get(payload, 'memory.free_gb')), 0),
        'disk_max_percent': _float(_first(summary.get('disk_max_percent'), _get(payload, 'disk.max_percent')), 0),
        'gpu_names': _first(summary.get('gpu_names'), _get(payload, 'gpu.names'), payload.get('gpu_names')) or [],
        'gpu_count': _int(_first(summary.get('gpu_count'), _get(payload, 'gpu.count')), 0),
        'gpu_max_usage': _first(summary.get('gpu_max_usage'), _get(payload, 'gpu.max_usage')),
        'gpu_max_temp_c': _first(summary.get('gpu_max_temp_c'), _get(payload, 'gpu.max_temp_c')),
        'gpu_total_memory_mb': _float(_first(summary.get('gpu_total_memory_mb'), _get(payload, 'gpu.total_memory_mb')), 0),
        'wan_download_mbps': _float(_first(summary.get('wan_download_mbps'), summary.get('current_download_mbps'), payload.get('wan_download_mbps')), 0),
        'wan_upload_mbps': _float(_first(summary.get('wan_upload_mbps'), summary.get('current_upload_mbps'), payload.get('wan_upload_mbps')), 0),
        'today_download_gb': _float(_first(summary.get('today_download_gb'), payload.get('today_download_gb')), 0),
        'today_upload_gb': _float(_first(summary.get('today_upload_gb'), payload.get('today_upload_gb')), 0),
        'traffic_date': _first(summary.get('traffic_date'), payload.get('traffic_date')) or '',
        'vpn_active': bool(_first(summary.get('vpn_active'), payload.get('vpn_active'), False)),
        'isp_name': _first(summary.get('isp_name'), payload.get('isp_name')) or 'Not reported',
        'public_ip': _first(summary.get('public_ip'), payload.get('public_ip')) or 'Not reported',
        'adapter_count': _int(_first(summary.get('adapter_count'), _get(payload, 'network.adapter_count')), 0),
        'software_count': _int(_first(summary.get('software_count'), _get(payload, 'software.count')), 0),
        'usb_count': _int(_first(summary.get('usb_count'), _get(payload, 'usb.count')), 0),
        'raw_summary': summary,
        'raw_payload_keys': list(payload.keys()) if isinstance(payload, dict) else [],
    }


def _latest_rows(limit: int = 500) -> List[Dict[str, Any]]:
    with _connect_ro() as con:
        if not _table_exists(con, 'latest'):
            return []
        cols = _columns(con, 'latest')
        order = 'updated_at DESC' if 'updated_at' in cols else 'rowid DESC'
        q = f'SELECT * FROM latest ORDER BY {order} LIMIT ?'
        return [_machine_from_latest(r) for r in con.execute(q, (limit,)).fetchall()]


def status() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        'ok': False,
        'mode': 'read_only_2278_source',
        'source_db': str(SOURCE_2278_DB),
        'source_db_exists': SOURCE_2278_DB.exists(),
        'no_write_to_2278': True,
        'api_2278_auth_note': '2278 HTTP APIs may return 401. V10 connector reads SQLite DB in read-only mode.',
    }
    if not SOURCE_2278_DB.exists():
        out['error'] = '2278 DB not found'
        return out
    try:
        with _connect_ro() as con:
            tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'").fetchall()]
            out['tables'] = tables
            counts = {}
            for t in ['latest', 'heartbeats', 'notifications', 'notification_rules', 'change_events', 'client_messages', 'client_message_receipts', 'users']:
                if t in tables:
                    counts[t] = con.execute(f'select count(*) c from {t}').fetchone()['c']
            out['counts'] = counts
            newest = None
            if 'latest' in tables and counts.get('latest', 0) > 0:
                cols = _columns(con, 'latest')
                if 'updated_at' in cols:
                    row = con.execute('select updated_at from latest order by updated_at desc limit 1').fetchone()
                    newest = row['updated_at'] if row else None
            out['newest_latest_at'] = newest
            out['newest_age_minutes'] = _age_minutes(newest)
            out['data_fresh'] = out['newest_age_minutes'] is not None and out['newest_age_minutes'] <= 10
            out['freshness_note'] = 'fresh if newest latest row age <= 10 minutes; stale means clients may not be posting now or latest table has old rows.'
            out['ok'] = True
    except Exception as e:
        out['error'] = str(e)
    return out


def machines(limit: int = 500) -> Dict[str, Any]:
    rows = _latest_rows(limit)
    online = len([r for r in rows if r.get('fresh')])
    issue = len([r for r in rows if _float(r.get('cpu_percent'),0) >= 90 or _float(r.get('ram_percent'),0) >= 90 or _float(r.get('disk_max_percent'),0) >= 90])
    return {
        'ok': True,
        'source': '2278_monitor_db_read_only_latest',
        'source_db': str(SOURCE_2278_DB),
        'total': len(rows),
        'online_by_10min_freshness': online,
        'stale_or_offline': max(0, len(rows) - online),
        'issue_count': issue,
        'machines': rows,
    }


def traffic_kpi_from_2278() -> Dict[str, Any]:
    rows = _latest_rows(1000)
    today = _now_utc().astimezone().date().isoformat()
    # Prefer today's traffic_date rows. If no today's row exists, use latest rows but flag stale.
    today_rows = [r for r in rows if str(r.get('traffic_date') or '').startswith(today)]
    use_rows = today_rows or rows
    return {
        'ok': True,
        'source': '2278_monitor_db_read_only_latest_no_dummy',
        'today': today,
        'used_today_rows': bool(today_rows),
        'stale_warning': None if today_rows else 'No traffic_date rows for today in 2278 latest; showing latest reported values only.',
        'clients_count': len(use_rows),
        'today_download_gb': round(sum(_float(r.get('today_download_gb'),0) for r in use_rows), 2),
        'today_upload_gb': round(sum(_float(r.get('today_upload_gb'),0) for r in use_rows), 2),
        'current_download_mbps': round(sum(_float(r.get('wan_download_mbps'),0) for r in use_rows), 2),
        'current_upload_mbps': round(sum(_float(r.get('wan_upload_mbps'),0) for r in use_rows), 2),
        'per_machine': use_rows,
        'cards': [
            {'label':'Today Download','unit':'GB','sub':'All clients'},
            {'label':'Today Upload','unit':'GB','sub':'All clients'},
            {'label':'Current Download','unit':'Mbps','sub':'Live client traffic'},
            {'label':'Current Upload','unit':'Mbps','sub':'Live client traffic'},
        ],
    }


def _read_table(table: str, limit: int = 200) -> List[Dict[str, Any]]:
    with _connect_ro() as con:
        if not _table_exists(con, table):
            return []
        cols = _columns(con, table)
        order = 'id DESC' if 'id' in cols else ('created_at DESC' if 'created_at' in cols else 'rowid DESC')
        q = f'SELECT * FROM {table} ORDER BY {order} LIMIT ?'
        return [_rowdict(r) for r in con.execute(q, (limit,)).fetchall()]


def notifications(limit: int = 100) -> Dict[str, Any]:
    return {
        'ok': True,
        'source': '2278_monitor_db_read_only',
        'notifications': _read_table('notifications', limit),
        'notification_rules': _read_table('notification_rules', 100),
        'client_messages': _read_table('client_messages', 100),
    }


def evaluate_notifications() -> Dict[str, Any]:
    rows = _latest_rows(1000)
    rules = _read_table('notification_rules', 100)
    alerts: List[Dict[str, Any]] = []
    for m in rows:
        hn = m.get('hostname') or m.get('machine_id')
        cpu = _float(m.get('cpu_percent'),0)
        ram = _float(m.get('ram_percent'),0)
        disk = _float(m.get('disk_max_percent'),0)
        cput = _float(m.get('cpu_temp_c'),0)
        gput = _float(m.get('gpu_max_temp_c'),0)
        if cpu >= 90 and ram >= 90:
            alerts.append({'machine_id':m.get('machine_id'),'hostname':hn,'rule':'cpu_ram_critical','severity':'critical','message':f'CPU {cpu}% and RAM {ram}% critical'})
        if disk >= 90:
            alerts.append({'machine_id':m.get('machine_id'),'hostname':hn,'rule':'disk_high','severity':'warning','message':f'Disk usage {disk}% high'})
        if cput >= 90:
            alerts.append({'machine_id':m.get('machine_id'),'hostname':hn,'rule':'cpu_temp_high','severity':'critical','message':f'CPU temperature {cput}C high'})
        if gput >= 90:
            alerts.append({'machine_id':m.get('machine_id'),'hostname':hn,'rule':'gpu_temp_high','severity':'critical','message':f'GPU temperature {gput}C high'})
    return {
        'ok': True,
        'mode': 'read_only_simulation_no_write',
        'source': '2278 latest + 2278 notification_rules',
        'rules_count': len(rules),
        'recent_notifications_count': len(_read_table('notifications', 100)),
        'machines_checked': len(rows),
        'simulated_alerts_count': len(alerts),
        'simulated_alerts': alerts[:100],
        'note': 'This endpoint tests notification logic without writing to 2278 or V10 notification tables.'
    }


def export_machines_csv(data: Dict[str, Any]) -> bytes:
    out = io.StringIO()
    fields = ['machine_id','hostname','os','primary_ip','updated_at','age_minutes','fresh','cpu_percent','cpu_temp_c','ram_percent','ram_total_gb','ram_used_gb','ram_free_gb','disk_max_percent','gpu_count','gpu_names','wan_download_mbps','wan_upload_mbps','today_download_gb','today_upload_gb','vpn_active','isp_name','public_ip','software_count','usb_count']
    w = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    for r in data.get('machines') or []:
        rr = dict(r)
        if isinstance(rr.get('gpu_names'), list):
            rr['gpu_names'] = '; '.join(map(str, rr['gpu_names']))
        w.writerow(rr)
    return out.getvalue().encode('utf-8-sig')


def _send_csv(handler: Any, body: bytes, filename: str) -> None:
    if hasattr(handler, '_send'):
        return handler._send(200, body, 'text/csv; charset=utf-8', {'Content-Disposition': f'attachment; filename={filename}'})
    handler.send_response(200)
    handler.send_header('Content-Type', 'text/csv; charset=utf-8')
    handler.send_header('Content-Disposition', f'attachment; filename={filename}')
    handler.end_headers()
    handler.wfile.write(body)


def install(Handler: Any, base_dir: Any) -> None:
    global BASE_DIR, SOURCE_2278_DB
    BASE_DIR = Path(base_dir)
    # Allow override from env or settings file later, but default is protected 2278 DB.
    SOURCE_2278_DB = Path(os.environ.get('V10_SOURCE_2278_DB', r'D:\SagarSystemHealthMonitor\data\monitor.db'))
    old_get = Handler.do_GET

    def new_get(self):
        path = self.path.split('?', 1)[0]
        try:
            if path in ('/api/v10/source2278/status', '/api/v10/live-source2278/status'):
                return self.send_json(status())
            if path in ('/api/v10/source2278/machines', '/api/v10/live-source2278/machines'):
                return self.send_json(machines())
            if path in ('/api/v10/source2278/notifications', '/api/v10/live-source2278/notifications'):
                return self.send_json(notifications())
            if path in ('/api/v10/source2278/notification-test', '/api/v10/live-source2278/notification-test'):
                return self.send_json(evaluate_notifications())
            if path in ('/api/v10/source2278/home-traffic-kpi', '/api/v10/live-source2278/home-traffic-kpi'):
                return self.send_json(traffic_kpi_from_2278())
            if path in ('/api/v10/source2278/machines/export.csv', '/api/v10/live-source2278/machines/export.csv'):
                return _send_csv(self, export_machines_csv(machines()), 'source2278_live_machines_readonly.csv')
        except Exception as e:
            try:
                return self.send_json({'ok': False, 'error': str(e), 'source_db': str(SOURCE_2278_DB)}, 500)
            except Exception:
                raise
        return old_get(self)

    Handler.do_GET = new_get
