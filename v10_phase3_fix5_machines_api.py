#!/usr/bin/env python3
# V10 Phase3 Fix5: normalize /api/v10final/machines response and add live API safety.
from __future__ import annotations
import json, traceback, urllib.parse, datetime
from pathlib import Path
from typing import Any, Dict, List

PHASE_NAME="V10_PHASE3_FIX5_MACHINES_API_NORMALIZER"
PHASE_VERSION="2026-07-03.5"


def _send_json(handler: Any, obj: Any, status: int = 200) -> None:
    body=json.dumps(obj, ensure_ascii=False, default=str).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type','application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Cache-Control','no-store')
    handler.end_headers()
    handler.wfile.write(body)


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == '': return default
        return float(v)
    except Exception:
        return default


def _first(*vals: Any) -> Any:
    for v in vals:
        if v is not None and v != '' and v != [] and v != {}:
            return v
    return None


def _dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else []


def _parse_time(value: Any) -> Any:
    if not value: return None
    s=str(value).replace('Z','+00:00')
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None


def _is_online(last_seen: Any, timeout_seconds: int = 45) -> bool:
    dt=_parse_time(last_seen)
    if not dt: return False
    if dt.tzinfo is None:
        now=datetime.datetime.now()
        return (now-dt).total_seconds() <= timeout_seconds
    now=datetime.datetime.now(datetime.timezone.utc)
    return (now-dt.astimezone(datetime.timezone.utc)).total_seconds() <= timeout_seconds


def _normalize_machine(row: Dict[str,Any]) -> Dict[str,Any]:
    payload=_dict(row.get('payload'))
    hw=_dict(payload.get('hardware') or payload.get('hw'))
    cpu=_dict(payload.get('cpu') or hw.get('cpu'))
    ram=_dict(payload.get('ram') or payload.get('memory') or hw.get('ram'))
    disk=_dict(payload.get('disk') or payload.get('disks_summary') or hw.get('disk'))
    net=_dict(payload.get('network'))
    pub=_dict(net.get('public_internet'))

    hostname=_first(row.get('hostname'), payload.get('hostname'), payload.get('computer_name'), row.get('machine_name'), 'Not reported')
    machine_id=_first(row.get('machine_id'), row.get('id'), payload.get('machine_id'), hostname)
    last_seen=_first(row.get('last_seen'), row.get('updated_at'), row.get('created_at'), payload.get('last_seen'), payload.get('timestamp'))
    online=_first(row.get('online'), row.get('is_online'))
    if online is None:
        online=_is_online(last_seen)
    online_bool=bool(online)

    cpu_percent=_first(row.get('cpu_percent'), payload.get('cpu_percent'), cpu.get('percent'), cpu.get('usage_percent'))
    ram_percent=_first(row.get('ram_percent'), payload.get('ram_percent'), ram.get('percent'), ram.get('usage_percent'))
    disk_percent=_first(row.get('disk_max_percent'), payload.get('disk_max_percent'), disk.get('max_percent'), disk.get('percent'), disk.get('usage_percent'))

    issues=[]
    if not online_bool: issues.append('offline')
    if _num(cpu_percent) >= 90 and _num(ram_percent) >= 90: issues.append('cpu_ram_critical')
    if _num(disk_percent) >= 90: issues.append('disk_high')
    if not _list(payload.get('software')) and not _list(payload.get('installed_software')) and _num(row.get('software_count')) == 0:
        # not a critical issue, but useful delivery truth
        pass

    ip=_first(row.get('ip'), row.get('local_ip'), payload.get('ip'), net.get('ip'), net.get('local_ip'))
    os_name=_first(row.get('os'), row.get('os_name'), payload.get('os'), payload.get('os_name'), payload.get('platform'))

    normalized=dict(row)
    normalized.update({
        'machine_id': machine_id,
        'hostname': hostname,
        'last_seen': last_seen,
        'online': online_bool,
        'status': 'online' if online_bool else 'offline',
        'issue': bool(issues),
        'issues': issues,
        'ip': ip or 'Not reported',
        'os': os_name or 'Not reported',
        'cpu_percent': _num(cpu_percent),
        'ram_percent': _num(ram_percent),
        'disk_percent': _num(disk_percent),
        'isp': _first(pub.get('isp'), net.get('isp'), row.get('isp'), 'Not reported'),
        'public_ip': _first(pub.get('public_ip'), net.get('public_ip'), row.get('public_ip'), 'Not reported'),
        'latency_ms': _first(net.get('latency_ms'), row.get('latency_ms'), 'Not reported'),
        'jitter_ms': _first(net.get('jitter_ms'), row.get('jitter_ms'), 'Not reported'),
        'packet_loss_percent': _first(net.get('packet_loss_percent'), row.get('packet_loss_percent'), 'Not reported'),
    })
    return normalized


def install(Handler: Any, BASE_DIR: Any, load_latest: Any, *args: Any, **kwargs: Any) -> None:
    try:
        import importlib.util
        bridge_file=Path(BASE_DIR)/'v10_final_bridge.py'
        spec=importlib.util.spec_from_file_location('v10_final_bridge_fix5', str(bridge_file))
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        bridge=mod.V10Bridge(Handler, BASE_DIR, load_latest)
        bridge.migrate()
        try: bridge.import_hw_if_needed(False)
        except Exception: pass
    except Exception as e:
        bridge=None
        print('V10_PHASE3_FIX5_BRIDGE_INIT_FAILED', e)

    old_get=Handler.do_GET

    def do_GET(self: Any) -> None:
        raw=self.path
        path=raw.split('?',1)[0]
        qs=urllib.parse.parse_qs(raw.split('?',1)[1]) if '?' in raw else {}
        try:
            if path == '/api/v10final/machines':
                rows=[]
                if bridge:
                    rows=bridge.latest()
                elif callable(load_latest):
                    data=load_latest()
                    if isinstance(data, list): rows=data
                    elif isinstance(data, dict): rows=list(data.values())
                machines=[_normalize_machine(r if isinstance(r,dict) else {'raw':r}) for r in (rows or [])]
                q=(qs.get('q') or [''])[0].lower().strip()
                filter_status=(qs.get('status') or ['all'])[0].lower().strip()
                if q:
                    machines=[m for m in machines if q in json.dumps(m,ensure_ascii=False,default=str).lower()]
                if filter_status in ('online','offline'):
                    want=(filter_status=='online')
                    machines=[m for m in machines if bool(m.get('online')) == want]
                if filter_status in ('issue','issues'):
                    machines=[m for m in machines if bool(m.get('issue'))]
                return _send_json(self, {
                    'ok': True,
                    'source': 'live latest table via v10_final_bridge normalized by Phase3 Fix5',
                    'machines': machines,
                    'rows': machines,
                    'count': len(machines),
                    'total': len(machines),
                    'online_count': sum(1 for m in machines if m.get('online')),
                    'offline_count': sum(1 for m in machines if not m.get('online')),
                    'issue_count': sum(1 for m in machines if m.get('issue')),
                    'filters': {'q': q, 'status': filter_status},
                    'version': PHASE_VERSION,
                })
        except Exception as e:
            return _send_json(self, {'ok':False,'error':str(e),'trace':traceback.format_exc()[-3000:]}, 500)
        return old_get(self)

    Handler.do_GET=do_GET
    print(f'{PHASE_NAME}_LOADED {PHASE_VERSION}')
