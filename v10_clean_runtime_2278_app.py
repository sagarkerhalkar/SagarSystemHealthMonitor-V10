from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs

BASE_DIR = Path('.')


def _load_contract():
    p = Path(BASE_DIR) / 'v10_selected_machine_contract_api.py'
    if not p.exists():
        raise RuntimeError('v10_selected_machine_contract_api.py not found')
    spec = importlib.util.spec_from_file_location('v10_selected_machine_contract_api_clean_runtime', str(p))
    if not spec or not spec.loader:
        raise RuntimeError('cannot import selected machine contract api')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.BASE_DIR = Path(BASE_DIR)
        mod.SOURCE_2278_DB = Path(os.environ.get('V10_SOURCE_2278_DB', r'D:\SagarSystemHealthMonitor\data\monitor.db'))
    except Exception:
        pass
    return mod


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


def _int(v: Any, default: int = 1000) -> int:
    try:
        return int(float(str(v)))
    except Exception:
        return default


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
        try:
            contract = _load_contract()
            machine_id = (qs.get('machine_id') or qs.get('id') or [''])[0]
            hostname = (qs.get('hostname') or [''])[0]
            query = (qs.get('query') or qs.get('q') or [''])[0]
            swq = (qs.get('software_query') or qs.get('sw_query') or [''])[0]
            limit = _int((qs.get('limit') or ['2000'])[0], 2000)

            if path == '/api/v10/app/health':
                return _send_json(self, {
                    'ok': True,
                    'app': 'V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP',
                    'auth': 'public_readonly_for_dashboard',
                    'source': '2278_readonly_selected_machine_contract',
                    'source_db': str(getattr(contract, 'SOURCE_2278_DB', '')),
                    'no_write_to_2278': True,
                })
            if path == '/api/v10/app/home':
                return _send_json(self, contract.home_summary())
            if path == '/api/v10/app/machines':
                return _send_json(self, contract.selected_list())
            if path in ('/api/v10/app/machine360', '/api/v10/app/hardware'):
                return _send_json(self, contract.selected_hardware(machine_id, query, hostname))
            if path == '/api/v10/app/network':
                return _send_json(self, contract.selected_network(machine_id, query, hostname))
            if path == '/api/v10/app/software':
                return _send_json(self, contract.selected_software(machine_id, query, hostname, swq, limit))
            if path == '/api/v10/app/notifications-fast':
                return _send_json(self, contract.notification_fast())
            if path == '/api/v10/app/isp-wan':
                # Keep it non-blocking. ISP/WAN manager can be wired later from existing endpoint/UI.
                return _send_json(self, {'ok': True, 'source': 'clean_runtime_placeholder', 'links': [], 'note': 'ISP/WAN Settings feed not loaded in clean runtime route yet; no dummy ISP speed shown.'})
            return _send_json(self, {'ok': False, 'error': 'not_found', 'path': path}, 404)
        except Exception as e:
            return _send_json(self, {'ok': False, 'error': str(e), 'path': path, 'no_write_to_2278': True}, 500)

    Handler.do_GET = new_get
