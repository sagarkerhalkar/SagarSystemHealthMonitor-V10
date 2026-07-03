from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

SOURCE_2278_DB = Path(os.environ.get('V10_SOURCE_2278_DB', r'D:\SagarSystemHealthMonitor\data\monitor.db'))
_CACHE: Dict[str, Any] = {'at': None, 'data': None}
CACHE_SECONDS = 20


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _connect_ro() -> sqlite3.Connection:
    uri = 'file:' + str(SOURCE_2278_DB).replace('\\', '/') + '?mode=ro'
    con = sqlite3.connect(uri, uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    return con


def _safe_json(v: Any) -> Dict[str, Any]:
    if isinstance(v, dict):
        return v
    if v is None:
        return {}
    try:
        d = json.loads(str(v))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == '':
            return default
        return float(str(v).replace('%', '').replace('C', '').replace('c', '').strip())
    except Exception:
        return default


def _iso_parse(s: Any) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        txt = str(s).strip()
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
    return round((_now() - d).total_seconds() / 60.0, 2)


def _count(con: sqlite3.Connection, table: str) -> int:
    try:
        exists = con.execute("select name from sqlite_master where type='table' and name=?", (table,)).fetchone()
        if not exists:
            return 0
        return int(con.execute(f"select count(*) c from {table}").fetchone()['c'])
    except Exception:
        return 0


def _table_cols(con: sqlite3.Connection, table: str) -> List[str]:
    try:
        return [r[1] for r in con.execute(f'PRAGMA table_info({table})').fetchall()]
    except Exception:
        return []


def _summary_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    rd = {k: row[k] for k in row.keys()}
    s = _safe_json(rd.get('summary_json'))
    payload = s.get('payload') if isinstance(s.get('payload'), dict) else {}
    updated_at = rd.get('updated_at') or s.get('updated_at') or payload.get('timestamp') or s.get('timestamp')
    return {
        'machine_id': rd.get('machine_id') or s.get('machine_id') or '',
        'hostname': rd.get('hostname') or s.get('hostname') or payload.get('hostname') or '',
        'updated_at': updated_at or '',
        'age_minutes': _age_minutes(updated_at),
        'cpu_percent': _float(s.get('cpu_percent') or payload.get('cpu_percent')),
        'ram_percent': _float(s.get('ram_percent') or payload.get('ram_percent')),
        'disk_max_percent': _float(s.get('disk_max_percent')),
        'cpu_temp_c': _float(s.get('cpu_temp_c')),
        'gpu_max_temp_c': _float(s.get('gpu_max_temp_c')),
    }


def evaluate_fast() -> Dict[str, Any]:
    cached_at = _CACHE.get('at')
    if isinstance(cached_at, dt.datetime) and (_now() - cached_at).total_seconds() < CACHE_SECONDS and _CACHE.get('data'):
        out = dict(_CACHE['data'])
        out['cached'] = True
        out['cache_age_seconds'] = round((_now() - cached_at).total_seconds(), 1)
        return out

    if not SOURCE_2278_DB.exists():
        return {'ok': False, 'mode': 'read_only_fast_simulation_no_write', 'error': '2278 DB not found', 'source_db': str(SOURCE_2278_DB), 'no_write_to_2278': True}

    started = _now()
    alerts: List[Dict[str, Any]] = []
    with _connect_ro() as con:
        rules_count = _count(con, 'notification_rules')
        recent_notifications_count = min(_count(con, 'notifications'), 100)
        cols = _table_cols(con, 'latest')
        if not cols:
            rows = []
        else:
            order = 'updated_at DESC' if 'updated_at' in cols else 'rowid DESC'
            select_cols = []
            for c in ['machine_id', 'hostname', 'updated_at', 'summary_json']:
                if c in cols:
                    select_cols.append(c)
            if 'summary_json' not in select_cols:
                select_cols.append('*')
            q = f"select {', '.join(select_cols)} from latest order by {order} limit 1000"
            rows = con.execute(q).fetchall()

    fresh = 0
    for row in rows:
        m = _summary_from_row(row)
        if m.get('age_minutes') is not None and m['age_minutes'] <= 10:
            fresh += 1
        hn = m.get('hostname') or m.get('machine_id')
        cpu = _float(m.get('cpu_percent'))
        ram = _float(m.get('ram_percent'))
        disk = _float(m.get('disk_max_percent'))
        cput = _float(m.get('cpu_temp_c'))
        gput = _float(m.get('gpu_max_temp_c'))
        if cpu >= 90 and ram >= 90:
            alerts.append({'machine_id': m.get('machine_id'), 'hostname': hn, 'rule': 'cpu_ram_critical', 'severity': 'critical', 'message': f'CPU {cpu}% and RAM {ram}% critical'})
        if disk >= 90:
            alerts.append({'machine_id': m.get('machine_id'), 'hostname': hn, 'rule': 'disk_high', 'severity': 'warning', 'message': f'Disk usage {disk}% high'})
        if cput >= 90:
            alerts.append({'machine_id': m.get('machine_id'), 'hostname': hn, 'rule': 'cpu_temp_high', 'severity': 'critical', 'message': f'CPU temperature {cput}C high'})
        if gput >= 90:
            alerts.append({'machine_id': m.get('machine_id'), 'hostname': hn, 'rule': 'gpu_temp_high', 'severity': 'critical', 'message': f'GPU temperature {gput}C high'})

    out = {
        'ok': True,
        'mode': 'read_only_fast_simulation_no_write',
        'source': '2278 latest + 2278 notification_rules; fast cached read-only evaluator',
        'source_db': str(SOURCE_2278_DB),
        'no_write_to_2278': True,
        'rules_count': rules_count,
        'recent_notifications_count': recent_notifications_count,
        'machines_checked': len(rows),
        'fresh_machines_checked': fresh,
        'simulated_alerts_count': len(alerts),
        'simulated_alerts': alerts[:100],
        'elapsed_ms': int((_now() - started).total_seconds() * 1000),
        'cached': False,
        'note': 'Fast read-only notification simulation. No writes to 2278 or V10 notification tables.',
    }
    _CACHE['at'] = _now()
    _CACHE['data'] = out
    return out


def install(Handler: Any, base_dir: Any) -> None:
    old_get = Handler.do_GET

    def new_get(self):
        path = self.path.split('?', 1)[0]
        if path in ('/api/v10/source2278/notification-test', '/api/v10/live-source2278/notification-test', '/api/v10/source2278/notification-test-fast'):
            try:
                return self.send_json(evaluate_fast())
            except Exception as e:
                return self.send_json({'ok': False, 'mode': 'read_only_fast_simulation_no_write', 'error': str(e), 'source_db': str(SOURCE_2278_DB), 'no_write_to_2278': True}, 500)
        return old_get(self)

    Handler.do_GET = new_get
