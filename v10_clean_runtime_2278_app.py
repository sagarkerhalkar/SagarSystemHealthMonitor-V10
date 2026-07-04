from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse, parse_qs

BASE_DIR = Path('.')
SOURCE_DB = Path(os.environ.get('V10_SOURCE_2278_DB', r'D:\SagarSystemHealthMonitor\data\monitor.db'))


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_json(v: Any, default: Any = None) -> Any:
    if default is None:
        default = {}
    if isinstance(v, (dict, list)):
        return v
    if v is None:
        return default
    try:
        if isinstance(v, bytes):
            v = v.decode('utf-8', 'ignore')
        s = str(v).strip()
        if not s:
            return default
        return json.loads(s)
    except Exception:
        return default


def _s(v: Any, default: str = '') -> str:
    if v is None:
        return default
    try:
        st = str(v).strip()
        return st if st else default
    except Exception:
        return default


def _f(v: Any, default: float | None = None) -> float | None:
    try:
        if v in (None, '', 'Not reported', 'Not reported by client', 'N/A'):
            return default
        return float(str(v).replace('%', '').replace(',', '').strip())
    except Exception:
        return default


def _round(v: Any, nd: int = 2, default: Any = None) -> Any:
    x = _f(v, None)
    if x is None:
        return default
    return round(x, nd)


def _dt(v: Any) -> dt.datetime | None:
    if not v:
        return None
    s = str(v).strip().replace('Z', '+00:00')
    try:
        d = dt.datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


def _pick(d: Any, *keys: str, default: Any = None) -> Any:
    cur = d if isinstance(d, dict) else {}
    for k in keys:
        if isinstance(cur, dict) and k in cur and cur[k] not in (None, ''):
            return cur[k]
    return default


def _deep_get(d: Any, paths: List[Tuple[str, ...]], default: Any = None) -> Any:
    for path in paths:
        cur = d
        ok = True
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                ok = False
                break
        if ok and cur not in (None, ''):
            return cur
    return default


def _as_list(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, tuple):
        return list(v)
    if isinstance(v, dict):
        # if dict of objects, return values, otherwise wrap as one row
        vals = list(v.values())
        if vals and all(isinstance(x, dict) for x in vals):
            return vals
        return [v]
    if isinstance(v, str) and v.strip():
        return [v]
    return []


def _connect_ro() -> sqlite3.Connection:
    db = Path(os.environ.get('V10_SOURCE_2278_DB', str(SOURCE_DB)))
    if not db.exists():
        raise FileNotFoundError(f'2278 DB not found: {db}')
    con = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True, timeout=20)
    con.row_factory = sqlite3.Row
    try:
        con.execute('PRAGMA query_only=ON')
        con.execute('PRAGMA temp_store=MEMORY')
    except Exception:
        pass
    return con


def _row_time(row: sqlite3.Row, summary: Dict[str, Any], payload: Dict[str, Any]) -> str:
    for k in ('updated_at', 'received_at', 'last_seen', 'timestamp', 'created_at'):
        try:
            if k in row.keys() and row[k]:
                return str(row[k])
        except Exception:
            pass
    for obj in (summary, payload):
        for k in ('updated_at', 'received_at', 'last_seen', 'timestamp'):
            if isinstance(obj, dict) and obj.get(k):
                return str(obj.get(k))
    return ''


def _extract_payload(row: sqlite3.Row, summary: Dict[str, Any]) -> Dict[str, Any]:
    payload = {}
    try:
        if 'payload_json' in row.keys():
            payload = _parse_json(row['payload_json'], {})
    except Exception:
        payload = {}
    if not payload and isinstance(summary.get('payload'), dict):
        payload = summary.get('payload') or {}
    return payload if isinstance(payload, dict) else {}


def _normal_disk(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'name': x, 'type': 'Not reported by client', 'mount': x}
    d = x if isinstance(x, dict) else {}
    size = _pick(d, 'size_gb', 'total_gb', 'totalGB', 'total', 'capacity_gb', 'capacityGB')
    used = _pick(d, 'used_gb', 'usedGB', 'used')
    free = _pick(d, 'free_gb', 'freeGB', 'free')
    percent = _pick(d, 'percent', 'used_percent', 'usage_percent', 'usage', 'disk_percent')
    # bytes fallback
    for key, target in [('size_bytes','size'), ('total_bytes','size'), ('used_bytes','used'), ('free_bytes','free')]:
        if d.get(key) is not None:
            gb = _round(float(d.get(key))/1024/1024/1024, 2)
            if target == 'size' and size in (None, ''): size = gb
            if target == 'used' and used in (None, ''): used = gb
            if target == 'free' and free in (None, ''): free = gb
    return {
        'name': _s(_pick(d, 'name', 'device', 'drive', 'letter', 'volume', 'filesystem', 'path'), 'Not reported by client'),
        'model': _s(_pick(d, 'model', 'caption', 'friendly_name'), 'Not reported by client'),
        'type': _s(_pick(d, 'type', 'media_type', 'drive_type', 'kind'), 'Not reported by client'),
        'mount': _s(_pick(d, 'mount', 'mountpoint', 'letter', 'drive', 'path'), _s(_pick(d, 'name', 'device'), 'Not reported by client')),
        'size_gb': _round(size, 2, 'Not reported by client'),
        'used_gb': _round(used, 2, 'Not reported by client'),
        'free_gb': _round(free, 2, 'Not reported by client'),
        'percent': _round(percent, 2, 'Not reported by client'),
        'serial': _s(_pick(d, 'serial', 'serial_number'), 'Not reported by client'),
        'health': _s(_pick(d, 'health', 'status'), 'Not reported by client'),
    }


def _normal_gpu(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'name': x, 'memory_mb': 'Not reported by client', 'usage_percent': 'Not reported by client', 'temperature_c': 'Not reported by client', 'driver': 'Not reported by client'}
    d = x if isinstance(x, dict) else {}
    mem = _pick(d, 'memory_mb', 'total_memory_mb', 'gpu_total_memory_mb', 'memory_total_mb', 'vram_mb', 'adapter_ram_mb')
    usage = _pick(d, 'usage_percent', 'utilization_gpu', 'gpu_usage_percent', 'load_percent', 'usage')
    temp = _pick(d, 'temperature_c', 'temp_c', 'gpu_temp_c', 'temperature')
    return {
        'name': _s(_pick(d, 'name', 'gpu_name', 'caption', 'model'), 'Not reported by client'),
        'memory_mb': _round(mem, 0, 'Not reported by client'),
        'usage_percent': _round(usage, 2, 'Not reported by client'),
        'temperature_c': _round(temp, 2, 'Not reported by client'),
        'driver': _s(_pick(d, 'driver', 'driver_version'), 'Not reported by client'),
        'source': _s(_pick(d, 'source'), 'client payload'),
    }


def _normal_adapter(x: Any) -> Dict[str, Any]:
    d = x if isinstance(x, dict) else {}
    ips = _pick(d, 'ips', 'ip_addresses', 'addresses', 'all_ips')
    if isinstance(ips, str):
        ips = [ips]
    if not isinstance(ips, list):
        ips = []
    dns = _pick(d, 'dns', 'dns_servers')
    if isinstance(dns, str):
        dns = [dns]
    if not isinstance(dns, list):
        dns = []
    return {
        'name': _s(_pick(d, 'name', 'adapter', 'interface', 'description'), 'Not reported by client'),
        'mac': _s(_pick(d, 'mac', 'mac_address', 'physical_address'), 'Not reported by client'),
        'ips': ips,
        'gateway': _s(_pick(d, 'gateway', 'default_gateway'), 'Not reported by client'),
        'dns': dns,
        'status': _s(_pick(d, 'status', 'state', 'oper_status'), 'Not reported by client'),
        'speed': _s(_pick(d, 'speed', 'link_speed', 'speed_mbps'), 'Not reported by client'),
    }


def _normal_usb(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'category': 'Peripheral', 'name': x, 'vendor': 'Not reported by client', 'status': 'Reported by client', 'device_id': ''}
    d = x if isinstance(x, dict) else {}
    return {
        'category': _s(_pick(d, 'category', 'type', 'class'), 'Peripheral'),
        'name': _s(_pick(d, 'name', 'caption', 'description', 'device'), 'Not reported by client'),
        'vendor': _s(_pick(d, 'vendor', 'manufacturer'), 'Not reported by client'),
        'status': _s(_pick(d, 'status'), 'Reported by client'),
        'device_id': _s(_pick(d, 'device_id', 'id', 'pnp_device_id', 'instance_id'), ''),
    }


def _normal_sw(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'name': x, 'version': '', 'publisher': '', 'install_date': '', 'install_location': '', 'status': 'Reported by client', 'source': '2278 latest payload'}
    d = x if isinstance(x, dict) else {}
    return {
        'name': _s(_pick(d, 'name', 'display_name', 'package', 'id'), 'Unknown software'),
        'version': _s(_pick(d, 'version', 'display_version'), ''),
        'publisher': _s(_pick(d, 'publisher', 'vendor', 'maintainer'), ''),
        'install_date': _s(_pick(d, 'install_date', 'installed_on', 'date'), ''),
        'install_location': _s(_pick(d, 'install_location', 'path', 'location'), ''),
        'uninstall_string': _s(_pick(d, 'uninstall_string'), ''),
        'architecture': _s(_pick(d, 'architecture', 'arch'), ''),
        'status': _s(_pick(d, 'status'), 'Reported by client'),
        'source': _s(_pick(d, 'source'), '2278 latest payload'),
    }


def _find_list(payload: Dict[str, Any], paths: List[Tuple[str, ...]]) -> List[Any]:
    for path in paths:
        v = _deep_get(payload, [path], None)
        lst = _as_list(v)
        if lst:
            return lst
    return []


def _machine_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    keys = set(row.keys())
    summary = _parse_json(row['summary_json'], {}) if 'summary_json' in keys else {}
    if not isinstance(summary, dict): summary = {}
    payload = _extract_payload(row, summary)
    ident = payload.get('identity') if isinstance(payload.get('identity'), dict) else {}
    hardware = payload.get('hardware') if isinstance(payload.get('hardware'), dict) else {}
    cpu = _deep_get(payload, [('hardware','cpu'), ('cpu',)], {}) or {}
    memory = _deep_get(payload, [('hardware','memory'), ('hardware','ram'), ('memory',), ('ram',)], {}) or {}
    network = payload.get('network') if isinstance(payload.get('network'), dict) else {}

    machine_id = _s(summary.get('machine_id') or (row['machine_id'] if 'machine_id' in keys else '') or ident.get('machine_id') or ident.get('asset_id'))
    hostname = _s(summary.get('hostname') or (row['hostname'] if 'hostname' in keys else '') or payload.get('hostname') or ident.get('hostname') or machine_id, 'Unknown')
    updated_at = _row_time(row, summary, payload)
    upd = _dt(updated_at)
    age_minutes = round((_now_utc() - upd).total_seconds()/60, 2) if upd else None
    fresh = bool(age_minutes is not None and age_minutes <= float(os.environ.get('V10_FRESH_SECONDS', '90'))/60.0)
    host_l = hostname.lower()
    monitor_server = host_l in {os.environ.get('COMPUTERNAME','').lower(), 'desktop-1vtkp12'}

    disks_raw = _as_list(summary.get('disks')) or _find_list(payload, [('storage','disks'),('storage','volumes'),('storage','drives'),('hardware','storage'),('disks',),('drives',)])
    disks = [_normal_disk(x) for x in disks_raw]
    if not disks and summary.get('disk_max_percent') not in (None, ''):
        disks = [{'name':'Disk summary','type':'Not reported by client','mount':'Not reported by client','size_gb':'Not reported by client','used_gb':'Not reported by client','free_gb':'Not reported by client','percent':_round(summary.get('disk_max_percent'),2,'Not reported by client')}]

    gpus_raw = _as_list(summary.get('gpus')) or _find_list(payload, [('hardware','gpus'),('hardware','gpu'),('gpu','devices'),('gpu',),('gpus',)])
    if not gpus_raw and isinstance(summary.get('gpu_names'), list):
        gpus_raw = [{'name': n, 'memory_mb': summary.get('gpu_total_memory_mb'), 'usage_percent': summary.get('gpu_max_usage'), 'temperature_c': summary.get('gpu_max_temp_c')} for n in summary.get('gpu_names')]
    gpus = [_normal_gpu(x) for x in gpus_raw]

    adapters_raw = _as_list(summary.get('network_adapters')) or _find_list(payload, [('network','adapters'),('network','interfaces'),('adapters',),('interfaces',)])
    adapters = [_normal_adapter(x) for x in adapters_raw]
    all_ips = summary.get('all_ips') if isinstance(summary.get('all_ips'), list) else []
    if not adapters and (summary.get('primary_ip') or all_ips):
        adapters = [_normal_adapter({'name':'Primary adapter','ips': all_ips or [summary.get('primary_ip')]})]

    usb_raw = _as_list(summary.get('usb_devices')) or _find_list(payload, [('usb','devices'),('usb',),('hardware','usb'),('peripherals',)])
    usb_devices = [_normal_usb(x) for x in usb_raw]

    sw_raw = _as_list(summary.get('software')) or _find_list(payload, [('software','installed'),('software','apps'),('software','packages'),('software',),('installed_software',),('apps',)])
    software = [_normal_sw(x) for x in sw_raw]

    cpu_name = _s(summary.get('cpu_name') or _pick(cpu, 'name', 'model', 'brand', 'processor'), 'Not reported by client')
    ram_total = summary.get('ram_total_gb') or _pick(memory, 'total_gb', 'totalGB', 'total')
    ram_used = summary.get('ram_used_gb') or _pick(memory, 'used_gb', 'usedGB', 'used')
    ram_free = summary.get('ram_free_gb') or _pick(memory, 'free_gb', 'freeGB', 'available_gb')
    ram_pct = summary.get('ram_percent') or _pick(memory, 'percent', 'usage_percent', 'used_percent')

    machine = {
        'machine_id': machine_id,
        'hostname': hostname,
        'updated_at': updated_at,
        'age_minutes': age_minutes,
        'fresh': fresh,
        'is_monitor_server': monitor_server,
        'os': _s(summary.get('os') or payload.get('os') or _deep_get(payload, [('system','os')], None), 'Not reported by client'),
        'primary_ip': _s(summary.get('primary_ip') or _deep_get(network, [('primary_ip',)], None), 'Not reported by client'),
        'all_ips': all_ips,
        'id_source': _s(summary.get('id_source') or ident.get('id_source'), 'asset_fingerprint'),
        'id_value': _s(summary.get('id_value') or ident.get('id_value') or f'{hostname} / {machine_id}', f'{hostname} / {machine_id}'),
        'serial_number': _s(summary.get('serial_number') or ident.get('serial_number') or _deep_get(hardware, [('serial_number',)], None), 'Not reported by client'),
        'motherboard_serial': _s(summary.get('motherboard_serial') or _deep_get(hardware, [('motherboard','serial'),('motherboard_serial',)], None), 'Not reported by client'),
        'bios_serial': _s(summary.get('bios_serial') or _deep_get(hardware, [('bios','serial'),('bios_serial',)], None), 'Not reported by client'),
        'manufacturer': _s(summary.get('manufacturer') or _deep_get(hardware, [('manufacturer',),('system','manufacturer')], None), 'Not reported by client'),
        'model': _s(summary.get('model') or _deep_get(hardware, [('model',),('system','model')], None), 'Not reported by client'),
        'cpu_name': cpu_name,
        'cpu_percent': _round(summary.get('cpu_percent') or _pick(cpu, 'percent','usage_percent','load_percent','usage'), 2, 0),
        'cpu_temp_c': _round(summary.get('cpu_temp_c') or _pick(cpu, 'temp_c','temperature_c','temperature'), 2, 'Not reported by client'),
        'cpu_cores': _round(summary.get('cpu_cores') or _pick(cpu,'cores','physical_cores'), 0, 'Not reported by client'),
        'cpu_logical_processors': _round(summary.get('cpu_logical_processors') or _pick(cpu,'logical_processors','threads'), 0, 'Not reported by client'),
        'ram_percent': _round(ram_pct, 2, 0),
        'ram_total_gb': _round(ram_total, 2, 'Not reported by client'),
        'ram_used_gb': _round(ram_used, 2, 'Not reported by client'),
        'ram_free_gb': _round(ram_free, 2, 'Not reported by client'),
        'ram_slots': _s(summary.get('ram_slots') or _deep_get(memory, [('slots',)], None), 'Not reported by client'),
        'disk_max_percent': _round(summary.get('disk_max_percent') or max([_f(d.get('percent'),0) or 0 for d in disks] or [0]), 2, 0),
        'disk_count': len(disks),
        'disks': disks,
        'gpu_names': summary.get('gpu_names') if isinstance(summary.get('gpu_names'), list) else [g.get('name') for g in gpus if g.get('name')],
        'gpu_count': int(_f(summary.get('gpu_count'), len(gpus)) or len(gpus)),
        'gpu_max_usage': _round(summary.get('gpu_max_usage') or max([_f(g.get('usage_percent'),0) or 0 for g in gpus] or [0]), 2, 'Not reported by client'),
        'gpu_max_temp_c': _round(summary.get('gpu_max_temp_c') or max([_f(g.get('temperature_c'),0) or 0 for g in gpus] or [0]), 2, 'Not reported by client'),
        'gpu_total_memory_mb': _round(summary.get('gpu_total_memory_mb') or sum([_f(g.get('memory_mb'),0) or 0 for g in gpus]), 0, 'Not reported by client'),
        'gpus': gpus,
        'vpn_active': bool(summary.get('vpn_active') or _deep_get(network, [('vpn_active',),('vpn','active')], False)),
        'isp_name': _s(summary.get('isp_name') or _deep_get(network, [('isp_name',),('public','isp')], None), 'Not reported by client'),
        'public_ip': _s(summary.get('public_ip') or _deep_get(network, [('public_ip',),('public','ip')], None), 'Not reported by client'),
        'wan_download_mbps': _round(summary.get('wan_download_mbps'), 2, 0),
        'wan_upload_mbps': _round(summary.get('wan_upload_mbps'), 2, 0),
        'today_download_gb': _round(summary.get('today_download_gb'), 2, 0),
        'today_upload_gb': _round(summary.get('today_upload_gb'), 2, 0),
        'adapter_count': int(_f(summary.get('adapter_count'), len(adapters)) or len(adapters)),
        'network_adapters': adapters,
        'software_count': int(_f(summary.get('software_count'), len(software)) or len(software)),
        'software': software,
        'usb_count': int(_f(summary.get('usb_count'), len(usb_devices)) or len(usb_devices)),
        'usb_devices': usb_devices,
        'change_count': int(_f(summary.get('change_count'), 0) or 0),
        'raw_summary_keys': list(summary.keys())[:100],
        'raw_payload_keys': list(payload.keys())[:100],
        'source': '2278 latest.summary_json/payload_json read-only self-contained mapper',
        'no_write_to_2278': True,
    }
    # Completeness from visible fields, not fake audit pass
    fields = ['cpu_name','ram_total_gb','disks','gpus','network_adapters','software_count','usb_devices','serial_number']
    good = 0
    for k in fields:
        v = machine.get(k)
        if v and v != 'Not reported by client' and v != []:
            good += 1
    machine['hardware_completeness_percent'] = round(good * 100 / len(fields), 1)
    return machine


def _load_machines() -> List[Dict[str, Any]]:
    with _connect_ro() as con:
        # Keep this fast: latest table only, never scan heartbeats here.
        rows = con.execute('SELECT * FROM latest').fetchall()
    machines = [_machine_from_row(r) for r in rows]
    machines.sort(key=lambda m: (not bool(m.get('fresh')), str(m.get('hostname','')).lower()))
    return machines


def _find_machine(machine_id: str = '', query: str = '', hostname: str = '') -> Tuple[Dict[str, Any] | None, List[Dict[str, Any]]]:
    machines = _load_machines()
    if machine_id:
        for m in machines:
            if str(m.get('machine_id')) == str(machine_id):
                return m, machines
        return None, machines
    h = (hostname or '').lower().strip()
    if h:
        for m in machines:
            if str(m.get('hostname','')).lower() == h:
                return m, machines
    q = (query or hostname or '').lower().strip()
    if q:
        for m in machines:
            blob = json.dumps({'hostname':m.get('hostname'), 'machine_id':m.get('machine_id'), 'primary_ip':m.get('primary_ip'), 'id_value':m.get('id_value')}, default=str).lower()
            if q in blob:
                return m, machines
    for m in machines:
        if not m.get('is_monitor_server'):
            return m, machines
    return (machines[0] if machines else None), machines


def _send_json(handler: Any, data: Dict[str, Any], status: int = 200) -> None:
    if hasattr(handler, 'send_json'):
        return handler.send_json(data, status)
    body = json.dumps(data, default=str, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    handler.wfile.write(body)


def _home() -> Dict[str, Any]:
    machines = _load_machines()
    clients = [m for m in machines if not m.get('is_monitor_server')]
    fresh = [m for m in clients if m.get('fresh')]
    stale = [m for m in clients if not m.get('fresh')]
    issue = [m for m in clients if (_f(m.get('cpu_percent'),0) or 0) >= 90 or (_f(m.get('ram_percent'),0) or 0) >= 90 or (_f(m.get('disk_max_percent'),0) or 0) >= 90]
    home = {
        'today_download_gb': round(sum((_f(m.get('today_download_gb'),0) or 0) for m in clients), 2),
        'today_upload_gb': round(sum((_f(m.get('today_upload_gb'),0) or 0) for m in clients), 2),
        'current_download_mbps': round(sum((_f(m.get('wan_download_mbps'),0) or 0) for m in fresh), 2),
        'current_upload_mbps': round(sum((_f(m.get('wan_upload_mbps'),0) or 0) for m in fresh), 2),
        'usb_devices': sum(int(_f(m.get('usb_count'),0) or 0) for m in clients),
        'installed_apps': sum(int(_f(m.get('software_count'),0) or 0) for m in clients),
        'issue_clients': len(issue),
    }
    return {
        'ok': True,
        'source': '2278_latest_readonly_self_contained_mapper',
        'source_db': str(SOURCE_DB),
        'no_write_to_2278': True,
        'home': home,
        'machines': {
            'ok': True,
            'total_rows': len(machines),
            'client_machines': len(clients),
            'fresh_clients': len(fresh),
            'stale_clients': len(stale),
            'monitor_server_count': len(machines) - len(clients),
            'machines': machines,
        },
        'fresh_machine_cards': (fresh or clients)[:12],
        'notifications': {'simulated_alerts_count': len(issue), 'issue_clients': issue[:20]},
    }


def _machines() -> Dict[str, Any]:
    machines = _load_machines()
    clients = [m for m in machines if not m.get('is_monitor_server')]
    return {'ok': True, 'source': '2278_latest_readonly_self_contained_mapper', 'source_db': str(SOURCE_DB), 'no_write_to_2278': True, 'count': len(machines), 'client_count': len(clients), 'machines': machines, 'clients': clients}


def _selected(machine_id: str, query: str, hostname: str) -> Tuple[Dict[str, Any], int]:
    m, all_m = _find_machine(machine_id, query, hostname)
    if not m:
        return {'ok': False, 'error': 'machine_not_found', 'requested_machine_id': machine_id, 'no_default_fallback': True}, 404
    return {'ok': True, 'machine': m, 'requested_machine_id': machine_id, 'returned_machine_id': m.get('machine_id'), 'hostname': m.get('hostname'), 'source': m.get('source'), 'no_write_to_2278': True}, 200


def _network(machine_id: str, query: str, hostname: str) -> Tuple[Dict[str, Any], int]:
    res, status = _selected(machine_id, query, hostname)
    if status != 200:
        return res, status
    m = res['machine']
    res.update({
        'primary_ip': m.get('primary_ip'), 'public_ip': m.get('public_ip'), 'isp_name': m.get('isp_name'), 'vpn_active': m.get('vpn_active'),
        'adapter_count': m.get('adapter_count'), 'network_adapters': m.get('network_adapters'),
        'wan_download_mbps': m.get('wan_download_mbps'), 'wan_upload_mbps': m.get('wan_upload_mbps')
    })
    return res, 200


def _software(machine_id: str, query: str, hostname: str, swq: str, limit: int) -> Tuple[Dict[str, Any], int]:
    res, status = _selected(machine_id, query, hostname)
    if status != 200:
        return res, status
    m = res['machine']
    rows = m.get('software') or []
    if swq:
        qq = swq.lower()
        rows = [r for r in rows if qq in json.dumps(r, default=str).lower()]
    try:
        limit = max(1, min(int(limit), 50000))
    except Exception:
        limit = 2000
    return {'ok': True, 'machine': m, 'requested_machine_id': machine_id, 'returned_machine_id': m.get('machine_id'), 'software_count': m.get('software_count'), 'loaded_count': len(rows[:limit]), 'software': rows[:limit], 'source': '2278 latest payload software read-only', 'no_write_to_2278': True}, 200


def install(Handler: Any, base_dir: Any) -> None:
    global BASE_DIR
    BASE_DIR = Path(base_dir)
    old_get = Handler.do_GET

    def new_get(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith('/api/v10/app/'):
            return old_get(self)
        qs = parse_qs(parsed.query or '')
        machine_id = (qs.get('machine_id') or qs.get('id') or [''])[0]
        hostname = (qs.get('hostname') or [''])[0]
        query = (qs.get('query') or qs.get('q') or [''])[0]
        swq = (qs.get('software_query') or qs.get('sw_query') or [''])[0]
        try:
            limit = int(float((qs.get('limit') or ['2000'])[0]))
        except Exception:
            limit = 2000
        try:
            if path == '/api/v10/app/health':
                return _send_json(self, {'ok': True, 'app': 'V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP_TODAY_STABLE', 'auth': 'public_readonly_for_dashboard', 'source': '2278_latest_readonly_self_contained_mapper', 'source_db': str(SOURCE_DB), 'no_write_to_2278': True})
            if path == '/api/v10/app/home': return _send_json(self, _home())
            if path == '/api/v10/app/machines': return _send_json(self, _machines())
            if path in ('/api/v10/app/machine360','/api/v10/app/hardware'):
                res, status = _selected(machine_id, query, hostname); return _send_json(self, res, status)
            if path == '/api/v10/app/network':
                res, status = _network(machine_id, query, hostname); return _send_json(self, res, status)
            if path == '/api/v10/app/software':
                res, status = _software(machine_id, query, hostname, swq, limit); return _send_json(self, res, status)
            if path == '/api/v10/app/notifications-fast':
                h = _home(); return _send_json(self, {'ok': True, 'simulated_alerts_count': h.get('notifications',{}).get('simulated_alerts_count',0), 'alerts': h.get('notifications',{}).get('issue_clients',[]), 'no_write_to_2278': True})
            if path == '/api/v10/app/isp-wan':
                return _send_json(self, {'ok': True, 'links': [], 'note': 'ISP/WAN settings route is preserved; clean runtime does not fake router feed.', 'no_write_to_2278': True})
            return _send_json(self, {'ok': False, 'error': 'not_found', 'path': path}, 404)
        except Exception as e:
            return _send_json(self, {'ok': False, 'error': str(e), 'path': path, 'source_db': str(SOURCE_DB), 'no_write_to_2278': True}, 500)

    Handler.do_GET = new_get
