from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict, List, Optional

BASE_DIR: Path = Path('.')
SOURCE_2278_DB: Path = Path(r'D:\SagarSystemHealthMonitor\data\monitor.db')


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _connect_ro() -> sqlite3.Connection:
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
        if v is None:
            continue
        if isinstance(v, str):
            if v.strip() == '' or v.strip().lower() in ('none','null','not reported','not reported by client','n/a'):
                continue
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
            for suf in ['mbps', 'gb', '%', 'c', 'mb']:
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
    return round((_now_utc() - d).total_seconds()/60, 2)


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    return bool(con.execute("select name from sqlite_master where type='table' and name=?", (name,)).fetchone())


def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    try:
        return [r[1] for r in con.execute(f'PRAGMA table_info({table})').fetchall()]
    except Exception:
        return []


def _rowdict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _as_list(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        for key in ('items','software','installed','installed_software','programs','apps','packages','list','rows','data'):
            if isinstance(v.get(key), list):
                return v.get(key) or []
        # dict of name -> version/details
        out = []
        for k, val in v.items():
            if isinstance(val, dict):
                x = dict(val)
                x.setdefault('name', k)
                out.append(x)
            elif isinstance(val, (str, int, float)):
                out.append({'name': k, 'version': val})
        return out
    if isinstance(v, str):
        # Do not split long text aggressively; one name is safer than fake rows.
        return [{'name': v}]
    return [v]


def _extract_payload(summary: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    payload = _safe_json(row.get('payload_json'), {})
    if isinstance(summary.get('payload'), dict):
        payload = summary.get('payload') or payload
    if not isinstance(payload, dict):
        payload = {}
    return payload


def _software_candidates(summary: Dict[str, Any], payload: Dict[str, Any]) -> List[Any]:
    candidates = [
        payload.get('software'),
        payload.get('installed_software'),
        payload.get('installedSoftware'),
        payload.get('programs'),
        payload.get('apps'),
        payload.get('packages'),
        payload.get('applications'),
        _get(payload, 'inventory.software'),
        _get(payload, 'inventory.installed_software'),
        _get(payload, 'software.installed'),
        _get(payload, 'software.items'),
        _get(payload, 'software.list'),
        summary.get('software'),
        summary.get('installed_software'),
    ]
    for c in candidates:
        if c:
            return _as_list(c)
    return []


def _norm_sw(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'name': x, 'version': '', 'publisher': '', 'source': 'client_reported_name_only'}
    if not isinstance(x, dict):
        return {'name': str(x), 'version': '', 'publisher': '', 'source': 'client_reported_value'}
    return {
        'name': _first(x.get('name'), x.get('display_name'), x.get('DisplayName'), x.get('package'), x.get('app'), x.get('title')) or 'Unknown software',
        'version': _first(x.get('version'), x.get('DisplayVersion'), x.get('display_version'), x.get('app_version')) or '',
        'publisher': _first(x.get('publisher'), x.get('Publisher'), x.get('vendor'), x.get('manufacturer')) or '',
        'install_date': _first(x.get('install_date'), x.get('InstallDate'), x.get('installed_at'), x.get('date')) or '',
        'install_location': _first(x.get('install_location'), x.get('InstallLocation'), x.get('path'), x.get('location')) or '',
        'uninstall_string': _first(x.get('uninstall_string'), x.get('UninstallString')) or '',
        'architecture': _first(x.get('architecture'), x.get('arch')) or '',
        'license_key': _first(x.get('license_key'), x.get('key')) or '',
        'license_type': _first(x.get('license_type'), x.get('license')) or '',
        'status': _first(x.get('status'), x.get('state')) or 'Reported by client',
        'source': _first(x.get('source'), x.get('source_type')) or '2278 latest payload',
    }


def _machine_software(row: sqlite3.Row, include_items: bool = False) -> Dict[str, Any]:
    rd = _rowdict(row)
    summary = _safe_json(rd.get('summary_json'), {})
    payload = _extract_payload(summary, rd)
    updated_at = _first(rd.get('updated_at'), summary.get('updated_at'), summary.get('timestamp'), payload.get('timestamp'))
    age = _age_minutes(updated_at)
    raw_items = _software_candidates(summary, payload)
    items = [_norm_sw(x) for x in raw_items]
    reported_count = _int(_first(summary.get('software_count'), payload.get('software_count'), len(items)), 0)
    machine = {
        'machine_id': _first(rd.get('machine_id'), summary.get('machine_id'), payload.get('machine_id')) or '',
        'hostname': _first(rd.get('hostname'), summary.get('hostname'), payload.get('hostname'), _get(payload,'system.hostname')) or '',
        'updated_at': updated_at or '',
        'age_minutes': age,
        'fresh': age is not None and age <= 10,
        'os': _first(summary.get('os'), payload.get('os'), _get(payload,'system.os'), _get(payload,'system.platform')) or 'Not reported',
        'primary_ip': _first(summary.get('primary_ip'), _get(payload,'network.primary_ip'), payload.get('primary_ip')) or 'Not reported',
        'software_count_reported': reported_count,
        'software_items_extracted': len(items),
        'software_detail_status': 'Full list reported by client' if len(items) else ('Count only reported by client' if reported_count else 'Not reported by client'),
        'source': '2278 latest.summary_json read-only',
        'raw_summary_keys': list(summary.keys()) if isinstance(summary, dict) else [],
        'raw_payload_keys': list(payload.keys()) if isinstance(payload, dict) else [],
    }
    if include_items:
        machine['software'] = items
    return machine


def _latest_rows(limit: int = 1000, include_items: bool = False) -> List[Dict[str, Any]]:
    with _connect_ro() as con:
        if not _table_exists(con, 'latest'):
            return []
        cols = _columns(con, 'latest')
        order = 'updated_at DESC' if 'updated_at' in cols else 'rowid DESC'
        return [_machine_software(r, include_items=include_items) for r in con.execute(f'SELECT * FROM latest ORDER BY {order} LIMIT ?', (limit,)).fetchall()]


def software_status() -> Dict[str, Any]:
    out = {'ok': False, 'mode': '2278_software_read_only', 'source_db': str(SOURCE_2278_DB), 'no_write_to_2278': True, 'source_db_exists': SOURCE_2278_DB.exists()}
    if not SOURCE_2278_DB.exists():
        out['error'] = '2278 DB not found'
        return out
    try:
        rows = _latest_rows(2000, include_items=True)
        out.update({
            'ok': True,
            'machines_checked': len(rows),
            'fresh_machines': len([r for r in rows if r.get('fresh')]),
            'stale_machines': len([r for r in rows if not r.get('fresh')]),
            'machines_with_software_count': len([r for r in rows if (r.get('software_count_reported') or 0) > 0]),
            'machines_with_software_detail_list': len([r for r in rows if (r.get('software_items_extracted') or 0) > 0]),
            'reported_software_count_total': sum(_int(r.get('software_count_reported'), 0) for r in rows),
            'extracted_software_rows_total': sum(_int(r.get('software_items_extracted'), 0) for r in rows),
            'note': 'Software data is read-only from 2278 latest.summary_json. If only count is available, client did not report full installed software list in latest payload. Values are not faked.',
        })
    except Exception as e:
        out['error'] = str(e)
    return out


def software_list(q: str = '', machine_id: str = '', limit: int = 500, freshness: str = 'all', with_items: bool = True) -> Dict[str, Any]:
    rows = _latest_rows(2000, include_items=True)
    if freshness == 'fresh':
        rows = [r for r in rows if r.get('fresh')]
    elif freshness == 'stale':
        rows = [r for r in rows if not r.get('fresh')]
    mid = (machine_id or '').strip().lower()
    if mid:
        rows = [r for r in rows if str(r.get('machine_id','')).lower() == mid or str(r.get('hostname','')).lower() == mid]
    ql = (q or '').strip().lower()
    flat: List[Dict[str, Any]] = []
    for r in rows:
        for sw in (r.get('software') or []):
            item = dict(sw)
            item['machine_id'] = r.get('machine_id')
            item['hostname'] = r.get('hostname')
            item['os'] = r.get('os')
            item['machine_updated_at'] = r.get('updated_at')
            if ql:
                blob = ' '.join(str(item.get(k,'')) for k in ['name','version','publisher','install_location','license_type','hostname','machine_id']).lower()
                if ql not in blob:
                    continue
            flat.append(item)
    flat = flat[:max(1, min(limit, 10000))]
    machines_out = []
    for r in rows[:max(1, min(limit, 2000))]:
        rr = dict(r)
        if not with_items and 'software' in rr:
            rr.pop('software', None)
        machines_out.append(rr)
    return {
        'ok': True,
        'source': '2278_monitor_db_read_only_latest_software',
        'source_db': str(SOURCE_2278_DB),
        'no_write_to_2278': True,
        'query': q,
        'machine_id': machine_id,
        'freshness': freshness,
        'count_machines': len(machines_out),
        'count_software_rows': len(flat),
        'summary': software_status(),
        'machines': machines_out,
        'software': flat,
    }


def export_csv(data: Dict[str, Any]) -> bytes:
    out = io.StringIO()
    fields = ['machine_id','hostname','os','machine_updated_at','name','version','publisher','install_date','install_location','architecture','license_type','license_key','status','source']
    w = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    software = data.get('software') or []
    if software:
        for r in software:
            w.writerow(r)
    else:
        # CSV still useful when client reports only counts.
        w2_fields = ['machine_id','hostname','updated_at','fresh','os','primary_ip','software_count_reported','software_items_extracted','software_detail_status','source']
        out = io.StringIO()
        w2 = csv.DictWriter(out, fieldnames=w2_fields, extrasaction='ignore')
        w2.writeheader()
        for r in data.get('machines') or []:
            w2.writerow(r)
    return out.getvalue().encode('utf-8-sig')


def sample_csv() -> bytes:
    out = io.StringIO()
    fields = ['software_name','version','publisher','license_type','license_key','assigned_machine','assigned_user','purchase_date','invoice_no','po_no','expiry_date','status','remarks']
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    w.writerow({'software_name':'Microsoft Office','version':'2021','publisher':'Microsoft','license_type':'Volume/OEM/Subscription','license_key':'Store securely / optional','assigned_machine':'HOSTNAME','assigned_user':'User name','purchase_date':'2026-07-03','invoice_no':'INV-001','po_no':'PO-001','expiry_date':'2027-07-03','status':'Active','remarks':'Sample row only'})
    return out.getvalue().encode('utf-8-sig')


def _send_json(handler: Any, data: Dict[str, Any], status: int = 200) -> None:
    if hasattr(handler, 'send_json'):
        return handler.send_json(data, status)
    body = json.dumps(data, default=str).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type','application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _send_csv(handler: Any, body: bytes, filename: str) -> None:
    if hasattr(handler, '_send'):
        return handler._send(200, body, 'text/csv; charset=utf-8', {'Content-Disposition': f'attachment; filename={filename}'})
    handler.send_response(200)
    handler.send_header('Content-Type','text/csv; charset=utf-8')
    handler.send_header('Content-Disposition', f'attachment; filename={filename}')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def install(Handler: Any, base_dir: Any) -> None:
    global BASE_DIR, SOURCE_2278_DB
    BASE_DIR = Path(base_dir)
    SOURCE_2278_DB = Path(os.environ.get('V10_SOURCE_2278_DB', r'D:\SagarSystemHealthMonitor\data\monitor.db'))
    old_get = Handler.do_GET
    def new_get(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query or '')
        try:
            if path in ('/api/v10/source2278/software/status','/api/v10/software2278/status'):
                return _send_json(self, software_status())
            if path in ('/api/v10/source2278/software','/api/v10/software2278/list'):
                q = (qs.get('q') or [''])[0]
                mid = (qs.get('machine_id') or qs.get('hostname') or [''])[0]
                freshness = (qs.get('freshness') or ['all'])[0]
                limit = _int((qs.get('limit') or ['500'])[0], 500)
                with_items = str((qs.get('with_items') or ['1'])[0]).lower() not in ('0','false','no')
                return _send_json(self, software_list(q, mid, limit, freshness, with_items))
            if path in ('/api/v10/source2278/software/export.csv','/api/v10/software2278/export.csv'):
                q = (qs.get('q') or [''])[0]
                mid = (qs.get('machine_id') or qs.get('hostname') or [''])[0]
                freshness = (qs.get('freshness') or ['all'])[0]
                body = export_csv(software_list(q, mid, 10000, freshness, True))
                return _send_csv(self, body, 'v10_2278_readonly_live_software.csv')
            if path in ('/api/v10/source2278/software/sample.csv','/api/v10/software2278/sample.csv'):
                return _send_csv(self, sample_csv(), 'v10_software_asset_register_sample.csv')
        except Exception as e:
            return _send_json(self, {'ok': False, 'error': str(e), 'source_db': str(SOURCE_2278_DB), 'no_write_to_2278': True}, 500)
        return old_get(self)
    Handler.do_GET = new_get
