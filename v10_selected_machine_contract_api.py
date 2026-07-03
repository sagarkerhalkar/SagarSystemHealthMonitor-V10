from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

BASE_DIR: Path = Path('.')
SOURCE_2278_DB: Path = Path(r'D:\SagarSystemHealthMonitor\data\monitor.db')


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _load_module(name: str, filename: str):
    p = Path(BASE_DIR) / filename
    spec = importlib.util.spec_from_file_location(name, str(p))
    if not spec or not spec.loader:
        raise RuntimeError(f'Cannot import {filename}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.BASE_DIR = Path(BASE_DIR)
        mod.SOURCE_2278_DB = SOURCE_2278_DB
    except Exception:
        pass
    return mod


def _connect_ro() -> sqlite3.Connection:
    uri = 'file:' + str(SOURCE_2278_DB).replace('\\','/') + '?mode=ro'
    con = sqlite3.connect(uri, uri=True, timeout=10)
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
        if isinstance(v, str) and (v.strip()=='' or v.strip().lower() in ('none','null','not reported','not reported by client','n/a')):
            continue
        return v
    return None


def _float(v: Any, default: float=0.0) -> float:
    try:
        if v is None or v=='':
            return default
        if isinstance(v, str):
            v=v.strip().replace(',','')
            for suf in ['mbps','gb','%','c','mb']:
                if v.lower().endswith(suf):
                    v=v[:-len(suf)].strip()
        return float(v)
    except Exception:
        return default


def _int(v: Any, default: int=0) -> int:
    try:
        if v is None or v=='': return default
        return int(float(str(v).strip()))
    except Exception:
        return default


def _iso_parse(s: Any) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        txt=str(s).strip()
        if txt.endswith('Z'):
            txt=txt[:-1] + '+00:00'
        d=dt.datetime.fromisoformat(txt)
        if d.tzinfo is None:
            d=d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


def _age_minutes(s: Any) -> Optional[float]:
    d=_iso_parse(s)
    if not d: return None
    return round((_now_utc()-d).total_seconds()/60, 2)


def _monitor_hostname() -> str:
    return (os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or '').strip().lower()


def _is_monitor_server(m: Dict[str,Any]) -> bool:
    h=str(m.get('hostname') or '').strip().lower()
    mid=str(m.get('machine_id') or '').strip().lower()
    # Current Windows server usually appears here when the client agent is also installed.
    known = {_monitor_hostname(), 'desktop-1vtkp12'}
    known = {x for x in known if x}
    return bool(h and h in known) or bool(mid and any(k and k in mid for k in known))


def _hw_mod():
    return _load_module('v10_hardware_2278_readonly_api_contract', 'v10_hardware_2278_readonly_api.py')


def _sw_mod():
    return _load_module('v10_software_2278_readonly_api_contract', 'v10_software_2278_readonly_api.py')


def _hardware_rows() -> List[Dict[str,Any]]:
    data = _hw_mod().hardware_list('', 2000, 'all')
    rows = data.get('machines') or []
    for m in rows:
        m['is_monitor_server'] = _is_monitor_server(m)
    rows.sort(key=lambda m: (1 if m.get('is_monitor_server') else 0, 0 if m.get('fresh') else 1, str(m.get('hostname') or '').lower()))
    return rows


def _match_machine(rows: List[Dict[str,Any]], machine_id: str='', query: str='', hostname: str='') -> Optional[Dict[str,Any]]:
    keys = [machine_id, hostname, query]
    keys = [str(k).strip() for k in keys if str(k or '').strip()]
    if not keys:
        return None
    # Exact machine_id first. This is the locked contract.
    for k in keys:
        kl = k.lower()
        for r in rows:
            if str(r.get('machine_id','')).lower() == kl:
                return r
    # Exact hostname second.
    for k in keys:
        kl = k.lower()
        for r in rows:
            if str(r.get('hostname','')).lower() == kl:
                return r
    # Then old identity/fingerprint/IP contains.
    for k in keys:
        kl = k.lower()
        for r in rows:
            blob = ' '.join(str(r.get(x,'')) for x in ['machine_id','hostname','id_value','primary_ip','os']).lower()
            if kl in blob:
                return r
    return None


def _default_machine(rows: List[Dict[str,Any]]) -> Optional[Dict[str,Any]]:
    return next((r for r in rows if r.get('fresh') and not r.get('is_monitor_server')), None) or next((r for r in rows if not r.get('is_monitor_server')), None) or (rows[0] if rows else None)


def selected_list() -> Dict[str,Any]:
    rows = _hardware_rows()
    clients = [m for m in rows if not m.get('is_monitor_server')]
    fresh_clients = [m for m in clients if m.get('fresh')]
    stale_clients = [m for m in clients if not m.get('fresh')]
    default = _default_machine(rows)
    return {
        'ok': True,
        'source': '2278_readonly_selected_machine_contract',
        'source_db': str(SOURCE_2278_DB),
        'no_write_to_2278': True,
        'contract': 'Every detail endpoint must return exactly the requested machine_id; server is separated from client machines.',
        'total_machines_in_2278': len(rows),
        'client_machines': len(clients),
        'fresh_clients': len(fresh_clients),
        'stale_clients': len(stale_clients),
        'monitor_server_count': len(rows) - len(clients),
        'default_machine_id': default.get('machine_id') if default else '',
        'machines': rows,
    }


def selected_hardware(machine_id: str='', query: str='', hostname: str='') -> Dict[str,Any]:
    rows = _hardware_rows()
    m = _match_machine(rows, machine_id, query, hostname) or _default_machine(rows)
    if not m:
        return {'ok': False, 'error': 'No machine found in 2278 read-only source', 'requested_machine_id': machine_id, 'requested_query': query}
    requested = machine_id or hostname or query or m.get('machine_id')
    exact = (str(m.get('machine_id')) == str(machine_id)) if machine_id else True
    return {
        'ok': True,
        'source': '2278_readonly_selected_machine_hardware',
        'source_db': str(SOURCE_2278_DB),
        'no_write_to_2278': True,
        'requested': requested,
        'requested_machine_id': machine_id,
        'returned_machine_id': m.get('machine_id'),
        'returned_hostname': m.get('hostname'),
        'exact_machine_id_match': exact,
        'machine': m,
    }


def selected_software(machine_id: str='', query: str='', hostname: str='', sw_query: str='', limit: int=1000) -> Dict[str,Any]:
    hw = selected_hardware(machine_id, query, hostname)
    if not hw.get('ok'):
        return hw
    m = hw['machine']
    # Read software by exact machine_id. If old software API doesn't match, fallback to hostname.
    data = _sw_mod().software_list(sw_query, str(m.get('machine_id') or ''), max(1,min(limit,10000)), 'all', True)
    software = data.get('software') or []
    if not software:
        data2 = _sw_mod().software_list(sw_query, str(m.get('hostname') or ''), max(1,min(limit,10000)), 'all', True)
        software = data2.get('software') or []
    return {
        'ok': True,
        'source': '2278_readonly_selected_machine_software',
        'source_db': str(SOURCE_2278_DB),
        'no_write_to_2278': True,
        'requested_machine_id': machine_id,
        'returned_machine_id': m.get('machine_id'),
        'returned_hostname': m.get('hostname'),
        'software_count': len(software),
        'reported_software_count': m.get('software_count'),
        'machine': m,
        'software': software,
    }


def selected_network(machine_id: str='', query: str='', hostname: str='') -> Dict[str,Any]:
    hw = selected_hardware(machine_id, query, hostname)
    if not hw.get('ok'):
        return hw
    m = hw['machine']
    return {
        'ok': True,
        'source': '2278_readonly_selected_machine_network',
        'source_db': str(SOURCE_2278_DB),
        'no_write_to_2278': True,
        'requested_machine_id': machine_id,
        'returned_machine_id': m.get('machine_id'),
        'returned_hostname': m.get('hostname'),
        'hostname': m.get('hostname'),
        'primary_ip': m.get('primary_ip'),
        'all_ips': m.get('all_ips') or [],
        'public_ip': m.get('public_ip'),
        'isp_name': m.get('isp_name'),
        'vpn_active': m.get('vpn_active'),
        'adapter_count': len(m.get('network_adapters') or []),
        'network_adapters': m.get('network_adapters') or [],
        'machine': m,
    }


def home_summary() -> Dict[str,Any]:
    rows = _hardware_rows()
    clients = [m for m in rows if not m.get('is_monitor_server')]
    fresh = [m for m in clients if m.get('fresh')]
    stale = [m for m in clients if not m.get('fresh')]
    today = _now_utc().astimezone().date().isoformat()
    today_rows = [m for m in clients if str(m.get('traffic_date') or '').startswith(today)]
    use_rows = today_rows or clients
    issue_rows = [m for m in clients if _float(m.get('cpu_percent')) >= 90 or _float(m.get('ram_percent')) >= 90 or _float(m.get('disk_max_percent')) >= 90]
    return {
        'ok': True,
        'source': '2278_readonly_home_contract_no_dummy',
        'source_db': str(SOURCE_2278_DB),
        'no_write_to_2278': True,
        'total_2278_rows': len(rows),
        'client_machines': len(clients),
        'fresh_clients': len(fresh),
        'stale_clients': len(stale),
        'monitor_server_count': len(rows)-len(clients),
        'issue_clients': len(issue_rows),
        'today': today,
        'used_today_rows': bool(today_rows),
        'traffic_note': None if today_rows else 'No traffic_date rows for today; showing latest reported values only.',
        'today_download_gb': round(sum(_float(m.get('today_download_gb')) for m in use_rows), 2),
        'today_upload_gb': round(sum(_float(m.get('today_upload_gb')) for m in use_rows), 2),
        'current_download_mbps': round(sum(_float(m.get('wan_download_mbps')) for m in use_rows if m.get('fresh') or not today_rows), 2),
        'current_upload_mbps': round(sum(_float(m.get('wan_upload_mbps')) for m in use_rows if m.get('fresh') or not today_rows), 2),
        'fresh_machine_cards': fresh[:12],
        'issue_machines': issue_rows[:50],
        'monitor_servers': [m for m in rows if m.get('is_monitor_server')],
    }


def notification_fast() -> Dict[str,Any]:
    rows = _hardware_rows()
    # Fast bounded simulation; no DB writes. Avoids old endpoint timeout.
    alerts = []
    for m in rows:
        if _is_monitor_server(m):
            continue
        if _float(m.get('disk_max_percent')) >= 90:
            alerts.append({'machine_id': m.get('machine_id'), 'hostname': m.get('hostname'), 'rule': 'disk_high', 'severity': 'warning', 'message': f"Disk usage {m.get('disk_max_percent')}% high"})
        if _float(m.get('cpu_percent')) >= 90:
            alerts.append({'machine_id': m.get('machine_id'), 'hostname': m.get('hostname'), 'rule': 'cpu_ram_critical', 'severity': 'critical', 'message': f"CPU usage {m.get('cpu_percent')}% critical"})
        if _float(m.get('ram_percent')) >= 95:
            alerts.append({'machine_id': m.get('machine_id'), 'hostname': m.get('hostname'), 'rule': 'cpu_ram_critical', 'severity': 'critical', 'message': f"RAM usage {m.get('ram_percent')}% critical"})
    rules_count = 0
    recent_notifications_count = 0
    try:
        with _connect_ro() as con:
            tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
            if 'notification_rules' in tabs:
                rules_count = con.execute('select count(*) c from notification_rules').fetchone()['c']
            if 'notifications' in tabs:
                recent_notifications_count = con.execute('select count(*) c from (select 1 from notifications limit 100)').fetchone()['c']
    except Exception:
        pass
    return {
        'ok': True,
        'mode': 'fast_read_only_simulation_no_write',
        'source': '2278 latest + notification_rules count',
        'rules_count': rules_count,
        'recent_notifications_count': recent_notifications_count,
        'machines_checked': len(rows),
        'simulated_alerts_count': len(alerts),
        'simulated_alerts': alerts[:100],
        'note': 'Fast endpoint tests notification logic without writing to 2278 or V10 tables and cannot block UI.',
    }


def _send_json(handler: Any, data: Dict[str, Any], status: int=200) -> None:
    if hasattr(handler, 'send_json'):
        return handler.send_json(data, status)
    body=json.dumps(data, default=str).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type','application/json; charset=utf-8')
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
            machine_id = (qs.get('machine_id') or [''])[0]
            hostname = (qs.get('hostname') or [''])[0]
            query = (qs.get('query') or qs.get('q') or [''])[0]
            swq = (qs.get('software_query') or qs.get('sw_query') or qs.get('q') or [''])[0]
            limit = _int((qs.get('limit') or ['1000'])[0], 1000)
            if path == '/api/v10/selected-machine/list':
                return _send_json(self, selected_list())
            if path == '/api/v10/selected-machine/hardware':
                return _send_json(self, selected_hardware(machine_id, query, hostname))
            if path == '/api/v10/selected-machine/software':
                return _send_json(self, selected_software(machine_id, query, hostname, swq, limit))
            if path == '/api/v10/selected-machine/network':
                return _send_json(self, selected_network(machine_id, query, hostname))
            if path == '/api/v10/selected-machine/home':
                return _send_json(self, home_summary())
            if path == '/api/v10/selected-machine/notification-fast':
                return _send_json(self, notification_fast())
            # Compatibility repair: old endpoint now accepts query= as alias of q=.
            if path in ('/api/v10/source2278/hardware','/api/v10/hardware2278/list') and (qs.get('query') and not qs.get('q')):
                freshness = (qs.get('freshness') or ['all'])[0]
                return _send_json(self, _hw_mod().hardware_list(query, min(limit,2000), freshness))
        except Exception as e:
            return _send_json(self, {'ok': False, 'error': str(e), 'source_db': str(SOURCE_2278_DB), 'no_write_to_2278': True}, 500)
        return old_get(self)
    Handler.do_GET = new_get
