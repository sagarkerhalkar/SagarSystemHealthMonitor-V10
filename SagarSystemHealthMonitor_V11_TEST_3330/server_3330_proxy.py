#!/usr/bin/env python3
"""
Sagar System Health Monitor - V11 Test Dashboard 3330 Bridge

Purpose:
- Run a separate test dashboard on port 3330.
- Read live data from existing production server on port 2278.
- Do NOT touch/replace current 2278 server/client flow.
- Keep test-only asset/ISO/settings/message writes in local shadow JSON by default.

Default:
  Dashboard: http://127.0.0.1:3330
  Source:    http://127.0.0.1:2278
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import os
import socket
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SHADOW_PATH = DATA_DIR / "test3330_shadow_store.json"
LOG_PATH = DATA_DIR / "test3330_proxy.log"

APP_NAME = "Sagar System Health Monitor V11 Test 3330 Bridge"
DEFAULT_SOURCE = os.environ.get("CMP_SOURCE_2278", "http://127.0.0.1:2278").rstrip("/")
ALLOW_WRITE_2278 = os.environ.get("CMP_3330_ALLOW_WRITE_2278", "0") == "1"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log(msg: str) -> None:
    line = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    try:
        LOG_PATH.open("a", encoding="utf-8").write(line)
    except Exception:
        pass


def read_shadow() -> Dict[str, Any]:
    if not SHADOW_PATH.exists():
        return {"hardware_assets": [], "software_assets": [], "iso_evidence": [], "messages": [], "notifications": [], "settings": {}}
    try:
        data = json.loads(SHADOW_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("shadow store is not object")
        data.setdefault("hardware_assets", [])
        data.setdefault("software_assets", [])
        data.setdefault("iso_evidence", [])
        data.setdefault("messages", [])
        data.setdefault("notifications", [])
        data.setdefault("settings", {})
        return data
    except Exception:
        return {"hardware_assets": [], "software_assets": [], "iso_evidence": [], "messages": [], "notifications": [], "settings": {}}


def write_shadow(data: Dict[str, Any]) -> None:
    tmp = SHADOW_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(SHADOW_PATH)


def json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def fetch_source(path: str, method: str = "GET", body: bytes | None = None, headers: Dict[str, str] | None = None, timeout: float = 20.0) -> Tuple[int, Dict[str, str], bytes]:
    source = Handler.source_base.rstrip("/")
    url = source + path
    req_headers = dict(headers or {})
    # Keep only safe forward headers.
    for h in ["Host", "Content-Length", "Accept-Encoding", "Connection", "Origin", "Referer"]:
        req_headers.pop(h, None)
    data = body if body else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read()
            resp_headers = {k: v for k, v in resp.headers.items()}
            return resp.status, resp_headers, resp_body
    except urllib.error.HTTPError as e:
        return e.code, {k: v for k, v in e.headers.items()}, e.read()
    except Exception as e:
        return 502, {"Content-Type": "application/json; charset=utf-8"}, json_bytes({
            "ok": False,
            "error": f"Could not read source 2278 server: {e}",
            "source": source,
            "bridge_port": Handler.listen_port,
        })


def source_json(path: str, default: Any = None) -> Any:
    status, _headers, body = fetch_source(path, timeout=8.0)
    if status < 200 or status >= 300:
        return default
    try:
        return json.loads(body.decode("utf-8", errors="replace") or "{}")
    except Exception:
        return default


def source_ok() -> Dict[str, Any]:
    t0 = time.perf_counter()
    data = source_json("/api/health", default={})
    ms = round((time.perf_counter() - t0) * 1000, 1)
    return {"ok": bool(isinstance(data, dict) and data.get("ok", False)), "latency_ms": ms, "health": data}


def overlay_overview(raw: bytes) -> bytes:
    try:
        obj = json.loads(raw.decode("utf-8", errors="replace") or "{}")
        if isinstance(obj, dict):
            sh = read_shadow()
            settings = obj.get("settings") if isinstance(obj.get("settings"), dict) else {}
            merged = dict(settings)
            merged.update(sh.get("settings") or {})
            merged.setdefault("organization_name", "Sagar")
            merged.setdefault("creator_name", "Sagar Kerhalkar")
            merged.setdefault("creator_phone", "8105977226")
            merged.setdefault("creator_website", "https://sagarkerhalkar.com")
            merged.setdefault("public_url", "https://monitor.sagarkerhalkar.com")
            obj["settings"] = merged
            obj["test3330_bridge"] = {
                "ok": True,
                "port": Handler.listen_port,
                "source": Handler.source_base,
                "mode": "read_2278_shadow_writes",
                "allow_write_2278": ALLOW_WRITE_2278,
            }
            return json_bytes(obj)
    except Exception:
        pass
    return raw


def live_machines() -> list[dict[str, Any]]:
    ov = source_json("/api/overview", default={})
    if isinstance(ov, dict):
        machines = ov.get("machines")
        if isinstance(machines, list):
            return machines
    return []


def machine_name(m: Dict[str, Any]) -> str:
    return str(m.get("hostname") or m.get("machine_name") or m.get("id_value") or m.get("machine_id") or "Machine")


def build_hardware_assets() -> list[Dict[str, Any]]:
    sh = read_shadow()
    assets = list(sh.get("hardware_assets", []))
    existing = {str(a.get("machine_id") or a.get("asset_id") or "") for a in assets}
    for m in live_machines():
        mid = str(m.get("machine_id") or "")
        if not mid or mid in existing:
            continue
        assets.append({
            "asset_id": "LIVE-" + mid[:16].replace(":", "-").replace("/", "-"),
            "source": "live_2278",
            "machine_id": mid,
            "hostname": machine_name(m),
            "serial_number": m.get("serial_number") or m.get("official_serial") or "Not reported by client",
            "manufacturer": m.get("manufacturer") or "Not reported by client",
            "model": m.get("model") or "Not reported by client",
            "cpu": m.get("cpu_name") or "Not reported by client",
            "ram_gb": m.get("ram_total_gb") or "Not reported by client",
            "disk_gb": m.get("disk_total_gb") or m.get("disk_size_gb") or "Not reported by client",
            "gpu": ", ".join(m.get("gpu_names") or []) if isinstance(m.get("gpu_names"), list) else (m.get("gpu_name") or "Not reported by client"),
            "location": m.get("location") or "Not mapped",
            "assigned_to": m.get("assigned_to") or "Not mapped",
            "status": "online" if m.get("online") or m.get("fresh") else "offline/stale",
            "last_seen": m.get("last_seen") or m.get("updated_at") or "",
            "remarks": "Auto-created from live 2278 heartbeat. Permanent edits are stored only in 3330 shadow store.",
        })
    return assets


def build_software_assets() -> list[Dict[str, Any]]:
    sh = read_shadow()
    assets = list(sh.get("software_assets", []))
    # Summarize software count per live machine if exact software asset rows are not available here.
    for m in live_machines():
        count = m.get("software_count")
        if count is None:
            continue
        assets.append({
            "asset_id": "LIVE-SW-" + str(m.get("machine_id") or "")[:14].replace(":", "-"),
            "source": "live_2278_summary",
            "software_name": "Installed software inventory",
            "version": "machine summary",
            "publisher": machine_name(m),
            "license_type": "inventory count",
            "license_count": count,
            "installed_count": count,
            "expiry_date": "Not mapped",
            "compliance_status": "review required",
            "remarks": "Machine reported installed software count from 2278. Add purchased software manually in 3330 shadow store.",
        })
    return assets


def build_iso_audit() -> Dict[str, Any]:
    sh = read_shadow()
    machines = live_machines()
    changes = source_json("/api/changes", default={})
    change_rows = changes.get("changes", []) if isinstance(changes, dict) else []
    hw = build_hardware_assets()
    sw = build_software_assets()
    online = [m for m in machines if m.get("online") or m.get("fresh")]
    checks = [
        {"control": "Machine inventory evidence", "status": "ok" if machines else "warning", "evidence": len(machines)},
        {"control": "Hardware asset register", "status": "ok" if hw else "warning", "evidence": len(hw)},
        {"control": "Software asset/license register", "status": "ok" if sw else "warning", "evidence": len(sw)},
        {"control": "Online/offline heartbeat evidence", "status": "ok" if online else "warning", "evidence": len(online)},
        {"control": "Human change-log evidence", "status": "ok" if change_rows else "warning", "evidence": len(change_rows)},
        {"control": "Manual audit evidence", "status": "ok" if sh.get("iso_evidence") else "warning", "evidence": len(sh.get("iso_evidence", []))},
        {"control": "3330 safe test isolation", "status": "ok", "evidence": 1},
    ]
    return {
        "ok": True,
        "mode": "3330 reads live 2278 + local shadow evidence",
        "source": Handler.source_base,
        "counts": {
            "machines": len(machines),
            "online": len(online),
            "offline_or_stale": max(0, len(machines) - len(online)),
            "hardware_assets": len(hw),
            "software_assets": len(sw),
            "changes": len(change_rows),
            "manual_evidence": len(sh.get("iso_evidence", [])),
        },
        "checks": checks,
        "evidence": sh.get("iso_evidence", []),
        "generated_at": now_iso(),
    }


class Handler(BaseHTTPRequestHandler):
    source_base = DEFAULT_SOURCE
    listen_port = 3330
    server_version = "SagarV11Test3330/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        log("%s - %s" % (self.client_address[0], fmt % args))

    def send_json(self, obj: Any, status: int = 200) -> None:
        body = json_bytes(obj)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, path: str) -> None:
        if path in ("", "/"):
            file_path = PUBLIC_DIR / "index.html"
        else:
            rel = urllib.parse.unquote(path.lstrip("/"))
            if ".." in Path(rel).parts:
                self.send_error(403)
                return
            file_path = PUBLIC_DIR / rel
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store" if file_path.suffix in {".html", ".js", ".css"} else "public, max-age=3600")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def proxy(self, method: str) -> None:
        body = self.read_body() if method in {"POST", "PUT", "PATCH"} else None
        status, headers, resp_body = fetch_source(self.path, method=method, body=body, headers=dict(self.headers))
        if self.path.startswith("/api/overview") and status == 200:
            resp_body = overlay_overview(resp_body)
        self.send_response(status)
        skip = {"transfer-encoding", "content-length", "connection", "content-encoding"}
        for k, v in headers.items():
            if k.lower() in skip:
                continue
            if k.lower() == "set-cookie":
                # Browser will save token for localhost:3330; bridge forwards Cookie value to 2278.
                self.send_header("Set-Cookie", v)
            elif k.lower() == "location":
                self.send_header(k, v.replace(self.source_base, ""))
            else:
                self.send_header(k, v)
        self.send_header("X-3330-Bridge", "read-2278")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)

    def local_post_json(self) -> Dict[str, Any]:
        body = self.read_body()
        if not body:
            return {}
        try:
            obj = json.loads(body.decode("utf-8"))
            return obj if isinstance(obj, dict) else {"value": obj}
        except Exception:
            return {"raw": body.decode("utf-8", errors="replace")}

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/test3330/health":
            so = source_ok()
            self.send_json({
                "ok": True,
                "app_name": APP_NAME,
                "port": self.listen_port,
                "source": self.source_base,
                "source_ok": so.get("ok"),
                "source_latency_ms": so.get("latency_ms"),
                "mode": "read 2278 APIs; test-only writes stay local unless CMP_3330_ALLOW_WRITE_2278=1",
                "shadow_store": str(SHADOW_PATH),
                "time": now_iso(),
            })
            return
        if path == "/api/health":
            so = source_ok()
            self.send_json({"ok": True, "app_name": APP_NAME, "version": "11-test-3330", "source": self.source_base, "source_ok": so.get("ok"), "source_health": so.get("health"), "port": self.listen_port})
            return
        if path == "/api/assets/hardware":
            self.send_json({"ok": True, "assets": build_hardware_assets(), "source": self.source_base, "mode": "live 2278 + local shadow"})
            return
        if path == "/api/assets/software":
            self.send_json({"ok": True, "assets": build_software_assets(), "source": self.source_base, "mode": "live 2278 + local shadow"})
            return
        if path == "/api/iso-audit":
            self.send_json(build_iso_audit())
            return
        if path == "/api/settings":
            sh = read_shadow()
            self.send_json({"ok": True, "settings": sh.get("settings", {})})
            return
        if path == "/api/messages":
            if ALLOW_WRITE_2278:
                self.proxy("GET")
            else:
                status, headers, body = fetch_source(self.path, method="GET", headers=dict(self.headers))
                rows = []
                if status == 200:
                    try:
                        rows = json.loads(body.decode("utf-8", errors="replace")).get("messages", [])
                    except Exception:
                        rows = []
                rows = list(read_shadow().get("messages", [])) + rows
                self.send_json({"ok": True, "messages": rows, "mode": "source read + local test messages"})
            return
        if path == "/api/notifications":
            status, headers, body = fetch_source(self.path, method="GET", headers=dict(self.headers))
            rows = []
            if status == 200:
                try:
                    rows = json.loads(body.decode("utf-8", errors="replace")).get("notifications", [])
                except Exception:
                    rows = []
            rows = list(read_shadow().get("notifications", [])) + rows
            self.send_json({"ok": True, "notifications": rows, "mode": "source read + local test notifications"})
            return
        if path.startswith("/api/") or path.startswith("/scripts/"):
            self.proxy("GET")
            return
        self.send_static(path)

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path in {"/api/auth/login", "/api/auth/logout", "/api/auth/change-password"}:
            # Auth must talk to source 2278 so 3330 can read protected 2278 data.
            self.proxy("POST")
            return
        if ALLOW_WRITE_2278 and path.startswith("/api/"):
            self.proxy("POST")
            return
        data = self.local_post_json()
        sh = read_shadow()
        data.setdefault("id", f"test3330-{int(time.time()*1000)}")
        data.setdefault("created_at", now_iso())
        if path == "/api/assets/hardware":
            sh.setdefault("hardware_assets", []).insert(0, data)
            write_shadow(sh)
            self.send_json({"ok": True, "asset": data, "mode": "saved only in 3330 shadow store"})
            return
        if path == "/api/assets/software":
            sh.setdefault("software_assets", []).insert(0, data)
            write_shadow(sh)
            self.send_json({"ok": True, "asset": data, "mode": "saved only in 3330 shadow store"})
            return
        if path == "/api/iso-audit":
            sh.setdefault("iso_evidence", []).insert(0, data)
            write_shadow(sh)
            self.send_json({"ok": True, "evidence": data, "mode": "saved only in 3330 shadow store"})
            return
        if path == "/api/settings":
            current = sh.setdefault("settings", {})
            current.update({k: v for k, v in data.items() if v is not None})
            write_shadow(sh)
            self.send_json({"ok": True, "settings": current, "mode": "saved only in 3330 shadow store"})
            return
        if path == "/api/messages":
            data.setdefault("status", "test-only-local-not-sent-to-client")
            data.setdefault("target_hostname", "3330 test bridge")
            sh.setdefault("messages", []).insert(0, data)
            write_shadow(sh)
            self.send_json({"ok": True, "message": data, "mode": "test-only message saved locally; not sent to 2278 clients"})
            return
        if path == "/api/notifications/test":
            note = {"id": data.get("id"), "created_at": now_iso(), "severity": "info", "hostname": "3330-test", "title": "V11 3330 test notification", "message": data.get("message") or "Test only; not written to 2278"}
            sh.setdefault("notifications", []).insert(0, note)
            write_shadow(sh)
            self.send_json({"ok": True, "notification": note, "mode": "local test notification"})
            return
        if path == "/api/notifications/clear":
            sh["notifications"] = []
            write_shadow(sh)
            self.send_json({"ok": True, "mode": "cleared 3330 local test notifications only"})
            return
        self.send_json({"ok": False, "error": f"3330 safe mode blocked write to {path}. Set CMP_3330_ALLOW_WRITE_2278=1 only if you really want to write to 2278."}, status=403)

    def do_PUT(self) -> None:
        if ALLOW_WRITE_2278:
            self.proxy("PUT")
        else:
            self.send_json({"ok": False, "error": "3330 safe mode blocks PUT to 2278"}, status=403)

    def do_DELETE(self) -> None:
        if ALLOW_WRITE_2278:
            self.proxy("DELETE")
        else:
            self.send_json({"ok": False, "error": "3330 safe mode blocks DELETE to 2278"}, status=403)


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--host", default=os.environ.get("CMP_3330_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CMP_3330_PORT", "3330")))
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Existing 2278 server URL, default http://127.0.0.1:2278")
    args = parser.parse_args()
    Handler.source_base = args.source.rstrip("/")
    Handler.listen_port = args.port
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    log(f"Starting {APP_NAME} on http://{args.host}:{args.port}, source={Handler.source_base}, allow_write_2278={ALLOW_WRITE_2278}")
    print(f"{APP_NAME}")
    print(f"Dashboard: http://127.0.0.1:{args.port}")
    print(f"Health:    http://127.0.0.1:{args.port}/api/test3330/health")
    print(f"Source:    {Handler.source_base}")
    print("Mode:      read 2278 + local shadow writes")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
