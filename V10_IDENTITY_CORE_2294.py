#!/usr/bin/env python3
"""
Sagar Kerhalkar System Monitor Tool - zero dependency receiver + premium dashboard.
Runs with Python standard library only.
Default: http://0.0.0.0:2278
"""
from __future__ import annotations

import argparse
import ast
import base64
import csv
import datetime as dt
import html
import hmac
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
SCRIPTS_DIR = BASE_DIR / "scripts"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "monitor_v10_notify.db"  # V10-only writable DB; main 2278 DB is not copied
LOG_PATH = DATA_DIR / "server.log"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_LOCK = threading.RLock()
SERVER_ISP_LOCK = threading.RLock()
SERVER_ISP_REFRESHING = False
SERVER_ISP_MEMORY: Dict[str, Any] = {"public_ip":"", "isp":"", "org":"", "as":"", "country":"", "city":"", "checked_at":"", "source":"not_checked", "ok":False}

APP_NAME = "Sagar Kerhalkar System Health Monitor Tool"
DEFAULT_ADMIN_PASSWORD = os.environ.get("CMP_ADMIN_PASSWORD", "Admin@12345")
SESSIONS: Dict[str, float] = {}
SESSION_TTL_SECONDS = 12 * 60 * 60
INTERNET_HEALTH_LOCK = threading.RLock()
INTERNET_HEALTH_CACHE: Dict[str, Any] = {"ok": False, "checked_at": "", "source": "not_checked"}
INTERNET_HEALTH_REFRESHING = False


BAD_IDS = {
    "", "none", "null", "unknown", "na", "n/a", "not available", "not applicable",
    "default string", "to be filled by o.e.m.", "to be filled by oem", "system serial number",
    "base board serial number", "chassis serial number", "0", "00000000", "ffffffff",
    "00000000-0000-0000-0000-000000000000", "ffffffff-ffff-ffff-ffff-ffffffffffff",
    "bss-0123456789", "bss0123456789", "0123456789", "123456789", "1234567890",
    "serial number", "system product name", "all series", "not specified", "not to be filled"
}

BAD_ID_PATTERNS = [
    r"^bss[-_ ]*0*123456789$",
    r"^bss[-_ ]*[0-9]{4,}$",
    r"^o\.e\.m",
    r"^to be filled",
    r"^default",
    r"^1234567",
    r"^0{4,}$",
    r"^f{4,}$",
]

DEFAULT_RULES = [
    {"id":"cpu_high","name":"CPU usage high","metric":"cpu_percent","op":">=","threshold":90,"enabled":True,"severity":"warning","cooldown_minutes":15},
    {"id":"ram_high","name":"RAM usage high","metric":"ram_percent","op":">=","threshold":90,"enabled":True,"severity":"warning","cooldown_minutes":15},
    {"id":"disk_high","name":"Disk usage high","metric":"disk_max_percent","op":">=","threshold":90,"enabled":True,"severity":"critical","cooldown_minutes":30},
    {"id":"cpu_temp_high","name":"CPU temperature high","metric":"cpu_temp_c","op":">=","threshold":85,"enabled":False,"severity":"critical","cooldown_minutes":20},
    {"id":"gpu_temp_high","name":"GPU temperature high","metric":"gpu_max_temp_c","op":">=","threshold":85,"enabled":False,"severity":"critical","cooldown_minutes":20},
    {"id":"wan_down_low","name":"Current download speed low","metric":"wan_download_mbps","op":"<=","threshold":1,"enabled":False,"severity":"warning","cooldown_minutes":15},
    {"id":"wan_up_low","name":"Current upload speed low","metric":"wan_upload_mbps","op":"<=","threshold":1,"enabled":False,"severity":"warning","cooldown_minutes":15},
    {"id":"offline","name":"Machine offline","metric":"offline_minutes","op":">=","threshold":1,"enabled":True,"severity":"critical","cooldown_minutes":5},
    {"id":"usb_change","name":"USB or peripheral changed","metric":"change_usb","op":"event","threshold":1,"enabled":False,"severity":"info","cooldown_minutes":1},
    {"id":"hardware_change","name":"Hardware changed","metric":"change_hardware","op":"event","threshold":1,"enabled":False,"severity":"warning","cooldown_minutes":2},
    {"id":"software_change","name":"Software installed/removed","metric":"change_software","op":"event","threshold":1,"enabled":False,"severity":"info","cooldown_minutes":5},
    {"id":"ip_change","name":"IP address changed","metric":"change_ip","op":"event","threshold":1,"enabled":False,"severity":"info","cooldown_minutes":2},
    {"id":"vpn_change","name":"VPN status changed","metric":"change_vpn","op":"event","threshold":1,"enabled":False,"severity":"warning","cooldown_minutes":2},
]

MIME = {
    ".html":"text/html; charset=utf-8", ".css":"text/css; charset=utf-8", ".js":"application/javascript; charset=utf-8",
    ".json":"application/json; charset=utf-8", ".svg":"image/svg+xml", ".ico":"image/x-icon", ".txt":"text/plain; charset=utf-8", ".ps1":"text/plain; charset=utf-8", ".sh":"text/plain; charset=utf-8", ".bat":"text/plain; charset=utf-8", ".deb":"application/vnd.debian.binary-package"
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log(msg: str) -> None:
    line = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass




def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or _b64(secrets.token_bytes(16))
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return "pbkdf2_sha256$120000$" + salt + "$" + _b64(dk)


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, good = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters))
        return hmac.compare_digest(_b64(dk), good)
    except Exception:
        return False


def parse_cookies(header: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in (header or "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            out[k] = v
    return out


def is_local_request(client_ip: str) -> bool:
    ip = (client_ip or "").strip()
    return ip in {"127.0.0.1", "::1", "localhost"} or ip.startswith("127.")


def new_session(username: str = "admin", role: str = "admin") -> str:
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {"expires": time.time() + SESSION_TTL_SECONDS, "username": username or "admin", "role": role or "admin"}
    return token


def session_info(token: str) -> Dict[str, Any]:
    raw = SESSIONS.get(token or "")
    if not raw:
        return {}
    # Backward compatibility for older in-memory sessions that stored only expiry as float.
    if isinstance(raw, (int, float)):
        exp = float(raw)
        info = {"expires": exp, "username": "admin", "role": "admin"}
    elif isinstance(raw, dict):
        info = dict(raw)
        exp = float(info.get("expires") or 0)
    else:
        return {}
    if exp < time.time():
        SESSIONS.pop(token, None)
        return {}
    info["expires"] = time.time() + SESSION_TTL_SECONDS
    SESSIONS[token] = info
    return info


def valid_session(token: str) -> bool:
    return bool(session_info(token))


def auth_required_path(method: str, path: str) -> bool:
    # Heartbeats and install scripts must stay open so clients can report and update.
    public_get = {"/api/health", "/api/auth/status"}
    public_post = {"/api/heartbeat", "/heartbeat", "/submit", "/api/auth/login"}
    if method == "GET" and (path in public_get or path.startswith("/scripts/")):
        return False
    if method == "POST" and path in public_post:
        return False
    if method == "GET" and not path.startswith("/api/"):
        return False
    return path.startswith("/api/")


def tcp_latency_ms(host: str, port: int, timeout: float = 1.5) -> Optional[float]:
    import socket
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return round((time.perf_counter() - t0) * 1000, 1)
    except Exception:
        return None


def run_ping_probe(host: str = "1.1.1.1", count: int = 4) -> Dict[str, Any]:
    result: Dict[str, Any] = {"host": host, "sent": count, "received": 0, "loss_percent": 100.0, "avg_ms": None, "min_ms": None, "max_ms": None, "jitter_ms": None}
    try:
        if os.name == "nt":
            cmd = ["ping", "-n", str(count), "-w", "1000", host]
        else:
            cmd = ["ping", "-c", str(count), "-W", "1", host]
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=count + 3)
        text = (cp.stdout or "") + "\n" + (cp.stderr or "")
        times = [float(x) for x in re.findall(r"time[=<]\s*([0-9.]+)\s*ms", text, flags=re.I)]
        result["received"] = len(times)
        if count > 0:
            result["loss_percent"] = round(max(0, (count - len(times)) * 100.0 / count), 1)
        if times:
            result["avg_ms"] = round(sum(times)/len(times), 1)
            result["min_ms"] = round(min(times), 1)
            result["max_ms"] = round(max(times), 1)
            result["jitter_ms"] = round(max(times)-min(times), 1)
    except Exception as e:
        result["error"] = str(e)
    return result


def server_internet_health(force: bool = False, speed_probe: bool = False) -> Dict[str, Any]:
    """Live server-side ISP health. Latency/loss is light; speed probe is small and cached."""
    global INTERNET_HEALTH_CACHE, INTERNET_HEALTH_REFRESHING
    with INTERNET_HEALTH_LOCK:
        try:
            checked = dt.datetime.fromisoformat(str(INTERNET_HEALTH_CACHE.get("checked_at", "")).replace("Z", "+00:00"))
            age = (dt.datetime.now(dt.timezone.utc) - checked).total_seconds()
        except Exception:
            age = 9999
        if not force and INTERNET_HEALTH_CACHE.get("ok") and age < 15:
            return dict(INTERNET_HEALTH_CACHE)
    isp = server_public_internet_info(False)
    # Use multiple latency methods. ICMP ping can be blocked on many Windows networks,
    # so TCP 443 fallback keeps the dashboard from showing N/A for live-class latency.
    tcp_targets = [("cloudflare_dns", "1.1.1.1", 443), ("cloudflare_site", "www.cloudflare.com", 443), ("google_dns", "8.8.8.8", 53)]
    latency = []
    for name, host, port in tcp_targets:
        latency.append({"name": name, "host": host, "port": port, "tcp_ms": tcp_latency_ms(host, port)})
    ping = run_ping_probe("1.1.1.1", 4)
    down_mbps = None
    up_mbps = None
    speed_note = "Live server ISP health probe. This is for class stability; use Full Speed Test for capacity."
    if speed_probe:
        try:
            size = 2_000_000
            url = f"https://speed.cloudflare.com/__down?bytes={size}"
            t0 = time.perf_counter()
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": APP_NAME}), timeout=8) as r:
                data = r.read(size + 128)
            elapsed = max(0.001, time.perf_counter() - t0)
            down_mbps = round((len(data) * 8 / 1_000_000) / elapsed, 2)
        except Exception as e:
            speed_note = "Download probe failed: " + str(e)[:120]
        try:
            size = 512_000
            req = urllib.request.Request("https://speed.cloudflare.com/__up", data=(b"0" * size), headers={"User-Agent": APP_NAME, "Content-Type":"application/octet-stream"}, method="POST")
            t0 = time.perf_counter()
            urllib.request.urlopen(req, timeout=8).read(2000)
            elapsed = max(0.001, time.perf_counter() - t0)
            up_mbps = round((size * 8 / 1_000_000) / elapsed, 2)
            speed_note = "Live server probe for online classes; not a full ISP capacity test."
        except Exception as e:
            if speed_note.startswith("Speed probe"):
                speed_note = "Upload probe failed: " + str(e)[:120]
    health = {
        "ok": True,
        "checked_at": now_iso(),
        "app_name": APP_NAME,
        "isp": isp,
        "isp_name": isp.get("isp") or isp.get("org") or isp.get("as") or "",
        "public_ip": isp.get("public_ip") or "",
        "latency": latency,
        "ping": ping,
        "latency_ms": ping.get("avg_ms") or next((x.get("tcp_ms") for x in latency if x.get("tcp_ms") is not None), None),
        "avg_latency_ms": ping.get("avg_ms") or next((x.get("tcp_ms") for x in latency if x.get("tcp_ms") is not None), None),
        "jitter_ms": ping.get("jitter_ms") or 0,
        "packet_loss_percent": ping.get("loss_percent") if ping.get("loss_percent") is not None else (0 if any(x.get("tcp_ms") is not None for x in latency) else None),
        "loss_percent": ping.get("loss_percent") if ping.get("loss_percent") is not None else (0 if any(x.get("tcp_ms") is not None for x in latency) else None),
        "probe_download_mbps": down_mbps,
        "probe_upload_mbps": up_mbps,
        "speed_note": speed_note,
        "source": "server_probe"
    }
    with INTERNET_HEALTH_LOCK:
        INTERNET_HEALTH_CACHE = health
    return health

def fetch_json_url(url: str, timeout: int = 2) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "SagarSystemMonitor/6.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(200000).decode("utf-8", errors="replace")
    return json.loads(raw)


def _server_public_internet_lookup(timeout: int = 2) -> Dict[str, Any]:
    errors: List[str] = []
    candidates = [
        ("ipinfo", "https://ipinfo.io/json"),
        ("ip-api", "http://ip-api.com/json/?fields=status,query,isp,org,as,country,city"),
        ("ipify", "https://api.ipify.org?format=json"),
    ]
    for source, url in candidates:
        try:
            d = fetch_json_url(url, timeout=timeout)
            if source == "ipinfo":
                obj = {"public_ip": clean_str(d.get("ip")), "isp": clean_str(d.get("org")), "org": clean_str(d.get("org")), "as": clean_str(d.get("org")), "country": clean_str(d.get("country")), "city": clean_str(d.get("city")), "checked_at": now_iso(), "source": source, "ok": True}
            elif source == "ip-api":
                obj = {"public_ip": clean_str(d.get("query")), "isp": clean_str(d.get("isp") or d.get("org") or d.get("as")), "org": clean_str(d.get("org")), "as": clean_str(d.get("as")), "country": clean_str(d.get("country")), "city": clean_str(d.get("city")), "checked_at": now_iso(), "source": source, "ok": True}
            else:
                obj = {"public_ip": clean_str(d.get("ip")), "isp": "", "org": "", "as": "", "country": "", "city": "", "checked_at": now_iso(), "source": source, "ok": True}
            if obj.get("public_ip") or obj.get("isp"):
                return obj
        except Exception as e:
            errors.append(f"{source}: {e}")
    return {"public_ip":"", "isp":"", "org":"", "as":"", "country":"", "city":"", "checked_at":now_iso(), "source":"unavailable", "ok":False, "errors":errors[-3:]}


def _refresh_server_isp_background() -> None:
    global SERVER_ISP_MEMORY, SERVER_ISP_REFRESHING
    try:
        obj = _server_public_internet_lookup(timeout=2)
        with SERVER_ISP_LOCK:
            SERVER_ISP_MEMORY = obj
        try:
            (DATA_DIR / "server_isp_cache.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    finally:
        with SERVER_ISP_LOCK:
            SERVER_ISP_REFRESHING = False




def server_cloudflare_speed_test(download_bytes: int = 5_000_000, upload_bytes: int = 1_000_000) -> Dict[str, Any]:
    """Small manual server-side speed check. It uses real traffic, so it is not run automatically."""
    result: Dict[str, Any] = {"ok": False, "checked_at": now_iso(), "source": "cloudflare_speed_endpoint", "download_mbps": 0.0, "upload_mbps": 0.0, "note": "Manual test; not auto-run because speed tests consume bandwidth."}
    try:
        size = max(100_000, min(int(download_bytes), 50_000_000))
        url = f"https://speed.cloudflare.com/__down?bytes={size}"
        t0 = time.perf_counter()
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"SagarSystemMonitor/6.0"}), timeout=20) as r:
            data = r.read(size + 1000)
        elapsed = max(0.001, time.perf_counter() - t0)
        result["download_mbps"] = round((len(data) * 8 / 1_000_000) / elapsed, 2)
    except Exception as e:
        result["download_error"] = str(e)
    try:
        size = max(10_000, min(int(upload_bytes), 10_000_000))
        data = b"0" * size
        req = urllib.request.Request("https://speed.cloudflare.com/__up", data=data, headers={"User-Agent":"SagarSystemMonitor/6.0", "Content-Type":"application/octet-stream"}, method="POST")
        t0 = time.perf_counter()
        urllib.request.urlopen(req, timeout=20).read(2000)
        elapsed = max(0.001, time.perf_counter() - t0)
        result["upload_mbps"] = round((size * 8 / 1_000_000) / elapsed, 2)
    except Exception as e:
        result["upload_error"] = str(e)
    result["ok"] = bool(result.get("download_mbps") or result.get("upload_mbps"))
    return result


def server_public_internet_info(force: bool = False) -> Dict[str, Any]:
    """Non-blocking server-side ISP fallback for the dashboard home screen."""
    global SERVER_ISP_MEMORY, SERVER_ISP_REFRESHING
    cache_path = DATA_DIR / "server_isp_cache.json"
    if SERVER_ISP_MEMORY.get("source") == "not_checked" and cache_path.exists():
        try:
            with SERVER_ISP_LOCK:
                SERVER_ISP_MEMORY = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    if force:
        obj = _server_public_internet_lookup(timeout=2)
        with SERVER_ISP_LOCK:
            SERVER_ISP_MEMORY = obj
        try:
            cache_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return obj
    # If stale/missing, refresh in background and immediately return old value so /api/overview never hangs.
    stale = True
    try:
        checked = dt.datetime.fromisoformat(str(SERVER_ISP_MEMORY.get("checked_at", "")).replace("Z", "+00:00"))
        stale = (dt.datetime.now(dt.timezone.utc) - checked).total_seconds() > 1800
    except Exception:
        stale = True
    with SERVER_ISP_LOCK:
        current = dict(SERVER_ISP_MEMORY)
        if stale and not SERVER_ISP_REFRESHING:
            SERVER_ISP_REFRESHING = True
            threading.Thread(target=_refresh_server_isp_background, daemon=True).start()
    return current


def clean_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def valid_machine_id_part(v: Any) -> str:
    s = clean_str(v)
    if not s:
        return ""
    low = re.sub(r"\s+", " ", s.lower()).strip()
    compact = re.sub(r"[^a-z0-9]", "", low)
    if low in BAD_IDS or compact in BAD_IDS:
        return ""
    if re.fullmatch(r"0+", compact) or re.fullmatch(r"f+", compact):
        return ""
    for pat in BAD_ID_PATTERNS:
        try:
            if re.search(pat, low) or re.search(pat, compact):
                return ""
        except Exception:
            pass
    if len(s) < 3:
        return ""
    return s


def first_physical_mac(payload: Dict[str, Any]) -> str:
    """Pick a stable network MAC for fallback identity.
    Many Windows PCs report fake board serials like BSS-0123456789.
    This fallback stops one PC replacing another in the dashboard.
    """
    adapters = get_nested(payload, ["network.adapters", "adapters"], [])
    best = ""
    for a in listify(adapters):
        if not isinstance(a, dict):
            continue
        mac = clean_str(a.get("mac") or a.get("mac_address") or a.get("MACAddress"))
        if not mac:
            continue
        mac_norm = re.sub(r"[^A-Fa-f0-9]", "", mac).upper()
        if len(mac_norm) < 12 or mac_norm in {"000000000000", "FFFFFFFFFFFF"}:
            continue
        desc = (clean_str(a.get("name")) + " " + clean_str(a.get("description"))).lower()
        if a.get("is_virtual") or a.get("is_vpn") or re.search(r"virtual|hyper-v|vmware|virtualbox|docker|wsl|loopback|tunnel|tap|tun|vpn", desc):
            if not best:
                best = mac_norm
            continue
        return mac_norm
    return best


def _safe_id(prefix: str, value: str) -> str:
    return prefix + ":" + re.sub(r"[^A-Za-z0-9_.:-]", "_", value)[:160]


def machine_fingerprint_value(payload: Dict[str, Any]) -> Tuple[str, str, str]:
    """Return stable, collision-safe machine identity.
    In real labs many budget/OEM Windows PCs report the same fake motherboard serial.
    To stop one PC replacing another, the dashboard identity is an asset fingerprint made from
    hostname + physical MAC + valid hardware IDs.  Hardware IDs are still stored/displayed.
    """
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    hostname = valid_machine_id_part(payload.get("hostname") or identity.get("hostname") or payload.get("computer_name")) or "UNKNOWN-HOST"
    mac = first_physical_mac(payload)
    board = valid_machine_id_part(identity.get("motherboard_serial") or payload.get("motherboard_serial") or payload.get("baseboard_serial"))
    uuid = valid_machine_id_part(identity.get("system_uuid") or payload.get("system_uuid") or payload.get("uuid"))
    bios = valid_machine_id_part(identity.get("bios_serial") or payload.get("bios_serial"))
    # Best identity for your multi-LAN setup: hostname + physical MAC + any valid serial/UUID.
    # This keeps cloned/fake serial machines separate and stable.
    if hostname != "UNKNOWN-HOST" and mac:
        raw = "|".join([hostname.upper(), mac.upper(), uuid.upper(), bios.upper(), board.upper()])
        short = hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16].upper()
        shown = f"{hostname} / {mac}"
        return f"ASSET:{short}", "asset_fingerprint", shown
    if uuid and hostname != "UNKNOWN-HOST":
        raw = "|".join([hostname.upper(), uuid.upper(), bios.upper(), board.upper()])
        short = hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16].upper()
        return f"ASSET:{short}", "hostname_uuid_fingerprint", f"{hostname} / {uuid}"
    if bios and hostname != "UNKNOWN-HOST":
        raw = "|".join([hostname.upper(), bios.upper(), board.upper()])
        short = hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16].upper()
        return f"ASSET:{short}", "hostname_bios_fingerprint", f"{hostname} / {bios}"
    if board:
        return _safe_id("MOTHERBOARD_SERIAL", board), "motherboard_serial", board
    if uuid:
        return _safe_id("SYSTEM_UUID", uuid), "system_uuid", uuid
    if bios:
        return _safe_id("BIOS_SERIAL", bios), "bios_serial", bios
    if mac:
        return _safe_id("MAC", mac), "mac_fallback", mac
    return _safe_id("HOSTNAME", hostname), "hostname_fallback", hostname


def make_machine_identity(payload: Dict[str, Any]) -> Tuple[str, str, str]:
    return machine_fingerprint_value(payload)

def get_nested(d: Dict[str, Any], paths: List[str], default: Any=None) -> Any:
    for p in paths:
        cur: Any = d
        ok = True
        for part in p.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return default


def to_float(v: Any, default: Optional[float]=None) -> Optional[float]:
    try:
        if v is None or v == "":
            return default
        return float(str(v).replace("%", "").strip())
    except Exception:
        return default


def safe_json_loads(s: str, fallback: Any) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return fallback


def parse_usb_repr_string(text: str) -> Any:
    """Best-effort parser for raw Windows/Powershell/Python repr USB strings.
    Handles values like "[{'name': 'Razer', 'device_id': 'USB\\VID_1532...'}]" even when Device ID contains braces/backslashes.
    """
    if not isinstance(text, str):
        return text
    t = text.strip()
    if not ("name" in t.lower() or "display_name" in t.lower() or "device_id" in t.lower() or "vid" in t.lower()):
        return text
    try:
        obj = ast.literal_eval(t)
        if isinstance(obj, (list, dict)):
            return obj
    except Exception:
        pass
    parts = re.split(r"\}\s*,\s*\{", t.strip().strip("[]"))
    out = []
    for part in parts[:120]:
        b = part.strip()
        if not b.startswith("{"):
            b = "{" + b
        if not b.endswith("}"):
            b = b + "}"
        obj = {}
        for key in ["name","display_name","friendly_name","class","type","vid","pid","device_id","manufacturer","status","source","connection"]:
            m = re.search(r"['\"]" + re.escape(key) + r"['\"]\s*:\s*(['\"])(.*?)\1", b, re.I | re.S)
            if m:
                obj[key] = m.group(2).replace('\\\\', '\\').strip()[:1000]
                continue
            m = re.search(r"\b" + re.escape(key) + r"\b\s*[:=]\s*([^,}]+)", b, re.I | re.S)
            if m:
                obj[key] = m.group(1).strip().strip("'\"")[:1000]
        if obj.get("name") or obj.get("display_name") or obj.get("device_id"):
            out.append(obj)
    return out if out else text

def loose_json_or_python(value: Any) -> Any:
    """Parse JSON/Python-looking strings that sometimes arrive from PowerShell as text.
    Example: "[{'name':'Razer Kraken', 'vid':'1532'}]" should become a list, not one raw string.
    """
    if not isinstance(value, str):
        return value
    t = value.strip()
    if not t:
        return value
    if (t.startswith("[") and t.endswith("]")) or (t.startswith("{") and t.endswith("}")):
        try:
            return json.loads(t)
        except Exception:
            pass
        try:
            return ast.literal_eval(t)
        except Exception:
            parsed = parse_usb_repr_string(value)
            return parsed
    parsed = parse_usb_repr_string(value)
    return parsed


def listify(value: Any) -> List[Any]:
    """Return a real list even when PowerShell/JSON sends one object, dictionary, or list-as-string.
    This fixes single USB device / single app / single adapter cases and strings like [{'name':...}].
    """
    value = loose_json_or_python(value)
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [x for x in value if x not in (None, "")]
    if isinstance(value, tuple):
        return [x for x in value if x not in (None, "")]
    if isinstance(value, dict):
        # Direct object, e.g. {name,class,type,device_id}.
        direct_keys = {"name", "class", "type", "device_id", "vid", "pid", "manufacturer", "status", "mount", "total_gb", "version", "publisher"}
        if any(k in value for k in direct_keys):
            return [value]
        # Dictionary keyed by instance id, e.g. {"USB\VID...": {...}}.
        vals = list(value.values())
        return [x for x in vals if x not in (None, "")]
    return [value]


def is_noisy_windows_usb_name(name: str, cls: str = "", did: str = "") -> bool:
    text = f"{name} {cls} {did}".lower()
    keep = r"keyboard|mouse|headset|headphone|speaker|microphone|audio|camera|webcam|printer|storage|flash|disk|bluetooth|ethernet|wi-fi|wifi|802\.11|wireless|razer|logitech|realtek|tp-link|hp|canon|epson"
    if re.search(keep, text):
        return False
    noisy = [
        "hid button", "hid-compliant system controller", "hid-compliant consumer control",
        "hid-compliant vendor-defined", "hid-compliant device", "hid sensor", "i2c hid",
        "gpio buttons", "system control", "usb composite device", "usb input device",
        "generic usb hub", "usb root hub", "root hub", "composite parent",
        "tap-windows adapter", "wan miniport", "virtual adapter", "loopback", "microsoft wi-fi direct virtual"
    ]
    if any(x in text for x in noisy):
        return True
    if re.search(r"^(acpi|root|swc|swd|display)\\", did.lower()):
        return True
    if "hidclass" in cls.lower() and not re.search(keep, text):
        return True
    return False

def normalize_usb_device(item: Any) -> Dict[str, Any]:
    """Convert raw Windows/Ubuntu USB item into a safe human-readable object."""
    if isinstance(item, dict):
        name = clean_str(item.get("display_name") or item.get("friendly_name") or item.get("name") or item.get("device_name") or item.get("description"))
        cls = clean_str(item.get("class") or item.get("pnp_class") or item.get("category"))
        dtype = clean_str(item.get("type") or cls or "Peripheral")
        did = clean_str(item.get("device_id") or item.get("instance_id") or item.get("id"))
        if is_noisy_windows_usb_name(name, cls, did):
            return {}
        if not name and did:
            name = re.split(r"[\\/]", did)[-1][:80]
        if not dtype or dtype.lower() in ("hidclass", "usb"):
            low = f"{name} {cls}".lower()
            if "keyboard" in low: dtype="Keyboard"
            elif "mouse" in low or "pointing" in low: dtype="Mouse"
            elif re.search(r"audio|headset|headphone|speaker|microphone", low): dtype="Audio"
            elif re.search(r"camera|webcam|image", low): dtype="Camera"
            elif re.search(r"storage|disk|flash|mass", low): dtype="Storage"
            elif "bluetooth" in low: dtype="Bluetooth"
            elif re.search(r"network|ethernet|wi-fi|wifi|802\.11|wireless", low): dtype="USB Network"
            else: dtype="Peripheral"
        return {"name": name or "Unknown USB / Peripheral", "display_name": name or "Unknown USB / Peripheral", "class": cls, "type": dtype or "Peripheral", "vid": clean_str(item.get("vid") or item.get("vendor_id")), "pid": clean_str(item.get("pid") or item.get("product_id")), "manufacturer": clean_str(item.get("manufacturer")), "status": clean_str(item.get("status")), "source": clean_str(item.get("source")), "device_id": did}
    parsed_item = parse_usb_repr_string(item) if isinstance(item, str) else item
    if isinstance(parsed_item, list) and parsed_item:
        # normalize_usb_list will flatten this; this branch protects direct calls.
        return normalize_usb_device(parsed_item[0])
    if isinstance(parsed_item, dict):
        return normalize_usb_device(parsed_item)
    s = clean_str(item)
    if not s:
        return {"name":"Unknown USB / Peripheral", "display_name":"Unknown USB / Peripheral", "class":"", "type":"Peripheral", "device_id":""}
    parts = [p.strip() for p in s.split("|")]
    if len(parts) >= 2:
        dtype = parts[0] or "Peripheral"
        name = parts[1] or "Unknown USB / Peripheral"
        vidpid = parts[2] if len(parts) > 2 else ""
        did = parts[3] if len(parts) > 3 else ""
        vid = ""; pid = ""
        if ":" in vidpid:
            vid, pid = [x.strip() for x in vidpid.split(":", 1)]
        return {"name":name, "display_name":name, "class":dtype, "type":dtype, "vid":vid, "pid":pid, "device_id":did, "source":"parsed"}
    short = s[:120] + ("..." if len(s) > 120 else "")
    return {"name": short, "display_name": short, "class":"", "type":"Peripheral", "device_id": s if len(s) < 250 else s[:250]+"...", "source":"raw"}


def normalize_usb_list(items: Any) -> List[Dict[str, Any]]:
    """Flatten and clean USB/peripheral payloads from Windows/Linux.
    Older Windows clients sometimes sent a whole list as one raw string, for example
    "[{\'name\': \'Razer...\'}]". This function recursively parses that so the UI
    receives clean device objects, not raw Python/PowerShell text.
    """
    out: List[Dict[str, Any]] = []
    seen = set()

    def walk(value: Any, depth: int = 0) -> None:
        if depth > 4:
            return
        value = loose_json_or_python(value)
        if value is None or value == "":
            return
        if isinstance(value, list) or isinstance(value, tuple):
            for v in value:
                walk(v, depth + 1)
            return
        if isinstance(value, dict):
            direct_keys = {"name", "display_name", "friendly_name", "class", "type", "device_id", "vid", "pid", "manufacturer", "status", "source"}
            if not any(k in value for k in direct_keys):
                for v in value.values():
                    walk(v, depth + 1)
                return
        obj = normalize_usb_device(value)
        if not obj or is_noisy_windows_usb_name(obj.get("name",""), obj.get("class",""), obj.get("device_id","")):
            return
        # Avoid showing VPN/TAP adapters under USB/peripherals. Network page already handles them.
        text = f"{obj.get('name','')} {obj.get('device_id','')} {obj.get('class','')}".lower()
        if re.search(r"tap-windows|wan miniport|wireguard|openvpn|vpn|virtual adapter|loopback", text):
            return
        key = (obj.get("type",""), obj.get("name",""), obj.get("vid",""), obj.get("pid",""), obj.get("device_id","")[:80])
        if key in seen:
            return
        seen.add(key)
        out.append(obj)

    walk(items)
    return out


def normalize_payload_inplace(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize client payload before saving so API + UI always receive arrays."""
    if not isinstance(payload, dict):
        return payload
    # USB devices: always store a clean list of objects, never a raw PowerShell string/object.
    usb = payload.get("usb")
    if isinstance(usb, dict):
        usb["devices"] = normalize_usb_list(loose_json_or_python(usb.get("devices")))
        usb["count"] = len(usb["devices"])
    elif usb:
        clean_usb = normalize_usb_list(usb)
        payload["usb"] = {"devices": clean_usb, "count": len(clean_usb)}
    else:
        payload.setdefault("usb", {"devices": [], "count": 0})
    # Installed software
    sw = payload.get("software")
    if isinstance(sw, dict):
        sw["installed"] = listify(sw.get("installed"))
    elif sw:
        payload["software"] = {"installed": listify(sw)}
    else:
        payload.setdefault("software", {"installed": []})
    # Hardware arrays
    hw = payload.get("hardware")
    if isinstance(hw, dict):
        hw["gpus"] = listify(hw.get("gpus"))
    st = payload.get("storage")
    if isinstance(st, dict):
        st["disks"] = listify(st.get("disks"))
    net = payload.get("network")
    if isinstance(net, dict):
        net["adapters"] = listify(net.get("adapters"))
    # Changes
    if "changes" in payload:
        payload["changes"] = listify(payload.get("changes"))
    else:
        payload["changes"] = []
    return payload


def summarize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    mid, id_source, id_value = make_machine_identity(payload)
    hostname = clean_str(get_nested(payload, ["identity.hostname", "hostname", "computer_name"], ""))
    os_name = clean_str(get_nested(payload, ["os.name", "os", "os_name", "platform"], ""))

    adapters = listify(get_nested(payload, ["network.adapters", "adapters", "interfaces"], []))
    primary_ip = clean_str(get_nested(payload, ["network.primary_ip", "primary_ip", "ip"], ""))
    all_ips: List[str] = []
    if isinstance(adapters, list):
        for a in adapters:
            if isinstance(a, dict):
                ips = a.get("ips") or a.get("ip_addresses") or []
                if isinstance(ips, str):
                    ips = [ips]
                for ip in ips:
                    if ip and str(ip) not in all_ips:
                        all_ips.append(str(ip))
    if primary_ip and primary_ip not in all_ips:
        all_ips.insert(0, primary_ip)
    if not primary_ip and all_ips:
        primary_ip = all_ips[0]

    disks = listify(get_nested(payload, ["storage.disks", "disks"], []))
    disk_max = 0.0
    if isinstance(disks, list):
        for d in disks:
            if isinstance(d, dict):
                disk_max = max(disk_max, to_float(d.get("used_percent") or d.get("usage_percent"), 0) or 0)

    gpus = listify(get_nested(payload, ["hardware.gpus", "gpus", "gpu"], []))
    gpu_names: List[str] = []
    gpu_max_usage = None
    gpu_max_temp = None
    gpu_total_mem = 0.0
    gpu_memory_values = []
    if isinstance(gpus, dict):
        gpus = [gpus]
    if isinstance(gpus, list):
        for g in gpus:
            if isinstance(g, dict):
                name = clean_str(g.get("name") or g.get("gpu_name"))
                if name:
                    gpu_names.append(name)
                u = to_float(g.get("usage_percent") or g.get("utilization_gpu") or g.get("load_percent"))
                t = to_float(g.get("temperature_c") or g.get("temp_c"))
                m = to_float(g.get("memory_total_mb") or g.get("adapter_ram_mb"), 0) or 0
                dedicated_m = to_float(g.get("dedicated_memory_mb"), 0) or 0
                shared_m = to_float(g.get("shared_memory_mb"), 0) or 0
                effective_m = max(m, dedicated_m, shared_m)
                if effective_m:
                    gpu_memory_values.append(effective_m)
                if u is not None:
                    gpu_max_usage = u if gpu_max_usage is None else max(gpu_max_usage, u)
                if t is not None:
                    gpu_max_temp = t if gpu_max_temp is None else max(gpu_max_temp, t)
                gpu_total_mem += effective_m

    usb = listify(get_nested(payload, ["usb.devices", "usb", "peripherals"], []))
    software = listify(get_nested(payload, ["software.installed", "software", "apps"], []))
    vpn = get_nested(payload, ["network.vpn", "vpn"], {}) or {}
    vpn_active = False
    if isinstance(vpn, dict):
        vpn_active = bool(vpn.get("active") or vpn.get("is_active"))
    elif isinstance(vpn, bool):
        vpn_active = vpn

    public_internet = get_nested(payload, ["network.public_internet", "public_internet", "isp"], {}) or {}
    if not isinstance(public_internet, dict):
        public_internet = {}
    internet_speed = get_nested(payload, ["network.internet_speed", "internet_speed"], {}) or {}
    if not isinstance(internet_speed, dict):
        internet_speed = {}
    isp_name = clean_str(public_internet.get("isp") or public_internet.get("org") or public_internet.get("as") or "")
    public_ip = clean_str(public_internet.get("public_ip") or public_internet.get("query") or public_internet.get("ip") or "")
    changes = listify(payload.get("changes"))

    memory = get_nested(payload, ["hardware.memory", "memory", "ram"], {}) or {}
    if not isinstance(memory, dict):
        memory = {}
    traffic = get_nested(payload, ["network.traffic", "traffic"], {}) or {}
    if not isinstance(traffic, dict):
        traffic = {}

    return {
        "machine_id": mid,
        "id_source": id_source,
        "id_value": id_value,
        "hostname": hostname,
        "os": os_name,
        "primary_ip": primary_ip,
        "all_ips": all_ips,
        "cpu_percent": to_float(get_nested(payload, ["hardware.cpu.usage_percent", "cpu_percent", "cpu.usage_percent"]), 0),
        "cpu_temp_c": to_float(get_nested(payload, ["hardware.cpu.temperature_c", "cpu_temp_c", "cpu.temperature_c"])),
        "ram_percent": to_float(get_nested(payload, ["hardware.memory.used_percent", "ram_percent", "memory.used_percent"]), 0),
        "ram_total_gb": to_float(memory.get("total_gb") or get_nested(payload, ["hardware.memory.total_gb", "memory.total_gb", "ram_total_gb"]), 0),
        "ram_used_gb": to_float(memory.get("used_gb") or get_nested(payload, ["hardware.memory.used_gb", "memory.used_gb", "ram_used_gb"]), 0),
        "ram_free_gb": to_float(memory.get("free_gb") or get_nested(payload, ["hardware.memory.free_gb", "memory.free_gb", "ram_free_gb"]), 0),
        "disk_max_percent": round(disk_max, 2),
        "wan_download_mbps": to_float(traffic.get("current_download_mbps") or get_nested(payload, ["network.current_download_mbps", "current_download_mbps", "download_mbps", "wan_download_mbps"]), 0),
        "wan_upload_mbps": to_float(traffic.get("current_upload_mbps") or get_nested(payload, ["network.current_upload_mbps", "current_upload_mbps", "upload_mbps", "wan_upload_mbps"]), 0),
        "today_download_gb": to_float(traffic.get("today_download_gb") or get_nested(payload, ["network.today_download_gb", "today_download_gb"]), 0),
        "today_upload_gb": to_float(traffic.get("today_upload_gb") or get_nested(payload, ["network.today_upload_gb", "today_upload_gb"]), 0),
        "traffic_date": clean_str(traffic.get("date") or get_nested(payload, ["network.traffic_date", "traffic_date"], "")),
        "gpu_names": gpu_names,
        "gpu_count": len(gpu_names),
        "gpu_max_usage": gpu_max_usage,
        "gpu_max_temp_c": gpu_max_temp,
        "gpu_total_memory_mb": round((max(gpu_memory_values) if gpu_memory_values else gpu_total_mem), 2),
        "vpn_active": vpn_active,
        "isp_name": isp_name,
        "public_ip": public_ip,
        "isp_download_mbps": to_float(internet_speed.get("download_mbps"), to_float(traffic.get("current_download_mbps") or get_nested(payload, ["network.current_download_mbps", "current_download_mbps", "download_mbps", "wan_download_mbps"]), 0)),
        "isp_upload_mbps": to_float(internet_speed.get("upload_mbps"), to_float(traffic.get("current_upload_mbps") or get_nested(payload, ["network.current_upload_mbps", "current_upload_mbps", "upload_mbps", "wan_upload_mbps"]), 0)),
        "isp_speed_source": clean_str(internet_speed.get("source") or "live_adapter_usage"),
        "change_count": len(changes),
        "adapter_count": len(adapters) if isinstance(adapters, list) else 0,
        "software_count": len(software) if isinstance(software, list) else 0,
        "usb_count": len(usb) if isinstance(usb, list) else 0,
        "payload": payload,
    }


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect("file:" + str(DB_PATH).replace("\\", "/") + "?mode=rwc", uri=True, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with DB_LOCK, db_connect() as con:
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS latest (
            machine_id TEXT PRIMARY KEY,
            hostname TEXT,
            id_source TEXT,
            id_value TEXT,
            updated_at TEXT,
            summary_json TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            hostname TEXT,
            payload_json TEXT NOT NULL
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_heartbeats_machine_time ON heartbeats(machine_id, received_at)")
        cur.execute("""CREATE TABLE IF NOT EXISTS notification_rules (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            metric TEXT NOT NULL,
            op TEXT NOT NULL,
            threshold REAL NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            severity TEXT NOT NULL DEFAULT 'warning',
            cooldown_minutes INTEGER NOT NULL DEFAULT 15
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            severity TEXT NOT NULL,
            machine_id TEXT,
            hostname TEXT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            rule_id TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS change_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            hostname TEXT,
            change_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            detail_json TEXT NOT NULL
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_change_events_time ON change_events(created_at)")
        cur.execute("""CREATE TABLE IF NOT EXISTS notification_state (
            rule_id TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            last_sent_ts REAL NOT NULL,
            PRIMARY KEY(rule_id, machine_id)
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS client_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            target_machine_id TEXT,
            target_hostname TEXT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'pending',
            delivered_at TEXT
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_client_messages_target ON client_messages(target_machine_id,status)")
        cur.execute("""CREATE TABLE IF NOT EXISTS client_message_receipts (
            message_id INTEGER NOT NULL,
            machine_id TEXT NOT NULL,
            hostname TEXT,
            delivered_at TEXT NOT NULL,
            PRIMARY KEY(message_id, machine_id)
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_client_message_receipts_msg ON client_message_receipts(message_id)")
        for r in DEFAULT_RULES:
            cur.execute("SELECT id FROM notification_rules WHERE id=?", (r["id"],))
            if not cur.fetchone():
                cur.execute("""INSERT INTO notification_rules(id,name,metric,op,threshold,enabled,severity,cooldown_minutes)
                    VALUES(?,?,?,?,?,?,?,?)""", (r["id"], r["name"], r["metric"], r["op"], r["threshold"], int(r["enabled"]), r["severity"], r["cooldown_minutes"]))
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('google_chat_webhook','')")
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('offline_timeout_minutes','0.20')")
        cur.execute("UPDATE settings SET value='0.20' WHERE key='offline_timeout_minutes' AND value IN ('','1')")
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('company_name',?)", (APP_NAME,))
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('admin_password_hash',?)", (hash_password(DEFAULT_ADMIN_PASSWORD),))
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('auto_speed_probe','1')")
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        # Admin user for role-based login/download permission. Existing password-only login still works.
        cur.execute("SELECT username FROM users WHERE username='admin'")
        if not cur.fetchone():
            cur.execute("INSERT INTO users(username,password_hash,role,enabled,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                ('admin', hash_password(DEFAULT_ADMIN_PASSWORD), 'admin', 1, now_iso(), now_iso()))
        con.commit()



def apply_v10_notification_policy(con):
    """V10 locked notification policy: disk >=90, CPU+RAM both >=95, real temps >=90 only."""
    try:
        con.execute("""UPDATE notification_rules
                       SET name=?, metric=?, op=?, threshold=?, enabled=?, severity=?, cooldown_minutes=?
                       WHERE id=?""",
                    ("CPU usage high (optional single metric disabled)", "cpu_percent", ">=", 95, 0, "warning", 15, "cpu_high"))
        con.execute("""UPDATE notification_rules
                       SET name=?, metric=?, op=?, threshold=?, enabled=?, severity=?, cooldown_minutes=?
                       WHERE id=?""",
                    ("RAM usage high (optional single metric disabled)", "ram_percent", ">=", 95, 0, "warning", 15, "ram_high"))
        con.execute("""INSERT OR REPLACE INTO notification_rules(id,name,metric,op,threshold,enabled,severity,cooldown_minutes)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    ("disk_high", "SSD / disk usage high", "disk_max_percent", ">=", 90, 1, "critical", 10))
        con.execute("""INSERT OR REPLACE INTO notification_rules(id,name,metric,op,threshold,enabled,severity,cooldown_minutes)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    ("cpu_ram_critical", "CPU + RAM both critical", "cpu_ram_combined_percent", "all>=", 95, 1, "critical", 10))
        con.execute("""INSERT OR REPLACE INTO notification_rules(id,name,metric,op,threshold,enabled,severity,cooldown_minutes)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    ("cpu_temp_high", "CPU temperature high", "cpu_temp_c", ">=", 90, 1, "critical", 20))
        con.execute("""INSERT OR REPLACE INTO notification_rules(id,name,metric,op,threshold,enabled,severity,cooldown_minutes)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    ("gpu_temp_high", "GPU temperature high", "gpu_max_temp_c", ">=", 90, 1, "critical", 20))
        try:
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", ("v10_notification_policy_active", "20260701_safe_backend"))
        except Exception:
            pass
    except Exception as e:
        try:
            log("V10 notification policy apply failed: " + str(e))
        except Exception:
            print("V10 notification policy apply failed", e)

def get_settings() -> Dict[str, str]:
    with DB_LOCK, db_connect() as con:
        rows = con.execute("SELECT key,value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_settings(values: Dict[str, Any]) -> None:
    with DB_LOCK, db_connect() as con:
        for k, v in values.items():
            if k in {"google_chat_webhook", "offline_timeout_minutes", "company_name", "company_website", "company_logo_url", "company_logo_data_url", "login_photo_url", "login_photo_data_url", "login_tagline", "company_short_name", "brand_primary", "brand_accent", "auto_speed_probe", "admin_password_hash", "deploy_commands_json", "retention_keep_days", "history_keep_days", "data_retention_days", "public_domain"}:
                con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, str(v)))
        con.commit()


def list_users_public() -> List[Dict[str, Any]]:
    with DB_LOCK, db_connect() as con:
        rows = con.execute("SELECT username,role,enabled,created_at,updated_at FROM users ORDER BY username").fetchall()
    return [dict(r) for r in rows]


def get_user_row(username: str) -> Optional[sqlite3.Row]:
    with DB_LOCK, db_connect() as con:
        return con.execute("SELECT * FROM users WHERE lower(username)=lower(?) AND enabled=1", (username or "",)).fetchone()


def upsert_user(username: str, password: str, role: str, enabled: bool = True) -> Dict[str, Any]:
    username = clean_str(username).strip()
    role = (clean_str(role) or "viewer").lower()
    if role not in {"super_admin", "admin", "inventory_editor", "viewer"}:
        role = "viewer"
    if not username:
        return {"ok": False, "error": "Username required"}
    if username.lower() == "admin" and role != "admin":
        return {"ok": False, "error": "Built-in admin must remain admin"}
    if password and len(password) < 8:
        return {"ok": False, "error": "Password must be at least 8 characters"}
    with DB_LOCK, db_connect() as con:
        row = con.execute("SELECT username FROM users WHERE lower(username)=lower(?)", (username,)).fetchone()
        if row:
            if password:
                con.execute("UPDATE users SET password_hash=?, role=?, enabled=?, updated_at=? WHERE lower(username)=lower(?)", (hash_password(password), role, 1 if enabled else 0, now_iso(), username))
            else:
                con.execute("UPDATE users SET role=?, enabled=?, updated_at=? WHERE lower(username)=lower(?)", (role, 1 if enabled else 0, now_iso(), username))
        else:
            if not password:
                return {"ok": False, "error": "Password required for new user"}
            con.execute("INSERT INTO users(username,password_hash,role,enabled,created_at,updated_at) VALUES(?,?,?,?,?,?)", (username, hash_password(password), role, 1 if enabled else 0, now_iso(), now_iso()))
        con.commit()
    return {"ok": True, "users": list_users_public()}


def delete_user(username: str) -> Dict[str, Any]:
    username = clean_str(username).strip()
    if username.lower() == "admin":
        return {"ok": False, "error": "admin user cannot be deleted"}
    with DB_LOCK, db_connect() as con:
        con.execute("DELETE FROM users WHERE lower(username)=lower(?)", (username,))
        con.commit()
    return {"ok": True, "users": list_users_public()}


def public_settings() -> Dict[str, Any]:
    s = get_settings()
    return {k:v for k,v in s.items() if k != "admin_password_hash"}


def rules_list() -> List[Dict[str, Any]]:
    with DB_LOCK, db_connect() as con:
        rows = con.execute("SELECT * FROM notification_rules ORDER BY name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["enabled"] = bool(d["enabled"])
        out.append(d)
    return out


def eval_rule(value: Optional[float], op: str, threshold: float) -> bool:
    if op == "event":
        return True
    if value is None:
        return False
    if op == ">=": return value >= threshold
    if op == ">": return value > threshold
    if op == "<=": return value <= threshold
    if op == "<": return value < threshold
    if op == "==": return value == threshold
    return False


def can_send_alert(con: sqlite3.Connection, rule_id: str, machine_id: str, cooldown: int) -> bool:
    row = con.execute("SELECT last_sent_ts FROM notification_state WHERE rule_id=? AND machine_id=?", (rule_id, machine_id)).fetchone()
    now = time.time()
    if row and now - float(row["last_sent_ts"]) < cooldown * 60:
        return False
    con.execute("INSERT OR REPLACE INTO notification_state(rule_id,machine_id,last_sent_ts) VALUES(?,?,?)", (rule_id, machine_id, now))
    return True


def send_google_chat(text: str) -> None:
    settings = get_settings()
    url = (settings.get("google_chat_webhook") or "").strip()
    if not url:
        return
    data = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=8).read()
    except Exception as e:
        log(f"Google Chat notification failed: {e}")


def record_notification(con: sqlite3.Connection, severity: str, machine_id: str, hostname: str, title: str, message: str, rule_id: str) -> None:
    con.execute("""INSERT INTO notifications(created_at,severity,machine_id,hostname,title,message,rule_id)
        VALUES(?,?,?,?,?,?,?)""", (now_iso(), severity, machine_id, hostname, title, message, rule_id))
    threading.Thread(target=send_google_chat, args=(f"[{severity.upper()}] {title}\n{message}",), daemon=True).start()


def evaluate_notifications(summary: Dict[str, Any]) -> None:
    with DB_LOCK, db_connect() as con:
        rows = con.execute("SELECT * FROM notification_rules WHERE enabled=1 AND metric!='offline_minutes' AND metric NOT LIKE 'change_%'").fetchall()
        for r in rows:
            value = to_float(summary.get(r["metric"]))
            if eval_rule(value, r["op"], float(r["threshold"])):
                if can_send_alert(con, r["id"], summary["machine_id"], int(r["cooldown_minutes"])):
                    host = summary.get("hostname") or summary["machine_id"]
                    msg = f"{host}: {r['metric']} is {value} {r['op']} {r['threshold']}"
                    record_notification(con, r["severity"], summary["machine_id"], host, r["name"], msg, r["id"])
        con.commit()







# === V10_NOTIFY_BACKEND_SAFE_START ===

def _v10_notify_float(v, default=None):
    try:
        if v is None or v == "":
            return default
        if isinstance(v, str):
            v = v.replace("%", "").replace("C", "").replace("c", "").strip()
            if not v or v.upper() in {"NA", "N/A", "NONE", "NULL", "UNKNOWN"}:
                return default
        return float(v)
    except Exception:
        return default


def _v10_notify_list(v):
    try:
        return listify(v)
    except Exception:
        if isinstance(v, list):
            return v
        return [] if v in (None, "") else [v]


def _v10_disk_detail_for_notification(summary):
    payload = summary.get("payload") if isinstance(summary.get("payload"), dict) else {}
    disks = []
    for keypath in (["storage.disks"], ["disks"], ["storage", "disks"]):
        try:
            val = get_nested(payload, keypath, [])
            if val:
                disks = _v10_notify_list(val)
                break
        except Exception:
            pass
    worst = {"name": "disk", "used_percent": _v10_notify_float(summary.get("disk_max_percent"), 0) or 0}
    parts = []
    for d in disks:
        if not isinstance(d, dict):
            continue
        used = _v10_notify_float(d.get("used_percent") or d.get("usage_percent"))
        if used is None:
            continue
        name = clean_str(d.get("name") or d.get("mount") or d.get("drive") or d.get("caption") or d.get("device") or "Disk")
        total = _v10_notify_float(d.get("total_gb") or d.get("size_gb"))
        free = _v10_notify_float(d.get("free_gb"))
        bit = f"{name} {used:.1f}%"
        if total is not None:
            bit += f" of {total:g} GB"
        if free is not None:
            bit += f", free {free:g} GB"
        parts.append(bit)
        if used >= float(worst.get("used_percent") or 0):
            worst = {"name": name, "used_percent": used, "total_gb": total, "free_gb": free}
    detail = "; ".join(parts[:8])
    return worst, detail


def _v10_gpu_temp_for_notification(summary):
    payload = summary.get("payload") if isinstance(summary.get("payload"), dict) else {}
    temp = _v10_notify_float(summary.get("gpu_max_temp_c"), None)
    name = "GPU"
    gpus = []
    for keypath in (["hardware.gpus"], ["gpus"], ["gpu"], ["hardware", "gpus"]):
        try:
            val = get_nested(payload, keypath, [])
            if val:
                gpus = _v10_notify_list(val)
                break
        except Exception:
            pass
    for g in gpus:
        if not isinstance(g, dict):
            continue
        t = _v10_notify_float(g.get("temperature_c") or g.get("temp_c"), None)
        if t is not None and (temp is None or t >= temp):
            temp = t
            name = clean_str(g.get("name") or g.get("gpu_name") or "GPU")
    return temp, name


def notification_match_context(summary, metric, op, threshold):
    metric = clean_str(metric)
    op = clean_str(op)
    host = summary.get("hostname") or summary.get("machine_id") or "Machine"

    if metric == "cpu_ram_combined_percent":
        cpu = _v10_notify_float(summary.get("cpu_percent"), None)
        ram = _v10_notify_float(summary.get("ram_percent"), None)
        matched = cpu is not None and ram is not None and cpu >= float(threshold) and ram >= float(threshold)
        shown = min(cpu, ram) if cpu is not None and ram is not None else None
        return matched, shown, f"{host}: CPU {cpu if cpu is not None else 'N/A'}% and RAM {ram if ram is not None else 'N/A'}%; alert only when both are >= {threshold:g}%."

    if metric == "disk_max_percent":
        worst, detail = _v10_disk_detail_for_notification(summary)
        value = _v10_notify_float(summary.get("disk_max_percent"), None)
        if value is None or float(worst.get("used_percent") or 0) > value:
            value = float(worst.get("used_percent") or 0)
        matched = eval_rule(value, op, threshold)
        if detail:
            return matched, value, f"{host}: SSD/HDD/NVMe/disk max usage is {value:.1f}% ({detail}); threshold {op} {threshold:g}%."
        return matched, value, f"{host}: SSD/HDD/NVMe/disk max usage is {value if value is not None else 'N/A'}%; threshold {op} {threshold:g}%."

    if metric == "cpu_temp_c":
        value = _v10_notify_float(summary.get("cpu_temp_c"), None)
        if value is None:
            return False, None, f"{host}: CPU temperature is N/A; no fake temperature alert."
        return eval_rule(value, op, threshold), value, f"{host}: CPU temperature is {value:g}C; threshold {op} {threshold:g}C."

    if metric == "gpu_max_temp_c":
        value, gpu_name = _v10_gpu_temp_for_notification(summary)
        if value is None:
            return False, None, f"{host}: GPU temperature is N/A; no fake temperature alert."
        return eval_rule(value, op, threshold), value, f"{host}: {gpu_name} temperature is {value:g}C; threshold {op} {threshold:g}C."

    value = _v10_notify_float(summary.get(metric), None)
    matched = eval_rule(value, op, threshold)
    return matched, value, f"{host}: {metric} is {value} {op} {threshold:g}"


def evaluate_notifications(summary):
    try:
        with DB_LOCK, db_connect() as con:
            try:
                apply_v10_notification_policy(con)
                v10_supplemental_payload_alerts(con, locals().get('machine_id'), locals().get('hostname'))
            except Exception:
                pass
            rows = con.execute("SELECT * FROM notification_rules WHERE enabled=1 AND metric!='offline_minutes' AND metric NOT LIKE 'change_%'").fetchall()
            for r in rows:
                try:
                    threshold = float(r["threshold"])
                except Exception:
                    threshold = 0.0
                matched, value, msg = notification_match_context(summary, r["metric"], r["op"], threshold)
                if matched:
                    if can_send_alert(con, r["id"], summary["machine_id"], int(r["cooldown_minutes"])):
                        host = summary.get("hostname") or summary["machine_id"]
                        record_notification(con, r["severity"], summary["machine_id"], host, r["name"], msg, r["id"])
            con.commit()
    except Exception as e:
        try:
            log("V10 evaluate_notifications failed: " + str(e))
        except Exception:
            print("V10 evaluate_notifications failed", e)


# === V10_DISK_GPU_NOTIFY_EXTRACTOR_START ===
def v10_supplemental_payload_alerts(con, machine_id=None, hostname=None):
    """
    V10 notification correction:
    - SSD/HDD/NVMe/disk >= 90% from nested payload storage.disks
    - GPU temp >= 90C from nested payload hardware.gpus
    - CPU temp >= 90C only if real numeric value exists
    - No fake N/A values
    """
    try:
        import json, datetime, math

        def _num(v):
            try:
                if v is None:
                    return None
                if isinstance(v, str):
                    s = v.strip().replace("%", "").replace("C", "").replace("c", "")
                    if s.upper() in ("", "NA", "N/A", "NONE", "NULL", "-", "UNKNOWN"):
                        return None
                    v = s
                x = float(v)
                if math.isnan(x) or math.isinf(x):
                    return None
                return x
            except Exception:
                return None

        def _loads(v):
            if not v:
                return {}
            if isinstance(v, dict):
                return v
            try:
                return json.loads(v)
            except Exception:
                return {}

        def _iter_dicts(obj):
            if isinstance(obj, dict):
                yield obj
                for vv in obj.values():
                    yield from _iter_dicts(vv)
            elif isinstance(obj, list):
                for item in obj:
                    yield from _iter_dicts(item)

        def _find_lists_by_name(obj, names):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if str(k).lower() in names and isinstance(v, list):
                        yield v
                    yield from _find_lists_by_name(v, names)
            elif isinstance(obj, list):
                for item in obj:
                    yield from _find_lists_by_name(item, names)

        def _disk_max(summary, payload):
            vals = []
            for k in ("disk_max_percent", "disk_percent", "disk_usage_percent", "storage_percent"):
                n = _num(summary.get(k))
                if n is not None:
                    vals.append(n)

            p = payload.get("payload", payload)
            disk_list_names = {"disks", "drives", "partitions", "volumes", "filesystems", "storage_devices"}
            percent_keys = ("used_percent", "usage_percent", "percent_used", "used_pct", "disk_percent", "percent", "use_percent")

            for lst in _find_lists_by_name(p, disk_list_names):
                for d in lst:
                    if not isinstance(d, dict):
                        continue
                    for k in percent_keys:
                        n = _num(d.get(k))
                        if n is not None:
                            vals.append(n)

            return max(vals) if vals else None

        def _gpu_max_temp(summary, payload):
            vals = []
            for k in ("gpu_max_temp_c", "gpu_temp_c", "gpu_temperature_c"):
                n = _num(summary.get(k))
                if n is not None:
                    vals.append(n)
                n = _num(payload.get(k))
                if n is not None:
                    vals.append(n)

            p = payload.get("payload", payload)
            gpu_list_names = {"gpus", "gpu", "graphics", "graphics_cards"}
            temp_keys = ("temperature_c", "temp_c", "gpu_temp_c", "gpu_temperature_c", "temperature")

            for lst in _find_lists_by_name(p, gpu_list_names):
                for g in lst:
                    if not isinstance(g, dict):
                        continue
                    for k in temp_keys:
                        n = _num(g.get(k))
                        if n is not None:
                            vals.append(n)

            return max(vals) if vals else None

        def _cpu_temp(summary, payload):
            for src in (summary, payload, payload.get("payload", {}) if isinstance(payload, dict) else {}):
                if isinstance(src, dict):
                    for k in ("cpu_temp_c", "cpu_temperature_c", "processor_temp_c"):
                        n = _num(src.get(k))
                        if n is not None:
                            return n
            return None

        def _send(rule_id, severity, mid, host, title, message, cooldown):
            try:
                allowed = True
                try:
                    allowed = can_send_alert(con, rule_id, mid, cooldown)
                except Exception:
                    allowed = True

                if not allowed:
                    return

                try:
                    record_notification(con, severity, mid, host, title, message, rule_id)
                    return
                except Exception:
                    pass

                cur2 = con.cursor()
                cols = [r[1] for r in cur2.execute("PRAGMA table_info(notifications)").fetchall()]
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                values = {
                    "created_at": now,
                    "severity": severity,
                    "machine_id": mid,
                    "hostname": host,
                    "title": title,
                    "message": message,
                    "rule_id": rule_id,
                    "acknowledged": 0
                }
                use_cols = [c for c in values.keys() if c in cols]
                if use_cols:
                    q = "INSERT INTO notifications (" + ",".join(use_cols) + ") VALUES (" + ",".join(["?"] * len(use_cols)) + ")"
                    cur2.execute(q, [values[c] for c in use_cols])
            except Exception as e:
                print("V10 supplemental alert insert failed:", repr(e), flush=True)

        cur = con.cursor()

        if machine_id:
            rows = cur.execute("""
                SELECT machine_id, hostname, summary_json, payload_json
                FROM latest
                WHERE machine_id=?
                LIMIT 1
            """, (machine_id,)).fetchall()
        else:
            rows = cur.execute("""
                SELECT machine_id, hostname, summary_json, payload_json
                FROM latest
                ORDER BY updated_at DESC
                LIMIT 20
            """).fetchall()

        for row in rows:
            mid = row[0]
            host = row[1] or hostname or mid
            summary = _loads(row[2])
            payload = _loads(row[3])

            disk_pct = _disk_max(summary, payload)
            gpu_temp = _gpu_max_temp(summary, payload)
            cpu_temp = _cpu_temp(summary, payload)

            cpu_pct = _num(summary.get("cpu_percent"))
            ram_pct = _num(summary.get("ram_percent"))

            if cpu_pct is not None and ram_pct is not None and cpu_pct >= 95 and ram_pct >= 95:
                _send(
                    "cpu_ram_critical",
                    "critical",
                    mid,
                    host,
                    "CPU + RAM both critical",
                    f"{host}: CPU {cpu_pct:.1f}% and RAM {ram_pct:.1f}%; alert only when both are >= 95%.",
                    15
                )

            if disk_pct is not None and disk_pct >= 90:
                _send(
                    "disk_high",
                    "critical",
                    mid,
                    host,
                    "SSD / disk usage high",
                    f"{host}: highest disk usage is {disk_pct:.1f}% >= 90%.",
                    30
                )

            if gpu_temp is not None and gpu_temp >= 90:
                _send(
                    "gpu_temp_high",
                    "critical",
                    mid,
                    host,
                    "GPU temperature high",
                    f"{host}: GPU temperature is {gpu_temp:.1f}C >= 90C.",
                    20
                )

            if cpu_temp is not None and cpu_temp >= 90:
                _send(
                    "cpu_temp_high",
                    "critical",
                    mid,
                    host,
                    "CPU temperature high",
                    f"{host}: CPU temperature is {cpu_temp:.1f}C >= 90C.",
                    20
                )

        try:
            con.commit()
        except Exception:
            pass

    except Exception as e:
        print("V10 supplemental payload alerts failed:", repr(e), flush=True)
# === V10_DISK_GPU_NOTIFY_EXTRACTOR_END ===

# === V10_NOTIFY_BACKEND_SAFE_END ===

def process_change_events(summary: Dict[str, Any], payload: Dict[str, Any]) -> None:
    changes = listify(payload.get("changes"))
    if not changes:
        return
    host = summary.get("hostname") or summary.get("machine_id", "UNKNOWN")
    mid = summary.get("machine_id", "UNKNOWN")
    with DB_LOCK, db_connect() as con:
        for ch in changes[:50]:
            if not isinstance(ch, dict):
                continue
            ctype = re.sub(r"[^a-z0-9_]+", "_", clean_str(ch.get("type") or "unknown").lower()).strip("_") or "unknown"
            title = clean_str(ch.get("title")) or f"{ctype.replace('_', ' ').title()} changed"
            message = clean_str(ch.get("message")) or json.dumps(ch, ensure_ascii=False)[:500]
            con.execute("""INSERT INTO change_events(created_at,machine_id,hostname,change_type,title,message,detail_json)
                VALUES(?,?,?,?,?,?,?)""", (now_iso(), mid, host, ctype, title, message, json.dumps(ch, ensure_ascii=False)))
            rules = con.execute("SELECT * FROM notification_rules WHERE enabled=1 AND metric=?", ("change_" + ctype,)).fetchall()
            for r in rules:
                if can_send_alert(con, r["id"], mid, int(r["cooldown_minutes"])):
                    record_notification(con, r["severity"], mid, host, r["name"], f"{host}: {message}", r["id"])
        con.commit()



def format_change_value(v: Any) -> str:
    """Compact a change item so human change log does not become unreadable."""
    if isinstance(v, dict):
        name = clean_str(v.get("display_name") or v.get("friendly_name") or v.get("name") or v.get("device_name") or v.get("description"))
        dtype = clean_str(v.get("type") or v.get("class") or v.get("category"))
        version = clean_str(v.get("version"))
        vid = clean_str(v.get("vid")); pid = clean_str(v.get("pid"))
        bits = []
        if dtype:
            bits.append(dtype)
        if name:
            bits.append(name)
        if version:
            bits.append("v" + version)
        if vid or pid:
            bits.append(f"VID:{vid or '-'} PID:{pid or '-'}")
        if bits:
            return " - ".join(bits)[:180]
        return json.dumps(v, ensure_ascii=False)[:180]
    s = clean_str(v)
    # Old broken Windows clients sometimes sent one huge raw string containing many hardware IDs.
    # Turn it into a short human sentence instead of a screen-filling paragraph.
    if len(s) > 220:
        # Try to preserve the first useful name before raw IDs.
        compact = re.sub(r"(USB|HID|PCI|SWD|BTH|ACPI)\\[^\s,;]+", "", s, flags=re.I)
        compact = re.sub(r"\s+", " ", compact).strip(" ,;|-")
        return (compact[:140] + " ... [details hidden; download CSV for full ID]") if compact else "Multiple USB/peripheral IDs changed [details hidden]"
    parts = [p.strip() for p in s.split("|")]
    if len(parts) >= 2:
        dtype = parts[0] or "Peripheral"
        name = parts[1] or "Unknown device"
        vidpid = parts[2] if len(parts) > 2 else ""
        out = f"{dtype} - {name}"
        if vidpid and vidpid != ":":
            out += f" ({vidpid})"
        return out[:160]
    s = re.sub(r"(USB|HID|PCI|SWD|BTH|ACPI)\\[^\s,;]+", "[hardware-id]", s, flags=re.I)
    return (s[:160] + "...") if len(s) > 160 else s


def humanize_change_row(row: sqlite3.Row | Dict[str, Any]) -> Dict[str, Any]:
    d = dict(row)
    detail = safe_json_loads(d.get("detail_json", "{}"), {}) if isinstance(d.get("detail_json", "{}"), str) else (d.get("detail_json") or {})
    added = [format_change_value(x) for x in listify(detail.get("added"))]
    removed = [format_change_value(x) for x in listify(detail.get("removed"))]
    ctype = clean_str(d.get("change_type") or detail.get("type") or "change")
    host = clean_str(d.get("hostname") or d.get("machine_id") or "Unknown machine")
    title = clean_str(d.get("title")) or f"{ctype.replace('_',' ').title()} changed"
    # Friendly sentence for humans.
    sentence = clean_str(d.get("message"))
    if ctype == "usb":
        sentence = f"{host}: USB/peripheral changed. Added {len(added)}, removed {len(removed)}."
    elif ctype == "software":
        sentence = f"{host}: Software list changed. Installed/updated {len(added)}, removed {len(removed)}."
    elif ctype == "hardware":
        sentence = f"{host}: Hardware inventory changed. Added {len(added)}, removed {len(removed)}."
    elif ctype == "ip":
        sentence = f"{host}: IP address changed. Added {len(added)}, removed {len(removed)}."
    elif ctype == "vpn":
        sentence = f"{host}: VPN status changed."
    d["human_title"] = title
    d["human_message"] = sentence
    d["added_items"] = added[:50]
    d["removed_items"] = removed[:50]
    d["added_text"] = " || ".join(added[:50])
    d["removed_text"] = " || ".join(removed[:50])
    d["added_count"] = len(added)
    d["removed_count"] = len(removed)
    return d


def latest_change_events(limit: int = 100, human: bool = False) -> List[Dict[str, Any]]:
    with DB_LOCK, db_connect() as con:
        rows = con.execute("SELECT * FROM change_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = [dict(r) for r in rows]
    if human:
        out = [humanize_change_row(r) for r in out]
    return out


def change_events_for_export(limit: int = 5000, machine_id: str = "") -> List[Dict[str, Any]]:
    with DB_LOCK, db_connect() as con:
        if machine_id:
            rows = con.execute("SELECT * FROM change_events WHERE machine_id=? ORDER BY id DESC LIMIT ?", (machine_id, limit)).fetchall()
        else:
            rows = con.execute("SELECT * FROM change_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    export = []
    for row in rows:
        r = humanize_change_row(dict(row))
        export.append({
            "time": r.get("created_at", ""),
            "machine": r.get("hostname") or r.get("machine_id") or "",
            "machine_id": r.get("machine_id", ""),
            "change_type": r.get("change_type", ""),
            "summary": r.get("human_message") or r.get("message") or "",
            "added_count": r.get("added_count", 0),
            "removed_count": r.get("removed_count", 0),
            "added_details": r.get("added_text", ""),
            "removed_details": r.get("removed_text", ""),
        })
    return export


def latest_payload_for_machine(machine_id: str = "") -> List[Dict[str, Any]]:
    machines = load_latest()
    if machine_id:
        machines = [m for m in machines if m.get("machine_id") == machine_id]
    return machines


def export_software_rows(machine_id: str = "") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for m in latest_payload_for_machine(machine_id):
        p = m.get("payload") or {}
        apps = listify(get_nested(p, ["software.installed", "software"], []))
        for a in apps:
            if not isinstance(a, dict):
                continue
            rows.append({
                "machine": m.get("hostname") or m.get("machine_id"),
                "machine_id": m.get("machine_id"),
                "ip": m.get("primary_ip", ""),
                "name": clean_str(a.get("name") or a.get("display_name")),
                "version": clean_str(a.get("version")),
                "publisher": clean_str(a.get("publisher")),
                "install_date": clean_str(a.get("install_date") or a.get("installDate")),
            })
    return rows


def export_usb_rows(machine_id: str = "") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for m in latest_payload_for_machine(machine_id):
        p = m.get("payload") or {}
        devices = normalize_usb_list(get_nested(p, ["usb.devices", "usb", "peripherals"], []))
        for u in devices:
            rows.append({
                "machine": m.get("hostname") or m.get("machine_id"),
                "machine_id": m.get("machine_id"),
                "ip": m.get("primary_ip", ""),
                "device": clean_str(u.get("display_name") or u.get("name")),
                "type": clean_str(u.get("type")),
                "class": clean_str(u.get("class")),
                "vid": clean_str(u.get("vid")),
                "pid": clean_str(u.get("pid")),
                "manufacturer": clean_str(u.get("manufacturer")),
                "status": clean_str(u.get("status")),
                "source": clean_str(u.get("source")),
                "device_id": clean_str(u.get("device_id")),
            })
    return rows



# ================= V10 INVENTORY BACKEND INTEGRATION =================
# Backend/API/export integration only.
# No client change. No Ubuntu collector change. No UI/CSS.
# Reads existing live payload and existing V10 truth-mapped fields.

def v10_inv_keep(v):
    try:
        if v is None:
            return ""
        return str(v).strip()
    except Exception:
        return ""

def v10_inv_join(v, sep="; "):
    try:
        if v is None or v == "":
            return ""
        if isinstance(v, list):
            return sep.join([v10_inv_keep(x) for x in v if v10_inv_keep(x)])
        if isinstance(v, tuple):
            return sep.join([v10_inv_keep(x) for x in v if v10_inv_keep(x)])
        return v10_inv_keep(v)
    except Exception:
        return ""

def v10_inv_rows_filter_machine(machine_id: str = ""):
    machines = load_latest()
    machine_id = clean_str(machine_id)
    if machine_id:
        machines = [
            m for m in machines
            if clean_str(m.get("machine_id")) == machine_id
            or clean_str(m.get("real_machine_id")) == machine_id
        ]
    return machines

def v10_inventory_machine_summary_rows(machine_id: str = ""):
    rows = []
    for m in v10_inv_rows_filter_machine(machine_id):
        rows.append({
            "hostname": m.get("hostname", ""),
            "machine_id": m.get("machine_id", ""),
            "real_machine_id": m.get("real_machine_id", ""),
            "identity_source": m.get("identity_source", m.get("id_source", "")),
            "online": m.get("online", ""),
            "last_seen": m.get("updated_at", ""),
            "os": m.get("os", ""),
            "primary_ip": m.get("primary_ip", ""),
            "public_ip": m.get("public_ip", ""),
            "isp_name": m.get("isp_name", ""),
            "cpu_percent": m.get("cpu_percent", ""),
            "cpu_temp_c": m.get("cpu_temp_c", ""),
            "ram_total_gb": m.get("ram_total_gb", ""),
            "ram_used_gb": m.get("ram_used_gb", ""),
            "ram_percent": m.get("ram_percent", ""),
            "disk_max_percent": m.get("disk_max_percent", ""),
            "gpu_count": m.get("gpu_count", ""),
            "gpu_names": v10_inv_join(m.get("gpu_names", "")),
            "gpu_total_vram_mb": m.get("gpu_total_vram_mb", m.get("gpu_total_memory_mb", "")),
            "gpu_max_usage": m.get("gpu_max_usage", ""),
            "gpu_max_temp_c": m.get("gpu_max_temp_c", ""),
            "software_count": m.get("software_count", ""),
            "usb_count": m.get("usb_count", ""),
            "vpn_active": m.get("vpn_active", ""),
        })
    return rows

def v10_inventory_hardware_rows(machine_id: str = ""):
    rows = []
    for m in v10_inv_rows_filter_machine(machine_id):
        p = m.get("payload") or {}
        hw = p.get("hardware") if isinstance(p.get("hardware"), dict) else {}
        cpu = hw.get("cpu") if isinstance(hw.get("cpu"), dict) else {}
        mem = hw.get("memory") if isinstance(hw.get("memory"), dict) else (p.get("memory") if isinstance(p.get("memory"), dict) else {})
        storage = p.get("storage") if isinstance(p.get("storage"), dict) else {}

        base = {
            "hostname": m.get("hostname", ""),
            "machine_id": m.get("machine_id", ""),
            "real_machine_id": m.get("real_machine_id", ""),
            "online": m.get("online", ""),
            "last_seen": m.get("updated_at", ""),
            "os": m.get("os", ""),
            "primary_ip": m.get("primary_ip", ""),
        }

        rows.append(dict(base, **{
            "component_type": "CPU",
            "component_name": clean_str(cpu.get("name") or "CPU"),
            "capacity": "",
            "used": "",
            "free": "",
            "usage_percent": cpu.get("usage_percent", m.get("cpu_percent", "")),
            "temperature_c": cpu.get("temperature_c", m.get("cpu_temp_c", "")),
            "manufacturer": cpu.get("manufacturer", ""),
            "model": cpu.get("name", ""),
            "serial": cpu.get("processor_id", cpu.get("serial", "")),
            "details": "cores=" + v10_inv_keep(cpu.get("cores", "")) + "; threads=" + v10_inv_keep(cpu.get("threads", "")) + "; current_mhz=" + v10_inv_keep(cpu.get("current_mhz", "")) + "; max_mhz=" + v10_inv_keep(cpu.get("max_mhz", "")),
            "source": cpu.get("source", ""),
            "accuracy": cpu.get("accuracy", "os_reported"),
        }))

        rows.append(dict(base, **{
            "component_type": "RAM",
            "component_name": "System Memory",
            "capacity": mem.get("total_gb", m.get("ram_total_gb", "")),
            "used": mem.get("used_gb", m.get("ram_used_gb", "")),
            "free": mem.get("free_gb", ""),
            "usage_percent": mem.get("used_percent", m.get("ram_percent", "")),
            "temperature_c": mem.get("temperature_c", ""),
            "manufacturer": "",
            "model": "",
            "serial": "",
            "details": "modules=" + v10_inv_keep(mem.get("modules_count", "")) + "; speed=" + v10_inv_keep(mem.get("speed_mhz", "")),
            "source": mem.get("source", ""),
            "accuracy": mem.get("accuracy", "os_reported"),
        }))

        for i, g in enumerate(listify(hw.get("gpus")), 1):
            if not isinstance(g, dict):
                continue
            gname = clean_str(g.get("name") or g.get("gpu_name") or ("GPU " + str(i)))
            low = gname.lower()
            manufacturer = "NVIDIA" if "nvidia" in low else ("Intel" if "intel" in low else ("AMD" if ("amd" in low or "radeon" in low) else ""))
            rows.append(dict(base, **{
                "component_type": "GPU",
                "component_name": gname,
                "capacity": g.get("gpu_capacity_label", g.get("gpu_capacity_mb", g.get("memory_total_mb", ""))),
                "used": g.get("gpu_used_mb", g.get("memory_used_mb", "")),
                "free": "",
                "usage_percent": g.get("usage_percent", g.get("utilization_gpu", "")),
                "temperature_c": g.get("temperature_c", g.get("temp_c", "")),
                "manufacturer": manufacturer,
                "model": gname,
                "serial": "",
                "details": "type=" + v10_inv_keep(g.get("gpu_type", "")) + "; vram_mb=" + v10_inv_keep(g.get("gpu_capacity_mb", "")) + "; shared_system_mb=" + v10_inv_keep(g.get("gpu_shared_system_mb", g.get("shared_memory_mb", ""))) + "; driver=" + v10_inv_keep(g.get("driver_version", "")),
                "source": g.get("source", ""),
                "accuracy": g.get("gpu_accuracy", g.get("accuracy", "")),
            }))

        for i, d in enumerate(listify(storage.get("disks")), 1):
            if not isinstance(d, dict):
                continue
            mount = d.get("mount") or d.get("name") or d.get("drive") or ("Disk " + str(i))
            rows.append(dict(base, **{
                "component_type": "DISK",
                "component_name": clean_str(mount),
                "capacity": d.get("total_gb", ""),
                "used": d.get("used_gb", ""),
                "free": d.get("free_gb", ""),
                "usage_percent": d.get("used_percent", d.get("usage_percent", "")),
                "temperature_c": d.get("temperature_c", ""),
                "manufacturer": d.get("manufacturer", ""),
                "model": d.get("model", ""),
                "serial": d.get("serial", ""),
                "details": "type=" + v10_inv_keep(d.get("type", "")) + "; fs=" + v10_inv_keep(d.get("file_system", d.get("fstype", ""))) + "; health=" + v10_inv_keep(d.get("health", "")),
                "source": d.get("source", ""),
                "accuracy": d.get("accuracy", "os_reported"),
            }))

        for i, u in enumerate(normalize_usb_list(get_nested(p, ["usb.devices", "usb", "peripherals"], [])), 1):
            if not isinstance(u, dict):
                continue
            rows.append(dict(base, **{
                "component_type": "USB_PERIPHERAL",
                "component_name": clean_str(u.get("display_name") or u.get("name") or ("USB " + str(i))),
                "capacity": "",
                "used": "",
                "free": "",
                "usage_percent": "",
                "temperature_c": "",
                "manufacturer": u.get("manufacturer", ""),
                "model": u.get("type", u.get("class", "")),
                "serial": u.get("serial", ""),
                "details": "class=" + v10_inv_keep(u.get("class", "")) + "; vid=" + v10_inv_keep(u.get("vid", "")) + "; pid=" + v10_inv_keep(u.get("pid", "")) + "; status=" + v10_inv_keep(u.get("status", "")) + "; device_id=" + v10_inv_keep(u.get("device_id", "")),
                "source": u.get("source", ""),
                "accuracy": "os_reported",
            }))

    return rows

def v10_inventory_software_rows(machine_id: str = ""):
    rows = []
    for m in v10_inv_rows_filter_machine(machine_id):
        p = m.get("payload") or {}
        apps = listify(get_nested(p, ["software.installed", "software", "apps"], []))
        for a in apps:
            if isinstance(a, str):
                a = {"name": a}
            if not isinstance(a, dict):
                continue
            rows.append({
                "hostname": m.get("hostname", ""),
                "machine_id": m.get("machine_id", ""),
                "real_machine_id": m.get("real_machine_id", ""),
                "online": m.get("online", ""),
                "last_seen": m.get("updated_at", ""),
                "os": m.get("os", ""),
                "primary_ip": m.get("primary_ip", ""),
                "software_name": clean_str(a.get("name") or a.get("display_name")),
                "version": clean_str(a.get("version")),
                "publisher": clean_str(a.get("publisher") or a.get("vendor")),
                "install_date": clean_str(a.get("install_date") or a.get("installDate")),
                "install_location": clean_str(a.get("install_location") or a.get("InstallLocation")),
                "source": clean_str(a.get("source")),
                "license_type": clean_str(a.get("license_type")),
                "license_status": clean_str(a.get("license_status")),
                "license_key_last5": clean_str(a.get("license_key_last5")),
                "bill_invoice_po_no": clean_str(a.get("bill_invoice_po_no")),
                "proof_link": clean_str(a.get("proof_link")),
            })
    return rows

def v10_inventory_summary(machine_id: str = ""):
    machines = v10_inv_rows_filter_machine(machine_id)
    hardware_rows = v10_inventory_hardware_rows(machine_id)
    software_rows = v10_inventory_software_rows(machine_id)
    by_component = {}
    for r in hardware_rows:
        k = r.get("component_type", "UNKNOWN") or "UNKNOWN"
        by_component[k] = by_component.get(k, 0) + 1
    return {
        "ok": True,
        "machines": len(machines),
        "hardware_rows": len(hardware_rows),
        "software_rows": len(software_rows),
        "component_counts": by_component,
        "note": "Existing payload inventory only. Client collector not changed. Missing exact values remain blank/N/A."
    }

# ================= END V10 INVENTORY BACKEND INTEGRATION =================

def check_offline_notifications() -> None:
    settings = get_settings()
    try:
        default_timeout = float(settings.get("offline_timeout_minutes", "0.25"))
    except Exception:
        default_timeout = 5.0
    now_ts = dt.datetime.now(dt.timezone.utc).timestamp()
    with DB_LOCK, db_connect() as con:
        rule = con.execute("SELECT * FROM notification_rules WHERE enabled=1 AND metric='offline_minutes' LIMIT 1").fetchone()
        if not rule:
            return
        timeout = float(rule["threshold"] or default_timeout or 5)
        rows = con.execute("SELECT machine_id,hostname,updated_at FROM latest").fetchall()
        for row in rows:
            try:
                updated = dt.datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            mins = (now_ts - updated) / 60.0
            if mins >= timeout and can_send_alert(con, rule["id"], row["machine_id"], int(rule["cooldown_minutes"])):
                host = row["hostname"] or row["machine_id"]
                record_notification(con, rule["severity"], row["machine_id"], host, rule["name"], f"{host} has not sent data for {mins:.1f} minutes", rule["id"])
        con.commit()



def create_client_message(target_machine_id: str, target_hostname: str, title: str, message: str, priority: str = "normal") -> Dict[str, Any]:
    with DB_LOCK, db_connect() as con:
        cur = con.execute("""INSERT INTO client_messages(created_at,target_machine_id,target_hostname,title,message,priority,status)
            VALUES(?,?,?,?,?,?,?)""", (now_iso(), target_machine_id or "", target_hostname or "", title or "Admin message", message or "", priority or "normal", "pending"))
        con.commit()
        mid = cur.lastrowid
    return {"ok": True, "id": mid}



def list_client_messages(limit: int = 200) -> List[Dict[str, Any]]:
    with DB_LOCK, db_connect() as con:
        rows = con.execute("""SELECT m.*, COUNT(r.machine_id) AS delivered_count, MAX(r.delivered_at) AS last_delivered_at,
                            GROUP_CONCAT(COALESCE(r.hostname, r.machine_id), ', ') AS delivered_hosts
                            FROM client_messages m
                            LEFT JOIN client_message_receipts r ON r.message_id=m.id
                            GROUP BY m.id
                            ORDER BY m.id DESC LIMIT ?""", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["delivered_count"] = int(d.get("delivered_count") or 0)
        if d.get("target_machine_id") or d.get("target_hostname"):
            d["status_label"] = "delivered" if d["delivered_count"] else "pending"
        else:
            d["status_label"] = f"broadcast delivered to {d['delivered_count']}" if d["delivered_count"] else "broadcast pending"
        out.append(d)
    return out


def take_pending_messages(con: sqlite3.Connection, machine_id: str, hostname: str) -> List[Dict[str, Any]]:
    """Return messages not yet delivered to THIS machine.
    Old bug: broadcast messages were marked delivered after the first client only.
    New logic stores per-machine receipts, so every Windows/Ubuntu client gets the broadcast once.
    """
    rows = con.execute("""SELECT * FROM client_messages m
        WHERE (m.target_machine_id='' OR m.target_machine_id=? OR lower(m.target_hostname)=lower(?))
          AND NOT EXISTS (SELECT 1 FROM client_message_receipts r WHERE r.message_id=m.id AND r.machine_id=?)
        ORDER BY m.id ASC LIMIT 10""", (machine_id, hostname or "", machine_id)).fetchall()
    out = []
    delivered_ids = []
    for r in rows:
        d = dict(r)
        out.append({"id": d["id"], "created_at": d["created_at"], "title": d["title"], "message": d["message"], "priority": d["priority"]})
        con.execute("""INSERT OR REPLACE INTO client_message_receipts(message_id,machine_id,hostname,delivered_at)
                       VALUES(?,?,?,?)""", (d["id"], machine_id, hostname or "", now_iso()))
        delivered_ids.append(d["id"])
    for mid in delivered_ids:
        # Targeted message becomes delivered after its target receives it. Broadcast remains trackable by receipts.
        con.execute("""UPDATE client_messages SET status='delivered', delivered_at=COALESCE(delivered_at, ?)
                       WHERE id=? AND (target_machine_id!='' OR target_hostname!='')""", (now_iso(), mid))
        con.execute("""UPDATE client_messages SET status='broadcast', delivered_at=COALESCE(delivered_at, ?)
                       WHERE id=? AND target_machine_id='' AND target_hostname=''""", (now_iso(), mid))
    return out

def upsert_heartbeat(payload: Dict[str, Any], client_ip: str) -> Dict[str, Any]:
    payload = normalize_payload_inplace(payload)
    if not isinstance(payload.get("network"), dict):
        payload["network"] = {}
    if not payload["network"].get("receiver_seen_ip"):
        payload["network"]["receiver_seen_ip"] = client_ip
    summary = summarize_payload(payload)
    received_at = now_iso()
    with DB_LOCK, db_connect() as con:
        con.execute("INSERT INTO heartbeats(machine_id,received_at,hostname,payload_json) VALUES(?,?,?,?)",
                    (summary["machine_id"], received_at, summary.get("hostname", ""), json.dumps(payload, ensure_ascii=False)))
        con.execute("""INSERT OR REPLACE INTO latest(machine_id,hostname,id_source,id_value,updated_at,summary_json,payload_json)
            VALUES(?,?,?,?,?,?,?)""",
            (summary["machine_id"], summary.get("hostname", ""), summary.get("id_source", ""), summary.get("id_value", ""), received_at,
             json.dumps(summary, ensure_ascii=False), json.dumps(payload, ensure_ascii=False)))
        pending_messages = take_pending_messages(con, summary["machine_id"], summary.get("hostname", ""))
        con.commit()
    evaluate_notifications(summary)
    process_change_events(summary, payload)
    return {"ok": True, "machine_id": summary["machine_id"], "id_source": summary["id_source"], "received_at": received_at, "changes_received": len(payload.get("changes") or []), "pending_messages": pending_messages}


def load_latest_raw() -> List[Dict[str, Any]]:
    # V10 read-only mode: skip DB-writing offline notification check
    settings = get_settings()
    try:
        timeout = float(settings.get("offline_timeout_minutes", "0.25"))
    except Exception:
        timeout = 0.25
    with DB_LOCK, db_connect() as con:
        rows = con.execute("SELECT * FROM latest ORDER BY updated_at DESC").fetchall()
    now_ts = dt.datetime.now(dt.timezone.utc).timestamp()
    out: List[Dict[str, Any]] = []
    seen_hosts_with_good_id = set()
    prepared: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        summary = safe_json_loads(d.get("summary_json", "{}"), {})
        payload = safe_json_loads(d.get("payload_json", "{}"), {})
        if isinstance(payload, dict):
            payload = normalize_payload_inplace(payload)
        if isinstance(summary, dict):
            # Always expose clean inventory counts from the normalized payload so old/raw USB rows do not pollute the UI.
            if isinstance(payload, dict):
                try:
                    summary["usb_count"] = int((payload.get("usb") or {}).get("count") or len(normalize_usb_list(get_nested(payload, ["usb.devices", "usb", "peripherals"], []))))
                except Exception:
                    summary["usb_count"] = summary.get("usb_count", 0)
                try:
                    summary["software_count"] = len(listify(get_nested(payload, ["software.installed", "software", "apps"], [])))
                except Exception:
                    pass
            summary.update({"machine_id": d["machine_id"], "hostname": d.get("hostname") or summary.get("hostname", ""), "id_source": d.get("id_source") or summary.get("id_source", ""), "id_value": d.get("id_value") or summary.get("id_value", ""), "updated_at": d.get("updated_at"), "payload": payload})
            try:
                updated = dt.datetime.fromisoformat((d.get("updated_at") or "").replace("Z", "+00:00")).timestamp()
                mins = max(0.0, (now_ts - updated)/60.0)
            except Exception:
                mins = 9999.0
            summary["offline_minutes"] = round(mins, 2)
            summary["online"] = mins <= timeout
            prepared.append(summary)
            host = (summary.get("hostname") or "").strip().lower()
            if host and summary.get("id_source") not in {"motherboard_serial", "hostname_fallback"}:
                seen_hosts_with_good_id.add(host)
    for summary in prepared:
        host = (summary.get("hostname") or "").strip().lower()
        # Hide stale legacy rows that used fake motherboard serial once a stable ASSET row exists for same host.
        if host and host in seen_hosts_with_good_id and summary.get("id_source") in {"motherboard_serial", "hostname_fallback"}:
            if not valid_machine_id_part(summary.get("id_value")) or str(summary.get("machine_id", "")).startswith("MOTHERBOARD_SERIAL:BSS"):
                continue
        out.append(summary)
    return out


# ================= V10 IDENTITY CORE BACKEND FIX =================
# Real backend fix. Not HTML/CSS.
# One physical machine = one record.
# Hostname changes merge by serial/MAC.
# UNKNOWN-HOST without serial/MAC is ghost.
# New machine with new serial/MAC appears as new machine.

V10_BAD_IDS = {
    "", "none", "null", "unknown", "unknown-host", "localhost",
    "na", "n/a", "not available", "not applicable",
    "default string", "to be filled by o.e.m", "to be filled by o.e.m.",
    "to be filled by oem", "system serial number",
    "base board serial number", "chassis serial number",
    "serial number", "0", "00000000", "000000000000",
    "ffffffff", "ffffffffffff",
    "00000000-0000-0000-0000-000000000000",
    "ffffffff-ffff-ffff-ffff-ffffffffffff",
    "03000200-0400-0500-0006-000700080009",
    "12345678-1234-5678-90ab-cddeefaabbcc",
    "bss-0123456789", "bss0123456789", "0123456789",
    "123456789", "1234567890"
}

def v10_clean_identity_value(v):
    s = str(v or "").strip()
    low = s.lower().strip()
    compact = re.sub(r"[^a-z0-9]", "", low)
    if low in V10_BAD_IDS or compact in V10_BAD_IDS:
        return ""
    if low.startswith("to be filled") or low.startswith("default"):
        return ""
    if re.fullmatch(r"0+", compact or "") or re.fullmatch(r"f+", compact or ""):
        return ""
    if len(s) < 3:
        return ""
    return s

def v10_walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k), v
            yield from v10_walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield "", v
            yield from v10_walk(v)

def v10_norm_mac(v):
    s = str(v or "").upper()
    pairs = re.findall(r"[0-9A-F]{2}", s)
    if len(pairs) < 6:
        return ""
    mac = ":".join(pairs[:6])
    if mac in {"00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"}:
        return ""
    return mac

def v10_virtual_mac(mac, text=""):
    t = str(text or "").lower()
    if mac.startswith("00:15:5D") or mac.startswith("0A:00:27") or mac.startswith("00:FF"):
        return True
    return bool(re.search(r"virtual|hyper-v|vmware|virtualbox|docker|wsl|loopback|tunnel|tap|tun|vpn", t))

def v10_collect_serials(payload):
    out = []
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    keys = [
        "bios_serial", "system_serial", "serial_number",
        "motherboard_serial", "baseboard_serial", "board_serial", "chassis_serial"
    ]
    for k in keys:
        s = v10_clean_identity_value(identity.get(k) or payload.get(k))
        if s and s.upper() not in [x.upper() for x in out]:
            out.append(s)

    for k, v in v10_walk(payload):
        lk = k.lower()
        if "serial" in lk and not re.search(r"disk|drive|volume|partition|usb|printer", lk):
            s = v10_clean_identity_value(v)
            if s and s.upper() not in [x.upper() for x in out]:
                out.append(s)

    return out[:8]

def v10_collect_uuids(payload):
    out = []
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    for k in ["system_uuid", "uuid", "machine_uuid"]:
        s = v10_clean_identity_value(identity.get(k) or payload.get(k))
        if s and s.upper() not in [x.upper() for x in out]:
            out.append(s)
    return out[:4]

def v10_collect_macs(payload):
    physical = []
    virtual = []

    net = payload.get("network") if isinstance(payload.get("network"), dict) else {}
    adapters = net.get("adapters") or payload.get("adapters") or []
    if isinstance(adapters, dict):
        adapters = list(adapters.values())
    if not isinstance(adapters, list):
        adapters = []

    for a in adapters:
        if not isinstance(a, dict):
            continue
        mac = v10_norm_mac(a.get("mac") or a.get("mac_address") or a.get("MACAddress"))
        if not mac:
            continue
        text = " ".join(str(a.get(k) or "") for k in ["name", "description", "type", "interface"])
        if v10_virtual_mac(mac, text):
            if mac not in virtual:
                virtual.append(mac)
        else:
            if mac not in physical:
                physical.append(mac)

    if not physical:
        for k, v in v10_walk(payload):
            if "mac" in k.lower():
                mac = v10_norm_mac(v)
                if mac and mac not in physical and mac not in virtual:
                    if v10_virtual_mac(mac):
                        virtual.append(mac)
                    else:
                        physical.append(mac)

    return (physical or virtual)[:10]

def v10_collect_ips(m):
    out = []
    for x in m.get("all_ips") or []:
        s = str(x or "").strip()
        if s and s not in out:
            out.append(s)
    for x in [m.get("primary_ip"), m.get("public_ip")]:
        s = str(x or "").strip()
        if s and s not in out:
            out.append(s)
    return out[:20]

def v10_machine_tokens(m):
    payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
    hostname = v10_clean_identity_value(m.get("hostname") or payload.get("hostname") or payload.get("computer_name"))

    serials = v10_collect_serials(payload)
    macs = v10_collect_macs(payload)
    uuids = v10_collect_uuids(payload)

    tokens = []
    for s in serials:
        tokens.append("S:" + s.upper())
    for mac in macs:
        tokens.append("M:" + mac.upper())
    for u in uuids:
        tokens.append("U:" + u.upper())

    # Hostname fallback only when no hardware fingerprint exists.
    # Hostname change will merge by serial/MAC above.
    if not tokens and hostname:
        tokens.append("H:" + hostname.upper())

    return tokens, serials, macs, uuids, hostname

def v10_merge_list(dst, values):
    if not isinstance(values, list):
        values = [values] if values else []
    for v in values:
        s = str(v or "").strip()
        if s and s not in dst:
            dst.append(s)

def load_latest() -> List[Dict[str, Any]]:
    raw = load_latest_raw()

    parent = {}
    row_tokens = []

    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for idx, m in enumerate(raw):
        m = v10_normalize_storage_in_machine(m)
        m = v10_normalize_gpus_in_machine(m)
        raw[idx] = m
        tokens, serials, macs, uuids, hostname = v10_machine_tokens(m)

        # remove UNKNOWN-HOST ghost: no serial, no MAC, no UUID, no valid hostname
        if not tokens:
            continue

        row_tokens.append((idx, tokens, serials, macs, uuids, hostname))

        for t in tokens:
            find(t)
        for t in tokens[1:]:
            union(tokens[0], t)

    groups = {}

    for idx, tokens, serials, macs, uuids, hostname in row_tokens:
        root = find(tokens[0])
        m = raw[idx]
        payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}

        if root not in groups:
            g = dict(m)
            g["real_machine_id"] = root
            g["identity_source"] = root.split(":", 1)[0].lower()
            g["rows_merged"] = 0
            g["hostnames_seen"] = []
            g["machine_ids_seen"] = []
            g["serials_seen"] = []
            g["macs_seen"] = []
            g["uuids_seen"] = []
            g["ips_seen"] = []
            groups[root] = g

        g = groups[root]
        g["rows_merged"] = int(g.get("rows_merged") or 0) + 1
        v10_merge_list(g["hostnames_seen"], hostname)
        v10_merge_list(g["machine_ids_seen"], m.get("machine_id"))
        v10_merge_list(g["serials_seen"], serials)
        v10_merge_list(g["macs_seen"], macs)
        v10_merge_list(g["uuids_seen"], uuids)
        v10_merge_list(g["ips_seen"], v10_collect_ips(m))

        # raw is newest first. Keep newest row as live data source.
        # This preserves CPU/RAM/Disk/Attention from backend, not from UI.

    machines = list(groups.values())
    machines.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return machines



# ================= V10 STORAGE BACKEND NORMALIZER =================
# Backend fix only. No HTML/CSS.
# Removes Linux pseudo mounts from API/dashboard/export source.
# Keeps real disks: /, C:, D:, E:, real mounted drives.
# Model/serial/temp/health can only show if client payload provides exact values.

def v10_to_float(v, default=None):
    try:
        if v is None or v == "":
            return default
        return float(str(v).replace("%", "").strip())
    except Exception:
        return default

def v10_simple_list(x):
    if x is None or x == "":
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, tuple):
        return list(x)
    if isinstance(x, dict):
        return [x]
    return []

def v10_is_pseudo_mount(mount, name="", dtype="", fs=""):
    mount = str(mount or "").strip()
    name = str(name or "").strip()
    dtype = str(dtype or "").strip().lower()
    fs = str(fs or "").strip().lower()
    text = (mount + " " + name + " " + dtype + " " + fs).lower()

    if mount in {"", "N/A"}:
        return False

    bad_exact = {
        "/boot/efi",
        "/sys/firmware/efi/efivars",
    }
    if mount.lower() in bad_exact:
        return True

    bad_prefix = (
        "/proc", "/sys", "/dev", "/run", "/snap",
        "/var/lib/snapd", "/var/lib/docker", "/var/lib/containerd"
    )
    if mount.lower().startswith(bad_prefix):
        return True

    bad_fs = {
        "tmpfs", "devtmpfs", "squashfs", "overlay",
        "proc", "sysfs", "cgroup", "cgroup2", "debugfs",
        "tracefs", "securityfs", "efivarfs", "pstore",
        "autofs", "mqueue", "hugetlbfs", "fusectl"
    }
    if fs in bad_fs:
        return True

    if "loop" in dtype or "loop" in name.lower():
        return True

    return False

def v10_normalize_storage_in_machine(m):
    try:
        p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        storage = p.get("storage") if isinstance(p.get("storage"), dict) else {}
        disks = v10_simple_list(storage.get("disks"))

        real = []
        for d in disks:
            if not isinstance(d, dict):
                continue

            mount = d.get("mount") or d.get("drive") or d.get("name") or ""
            name = d.get("name") or d.get("device") or ""
            dtype = d.get("type") or d.get("drive_type") or ""
            fs = d.get("file_system") or d.get("filesystem") or d.get("fstype") or ""

            if v10_is_pseudo_mount(mount, name, dtype, fs):
                continue

            total = v10_to_float(d.get("total_gb"))
            used = v10_to_float(d.get("used_gb"))
            free = v10_to_float(d.get("free_gb"))
            pct = v10_to_float(d.get("used_percent") or d.get("usage_percent"))

            # Remove zero-size pseudo rows.
            if total is not None and total <= 0:
                continue

            # Fill missing values only from exact capacity numbers already present.
            nd = dict(d)
            if not nd.get("mount") and mount:
                nd["mount"] = mount
            if not nd.get("name") and name:
                nd["name"] = name

            if pct is None and total and used is not None:
                pct = round((used / total) * 100, 2)
                nd["used_percent"] = pct

            if used is None and total and free is not None:
                used = round(total - free, 2)
                nd["used_gb"] = used

            if free is None and total and used is not None:
                free = round(total - used, 2)
                nd["free_gb"] = free

            real.append(nd)

        storage["disks"] = real
        storage["count"] = len(real)
        p["storage"] = storage
        m["payload"] = p
        m["disk_count"] = len(real)

        vals = []
        for d in real:
            pct = v10_to_float(d.get("used_percent") or d.get("usage_percent"))
            if pct is not None:
                vals.append(pct)
        m["disk_max_percent"] = round(max(vals), 2) if vals else 0

        return m
    except Exception:
        return m

# ================= END V10 STORAGE BACKEND NORMALIZER =================




# ================= V10 GPU BACKEND NORMALIZER =================
# Backend truth mapping only. No HTML/CSS. No Ubuntu client change.
# Main rule:
# - NVIDIA nvidia-smi: capacity = dedicated VRAM only.
# - Intel/AMD integrated: shared RAM is NOT GPU capacity.
# - Do not fake usage/temp.

def v10_gpu_num(v):
    try:
        if v is None or v == "":
            return None
        s = str(v).replace("%", "").strip()
        if not s or s.upper() == "N/A":
            return None
        return float(s)
    except Exception:
        return None

def v10_gpu_outnum(v):
    n = v10_gpu_num(v)
    if n is None:
        return ""
    return int(n) if float(n).is_integer() else round(n, 2)

def v10_gpu_blank(v):
    return v is None or str(v).strip() == "" or str(v).strip().upper() == "N/A"

def v10_gpu_list(x):
    if x is None or x == "":
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, tuple):
        return list(x)
    if isinstance(x, dict):
        return [x]
    return []

def v10_gpu_kind(name, source):
    low = str(name or "").lower()
    src = str(source or "").lower()

    is_nvidia = ("nvidia" in low) or ("nvidia-smi" in src)
    is_intel = ("intel" in low) or ("uhd graphics" in low) or ("iris" in low)
    is_integrated_amd = (
        "radeon(tm) graphics" in low or
        "radeon(tm) 610m" in low or
        "radeon 610m" in low or
        "with radeon graphics" in low
    )
    is_amd = ("amd" in low) or ("radeon" in low)

    if is_nvidia:
        return "nvidia_dedicated"
    if is_intel:
        return "intel_integrated"
    if is_integrated_amd:
        return "amd_integrated"
    if is_amd:
        return "amd_gpu"
    return "gpu"

def v10_normalize_gpus_in_machine(m):
    try:
        p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        hw = p.get("hardware") if isinstance(p.get("hardware"), dict) else {}
        gpus = v10_gpu_list(hw.get("gpus"))

        out = []
        names = []
        usage_vals = []
        temp_vals = []
        total_vram = 0.0

        for g in gpus:
            if not isinstance(g, dict):
                continue

            ng = dict(g)
            name = str(ng.get("name") or ng.get("gpu_name") or "").strip()
            source = str(ng.get("source") or "").strip()
            src_low = source.lower()
            kind = v10_gpu_kind(name, source)

            # Ubuntu unchanged now.
            if src_low == "lspci":
                ng["gpu_type"] = ng.get("gpu_type") or "Linux GPU name only"
                ng["gpu_display_type"] = "Linux GPU name only"
                ng["gpu_capacity_mb"] = ""
                ng["gpu_capacity_label"] = "N/A"
                ng["gpu_shared_system_mb"] = ""
                ng["gpu_accuracy"] = "name_only_lspci"
                out.append(ng)
                if name:
                    names.append(name)
                continue

            raw_total = v10_gpu_num(ng.get("memory_total_mb"))
            raw_dedicated = v10_gpu_num(ng.get("dedicated_memory_mb"))
            raw_shared = v10_gpu_num(ng.get("shared_memory_mb"))
            raw_used = v10_gpu_num(ng.get("memory_used_mb"))
            raw_usage = v10_gpu_num(ng.get("usage_percent") or ng.get("utilization_gpu"))
            raw_temp = v10_gpu_num(ng.get("temperature_c") or ng.get("temp_c"))

            if kind == "nvidia_dedicated":
                vram = raw_dedicated if raw_dedicated is not None else raw_total

                ng["gpu_type"] = "Dedicated NVIDIA"
                ng["gpu_display_type"] = "Dedicated NVIDIA"
                ng["gpu_accuracy"] = "exact_nvidia_smi" if "nvidia-smi" in src_low else "os_reported_nvidia"

                if vram is not None:
                    ng["memory_total_mb"] = v10_gpu_outnum(vram)
                    ng["dedicated_memory_mb"] = v10_gpu_outnum(vram)
                    ng["gpu_capacity_mb"] = v10_gpu_outnum(vram)
                    ng["gpu_capacity_label"] = str(v10_gpu_outnum(vram)) + " MB VRAM"
                    total_vram += float(vram)
                else:
                    ng["gpu_capacity_mb"] = ""
                    ng["gpu_capacity_label"] = "N/A"

                # Shared system memory may be reported by Windows, but it is NOT GPU capacity.
                ng["gpu_shared_system_mb"] = v10_gpu_outnum(raw_shared)
                ng["gpu_capacity_note"] = "Capacity is dedicated VRAM only. Shared system memory is separate."

            elif kind in ("intel_integrated", "amd_integrated"):
                if kind == "intel_integrated":
                    ng["gpu_type"] = "Integrated Intel"
                    ng["gpu_display_type"] = "Integrated Intel"
                else:
                    ng["gpu_type"] = "Integrated AMD"
                    ng["gpu_display_type"] = "Integrated AMD"

                # Important correction:
                # For integrated GPU, memory_total_mb often equals shared system RAM.
                # Do not show it as GPU capacity.
                if raw_shared is None and raw_total is not None:
                    raw_shared = raw_total

                # Keep OS-reported dedicated value separate.
                if raw_dedicated is None and raw_total is not None and raw_total <= 1024:
                    raw_dedicated = raw_total

                ng["memory_total_mb"] = ""
                ng["gpu_capacity_mb"] = ""
                ng["gpu_capacity_label"] = "Shared system memory"
                ng["gpu_shared_system_mb"] = v10_gpu_outnum(raw_shared)
                ng["gpu_os_reported_dedicated_mb"] = v10_gpu_outnum(raw_dedicated)
                if raw_dedicated is not None:
                    ng["dedicated_memory_mb"] = v10_gpu_outnum(raw_dedicated)

                if "gpu_engine" in src_low:
                    ng["gpu_accuracy"] = "os_reported_integrated_usage"
                else:
                    ng["gpu_accuracy"] = "os_reported_integrated_memory_only"

                ng["gpu_capacity_note"] = "Integrated GPU uses shared system memory. Shared RAM is not counted as GPU capacity."

            else:
                ng["gpu_type"] = ng.get("gpu_type") or "GPU"
                ng["gpu_display_type"] = ng["gpu_type"]
                ng["gpu_accuracy"] = "os_reported_gpu"
                ng["gpu_capacity_mb"] = v10_gpu_outnum(raw_dedicated if raw_dedicated is not None else raw_total)
                ng["gpu_capacity_label"] = str(ng["gpu_capacity_mb"]) + " MB" if ng["gpu_capacity_mb"] != "" else "N/A"
                ng["gpu_shared_system_mb"] = v10_gpu_outnum(raw_shared)
                if raw_dedicated is not None:
                    total_vram += float(raw_dedicated)

            if name:
                names.append(name)

            # Usage/temp only if exact value already exists. No fake calculation.
            if raw_usage is not None:
                usage_vals.append(raw_usage)
            if raw_temp is not None:
                temp_vals.append(raw_temp)

            if raw_used is not None:
                ng["gpu_used_mb"] = v10_gpu_outnum(raw_used)

            out.append(ng)

        hw["gpus"] = out
        p["hardware"] = hw
        m["payload"] = p

        m["gpu_count"] = len(out)
        m["gpu_names"] = names
        m["gpu_max_usage"] = round(max(usage_vals), 2) if usage_vals else None
        m["gpu_max_temp_c"] = round(max(temp_vals), 2) if temp_vals else None
        m["gpu_total_memory_mb"] = round(total_vram, 2) if total_vram else 0
        m["gpu_total_vram_mb"] = round(total_vram, 2) if total_vram else 0

        return m
    except Exception:
        return m

# ================= END V10 GPU BACKEND NORMALIZER =================


# ================= END V10 IDENTITY CORE BACKEND FIX =================


def overview() -> Dict[str, Any]:
    machines = load_latest()
    server_isp = server_public_internet_info(False)
    settings = get_settings()
    auto_speed_probe = str(settings.get("auto_speed_probe", "1")).lower() in ("1", "true", "yes", "on")
    internet_health = server_internet_health(False, auto_speed_probe)
    total = len(machines)
    online = sum(1 for m in machines if m.get("online"))
    offline = total - online
    critical = sum(1 for m in machines if (to_float(m.get("cpu_percent"),0) or 0) >= 90 or (to_float(m.get("ram_percent"),0) or 0) >= 90 or (to_float(m.get("disk_max_percent"),0) or 0) >= 90)
    today_down = sum(to_float(m.get("today_download_gb"),0) or 0 for m in machines)
    today_up = sum(to_float(m.get("today_upload_gb"),0) or 0 for m in machines)
    cur_down = sum(to_float(m.get("wan_download_mbps"),0) or 0 for m in machines)
    cur_up = sum(to_float(m.get("wan_upload_mbps"),0) or 0 for m in machines)
    client_isp_down = sum(to_float(m.get("isp_download_mbps"),0) or 0 for m in machines)
    client_isp_up = sum(to_float(m.get("isp_upload_mbps"),0) or 0 for m in machines)
    probe_down = to_float(internet_health.get("probe_download_mbps"), 0) or 0
    probe_up = to_float(internet_health.get("probe_upload_mbps"), 0) or 0
    # Home ISP speed should not stay 0 when clients are idle; show server live ISP probe as fallback.
    isp_down = max(client_isp_down, probe_down)
    isp_up = max(client_isp_up, probe_up)
    isp_counts: Dict[str, int] = {}
    public_ips: List[str] = []
    for m in machines:
        if m.get("isp_name"):
            isp_counts[m["isp_name"]] = isp_counts.get(m["isp_name"], 0) + 1
        if m.get("public_ip") and m.get("public_ip") not in public_ips:
            public_ips.append(m["public_ip"])
    top_isps = sorted(isp_counts.items(), key=lambda kv: kv[1], reverse=True)[:3]
    # Fallback: if no updated client has sent ISP yet, show server ISP so home page is not blank after server start.
    if not top_isps and server_isp.get("isp"):
        top_isps = [(server_isp.get("isp", ""), 1)]
    if not public_ips and server_isp.get("public_ip"):
        public_ips.append(server_isp.get("public_ip", ""))
    with DB_LOCK, db_connect() as con:
        notif = con.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 10").fetchall()
        changes = con.execute("SELECT * FROM change_events ORDER BY id DESC LIMIT 10").fetchall()
    return {
        "total": total, "online": online, "offline": offline, "critical": critical,
        "today_download_gb": round(today_down, 2), "today_upload_gb": round(today_up, 2),
        "current_download_mbps": round(cur_down, 2), "current_upload_mbps": round(cur_up, 2),
        "isp_download_mbps": round(isp_down, 2), "isp_upload_mbps": round(isp_up, 2),
        "isp_names": [name for name, count in top_isps], "public_ips": public_ips[:5],
        "server_isp": server_isp,
        "internet_health": internet_health,
        "isp_speed_note": internet_health.get("speed_note", ""),
        "isp_speed_source": "server_live_probe" if (probe_down or probe_up) else "client_live_usage",
        "machines": machines[:500], "notifications": [dict(r) for r in notif], "changes": [humanize_change_row(dict(r)) for r in changes], "settings": settings
    }


def daily_history(days: int = 30, machine_id: str = "", date_from: str = "", date_to: str = "", include_samples: bool = False) -> Dict[str, Any]:
    """Build daily traffic/history from stored heartbeats.
    User can select an exact date or date range and download all data.
    """
    days = max(1, min(int(days or 30), 3650))
    now_utc = dt.datetime.now(dt.timezone.utc)
    def parse_day(v: str) -> Optional[dt.date]:
        try:
            return dt.date.fromisoformat((v or "").strip()[:10])
        except Exception:
            return None
    df = parse_day(date_from)
    dt_to = parse_day(date_to)
    if df:
        start_dt = dt.datetime.combine(df, dt.time.min, tzinfo=dt.timezone.utc)
    else:
        start_dt = now_utc - dt.timedelta(days=days)
    if dt_to:
        end_dt = dt.datetime.combine(dt_to + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
    elif df:
        end_dt = dt.datetime.combine(df + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
    else:
        end_dt = now_utc + dt.timedelta(seconds=1)
    with DB_LOCK, db_connect() as con:
        if machine_id:
            rows = con.execute("SELECT machine_id,received_at,hostname,payload_json FROM heartbeats WHERE received_at>=? AND received_at<? AND machine_id=? ORDER BY received_at ASC", (start_dt.isoformat(), end_dt.isoformat(), machine_id)).fetchall()
        else:
            rows = con.execute("SELECT machine_id,received_at,hostname,payload_json FROM heartbeats WHERE received_at>=? AND received_at<? ORDER BY received_at ASC", (start_dt.isoformat(), end_dt.isoformat())).fetchall()
    buckets: Dict[str, Dict[str, Any]] = {}
    machines: Dict[str, Dict[str, Any]] = {}
    samples: List[Dict[str, Any]] = []
    for r in rows:
        try:
            day = dt.datetime.fromisoformat(str(r["received_at"]).replace("Z", "+00:00")).astimezone(dt.timezone.utc).date().isoformat()
        except Exception:
            day = str(r["received_at"])[:10]
        payload = normalize_payload_inplace(safe_json_loads(r["payload_json"], {}))
        summary = summarize_payload(payload)
        mid = summary.get("machine_id") or r["machine_id"]
        host = summary.get("hostname") or r["hostname"] or mid
        b = buckets.setdefault(day, {"date": day, "machines_seen": set(), "download_gb": 0.0, "upload_gb": 0.0, "max_current_download_mbps": 0.0, "max_current_upload_mbps": 0.0, "cpu_samples": [], "ram_samples": [], "usb_max": 0, "software_max": 0, "heartbeat_count": 0})
        b["machines_seen"].add(mid)
        b["heartbeat_count"] += 1
        b["usb_max"] = max(int(b["usb_max"]), int(to_float(summary.get("usb_count"), 0) or 0))
        b["software_max"] = max(int(b["software_max"]), int(to_float(summary.get("software_count"), 0) or 0))
        # Client counters are day-to-date, so for each machine/day take the max seen value.
        mkey = day + "|" + mid
        mm = machines.setdefault(mkey, {"date":day, "machine_id":mid, "hostname":host, "download_gb":0.0, "upload_gb":0.0, "max_current_download_mbps":0.0, "max_current_upload_mbps":0.0, "cpu_max":0.0, "ram_max":0.0, "ram_total_gb":summary.get("ram_total_gb") or 0, "usb_count":0, "software_count":0, "public_ip":"", "isp_name":"", "last_seen":r["received_at"], "heartbeat_count":0})
        mm["download_gb"] = max(float(mm["download_gb"]), float(to_float(summary.get("today_download_gb"), 0) or 0))
        mm["upload_gb"] = max(float(mm["upload_gb"]), float(to_float(summary.get("today_upload_gb"), 0) or 0))
        mm["max_current_download_mbps"] = max(float(mm["max_current_download_mbps"]), float(to_float(summary.get("wan_download_mbps"), 0) or 0))
        mm["max_current_upload_mbps"] = max(float(mm["max_current_upload_mbps"]), float(to_float(summary.get("wan_upload_mbps"), 0) or 0))
        mm["cpu_max"] = max(float(mm["cpu_max"]), float(to_float(summary.get("cpu_percent"), 0) or 0))
        mm["ram_max"] = max(float(mm["ram_max"]), float(to_float(summary.get("ram_percent"), 0) or 0))
        mm["ram_total_gb"] = summary.get("ram_total_gb") or mm.get("ram_total_gb") or 0
        mm["usb_count"] = max(int(mm.get("usb_count") or 0), int(to_float(summary.get("usb_count"), 0) or 0))
        mm["software_count"] = max(int(mm.get("software_count") or 0), int(to_float(summary.get("software_count"), 0) or 0))
        if summary.get("public_ip"): mm["public_ip"] = summary.get("public_ip")
        if summary.get("isp_name"): mm["isp_name"] = summary.get("isp_name")
        mm["last_seen"] = r["received_at"]
        mm["heartbeat_count"] += 1
        b["max_current_download_mbps"] = max(float(b["max_current_download_mbps"]), float(to_float(summary.get("wan_download_mbps"), 0) or 0))
        b["max_current_upload_mbps"] = max(float(b["max_current_upload_mbps"]), float(to_float(summary.get("wan_upload_mbps"), 0) or 0))
        cp = to_float(summary.get("cpu_percent"))
        rp = to_float(summary.get("ram_percent"))
        if cp is not None: b["cpu_samples"].append(cp)
        if rp is not None: b["ram_samples"].append(rp)
        if include_samples:
            samples.append({
                "received_at": r["received_at"], "date": day, "machine_id": mid, "hostname": host,
                "primary_ip": summary.get("primary_ip"), "public_ip": summary.get("public_ip"), "isp_name": summary.get("isp_name"),
                "cpu_percent": summary.get("cpu_percent"), "cpu_temp_c": summary.get("cpu_temp_c"),
                "ram_percent": summary.get("ram_percent"), "ram_total_gb": summary.get("ram_total_gb"), "ram_used_gb": summary.get("ram_used_gb"),
                "disk_max_percent": summary.get("disk_max_percent"), "current_download_mbps": summary.get("wan_download_mbps"), "current_upload_mbps": summary.get("wan_upload_mbps"),
                "today_download_gb": summary.get("today_download_gb"), "today_upload_gb": summary.get("today_upload_gb"), "gpu_count": summary.get("gpu_count"),
                "gpu_names": ", ".join(summary.get("gpu_names") or []), "gpu_temp_c": summary.get("gpu_max_temp_c"), "vpn_active": summary.get("vpn_active"),
                "software_count": summary.get("software_count"), "usb_count": summary.get("usb_count"), "change_count": summary.get("change_count"),
            })
    for mm in machines.values():
        b = buckets[mm["date"]]
        b["download_gb"] += float(mm["download_gb"])
        b["upload_gb"] += float(mm["upload_gb"])
    daily = []
    for day in sorted(buckets.keys(), reverse=True):
        b = buckets[day]
        cpu_avg = round(sum(b["cpu_samples"])/len(b["cpu_samples"]), 2) if b["cpu_samples"] else 0
        ram_avg = round(sum(b["ram_samples"])/len(b["ram_samples"]), 2) if b["ram_samples"] else 0
        daily.append({"date": day, "machines_seen": len(b["machines_seen"]), "heartbeat_count": b["heartbeat_count"], "download_gb": round(float(b["download_gb"]), 2), "upload_gb": round(float(b["upload_gb"]), 2), "max_current_download_mbps": round(float(b["max_current_download_mbps"]), 2), "max_current_upload_mbps": round(float(b["max_current_upload_mbps"]), 2), "avg_cpu_percent": cpu_avg, "avg_ram_percent": ram_avg, "usb_max": b["usb_max"], "software_max": b["software_max"]})
    per_machine = list(machines.values())
    per_machine.sort(key=lambda x: (x["date"], x["hostname"]), reverse=True)
    return {"ok": True, "days": days, "date_from": start_dt.date().isoformat(), "date_to": (end_dt.date() - dt.timedelta(days=1)).isoformat(), "history_note": "History is available from heartbeats stored in this server database.", "daily": daily, "per_machine": per_machine[:5000], "samples": samples[:20000] if include_samples else []}


def csv_response(rows: List[Dict[str, Any]], filename: str) -> Tuple[bytes, Dict[str, str]]:
    out = io.StringIO()
    if rows:
        fields = list(rows[0].keys())
    else:
        fields = ["no_data"]
        rows = [{"no_data":"No rows for selected date/range"}]
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k, "") for k in fields})
    return out.getvalue().encode("utf-8"), {"Content-Disposition": f"attachment; filename={filename}"}


class Handler(BaseHTTPRequestHandler):
    server_version = "SagarSystemMonitor/6.4"

    def log_message(self, fmt: str, *args: Any) -> None:
        log(f"{self.address_string()} {fmt % args}")

    def current_session(self) -> Dict[str, Any]:
        cookies = parse_cookies(self.headers.get("Cookie", ""))
        return session_info(cookies.get("cmp_session", ""))

    def is_authenticated(self) -> bool:
        return bool(self.current_session())

    def current_role(self) -> str:
        return clean_str(self.current_session().get("role") or "")

    def current_username(self) -> str:
        return clean_str(self.current_session().get("username") or "")

    def is_admin(self) -> bool:
        return self.current_role() in ("super_admin", "admin")

    def require_admin(self) -> bool:
        if not self.is_authenticated():
            return self.send_json({"error":"auth_required"}, 401) or False
        if not self.is_admin():
            return self.send_json({"error":"admin_required", "message":"This action is available only to admin users."}, 403) or False
        return True

    def require_auth(self, path: str, method: str) -> bool:
        if not auth_required_path(method, path):
            return True
        if self.is_authenticated():
            return True
        self.send_json({"error":"login_required", "message":"Admin login required"}, 401)
        return False

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8", extra_headers: Optional[Dict[str,str]]=None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if extra_headers:
            for k, v in extra_headers.items(): self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj: Any, status: int=200) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))

    def read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8", errors="replace") or "{}")

    def do_OPTIONS(self) -> None:
        self._send(204, b"")

    def do_GET(self) -> None:
        try:
            path = self.path.split("?", 1)[0]
            qs = {}
            if "?" in self.path:
                from urllib.parse import parse_qs
                qs = parse_qs(self.path.split("?",1)[1])
            if path == "/api/health":
                return self.send_json({"ok": True, "time": now_iso(), "db": str(DB_PATH), "app_name": APP_NAME, "version":"8.4"})
            if path == "/api/auth/status":
                return self.send_json({"ok": True, "authenticated": self.is_authenticated(), "app_name": APP_NAME, "local": is_local_request(self.client_address[0]), "username": self.current_username(), "role": self.current_role()})
            if not self.require_auth(path, "GET"):
                return
            if path == "/api/isp-check":
                server_isp = server_public_internet_info(True)
                machines = load_latest()
                client_isp = [m for m in machines if m.get("isp_name") or m.get("public_ip")]
                return self.send_json({"ok": True, "server_isp": server_isp, "machines_total": len(machines), "machines_with_client_isp": len(client_isp), "client_isp_samples": client_isp[:10]})
            if path == "/api/server-speed-test":
                full = (qs.get("full") or ["0"])[0] in ("1", "true", "yes", "on")
                try:
                    down_mb = int(float((qs.get("download_mb") or ["0"])[0] or 0))
                except Exception:
                    down_mb = 0
                try:
                    up_mb = int(float((qs.get("upload_mb") or ["0"])[0] or 0))
                except Exception:
                    up_mb = 0
                if full:
                    down_b = (down_mb if down_mb else 50) * 1000 * 1000
                    up_b = (up_mb if up_mb else 10) * 1000 * 1000
                else:
                    down_b = (down_mb if down_mb else 5) * 1000 * 1000
                    up_b = (up_mb if up_mb else 1) * 1000 * 1000
                out = server_cloudflare_speed_test(down_b, up_b)
                out["mode"] = "full_capacity" if full else "quick_probe"
                out["download_mb_requested"] = round(down_b/1000/1000, 1)
                out["upload_mb_requested"] = round(up_b/1000/1000, 1)
                out["isp"] = server_public_internet_info(False)
                return self.send_json(out)
            if path == "/api/internet-health":
                force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
                speed = (qs.get("speed") or ["1"])[0] in ("1", "true", "yes")
                return self.send_json(server_internet_health(force, speed))
            if path == "/api/users":
                if not self.require_admin():
                    return
                return self.send_json({"users": list_users_public()})
            if path == "/api/messages":
                return self.send_json({"messages": list_client_messages(300)})
            if path == "/api/overview":
                return self.send_json(overview())
            if path == "/api/inventory/summary":
                mid = (qs.get("machine_id") or [""])[0]
                return self.send_json(v10_inventory_summary(mid))
            if path == "/api/inventory/hardware":
                mid = (qs.get("machine_id") or [""])[0]
                rows = v10_inventory_hardware_rows(mid)
                return self.send_json({"ok": True, "count": len(rows), "rows": rows})
            if path == "/api/inventory/software":
                mid = (qs.get("machine_id") or [""])[0]
                rows = v10_inventory_software_rows(mid)
                return self.send_json({"ok": True, "count": len(rows), "rows": rows})
            if path == "/api/inventory/machine_summary":
                mid = (qs.get("machine_id") or [""])[0]
                rows = v10_inventory_machine_summary_rows(mid)
                return self.send_json({"ok": True, "count": len(rows), "rows": rows})
            if path == "/api/machines":
                return self.send_json({"machines": load_latest()})
            if path == "/api/history":
                days = int((qs.get("days") or ["30"])[0] or 30)
                mid = (qs.get("machine_id") or [""])[0]
                date_from = (qs.get("date_from") or [""])[0]
                date_to = (qs.get("date_to") or [""])[0]
                include_samples = (qs.get("samples") or ["0"])[0] in ("1", "true", "yes")
                return self.send_json(daily_history(days, mid, date_from, date_to, include_samples))
            if path == "/api/machine":
                mid = (qs.get("id") or [""])[0]
                machines = load_latest()
                for m in machines:
                    if m.get("machine_id") == mid:
                        return self.send_json(m)
                return self.send_json({"error":"Machine not found"}, 404)
            if path == "/api/notifications/rules":
                return self.send_json({"rules": rules_list(), "settings": public_settings()})
            if path == "/api/notifications":
                with DB_LOCK, db_connect() as con:
                    rows = con.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 200").fetchall()
                return self.send_json({"notifications": [dict(r) for r in rows]})
            if path == "/api/changes":
                return self.send_json({"changes": latest_change_events(300, human=True)})
            if path == "/api/export/changes.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                mid = (qs.get("machine_id") or [""])[0]
                rows = change_events_for_export(5000, mid)
                body, headers = csv_response(rows, "human_change_log.csv" if not mid else "human_change_log_selected_machine.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/software.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                mid = (qs.get("machine_id") or [""])[0]
                rows = export_software_rows(mid)
                body, headers = csv_response(rows, "software_inventory.csv" if not mid else "software_selected_machine.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/usb.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                mid = (qs.get("machine_id") or [""])[0]
                rows = export_usb_rows(mid)
                body, headers = csv_response(rows, "usb_peripherals.csv" if not mid else "usb_selected_machine.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/history_daily.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                days = int((qs.get("days") or ["30"])[0] or 30)
                mid = (qs.get("machine_id") or [""])[0]
                date_from = (qs.get("date_from") or [""])[0]
                date_to = (qs.get("date_to") or [""])[0]
                data = daily_history(days, mid, date_from, date_to, False)
                body, headers = csv_response(data.get("daily") or [], "day_summary.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/history_machine.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                days = int((qs.get("days") or ["30"])[0] or 30)
                mid = (qs.get("machine_id") or [""])[0]
                date_from = (qs.get("date_from") or [""])[0]
                date_to = (qs.get("date_to") or [""])[0]
                data = daily_history(days, mid, date_from, date_to, False)
                body, headers = csv_response(data.get("per_machine") or [], "system_wise_day_history.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/inventory_hardware.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                mid = (qs.get("machine_id") or [""])[0]
                body, headers = csv_response(v10_inventory_hardware_rows(mid), "hardware_inventory.csv" if not mid else "hardware_inventory_selected_machine.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/inventory_software.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                mid = (qs.get("machine_id") or [""])[0]
                body, headers = csv_response(v10_inventory_software_rows(mid), "software_inventory_full.csv" if not mid else "software_inventory_selected_machine.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/inventory_machine_summary.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                mid = (qs.get("machine_id") or [""])[0]
                body, headers = csv_response(v10_inventory_machine_summary_rows(mid), "inventory_machine_summary.csv" if not mid else "inventory_machine_summary_selected_machine.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path.startswith("/api/export/") and not self.is_admin():
                return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
            if path == "/api/export/history.csv":
                days = int((qs.get("days") or ["30"])[0] or 30)
                mid = (qs.get("machine_id") or [""])[0]
                date_from = (qs.get("date_from") or [""])[0]
                date_to = (qs.get("date_to") or [""])[0]
                data = daily_history(days, mid, date_from, date_to, False)
                rows = data.get("per_machine") or data.get("daily") or []
                body, headers = csv_response(rows, "history_per_machine.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/history_samples.csv":
                days = int((qs.get("days") or ["30"])[0] or 30)
                mid = (qs.get("machine_id") or [""])[0]
                date_from = (qs.get("date_from") or [""])[0]
                date_to = (qs.get("date_to") or [""])[0]
                data = daily_history(days, mid, date_from, date_to, True)
                body, headers = csv_response(data.get("samples") or [], "history_all_heartbeats.csv")
                return self._send(200, body, "text/csv; charset=utf-8", headers)
            if path == "/api/export/machine_current.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                mid = (qs.get("machine_id") or [""])[0]
                machines = load_latest()
                if mid:
                    machines = [m for m in machines if m.get("machine_id") == mid]
                fields = ["hostname","machine_id","os","primary_ip","public_ip","isp_name","online","cpu_percent","cpu_temp_c","ram_percent","ram_total_gb","ram_used_gb","disk_max_percent","wan_download_mbps","wan_upload_mbps","today_download_gb","today_upload_gb","gpu_count","gpu_names","vpn_active","software_count","usb_count","updated_at"]
                out = io.StringIO(); w = csv.DictWriter(out, fieldnames=fields); w.writeheader()
                for m in machines:
                    row = {k: m.get(k, "") for k in fields}
                    if isinstance(row.get("gpu_names"), list): row["gpu_names"] = "; ".join(row["gpu_names"])
                    w.writerow(row)
                return self._send(200, out.getvalue().encode("utf-8"), "text/csv; charset=utf-8", {"Content-Disposition":"attachment; filename=machine_current.csv"})
            if path == "/api/export/machines.csv":
                if not self.is_admin():
                    return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
                machines = load_latest()
                out = io.StringIO()
                fields = ["hostname","machine_id","id_source","os","primary_ip","public_ip","isp_name","online","cpu_percent","cpu_temp_c","ram_percent","ram_total_gb","ram_used_gb","disk_max_percent","wan_download_mbps","wan_upload_mbps","isp_download_mbps","isp_upload_mbps","today_download_gb","today_upload_gb","gpu_count","gpu_max_usage","gpu_max_temp_c","vpn_active","software_count","usb_count","change_count","updated_at"]
                w = csv.DictWriter(out, fieldnames=fields)
                w.writeheader()
                for m in machines:
                    w.writerow({k: m.get(k, "") for k in fields})
                return self._send(200, out.getvalue().encode("utf-8"), "text/csv; charset=utf-8", {"Content-Disposition":"attachment; filename=machines.csv"})
            return self.serve_static(path)
        except Exception as e:
            log(traceback.format_exc())
            return self.send_json({"error": str(e)}, 500)

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        rel = path.lstrip("/")
        if ".." in rel or rel.startswith("/"):
            return self.send_json({"error":"bad path"}, 400)

        # Single-port client update system:
        # The main server on 2278 also serves scripts, so no separate 8511 file-server window is required.
        if rel == "scripts" or rel.startswith("scripts/"):
            script_rel = rel[len("scripts/"): ] if rel.startswith("scripts/") else ""
            file_path = SCRIPTS_DIR / script_rel
            if file_path.exists() and file_path.is_file():
                data = file_path.read_bytes()
                return self._send(200, data, MIME.get(file_path.suffix.lower(), "application/octet-stream"), {"Cache-Control":"no-store"})
            return self.send_json({"error":"script not found"}, 404)

        if rel == "dist" or rel.startswith("dist/"):
            dist_rel = rel[len("dist/"): ] if rel.startswith("dist/") else ""
            dist_path = BASE_DIR / "dist" / dist_rel
            if dist_path.exists() and dist_path.is_file():
                data = dist_path.read_bytes()
                return self._send(200, data, MIME.get(dist_path.suffix.lower(), "application/octet-stream"), {"Cache-Control":"no-store"})
            return self.send_json({"error":"file not found"}, 404)

        file_path = PUBLIC_DIR / rel
        if not file_path.exists() or not file_path.is_file():
            file_path = PUBLIC_DIR / "index.html"
        data = file_path.read_bytes()
        self._send(200, data, MIME.get(file_path.suffix.lower(), "application/octet-stream"), {"Cache-Control":"no-store, max-age=0"})

    def do_POST(self) -> None:
        try:
            path = self.path.split("?",1)[0]
            body = self.read_json()
            if path == "/api/auth/login":
                username = clean_str(body.get("username") or "admin").strip() or "admin"
                password = clean_str(body.get("password"))
                row = get_user_row(username)
                if row and verify_password(password, row["password_hash"]):
                    token = new_session(row["username"], row["role"])
                    data = json.dumps({"ok": True, "app_name": APP_NAME, "version":"8.4", "username": row["username"], "role": row["role"]}).encode("utf-8")
                    self._send(200, data, "application/json; charset=utf-8", {"Set-Cookie": f"cmp_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={SESSION_TTL_SECONDS}"})
                    return
                settings = get_settings()
                stored = settings.get("admin_password_hash", "")
                if username.lower() == "admin" and verify_password(password, stored):
                    token = new_session("admin", "admin")
                    data = json.dumps({"ok": True, "app_name": APP_NAME, "version":"8.4", "username":"admin", "role":"admin"}).encode("utf-8")
                    self._send(200, data, "application/json; charset=utf-8", {"Set-Cookie": f"cmp_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={SESSION_TTL_SECONDS}"})
                    return
                return self.send_json({"ok": False, "error":"bad_password"}, 403)
            if path in ("/api/heartbeat", "/heartbeat", "/submit"):
                return self.send_json(upsert_heartbeat(body, self.client_address[0]))
            if not self.require_auth(path, "POST"):
                return
            if path == "/api/auth/logout":
                cookies = parse_cookies(self.headers.get("Cookie", "")); SESSIONS.pop(cookies.get("cmp_session", ""), None)
                return self._send(200, b'{"ok": true}', "application/json; charset=utf-8", {"Set-Cookie":"cmp_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"})
            if path == "/api/auth/change-password":
                oldp = clean_str(body.get("old_password")); newp = clean_str(body.get("new_password"))
                if len(newp) < 8:
                    return self.send_json({"ok": False, "error":"Password must be at least 8 characters"}, 400)
                stored = get_settings().get("admin_password_hash", "")
                if not verify_password(oldp, stored):
                    return self.send_json({"ok": False, "error":"Old password wrong"}, 403)
                new_hash = hash_password(newp)
                set_settings({"admin_password_hash": new_hash})
                with DB_LOCK, db_connect() as con:
                    con.execute("UPDATE users SET password_hash=?, updated_at=? WHERE username=?", (new_hash, now_iso(), self.current_username() or 'admin'))
                    if (self.current_username() or 'admin').lower() == 'admin':
                        con.execute("UPDATE users SET password_hash=?, updated_at=? WHERE username='admin'", (new_hash, now_iso()))
                    con.commit()
                return self.send_json({"ok": True})
            if path == "/api/settings":
                if not self.require_admin(): return
                set_settings(body)
                return self.send_json({"ok": True, "settings": public_settings()})
            if path == "/api/users":
                if not self.require_admin(): return
                return self.send_json(upsert_user(clean_str(body.get("username")), clean_str(body.get("password")), clean_str(body.get("role") or "viewer"), body.get("enabled", True) not in (False, 0, "0", "false", "False")))
            if path == "/api/notifications/rule":
                if not self.require_admin(): return
                rid = clean_str(body.get("id")) or ("rule_" + str(int(time.time()*1000)))
                name = clean_str(body.get("name")) or rid
                metric = clean_str(body.get("metric")) or "cpu_percent"
                op = clean_str(body.get("op")) or ">="
                threshold = to_float(body.get("threshold"), 0) or 0
                enabled = 1 if body.get("enabled") in (True, 1, "1", "true", "True", "on") else 0
                severity = clean_str(body.get("severity")) or "warning"
                cooldown = int(to_float(body.get("cooldown_minutes"), 15) or 15)
                with DB_LOCK, db_connect() as con:
                    con.execute("""INSERT OR REPLACE INTO notification_rules(id,name,metric,op,threshold,enabled,severity,cooldown_minutes)
                        VALUES(?,?,?,?,?,?,?,?)""", (rid,name,metric,op,threshold,enabled,severity,cooldown))
                    con.commit()
                return self.send_json({"ok": True, "rules": rules_list()})
            if path == "/api/messages":
                if not self.require_admin(): return
                return self.send_json(create_client_message(clean_str(body.get("target_machine_id")), clean_str(body.get("target_hostname")), clean_str(body.get("title") or "Admin message"), clean_str(body.get("message")), clean_str(body.get("priority") or "normal")))
            if path == "/api/notifications/test":
                if not self.require_admin(): return
                message = clean_str(body.get("message")) or "Test notification from Commercial Monitor Pro"
                with DB_LOCK, db_connect() as con:
                    record_notification(con, "info", "SERVER", "SERVER", "Test notification", message, "test")
                    con.commit()
                return self.send_json({"ok": True})
            if path == "/api/notifications/clear":
                if not self.require_admin(): return
                with DB_LOCK, db_connect() as con:
                    con.execute("DELETE FROM notifications")
                    con.commit()
                return self.send_json({"ok": True})
            return self.send_json({"error":"not found"}, 404)
        except Exception as e:
            log(traceback.format_exc())
            return self.send_json({"error": str(e)}, 500)

    def do_DELETE(self) -> None:
        try:
            path = self.path.split("?",1)[0]
            from urllib.parse import parse_qs
            qs = parse_qs(self.path.split("?",1)[1]) if "?" in self.path else {}
            if not self.require_auth(path, "DELETE"):
                return
            if path == "/api/notifications/rule":
                if not self.require_admin(): return
                rid = (qs.get("id") or [""])[0]
                if rid:
                    with DB_LOCK, db_connect() as con:
                        con.execute("DELETE FROM notification_rules WHERE id=?", (rid,))
                        con.commit()
                return self.send_json({"ok": True, "rules": rules_list()})
            if path == "/api/users":
                if not self.require_admin(): return
                username = (qs.get("username") or [""])[0]
                return self.send_json(delete_user(username))
            return self.send_json({"error":"not found"}, 404)
        except Exception as e:
            return self.send_json({"error": str(e)}, 500)



# ================= REAL FINAL HW INVENTORY START =================
import json as _hwi_json
import csv as _hwi_csv
import io as _hwi_io
import hashlib as _hwi_hash
import urllib.parse as _hwi_url
import re as _hwi_re
from pathlib import Path as _hwi_Path
from collections import Counter as _hwi_Counter

_HWI_BASE = _hwi_Path(BASE_DIR) if "BASE_DIR" in globals() else _hwi_Path(__file__).resolve().parent
_HWI_FILE = _HWI_BASE / "data" / "fresh_hw_inventory_v2.json"

_HWI_COLS = [
    "asset_uid","asset_code","make_name","model_name","asset_name","asset_type",
    "configuration_details","quantity","rate","vendor_name","warranty_end_date",
    "warranty_end_year","purchase_date","po_invoice_bill_no","po_invoice_bill_path",
    "tagname_hostname","serial_number","assigned_to","asset_location","status",
    "remarks","source_sheet","source_row","live_sync_status","live_hostname",
    "live_machine_id","live_ip","live_online","live_last_seen"
]

def _hwi_s(v):
    return "" if v is None else str(v).strip()

def _hwi_uid(r):
    base = _hwi_s(r.get("asset_uid") or r.get("asset_code") or r.get("serial_number") or r.get("tagname_hostname"))
    if base:
        return base
    raw = _hwi_json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)
    return "HW-" + _hwi_hash.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()

def _hwi_norm(r):
    x = dict(r or {})
    alias = {
        "Code":"asset_code",
        "Name":"asset_name",
        "AssetType":"asset_type",
        "Details":"configuration_details",
        "Quantity":"quantity",
        "Rate":"rate",
        "WarrantyDate":"warranty_end_date",
        "PurchaseDate":"purchase_date",
        "SerialNumber":"serial_number",
        "VendorName":"vendor_name",
        "Vendor Name":"vendor_name",
        "Make Name":"make_name",
        "Model Name":"model_name",
        "PO / Invoice / Bill No":"po_invoice_bill_no",
        "PO / Invoice / Bill Path":"po_invoice_bill_path",
        "Tagname / Hostname":"tagname_hostname",
        "Assigned To":"assigned_to",
        "Location":"asset_location",
        "Status":"status",
        "Remarks":"remarks"
    }
    for old, new in alias.items():
        if not _hwi_s(x.get(new)) and _hwi_s(x.get(old)):
            x[new] = _hwi_s(x.get(old))

    if not _hwi_s(x.get("asset_name")):
        x["asset_name"] = _hwi_s(x.get("model_name") or x.get("asset_type") or "Asset")
    if not _hwi_s(x.get("model_name")):
        x["model_name"] = _hwi_s(x.get("asset_name"))
    if not _hwi_s(x.get("asset_type")):
        x["asset_type"] = _hwi_s(x.get("category") or "Uncategorized")
    if not _hwi_s(x.get("quantity")):
        x["quantity"] = "1"
    if not _hwi_s(x.get("status")):
        x["status"] = "Review"

    if not _hwi_s(x.get("warranty_end_year")) and _hwi_s(x.get("warranty_end_date")):
        m = _hwi_re.search(r"(20\d{2}|19\d{2})", _hwi_s(x.get("warranty_end_date")))
        if m:
            x["warranty_end_year"] = m.group(1)

    x["asset_uid"] = _hwi_uid(x)
    for c in _HWI_COLS:
        x.setdefault(c, "")
    return x

def _hwi_load():
    try:
        if _HWI_FILE.exists():
            data = _hwi_json.loads(_HWI_FILE.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                return [_hwi_norm(r) for r in data if isinstance(r, dict)]
    except Exception:
        pass
    return []

def _hwi_write(rows):
    out = [_hwi_norm(r) for r in rows if isinstance(r, dict)]
    tmp = _HWI_FILE.with_suffix(".json.tmp")
    tmp.write_text(_hwi_json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(_HWI_FILE)

def _hwi_summary():
    rows = _hwi_load()
    def miss(k):
        return sum(1 for r in rows if not _hwi_s(r.get(k)))
    return {
        "ok": True,
        "imported_assets": len(rows),
        "missing_make_name": miss("make_name"),
        "missing_model_name": miss("model_name"),
        "missing_vendor_name": miss("vendor_name"),
        "missing_serial_number": miss("serial_number"),
        "missing_tagname_hostname": miss("tagname_hostname"),
        "missing_assigned_to": miss("assigned_to"),
        "missing_location": miss("asset_location"),
        "missing_po_invoice_bill_no": miss("po_invoice_bill_no"),
        "categories": dict(_hwi_Counter([_hwi_s(r.get("asset_type")) or "Uncategorized" for r in rows]).most_common(30)),
        "source_file": str(_HWI_FILE)
    }

def _hwi_filter(rows, qs):
    q = _hwi_s((qs.get("q") or [""])[0]).lower()
    if not q:
        return rows
    return [r for r in rows if q in _hwi_json.dumps(r, ensure_ascii=False, default=str).lower()]

def _hwi_csv_bytes(rows):
    fields = list(_HWI_COLS)
    for r in rows:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    buf = _hwi_io.StringIO()
    w = _hwi_csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8-sig")

def _hwi_body(self):
    n = int(self.headers.get("Content-Length") or 0)
    raw = self.rfile.read(n) if n else b"{}"
    return _hwi_json.loads(raw.decode("utf-8-sig") or "{}")

def _hwi_tokens(m):
    vals = []
    if isinstance(m, dict):
        vals += [m.get("hostname"), m.get("machine_id"), m.get("real_machine_id"), m.get("primary_ip"), m.get("public_ip")]
        p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        ident = p.get("identity") if isinstance(p.get("identity"), dict) else {}
        vals += [ident.get("serial"), ident.get("bios_serial"), ident.get("uuid"), ident.get("system_uuid"), ident.get("hostname")]
    return set([_hwi_s(v).lower() for v in vals if _hwi_s(v)])

def _hwi_sync(save=False):
    rows = _hwi_load()
    try:
        machines = load_latest()
    except Exception:
        machines = []
    machine_tokens = [(m, _hwi_tokens(m)) for m in machines]
    out = []
    matched = 0
    for r in rows:
        x = dict(r)
        keys = [_hwi_s(x.get(k)).lower() for k in ["serial_number","tagname_hostname","asset_code"] if _hwi_s(x.get(k))]
        match = None
        for m, toks in machine_tokens:
            if any(k in toks for k in keys):
                match = m
                break
        if match:
            matched += 1
            x["live_sync_status"] = "matched"
            x["live_hostname"] = _hwi_s(match.get("hostname"))
            x["live_machine_id"] = _hwi_s(match.get("machine_id"))
            x["live_ip"] = _hwi_s(match.get("primary_ip"))
            x["live_online"] = _hwi_s(match.get("online"))
            x["live_last_seen"] = _hwi_s(match.get("updated_at"))
        else:
            x["live_sync_status"] = "not_matched"
            x["live_hostname"] = ""
            x["live_machine_id"] = ""
            x["live_ip"] = ""
            x["live_online"] = ""
            x["live_last_seen"] = ""
        out.append(_hwi_norm(x))
    if save:
        _hwi_write(out)
    return out, matched

def _hwi_html():
    return '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>H/W Inventory</title>
<style>
body{margin:0;font-family:Segoe UI,Arial;background:#eef5fb;color:#0f172a}
.layout{display:flex;min-height:100vh}
.side{width:250px;background:#071426;color:#dbeafe;padding:22px 14px;box-sizing:border-box;position:sticky;top:0;height:100vh}
.logo{width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#2563eb,#14b8a6);display:grid;place-items:center;font-weight:900}
.brand{display:flex;gap:12px;align-items:center;margin-bottom:24px}
.nav a{display:block;color:#dbeafe;text-decoration:none;padding:13px 14px;border-radius:12px;font-weight:800;margin:7px 0}
.nav a.active{background:linear-gradient(135deg,#0f766e,#1d4ed8);box-shadow:inset 3px 0 #2dd4bf}
.main{flex:1;padding:24px}
.top,.panel,.card{background:white;border-radius:20px;box-shadow:0 18px 50px #1e3a8a18}
.top{padding:22px;margin-bottom:18px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:16px 0}
.card{padding:16px;border:1px solid #d9e7f7}
.k{font-size:12px;color:#64748b;font-weight:900;text-transform:uppercase}
.v{font-size:26px;font-weight:900}
.panel{padding:16px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
button,.btn{border:0;border-radius:12px;padding:11px 14px;background:#2563eb;color:white;font-weight:900;cursor:pointer;text-decoration:none}
button.alt,.btn.alt{background:#0f172a}
button.danger{background:#dc2626}
input{border:1px solid #cbd5e1;border-radius:10px;padding:10px;background:white}
.search{width:520px;max-width:95%}
.form{display:none;background:#f8fbff;border:1px solid #cfe0f5;border-radius:16px;padding:14px;margin:12px 0}
.formgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.formgrid label{font-size:12px;font-weight:900;color:#334155}
.formgrid input{width:100%;box-sizing:border-box}
.tablewrap{overflow:auto;max-height:62vh;border-radius:14px;border:1px solid #d9e7f7}
table{border-collapse:collapse;width:100%;min-width:1950px}
th,td{padding:9px;border-bottom:1px solid #e2e8f0;font-size:13px;vertical-align:top}
th{position:sticky;top:0;background:#eaf2ff;text-align:left;color:#1e3a8a}
</style>
</head>
<body>
<div class="layout">
<aside class="side">
  <div class="brand"><div class="logo">SK</div><div><b>Sagar Kerhalkar</b><br><small>System Health Monitor</small></div></div>
  <nav class="nav">
    <a href="/">Command Center</a>
    <a href="/#fleet">Machine Fleet</a>
    <a href="/#machine360">Machine 360</a>
    <a href="/#hardware">Hardware</a>
    <a href="/#software">Software</a>
    <a class="active" href="/hw-inventory-v2">H/W Inventory</a>
    <a href="/#deploy">Deploy</a>
    <a href="/#settings">Settings</a>
  </nav>
</aside>
<main class="main">
  <div class="top">
    <h1>H/W Inventory</h1>
    <div>Fresh Google Sheet inventory + editable ISO/ITAM columns + live monitor sync.</div>
  </div>
  <div class="cards" id="cards"></div>
  <div class="panel">
    <div class="toolbar">
      <input id="q" class="search" placeholder="Search code, serial, tag/hostname, make, model, vendor, location...">
      <button onclick="loadRows()">Search</button>
      <button onclick="openForm({})">Add New Asset</button>
      <button onclick="syncLive()">Sync With Live Data</button>
      <a class="btn alt" href="/api/hw-inventory-v2/export.csv">Download CSV</a>
      <a class="btn alt" href="/">Back Dashboard</a>
    </div>
    <div class="form" id="form">
      <h3 id="formTitle">Edit Asset</h3>
      <div class="formgrid" id="formgrid"></div>
      <div class="toolbar"><button onclick="saveForm()">Save</button><button class="alt" onclick="closeForm()">Cancel</button></div>
    </div>
    <div class="tablewrap">
      <table><thead><tr id="thead"></tr></thead><tbody id="tbody"></tbody></table>
    </div>
  </div>
</main>
</div>
<script>
const cols=[
['Asset UID','asset_uid'],['Asset Code','asset_code'],['Make Name','make_name'],['Model Name','model_name'],
['Asset Name','asset_name'],['Asset Type','asset_type'],['Configuration / Details','configuration_details'],
['Qty','quantity'],['Rate','rate'],['Vendor Name','vendor_name'],['Warranty End Date','warranty_end_date'],
['Warranty End Year','warranty_end_year'],['Purchase Date','purchase_date'],['PO / Invoice / Bill No','po_invoice_bill_no'],
['PO / Invoice / Bill Path','po_invoice_bill_path'],['Tagname / Hostname','tagname_hostname'],['Serial Number','serial_number'],
['Assigned To','assigned_to'],['Location','asset_location'],['Status','status'],['Remarks','remarks'],
['Live Sync Status','live_sync_status'],['Live Host','live_hostname'],['Live IP','live_ip']
];
const editCols=['asset_uid','asset_code','make_name','model_name','asset_name','asset_type','configuration_details','quantity','rate','vendor_name','warranty_end_date','warranty_end_year','purchase_date','po_invoice_bill_no','po_invoice_bill_path','tagname_hostname','serial_number','assigned_to','asset_location','status','remarks'];
let rows=[], current={};
function esc(x){return String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function api(u,o){let r=await fetch(u,o); if(!r.ok)throw new Error(await r.text()); return r.json()}
function card(k,v){return `<div class=card><div class=k>${esc(k)}</div><div class=v>${esc(v)}</div></div>`}
async function loadSummary(){let s=await api('/api/hw-inventory-v2/summary'); cards.innerHTML=card('Assets',s.imported_assets)+card('Missing Vendor',s.missing_vendor_name)+card('Missing Make',s.missing_make_name)+card('Missing Model',s.missing_model_name)+card('Missing Serial',s.missing_serial_number)+card('Missing Tag/Host',s.missing_tagname_hostname)+card('Missing Bill/PO',s.missing_po_invoice_bill_no)}
async function loadRows(){await loadSummary(); let q=encodeURIComponent(document.getElementById('q').value||''); let j=await api('/api/hw-inventory-v2/assets?q='+q); rows=j.rows||[]; thead.innerHTML='<th>Action</th>'+cols.map(c=>'<th>'+esc(c[0])+'</th>').join(''); tbody.innerHTML=rows.map((r,i)=>'<tr><td><button onclick="editRow('+i+')">Edit</button> <button class="danger" onclick="delRow('+i+')">Delete</button></td>'+cols.map(c=>'<td>'+esc(r[c[1]]||'')+'</td>').join('')+'</tr>').join('')||'<tr><td>No rows</td></tr>'}
function openForm(r){current=r||{}; form.style.display='block'; formTitle.textContent=current.asset_uid?'Edit Asset':'Add New Asset'; formgrid.innerHTML=editCols.map(k=>`<label>${esc(k.replaceAll('_',' ').toUpperCase())}<input id="f_${k}" value="${esc(current[k]||'')}"></label>`).join(''); window.scrollTo({top:0,behavior:'smooth'})}
function closeForm(){form.style.display='none';current={}}
function editRow(i){openForm(rows[i])}
async function saveForm(){let r={}; editCols.forEach(k=>r[k]=document.getElementById('f_'+k).value); await api('/api/hw-inventory-v2/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(r)}); closeForm(); await loadRows()}
async function delRow(i){if(!confirm('Delete this asset?'))return; await api('/api/hw-inventory-v2/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_uid:rows[i].asset_uid})}); await loadRows()}
async function syncLive(){let j=await api('/api/hw-inventory-v2/sync-save',{method:'POST'}); alert('Sync done. matched='+j.matched+' / rows='+j.rows); await loadRows()}
loadRows().catch(e=>{document.body.innerHTML='<pre style="padding:20px;color:red">'+esc(e.message)+'</pre>'})
</script>
</body>
</html>'''

_HWI_OLD_GET = Handler.do_GET
_HWI_OLD_POST = getattr(Handler, "do_POST", None)
_HWI_OLD_SEND = Handler._send

def _hwi_direct_send(self, status, body, content_type="application/octet-stream", headers=None):
    try:
        if isinstance(body, str):
            body = body.encode("utf-8")
        if headers is None:
            headers = {}
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
        return None

def _hwi_get(self):
    try:
        u = _hwi_url.urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        qs = _hwi_url.parse_qs(u.query)

        if path in ["/hw-inventory-v2", "/inventory-manager"]:
            return _hwi_direct_send(self, 200, _hwi_html().encode("utf-8"), "text/html; charset=utf-8")

        if path == "/api/hw-inventory-v2/summary":
            return self.send_json(_hwi_summary())

        if path == "/api/hw-inventory-v2/assets":
            rows = _hwi_filter(_hwi_load(), qs)
            return self.send_json({"ok": True, "count": len(rows), "rows": rows})

        if path == "/api/hw-inventory-v2/export.csv":
            return _hwi_direct_send(self, 200, _hwi_csv_bytes(_hwi_load()), "text/csv; charset=utf-8", {"Content-Disposition": 'attachment; filename="fresh_hw_inventory_v2.csv"'})

        return _HWI_OLD_GET(self)
    except Exception as e:
        return self.send_json({"ok": False, "error": str(e)}, 500)

def _hwi_post(self):
    try:
        u = _hwi_url.urlparse(self.path)
        path = u.path.rstrip("/") or "/"

        if path == "/api/hw-inventory-v2/save":
            body = _hwi_norm(_hwi_body(self))
            rows = _hwi_load()
            uid = _hwi_s(body.get("asset_uid"))
            out = []
            found = False
            for r in rows:
                if _hwi_s(r.get("asset_uid")) == uid:
                    out.append(body)
                    found = True
                else:
                    out.append(r)
            if not found:
                out.append(body)
            _hwi_write(out)
            return self.send_json({"ok": True, "saved": body})

        if path == "/api/hw-inventory-v2/delete":
            body = _hwi_body(self)
            uid = _hwi_s(body.get("asset_uid"))
            rows = [r for r in _hwi_load() if _hwi_s(r.get("asset_uid")) != uid]
            _hwi_write(rows)
            return self.send_json({"ok": True, "deleted": uid, "rows": len(rows)})

        if path == "/api/hw-inventory-v2/sync-save":
            rows, matched = _hwi_sync(save=True)
            return self.send_json({"ok": True, "rows": len(rows), "matched": matched})

        if _HWI_OLD_POST:
            return _HWI_OLD_POST(self)
        return self.send_json({"error": "not_found"}, 404)
    except Exception as e:
        return self.send_json({"ok": False, "error": str(e)}, 500)

def _hwi_send(self, status, body, content_type="application/octet-stream", headers=None):
    try:
        if isinstance(body, (bytes, bytearray)) and b"Sagar Kerhalkar System Monitor Tool" in body[:500000]:
            html = bytes(body).decode("utf-8", "ignore")
            js = '''
<script>
(function(){
  function removeOldModal(){
    Array.from(document.querySelectorAll('*')).forEach(function(el){
      var t=(el.textContent||'').trim();
      if(t==='Inventory / ISO' || t.indexOf('V10 Inventory / ISO Merge')>=0){
        var p=el;
        for(var i=0;i<8 && p;i++){
          var s=getComputedStyle(p);
          if(s.position==='fixed' || s.position==='absolute'){p.style.display='none';break;}
          p=p.parentElement;
        }
      }
    });
  }
  function addMenu(){
    if(document.getElementById('hwiLeftMenu')) return;
    var ref=Array.from(document.querySelectorAll('button,a,div,span')).find(x=>(x.textContent||'').trim()==='Software');
    var n=document.createElement('div');
    n.id='hwiLeftMenu';
    n.textContent='H/W Inventory';
    n.onclick=function(){location.href='/hw-inventory-v2'};
    n.style.cssText='cursor:pointer;margin:8px 0;padding:12px 14px;border-radius:12px;font-weight:900;color:#dce8ff;background:linear-gradient(135deg,#1d4ed8,#0e7490);border-left:4px solid #2dd4bf';
    if(ref && ref.parentNode){ref.parentNode.insertBefore(n,ref.nextSibling);}
  }
  function run(){removeOldModal();addMenu();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
  setInterval(removeOldModal,1200);
})();
</script>
'''
            if "hwiLeftMenu" not in html:
                html = html.replace("</body>", js + "</body>")
                body = html.encode("utf-8")
        return _hwi_direct_send(self, status, body, content_type, headers)
    except Exception:
        return _hwi_direct_send(self, status, body, content_type, headers)

Handler.do_GET = _hwi_get
Handler.do_POST = _hwi_post
Handler._send = _hwi_send
# ================= REAL FINAL HW INVENTORY END =================



# === HW_INVENTORY_PRO_UI_HOOK_START ===
try:
    import importlib.util as _hwi_spec_util
    from pathlib import Path as _hwi_pathlib
    _hwi_path = _hwi_pathlib(BASE_DIR) / "hw_inventory_pro_ui.py"
    _hwi_spec = _hwi_spec_util.spec_from_file_location("hw_inventory_pro_ui", str(_hwi_path))
    _hwi_mod = _hwi_spec_util.module_from_spec(_hwi_spec)
    _hwi_spec.loader.exec_module(_hwi_mod)
    _hwi_mod.install(Handler, BASE_DIR, load_latest)
    print("HW_INVENTORY_PRO_UI_LOADED")
except Exception as _hwi_e:
    print("HW_INVENTORY_PRO_UI_FAILED", _hwi_e)
# === HW_INVENTORY_PRO_UI_HOOK_END ===



# === NATIVE_HW_SW_ISO_INVENTORY_HOOK_START ===
try:
    import importlib.util as _native_inv_util
    from pathlib import Path as _native_inv_path
    _native_inv_file = _native_inv_path(BASE_DIR) / "native_inventory_api.py"
    _native_inv_spec = _native_inv_util.spec_from_file_location("native_inventory_api", str(_native_inv_file))
    _native_inv_mod = _native_inv_util.module_from_spec(_native_inv_spec)
    _native_inv_spec.loader.exec_module(_native_inv_mod)
    _native_inv_mod.install(Handler, BASE_DIR, load_latest)
    print("NATIVE_HW_SW_ISO_INVENTORY_LOADED")
except Exception as _native_inv_e:
    print("NATIVE_HW_SW_ISO_INVENTORY_FAILED", _native_inv_e)
# === NATIVE_HW_SW_ISO_INVENTORY_HOOK_END ===



# === INVENTORY_30MIN_HOOK_START ===
try:
    import importlib.util as _inv30_util
    from pathlib import Path as _inv30_path
    _inv30_file = _inv30_path(BASE_DIR) / "inventory_30min.py"
    _inv30_spec = _inv30_util.spec_from_file_location("inventory_30min", str(_inv30_file))
    _inv30_mod = _inv30_util.module_from_spec(_inv30_spec)
    _inv30_spec.loader.exec_module(_inv30_mod)
    _inv30_mod.install(Handler, BASE_DIR, load_latest)
    print("INVENTORY_30MIN_LOADED")
except Exception as _inv30_e:
    print("INVENTORY_30MIN_FAILED", _inv30_e)
# === INVENTORY_30MIN_HOOK_END ===






















# === HISTORY_CACHE_LITE_HOOK_START ===
try:
    import importlib.util as _hcl_util
    from pathlib import Path as _hcl_path
    _hcl_file = _hcl_path(BASE_DIR) / "history_cache_lite.py"
    _hcl_spec = _hcl_util.spec_from_file_location("history_cache_lite", str(_hcl_file))
    _hcl_mod = _hcl_util.module_from_spec(_hcl_spec)
    _hcl_spec.loader.exec_module(_hcl_mod)
    _hcl_mod.install(Handler, BASE_DIR)
    print("HISTORY_CACHE_LITE_LOADED")
except Exception as _hcl_e:
    print("HISTORY_CACHE_LITE_FAILED", _hcl_e)
# === HISTORY_CACHE_LITE_HOOK_END ===



# === V10_2DAY_PHASE1_DB_API_BRIDGE_HOOK_START ===
try:
    import importlib.util as _v10final_util
    from pathlib import Path as _v10final_path
    _v10final_file = _v10final_path(BASE_DIR) / "v10_final_bridge.py"
    _v10final_spec = _v10final_util.spec_from_file_location("v10_final_bridge", str(_v10final_file))
    _v10final_mod = _v10final_util.module_from_spec(_v10final_spec)
    _v10final_spec.loader.exec_module(_v10final_mod)
    _v10final_mod.install(Handler, BASE_DIR, load_latest)
    print("V10_2DAY_PHASE1_DB_API_BRIDGE_LOADED")
except Exception as _v10final_e:
    print("V10_2DAY_PHASE1_DB_API_BRIDGE_FAILED", _v10final_e)
# === V10_2DAY_PHASE1_DB_API_BRIDGE_HOOK_END ===


# === V10_2DAY_PHASE2_CLIENT_PAYLOAD_NORMALIZER_HOOK_START ===
try:
    import importlib.util as _v10p2_util
    from pathlib import Path as _v10p2_path
    _v10p2_file = _v10p2_path(BASE_DIR) / "v10_phase2_payload_normalizer.py"
    _v10p2_spec = _v10p2_util.spec_from_file_location("v10_phase2_payload_normalizer", str(_v10p2_file))
    _v10p2_mod = _v10p2_util.module_from_spec(_v10p2_spec)
    _v10p2_spec.loader.exec_module(_v10p2_mod)
    _v10p2_mod.install(globals())
    print("V10_2DAY_PHASE2_CLIENT_PAYLOAD_NORMALIZER_LOADED")
except Exception as _v10p2_e:
    print("V10_2DAY_PHASE2_CLIENT_PAYLOAD_NORMALIZER_FAILED", _v10p2_e)
# === V10_2DAY_PHASE2_CLIENT_PAYLOAD_NORMALIZER_HOOK_END ===


# === V10_PHASE3_FIX4_FULL_TAB_REQUIREMENTS_LIVE_HOOK_START ===
try:
    import importlib.util as _v10fix3_util
    from pathlib import Path as _v10fix3_path
    _v10fix3_file = _v10fix3_path(BASE_DIR) / "v10_phase3_fix4_extra_api.py"
    _v10fix3_spec = _v10fix3_util.spec_from_file_location("v10_phase3_fix4_extra_api", str(_v10fix3_file))
    _v10fix3_mod = _v10fix3_util.module_from_spec(_v10fix3_spec)
    _v10fix3_spec.loader.exec_module(_v10fix3_mod)
    _v10fix3_mod.install(Handler, BASE_DIR, load_latest)
    print("V10_PHASE3_FIX4_FULL_TAB_REQUIREMENTS_LIVE_LOADED")
except Exception as _v10fix3_e:
    print("V10_PHASE3_FIX4_FULL_TAB_REQUIREMENTS_LIVE_FAILED", _v10fix3_e)
# === V10_PHASE3_FIX4_FULL_TAB_REQUIREMENTS_LIVE_HOOK_END ===


# === V10_PHASE3_FIX5_MACHINES_API_GITHUB_VERIFY_HOOK_START ===
try:
    import importlib.util as _v10fix5_util
    from pathlib import Path as _v10fix5_path
    _v10fix5_file = _v10fix5_path(BASE_DIR) / "v10_phase3_fix5_machines_api.py"
    _v10fix5_spec = _v10fix5_util.spec_from_file_location("v10_phase3_fix5_machines_api", str(_v10fix5_file))
    _v10fix5_mod = _v10fix5_util.module_from_spec(_v10fix5_spec)
    _v10fix5_spec.loader.exec_module(_v10fix5_mod)
    _v10fix5_mod.install(Handler, BASE_DIR, load_latest)
    print("V10_PHASE3_FIX5_MACHINES_API_GITHUB_VERIFY_LOADED")
except Exception as _v10fix5_e:
    print("V10_PHASE3_FIX5_MACHINES_API_GITHUB_VERIFY_FAILED", _v10fix5_e)
# === V10_PHASE3_FIX5_MACHINES_API_GITHUB_VERIFY_HOOK_END ===

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=2294)
    args = parser.parse_args()
    print("V10 identity-core read-only mode: init_db skipped; live DB not modified")
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"{APP_NAME} running: http://{args.host}:{args.port}")
    print("Default admin password: " + DEFAULT_ADMIN_PASSWORD + "  (change it from UI after login)")
    print(f"Open dashboard from server: http://localhost:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")

if __name__ == "__main__":
    main()



# === NEXTTOPPERS_FULL_UI_ONESHOT_SOURCE_LOCK ===
# UI is rebuilt as a full Next Toppers one-shot responsive command center. Main 2278 must remain untouched.


# === V10_NEXTTOPPERS_UI_FIX2_REALDATA_SOURCE_LOCK ===
# UI Fix2: readability, deploy center, active notifications, settings retention days. Main 2278 untouched.




