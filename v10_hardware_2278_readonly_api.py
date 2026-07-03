
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
            if v.strip() == '' or v.strip().lower() in ('none','null','not reported','n/a'):
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
        for key in ('items','devices','adapters','disks','gpus','monitors','usb_devices','list'):
            if isinstance(v.get(key), list):
                return v.get(key) or []
        return [v]
    return [v]


def _compact_dict(d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    return {k: d.get(k) for k in keys if d.get(k) not in (None, '')}


def _norm_disk(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'name': x}
    if not isinstance(x, dict):
        return {'value': str(x)}
    return {
        'name': _first(x.get('name'), x.get('device'), x.get('caption'), x.get('model'), x.get('mountpoint'), x.get('drive')) or 'Disk',
        'model': _first(x.get('model'), x.get('serial_model'), x.get('caption')),
        'type': _first(x.get('type'), x.get('media_type'), x.get('bus_type')),
        'mount': _first(x.get('mountpoint'), x.get('mount'), x.get('drive'), x.get('letter')),
        'size_gb': _first(x.get('size_gb'), x.get('total_gb'), x.get('capacity_gb')),
        'used_gb': _first(x.get('used_gb'), x.get('used')),
        'free_gb': _first(x.get('free_gb'), x.get('free')),
        'percent': _first(x.get('percent'), x.get('usage_percent'), x.get('used_percent')),
        'health': _first(x.get('health'), x.get('status')),
        'temperature_c': _first(x.get('temperature_c'), x.get('temp_c')),
        'serial': _first(x.get('serial'), x.get('serial_number')),
    }


def _norm_gpu(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'name': x}
    if not isinstance(x, dict):
        return {'value': str(x)}
    return {
        'name': _first(x.get('name'), x.get('model'), x.get('caption')) or 'GPU',
        'memory_mb': _first(x.get('memory_mb'), x.get('total_memory_mb'), x.get('vram_mb')),
        'usage_percent': _first(x.get('usage_percent'), x.get('usage'), x.get('load_percent')),
        'temperature_c': _first(x.get('temperature_c'), x.get('temp_c')),
        'driver': _first(x.get('driver'), x.get('driver_version')),
    }


def _norm_usb(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'name': x, 'category': 'USB/Peripheral'}
    if not isinstance(x, dict):
        return {'name': str(x), 'category': 'USB/Peripheral'}
    name = _first(x.get('name'), x.get('caption'), x.get('description'), x.get('device_name'), x.get('friendly_name'), x.get('model')) or 'USB/Peripheral'
    low = str(name).lower()
    cat = _first(x.get('category'), x.get('class'), x.get('type')) or 'USB/Peripheral'
    if 'keyboard' in low: cat = 'Keyboard'
    elif 'mouse' in low or 'pointing' in low: cat = 'Mouse'
    elif 'headset' in low or 'headphone' in low or 'audio' in low: cat = 'Headset/Audio'
    elif 'storage' in low or 'mass' in low or 'disk' in low: cat = 'USB Storage'
    return {
        'name': name,
        'category': cat,
        'vendor': _first(x.get('vendor'), x.get('manufacturer')),
        'serial': _first(x.get('serial'), x.get('serial_number')),
        'status': _first(x.get('status'), x.get('connected')),
        'device_id': _first(x.get('device_id'), x.get('pnp_device_id'), x.get('id')),
    }


def _norm_adapter(x: Any) -> Dict[str, Any]:
    if isinstance(x, str):
        return {'name': x}
    if not isinstance(x, dict):
        return {'value': str(x)}
    ips = _first(x.get('ips'), x.get('ip_addresses'), x.get('ip'), x.get('ipv4')) or []
    if isinstance(ips, str): ips = [ips]
    return {
        'name': _first(x.get('name'), x.get('adapter'), x.get('interface'), x.get('description')) or 'Adapter',
        'mac': _first(x.get('mac'), x.get('mac_address'), x.get('physical_address')),
        'ips': ips,
        'gateway': _first(x.get('gateway'), x.get('default_gateway')),
        'dns': _first(x.get('dns'), x.get('dns_servers')),
        'status': _first(x.get('status'), x.get('oper_status')),
        'speed': _first(x.get('speed'), x.get('link_speed')),
    }


def _machine_hardware(row: sqlite3.Row) -> Dict[str, Any]:
    rd = _rowdict(row)
    summary = _safe_json(rd.get('summary_json'), {})
    payload = _safe_json(rd.get('payload_json'), {})
    if isinstance(summary.get('payload'), dict):
        payload = summary.get('payload') or payload
    if not isinstance(payload, dict): payload = {}
    hardware = payload.get('hardware') if isinstance(payload.get('hardware'), dict) else {}
    system = _first(payload.get('system'), hardware.get('system'), {})
    if not isinstance(system, dict): system = {}
    cpu = _first(payload.get('cpu'), hardware.get('cpu'), {})
    if not isinstance(cpu, dict): cpu = {}
    mem = _first(payload.get('memory'), payload.get('ram'), hardware.get('memory'), hardware.get('ram'), {})
    if not isinstance(mem, dict): mem = {}
    network = payload.get('network') if isinstance(payload.get('network'), dict) else {}
    bios = _first(payload.get('bios'), hardware.get('bios'), {})
    if not isinstance(bios, dict): bios = {}
    mb = _first(payload.get('motherboard'), hardware.get('motherboard'), hardware.get('baseboard'), {})
    if not isinstance(mb, dict): mb = {}
    storage_src = _first(payload.get('storage'), payload.get('disks'), payload.get('disk'), hardware.get('storage'), hardware.get('disks'), [])
    gpu_src = _first(payload.get('gpu'), payload.get('gpus'), hardware.get('gpu'), hardware.get('gpus'), summary.get('gpu_names'), [])
    usb_src = _first(payload.get('usb'), payload.get('peripherals'), hardware.get('usb'), hardware.get('peripherals'), [])
    adapters_src = _first(network.get('adapters'), payload.get('adapters'), hardware.get('adapters'), [])
    monitor_src = _first(payload.get('monitors'), payload.get('display'), hardware.get('monitors'), [])
    disks = [_norm_disk(x) for x in _as_list(storage_src)]
    gpus = [_norm_gpu(x) for x in _as_list(gpu_src)]
    usb = [_norm_usb(x) for x in _as_list(usb_src)]
    adapters = [_norm_adapter(x) for x in _as_list(adapters_src)]
    updated_at = _first(rd.get('updated_at'), summary.get('updated_at'), summary.get('timestamp'), payload.get('timestamp'))
    age = _age_minutes(updated_at)
    gpu_names = summary.get('gpu_names') if isinstance(summary.get('gpu_names'), list) else [g.get('name') for g in gpus if g.get('name')]
    all_ips = _first(summary.get('all_ips'), network.get('all_ips'), payload.get('all_ips')) or []
    if isinstance(all_ips, str): all_ips = [all_ips]
    serial = _first(summary.get('serial_number'), payload.get('serial_number'), system.get('serial_number'), system.get('serial'), bios.get('serial_number'), bios.get('serial'), mb.get('serial_number'), hardware.get('serial_number'))
    cpu_name = _first(summary.get('cpu_name'), cpu.get('name'), cpu.get('brand'), cpu.get('model'), cpu.get('processor'))
    row_out: Dict[str, Any] = {
        'machine_id': _first(rd.get('machine_id'), summary.get('machine_id'), payload.get('machine_id')) or '',
        'hostname': _first(rd.get('hostname'), summary.get('hostname'), payload.get('hostname'), system.get('hostname')) or '',
        'updated_at': updated_at or '',
        'age_minutes': age,
        'fresh': age is not None and age <= 10,
        'os': _first(summary.get('os'), payload.get('os'), system.get('os'), system.get('platform')) or 'Not reported',
        'primary_ip': _first(summary.get('primary_ip'), network.get('primary_ip'), payload.get('primary_ip')) or 'Not reported',
        'all_ips': all_ips,
        'id_source': _first(rd.get('id_source'), summary.get('id_source')) or '',
        'id_value': _first(rd.get('id_value'), summary.get('id_value')) or '',
        'serial_number': serial or 'Not reported by client',
        'motherboard_serial': _first(mb.get('serial_number'), mb.get('serial'), hardware.get('motherboard_serial')) or 'Not reported by client',
        'bios_serial': _first(bios.get('serial_number'), bios.get('serial'), hardware.get('bios_serial')) or 'Not reported by client',
        'manufacturer': _first(system.get('manufacturer'), hardware.get('manufacturer'), mb.get('manufacturer')) or 'Not reported by client',
        'model': _first(system.get('model'), hardware.get('model'), mb.get('product'), mb.get('model')) or 'Not reported by client',
        'cpu_name': cpu_name or 'Not reported by client',
        'cpu_percent': _float(_first(summary.get('cpu_percent'), cpu.get('percent'), payload.get('cpu_percent')), 0),
        'cpu_temp_c': _first(summary.get('cpu_temp_c'), cpu.get('temp_c'), cpu.get('temperature_c')),
        'cpu_cores': _first(cpu.get('cores'), cpu.get('physical_cores'), payload.get('cpu_cores')),
        'cpu_logical_processors': _first(cpu.get('logical_processors'), cpu.get('threads'), payload.get('cpu_logical_processors')),
        'ram_percent': _float(_first(summary.get('ram_percent'), mem.get('percent'), payload.get('ram_percent')), 0),
        'ram_total_gb': _float(_first(summary.get('ram_total_gb'), mem.get('total_gb'), payload.get('ram_total_gb')), 0),
        'ram_used_gb': _float(_first(summary.get('ram_used_gb'), mem.get('used_gb'), payload.get('ram_used_gb')), 0),
        'ram_free_gb': _float(_first(summary.get('ram_free_gb'), mem.get('free_gb'), payload.get('ram_free_gb')), 0),
        'ram_slots': _first(mem.get('slots'), mem.get('slot_count'), hardware.get('ram_slots')) or 'Not reported by client',
        'disk_max_percent': _float(_first(summary.get('disk_max_percent'), payload.get('disk_max_percent')), 0),
        'disk_count': len(disks),
        'disks': disks,
        'gpu_count': _int(_first(summary.get('gpu_count'), len(gpus)), 0),
        'gpu_names': gpu_names or [],
        'gpu_total_memory_mb': _float(_first(summary.get('gpu_total_memory_mb'), payload.get('gpu_total_memory_mb')), 0),
        'gpu_max_usage': _first(summary.get('gpu_max_usage'), payload.get('gpu_max_usage')),
        'gpu_max_temp_c': _first(summary.get('gpu_max_temp_c'), payload.get('gpu_max_temp_c')),
        'gpus': gpus,
        'usb_count': _int(_first(summary.get('usb_count'), len(usb)), 0),
        'usb_devices': usb,
        'adapter_count': _int(_first(summary.get('adapter_count'), len(adapters)), 0),
        'network_adapters': adapters,
        'monitor_count': len(_as_list(monitor_src)) if monitor_src else 0,
        'monitors': _as_list(monitor_src),
        'software_count': _int(summary.get('software_count'), 0),
        'vpn_active': bool(_first(summary.get('vpn_active'), payload.get('vpn_active'), False)),
        'public_ip': _first(summary.get('public_ip'), payload.get('public_ip')) or 'Not reported',
        'isp_name': _first(summary.get('isp_name'), payload.get('isp_name')) or 'Not reported',
        'source': '2278 latest.summary_json read-only',
        'raw_summary_keys': list(summary.keys()) if isinstance(summary, dict) else [],
        'raw_payload_keys': list(payload.keys()) if isinstance(payload, dict) else [],
    }
    missing = []
    for key,label in [('serial_number','serial number'),('cpu_name','CPU name'),('ram_total_gb','RAM total'),('disk_count','disk details'),('gpu_count','GPU details'),('usb_count','USB/peripherals')]:
        v = row_out.get(key)
        if v in (None, '', 0, [], 'Not reported by client', 'Not reported'):
            missing.append(label)
    row_out['missing_live_hardware_fields'] = missing
    row_out['hardware_completeness_percent'] = max(0, round(100 - (len(missing) * (100/6)), 1))
    return row_out


def _latest_rows(limit: int = 1000) -> List[Dict[str, Any]]:
    with _connect_ro() as con:
        if not _table_exists(con, 'latest'):
            return []
        cols = _columns(con, 'latest')
        order = 'updated_at DESC' if 'updated_at' in cols else 'rowid DESC'
        return [_machine_hardware(r) for r in con.execute(f'SELECT * FROM latest ORDER BY {order} LIMIT ?', (limit,)).fetchall()]


def hardware_status() -> Dict[str, Any]:
    out = {'ok': False, 'mode': '2278_hardware_read_only', 'source_db': str(SOURCE_2278_DB), 'no_write_to_2278': True, 'source_db_exists': SOURCE_2278_DB.exists()}
    if not SOURCE_2278_DB.exists():
        out['error'] = '2278 DB not found'
        return out
    try:
        rows = _latest_rows(2000)
        out.update({
            'ok': True,
            'machines_checked': len(rows),
            'fresh_machines': len([r for r in rows if r.get('fresh')]),
            'stale_machines': len([r for r in rows if not r.get('fresh')]),
            'missing_serial_count': len([r for r in rows if str(r.get('serial_number','')).startswith('Not reported')]),
            'gpu_reported_count': len([r for r in rows if (r.get('gpu_count') or 0) > 0 or r.get('gpu_names')]),
            'usb_reported_count': len([r for r in rows if (r.get('usb_count') or 0) > 0 or r.get('usb_devices')]),
            'disk_reported_count': len([r for r in rows if (r.get('disk_count') or 0) > 0 or (r.get('disk_max_percent') or 0) > 0]),
            'note': 'Hardware data is read-only from 2278 latest.summary_json. Missing fields mean the client did not report that field; values are not faked.',
        })
    except Exception as e:
        out['error'] = str(e)
    return out


def hardware_list(q: str = '', limit: int = 500, freshness: str = 'all') -> Dict[str, Any]:
    rows = _latest_rows(limit)
    ql = (q or '').strip().lower()
    if ql:
        def hit(r):
            blob = ' '.join(str(r.get(k,'')) for k in ['machine_id','hostname','os','primary_ip','serial_number','cpu_name','manufacturer','model','id_value']).lower()
            return ql in blob
        rows = [r for r in rows if hit(r)]
    if freshness == 'fresh':
        rows = [r for r in rows if r.get('fresh')]
    elif freshness == 'stale':
        rows = [r for r in rows if not r.get('fresh')]
    summary = hardware_status()
    return {
        'ok': True,
        'source': '2278_monitor_db_read_only_latest_hardware',
        'source_db': str(SOURCE_2278_DB),
        'no_write_to_2278': True,
        'query': q,
        'freshness': freshness,
        'count': len(rows),
        'summary': summary,
        'machines': rows,
    }


def hardware_machine(machine_id: str) -> Dict[str, Any]:
    rows = _latest_rows(2000)
    for r in rows:
        if str(r.get('machine_id')) == str(machine_id) or str(r.get('hostname')).lower() == str(machine_id).lower():
            return {'ok': True, 'machine': r, 'source': '2278 read-only'}
    return {'ok': False, 'error': 'Machine not found in 2278 latest read-only source', 'machine_id': machine_id}


def export_csv(data: Dict[str, Any]) -> bytes:
    out = io.StringIO()
    fields = ['machine_id','hostname','updated_at','age_minutes','fresh','os','primary_ip','serial_number','motherboard_serial','bios_serial','manufacturer','model','cpu_name','cpu_percent','cpu_temp_c','cpu_cores','cpu_logical_processors','ram_total_gb','ram_used_gb','ram_free_gb','ram_percent','ram_slots','disk_count','disk_max_percent','gpu_count','gpu_names','gpu_total_memory_mb','gpu_max_usage','gpu_max_temp_c','usb_count','adapter_count','monitor_count','software_count','vpn_active','public_ip','isp_name','hardware_completeness_percent','missing_live_hardware_fields']
    w = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    for r in data.get('machines') or []:
        rr = dict(r)
        for k in ['gpu_names','missing_live_hardware_fields']:
            if isinstance(rr.get(k), list): rr[k] = '; '.join(map(str, rr.get(k) or []))
        w.writerow(rr)
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
            if path in ('/api/v10/source2278/hardware/status','/api/v10/hardware2278/status'):
                return _send_json(self, hardware_status())
            if path in ('/api/v10/source2278/hardware','/api/v10/hardware2278/list'):
                q = (qs.get('q') or [''])[0]
                freshness = (qs.get('freshness') or ['all'])[0]
                limit = _int((qs.get('limit') or ['500'])[0], 500)
                return _send_json(self, hardware_list(q, min(limit, 2000), freshness))
            if path in ('/api/v10/source2278/hardware-machine','/api/v10/hardware2278/machine'):
                mid = (qs.get('machine_id') or qs.get('hostname') or [''])[0]
                return _send_json(self, hardware_machine(mid), 200 if mid else 400)
            if path in ('/api/v10/source2278/hardware/export.csv','/api/v10/hardware2278/export.csv'):
                q = (qs.get('q') or [''])[0]
                freshness = (qs.get('freshness') or ['all'])[0]
                body = export_csv(hardware_list(q, 2000, freshness))
                return _send_csv(self, body, 'v10_2278_readonly_live_hardware.csv')
        except Exception as e:
            return _send_json(self, {'ok': False, 'error': str(e), 'source_db': str(SOURCE_2278_DB), 'no_write_to_2278': True}, 500)
        return old_get(self)
    Handler.do_GET = new_get
