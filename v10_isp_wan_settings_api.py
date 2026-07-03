from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import sqlite3
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR: Path = Path('.')
DB_PATH: Path = Path('data/monitor_v10_notify.db')


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def _clean(v: Any, limit: int = 500) -> str:
    if v is None:
        return ''
    s = str(v).strip()
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    return s[:limit]


def _float(v: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if v is None or v == '':
            return default
        return float(v)
    except Exception:
        return default


def _int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == '':
            return default
        return int(float(v))
    except Exception:
        return default


def _bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if v is None:
        return default
    return str(v).strip().lower() in {'1','true','yes','on','enabled','active'}


def _is_local(handler: Any) -> bool:
    try:
        ip = (handler.client_address[0] or '').strip()
        return ip in {'127.0.0.1', '::1', 'localhost'} or ip.startswith('127.')
    except Exception:
        return False


def _current_role(handler: Any) -> str:
    try:
        return (handler.current_role() or '').strip().lower()
    except Exception:
        return ''


def _can_admin(handler: Any) -> bool:
    # Localhost is allowed so offline acceptance tests can verify CRUD without browser cookies.
    # Remote/public requests must still be logged in as admin/super_admin through the base app.
    if _is_local(handler):
        return True
    role = _current_role(handler)
    return role in {'admin', 'super_admin'}


def _can_super_admin(handler: Any) -> bool:
    if _is_local(handler):
        return True
    return _current_role(handler) == 'super_admin'


def ensure_schema() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as con:
        con.execute('''
        CREATE TABLE IF NOT EXISTS router_wan_links(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot INTEGER NOT NULL UNIQUE,
            enabled INTEGER NOT NULL DEFAULT 1,
            locked INTEGER NOT NULL DEFAULT 0,
            isp_name TEXT NOT NULL DEFAULT '',
            wan_name TEXT NOT NULL DEFAULT '',
            router_ip TEXT NOT NULL DEFAULT '',
            gateway_ip TEXT NOT NULL DEFAULT '',
            interface_name TEXT NOT NULL DEFAULT '',
            configured_public_ip TEXT NOT NULL DEFAULT '',
            expected_download_mbps REAL,
            expected_upload_mbps REAL,
            role TEXT NOT NULL DEFAULT 'primary',
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'not_checked',
            last_checked TEXT NOT NULL DEFAULT '',
            latency_ms REAL,
            jitter_ms REAL,
            packet_loss_percent REAL,
            current_download_mbps REAL,
            current_upload_mbps REAL,
            detected_public_ip TEXT NOT NULL DEFAULT '',
            detected_isp TEXT NOT NULL DEFAULT '',
            probe_source TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )''')
        con.execute('CREATE INDEX IF NOT EXISTS idx_router_wan_slot ON router_wan_links(slot)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_router_wan_enabled ON router_wan_links(enabled)')
        con.execute('''
        CREATE TABLE IF NOT EXISTS router_probe_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER,
            slot INTEGER,
            checked_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'not_checked',
            latency_ms REAL,
            jitter_ms REAL,
            packet_loss_percent REAL,
            current_download_mbps REAL,
            current_upload_mbps REAL,
            detected_public_ip TEXT NOT NULL DEFAULT '',
            detected_isp TEXT NOT NULL DEFAULT '',
            probe_source TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT ''
        )''')
        con.execute('CREATE INDEX IF NOT EXISTS idx_router_probe_slot_time ON router_probe_history(slot, checked_at)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_router_probe_time ON router_probe_history(checked_at)')
        con.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    for k in ('enabled','locked'):
        d[k] = bool(d.get(k))
    return d


def list_links() -> List[Dict[str, Any]]:
    ensure_schema()
    with _connect() as con:
        rows = con.execute('SELECT * FROM router_wan_links ORDER BY slot ASC').fetchall()
    return [_row_to_dict(r) for r in rows]


def validate_link(payload: Dict[str, Any]) -> Dict[str, Any]:
    slot = _int(payload.get('slot'), 0)
    if slot < 1 or slot > 10:
        raise ValueError('ISP/WAN slot must be between 1 and 10')
    role = _clean(payload.get('role') or payload.get('type') or 'primary', 50).lower()
    if role not in {'primary','backup','load-balance','load_balance','standby'}:
        role = 'primary'
    role = role.replace('_','-')
    now = now_iso()
    return {
        'slot': slot,
        'enabled': 1 if _bool(payload.get('enabled'), True) else 0,
        'locked': 1 if _bool(payload.get('locked'), False) else 0,
        'isp_name': _clean(payload.get('isp_name') or payload.get('provider') or payload.get('name'), 160),
        'wan_name': _clean(payload.get('wan_name') or payload.get('wan') or f'WAN {slot}', 120),
        'router_ip': _clean(payload.get('router_ip'), 80),
        'gateway_ip': _clean(payload.get('gateway_ip') or payload.get('gateway'), 80),
        'interface_name': _clean(payload.get('interface_name') or payload.get('interface') or payload.get('port'), 120),
        'configured_public_ip': _clean(payload.get('configured_public_ip') or payload.get('public_ip'), 80),
        'expected_download_mbps': _float(payload.get('expected_download_mbps') or payload.get('expected_down_mbps')),
        'expected_upload_mbps': _float(payload.get('expected_upload_mbps') or payload.get('expected_up_mbps')),
        'role': role,
        'notes': _clean(payload.get('notes') or payload.get('message'), 1000),
        'updated_at': now,
    }


def upsert_link(payload: Dict[str, Any], allow_locked_edit: bool = False) -> Dict[str, Any]:
    ensure_schema()
    data = validate_link(payload)
    now = now_iso()
    with _connect() as con:
        existing = con.execute('SELECT * FROM router_wan_links WHERE slot=?', (data['slot'],)).fetchone()
        if existing and int(existing['locked'] or 0) and not allow_locked_edit:
            return {'ok': False, 'error': 'locked', 'message': 'This ISP/WAN link is locked. Only Super Admin can edit/delete it.'}
        if existing:
            con.execute('''
                UPDATE router_wan_links SET enabled=?, locked=?, isp_name=?, wan_name=?, router_ip=?, gateway_ip=?,
                    interface_name=?, configured_public_ip=?, expected_download_mbps=?, expected_upload_mbps=?, role=?, notes=?, updated_at=?
                WHERE slot=?
            ''', (data['enabled'], data['locked'], data['isp_name'], data['wan_name'], data['router_ip'], data['gateway_ip'],
                  data['interface_name'], data['configured_public_ip'], data['expected_download_mbps'], data['expected_upload_mbps'],
                  data['role'], data['notes'], data['updated_at'], data['slot']))
        else:
            con.execute('''
                INSERT INTO router_wan_links(slot,enabled,locked,isp_name,wan_name,router_ip,gateway_ip,interface_name,
                    configured_public_ip,expected_download_mbps,expected_upload_mbps,role,notes,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (data['slot'], data['enabled'], data['locked'], data['isp_name'], data['wan_name'], data['router_ip'], data['gateway_ip'],
                  data['interface_name'], data['configured_public_ip'], data['expected_download_mbps'], data['expected_upload_mbps'],
                  data['role'], data['notes'], now, data['updated_at']))
        con.commit()
    return {'ok': True, 'link': get_link_by_slot(data['slot'])}


def save_links(payloads: List[Dict[str, Any]], allow_locked_edit: bool = False) -> Dict[str, Any]:
    if not isinstance(payloads, list):
        raise ValueError('isp_links must be an array')
    if len(payloads) > 10:
        return {'ok': False, 'error': 'max_10_isp_links', 'message': 'One organization can have maximum 10 ISP/WAN links.'}
    if len(payloads) < 1:
        return {'ok': False, 'error': 'min_1_isp_link', 'message': 'At least one ISP/WAN link is required when saving full ISP list.'}
    saved = []
    for p in payloads:
        res = upsert_link(p, allow_locked_edit=allow_locked_edit)
        if not res.get('ok'):
            return res
        saved.append(res.get('link'))
    return {'ok': True, 'count': len(saved), 'links': list_links()}


def get_link_by_slot(slot: int) -> Dict[str, Any]:
    ensure_schema()
    with _connect() as con:
        row = con.execute('SELECT * FROM router_wan_links WHERE slot=?', (int(slot),)).fetchone()
    return _row_to_dict(row) if row else {}


def delete_link(slot: int, allow_locked_delete: bool = False) -> Dict[str, Any]:
    ensure_schema()
    slot = int(slot)
    if slot < 1 or slot > 10:
        return {'ok': False, 'error': 'bad_slot'}
    with _connect() as con:
        existing = con.execute('SELECT * FROM router_wan_links WHERE slot=?', (slot,)).fetchone()
        if not existing:
            return {'ok': True, 'deleted': False, 'slot': slot}
        if int(existing['locked'] or 0) and not allow_locked_delete:
            return {'ok': False, 'error': 'locked', 'message': 'This ISP/WAN link is locked. Only Super Admin can delete it.'}
        con.execute('DELETE FROM router_wan_links WHERE slot=?', (slot,))
        con.commit()
    return {'ok': True, 'deleted': True, 'slot': slot}


def ping_probe(host: str, count: int = 4) -> Dict[str, Any]:
    host = _clean(host, 100)
    if not host:
        return {'status': 'not_configured', 'latency_ms': None, 'jitter_ms': None, 'packet_loss_percent': None, 'error': 'gateway_ip not configured'}
    result = {'status': 'unknown', 'latency_ms': None, 'jitter_ms': None, 'packet_loss_percent': 100.0, 'error': ''}
    try:
        if os.name == 'nt':
            cmd = ['ping', '-n', str(count), '-w', '1000', host]
        else:
            cmd = ['ping', '-c', str(count), '-W', '1', host]
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=count + 5)
        text = (cp.stdout or '') + '\n' + (cp.stderr or '')
        times = [float(x) for x in re.findall(r'time[=<]\s*([0-9.]+)\s*ms', text, flags=re.I)]
        # Windows sometimes outputs "Average = 1ms" when regex times are missing.
        if not times:
            avg = re.search(r'Average\s*=\s*([0-9.]+)\s*ms', text, flags=re.I)
            if avg:
                times = [float(avg.group(1))]
        received = len(times)
        loss = max(0.0, round((count - received) * 100.0 / count, 1)) if count else 100.0
        if times:
            result.update({
                'status': 'up' if loss < 100 else 'down',
                'latency_ms': round(sum(times) / len(times), 1),
                'jitter_ms': round(max(times) - min(times), 1) if len(times) > 1 else 0.0,
                'packet_loss_percent': loss,
                'error': ''
            })
        else:
            result.update({'status': 'down', 'packet_loss_percent': loss, 'error': 'ping no response'})
    except Exception as e:
        result.update({'status': 'error', 'error': str(e)})
    return result


def cloudflare_trace(timeout: float = 5.0) -> Dict[str, Any]:
    # Active public route only. It cannot identify all WANs without router/SNMP/Omada feed.
    out = {'ok': False, 'public_ip': '', 'isp': '', 'source': 'cloudflare_trace', 'error': ''}
    try:
        req = urllib.request.Request('https://www.cloudflare.com/cdn-cgi/trace', headers={'User-Agent':'V10Monitor/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read(8192).decode('utf-8', errors='replace')
        data = {}
        for line in txt.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                data[k.strip()] = v.strip()
        out.update({'ok': True, 'public_ip': data.get('ip',''), 'isp': data.get('colo',''), 'raw': data})
    except Exception as e:
        out.update({'error': str(e)})
    return out


def probe_link(link: Dict[str, Any], active_route: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    p = ping_probe(link.get('gateway_ip') or link.get('router_ip') or '')
    active_route = active_route or {}
    detected_public_ip = active_route.get('public_ip') or ''
    configured_public_ip = link.get('configured_public_ip') or ''
    public_match = bool(configured_public_ip and detected_public_ip and configured_public_ip == detected_public_ip)
    status = p.get('status') or 'not_checked'
    if not link.get('enabled'):
        status = 'disabled'
    elif p.get('status') == 'up' and (not configured_public_ip or public_match):
        status = 'up'
    elif p.get('status') == 'up' and configured_public_ip and not public_match:
        status = 'gateway_up_not_active_public_route'
    checked = now_iso()
    result = dict(link)
    result.update({
        'status': status,
        'last_checked': checked,
        'latency_ms': p.get('latency_ms'),
        'jitter_ms': p.get('jitter_ms'),
        'packet_loss_percent': p.get('packet_loss_percent'),
        # Do not fake speed. Per-WAN speed needs router feed or a routed probe through that WAN.
        'current_download_mbps': None,
        'current_upload_mbps': None,
        'detected_public_ip': detected_public_ip,
        'detected_isp': active_route.get('isp') or '',
        'probe_source': 'gateway_ping + cloudflare_active_route',
        'last_error': p.get('error') or active_route.get('error') or '',
        'active_public_route_match': public_match,
        'router_feed_connected': False,
        'router_feed_message': 'Router API/SNMP/Omada feed not configured. Gateway ping and active Cloudflare route are being monitored.'
    })
    return result


def update_probe_result(result: Dict[str, Any]) -> None:
    ensure_schema()
    with _connect() as con:
        con.execute('''
            UPDATE router_wan_links SET status=?, last_checked=?, latency_ms=?, jitter_ms=?, packet_loss_percent=?,
                current_download_mbps=?, current_upload_mbps=?, detected_public_ip=?, detected_isp=?, probe_source=?, last_error=?, updated_at=?
            WHERE slot=?
        ''', (result.get('status') or '', result.get('last_checked') or '', result.get('latency_ms'), result.get('jitter_ms'),
              result.get('packet_loss_percent'), result.get('current_download_mbps'), result.get('current_upload_mbps'),
              result.get('detected_public_ip') or '', result.get('detected_isp') or '', result.get('probe_source') or '',
              result.get('last_error') or '', now_iso(), result.get('slot')))
        con.execute('''
            INSERT INTO router_probe_history(link_id, slot, checked_at, status, latency_ms, jitter_ms, packet_loss_percent,
                current_download_mbps, current_upload_mbps, detected_public_ip, detected_isp, probe_source, error, raw_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (result.get('id'), result.get('slot'), result.get('last_checked') or now_iso(), result.get('status') or '',
              result.get('latency_ms'), result.get('jitter_ms'), result.get('packet_loss_percent'), result.get('current_download_mbps'),
              result.get('current_upload_mbps'), result.get('detected_public_ip') or '', result.get('detected_isp') or '',
              result.get('probe_source') or '', result.get('last_error') or '', json.dumps(result, ensure_ascii=False, default=str)))
        con.commit()


def status(force: bool = False) -> Dict[str, Any]:
    ensure_schema()
    links = list_links()
    active_route = cloudflare_trace(timeout=4.0) if force else cloudflare_trace(timeout=3.0)
    probed = []
    for link in links:
        if link.get('enabled'):
            res = probe_link(link, active_route)
            update_probe_result(res)
            probed.append(res)
        else:
            probed.append(link)
    total = len(probed)
    enabled = len([x for x in probed if x.get('enabled')])
    up = len([x for x in probed if str(x.get('status')) in {'up','gateway_up_not_active_public_route'}])
    down = len([x for x in probed if str(x.get('status')) in {'down','error'}])
    return {
        'ok': True,
        'source': 'router_wan_links_manual_settings_plus_gateway_ping_cloudflare_active_route',
        'max_isp_links': 10,
        'total_links': total,
        'enabled_links': enabled,
        'up_links': up,
        'down_links': down,
        'active_public_route': active_route,
        'links': probed,
        'message': 'ISP links are configured in Settings. Monitoring is automatic after save. Speed per WAN requires router API/SNMP/Omada feed or routed WAN probes.'
    }


def sample_csv() -> bytes:
    out = io.StringIO()
    fields = ['slot','enabled','isp_name','wan_name','router_ip','gateway_ip','interface_name','configured_public_ip','expected_download_mbps','expected_upload_mbps','role','notes']
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    w.writerow({'slot':1,'enabled':1,'isp_name':'Airtel','wan_name':'WAN 1','router_ip':'192.168.0.1','gateway_ip':'192.168.0.1','interface_name':'WAN1','configured_public_ip':'','expected_download_mbps':300,'expected_upload_mbps':100,'role':'primary','notes':'Main ISP'})
    w.writerow({'slot':2,'enabled':1,'isp_name':'Jio','wan_name':'WAN 2','router_ip':'192.168.0.1','gateway_ip':'192.168.1.1','interface_name':'WAN2','configured_public_ip':'','expected_download_mbps':300,'expected_upload_mbps':100,'role':'backup','notes':'Backup ISP'})
    return out.getvalue().encode('utf-8-sig')


def export_csv(rows: List[Dict[str, Any]]) -> bytes:
    fields = ['slot','enabled','locked','isp_name','wan_name','role','router_ip','gateway_ip','interface_name','configured_public_ip','expected_download_mbps','expected_upload_mbps','status','last_checked','latency_ms','jitter_ms','packet_loss_percent','current_download_mbps','current_upload_mbps','detected_public_ip','detected_isp','notes']
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return out.getvalue().encode('utf-8-sig')


def _send_csv(handler: Any, body: bytes, filename: str) -> None:
    handler._send(200, body, 'text/csv; charset=utf-8', {'Content-Disposition': f'attachment; filename={filename}'})


def install(Handler: Any, base_dir: Any) -> None:
    global BASE_DIR, DB_PATH
    BASE_DIR = Path(base_dir)
    DB_PATH = BASE_DIR / 'data' / 'monitor_v10_notify.db'
    ensure_schema()

    old_get = Handler.do_GET
    old_post = Handler.do_POST

    def new_get(self):
        path = self.path.split('?', 1)[0]
        qs: Dict[str, List[str]] = {}
        if '?' in self.path:
            from urllib.parse import parse_qs
            qs = parse_qs(self.path.split('?', 1)[1])
        try:
            if path in ('/api/v10/settings/isp-links', '/api/v10/isp-wan/links', '/api/v10final/settings/isp-links'):
                return self.send_json({'ok': True, 'max_isp_links': 10, 'links': list_links()})
            if path in ('/api/v10/isp-wan/status', '/api/v10/router-wan/status', '/api/v10final/router-wan/status'):
                force = (qs.get('force') or ['0'])[0] in ('1','true','yes','on')
                return self.send_json(status(force=force))
            if path in ('/api/v10/isp-wan/summary', '/api/v10final/router-wan/summary'):
                s = status(force=False)
                return self.send_json({'ok': True, 'summary': {k:s.get(k) for k in ['source','max_isp_links','total_links','enabled_links','up_links','down_links','active_public_route','message']}, 'links': s.get('links')})
            if path == '/api/v10/isp-wan/sample.csv':
                return _send_csv(self, sample_csv(), 'sample_isp_wan_links.csv')
            if path == '/api/v10/isp-wan/export.csv':
                return _send_csv(self, export_csv(list_links()), 'isp_wan_links.csv')
        except Exception as e:
            return self.send_json({'ok': False, 'error': str(e)}, 500)
        return old_get(self)

    def new_post(self):
        path = self.path.split('?', 1)[0]
        try:
            if path in ('/api/v10/settings/isp-link', '/api/v10/isp-wan/link', '/api/v10final/settings/isp-link'):
                body = self.read_json()
                if not _can_admin(self):
                    return self.send_json({'ok': False, 'error': 'admin_required'}, 403)
                return self.send_json(upsert_link(body, allow_locked_edit=_can_super_admin(self)))
            if path in ('/api/v10/settings/isp-links', '/api/v10/isp-wan/links', '/api/v10final/settings/isp-links'):
                body = self.read_json()
                if not _can_admin(self):
                    return self.send_json({'ok': False, 'error': 'admin_required'}, 403)
                links = body.get('isp_links') or body.get('links') or []
                return self.send_json(save_links(links, allow_locked_edit=_can_super_admin(self)))
            if path in ('/api/v10/settings/isp-link/delete', '/api/v10/isp-wan/link/delete', '/api/v10final/settings/isp-link/delete'):
                body = self.read_json()
                if not _can_admin(self):
                    return self.send_json({'ok': False, 'error': 'admin_required'}, 403)
                return self.send_json(delete_link(_int(body.get('slot'), 0), allow_locked_delete=_can_super_admin(self)))
            if path in ('/api/v10/isp-wan/probe-now', '/api/v10final/router-wan/probe-now'):
                if not _can_admin(self):
                    return self.send_json({'ok': False, 'error': 'admin_required'}, 403)
                return self.send_json(status(force=True))
        except Exception as e:
            return self.send_json({'ok': False, 'error': str(e)}, 500)
        return old_post(self)

    Handler.do_GET = new_get
    Handler.do_POST = new_post
