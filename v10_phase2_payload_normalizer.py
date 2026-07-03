#!/usr/bin/env python3
# V10 2-Day Phase 2 Client Payload Normalizer
# Purpose: fix client payload mapping for CPU/RAM/Disk/GPU/USB/Software/Network/VPN without touching main 2278.
from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
import traceback
import urllib.parse
from typing import Any, Dict, List, Tuple

PHASE_NAME = "V10_2DAY_PHASE2_CLIENT_PAYLOAD_NORMALIZER"
PHASE_VERSION = "2026-07-03.2"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")

def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()

def _lower(v: Any) -> str:
    return _s(v).lower()

def _float(v: Any, default: float | None = None) -> float | None:
    try:
        if v is None or v == "":
            return default
        if isinstance(v, str):
            v = v.replace('%','').replace(',','').strip()
        return float(v)
    except Exception:
        return default

def _gb(v: Any, unit_hint: str = "") -> float:
    """Convert bytes/KB/MB/GB-ish values to GB. If already small, treat as GB."""
    n = _float(v, None)
    if n is None:
        return 0.0
    u = unit_hint.lower()
    if "byte" in u or "bytes" in u:
        return round(n / (1024**3), 2)
    if "kb" in u:
        return round(n / (1024**2), 2)
    if "mb" in u:
        return round(n / 1024, 2)
    if "tb" in u:
        return round(n * 1024, 2)
    # auto detect huge byte values
    if n > 10_000_000_000:
        return round(n / (1024**3), 2)
    if n > 10_000_000:
        return round(n / (1024**2), 2)
    if n > 100_000:
        return round(n / 1024, 2)
    return round(n, 2)

def _first(*vals: Any) -> str:
    for v in vals:
        x = _s(v)
        if x:
            return x
    return ""

def _get(d: Any, *paths: str, default: Any=None) -> Any:
    if not isinstance(d, dict):
        return default
    for p in paths:
        cur = d
        ok = True
        for part in p.split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return default

def _list(v: Any) -> List[Any]:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [x for x in v if x not in (None, "")]
    if isinstance(v, tuple):
        return [x for x in v if x not in (None, "")]
    if isinstance(v, dict):
        # Object keyed by IDs or one direct object.
        direct = {"name","display_name","model","mount","device","total_gb","size_gb","version","publisher","mac","ip","ips"}
        if any(k in v for k in direct):
            return [v]
        return [x for x in v.values() if x not in (None, "")]
    if isinstance(v, str):
        t = v.strip()
        if (t.startswith('[') and t.endswith(']')) or (t.startswith('{') and t.endswith('}')):
            try:
                return _list(json.loads(t))
            except Exception:
                pass
    return [v]

def _send_json(handler: Any, obj: Any, status: int = 200) -> None:
    if hasattr(handler, 'send_json'):
        return handler.send_json(obj, status)
    body = json.dumps(obj, ensure_ascii=False, default=str).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Cache-Control', 'no-store')
    handler.end_headers()
    handler.wfile.write(body)

def _clean_app(a: Any, machine_id: str = '', hostname: str = '') -> Dict[str, Any] | None:
    if isinstance(a, str):
        name = a.strip()
        if not name:
            return None
        return {"software_name": name, "name": name, "version": "", "publisher": "", "machine_id": machine_id, "hostname": hostname, "source": "live_client"}
    if not isinstance(a, dict):
        return None
    name = _first(a.get('software_name'), a.get('name'), a.get('display_name'), a.get('DisplayName'), a.get('app_name'), a.get('package'), a.get('PackageName'))
    if not name:
        return None
    return {
        "software_name": name,
        "name": name,
        "version": _first(a.get('version'), a.get('Version'), a.get('DisplayVersion')),
        "publisher": _first(a.get('publisher'), a.get('Publisher'), a.get('vendor')),
        "install_date": _first(a.get('install_date'), a.get('InstallDate'), a.get('installDate')),
        "install_location": _first(a.get('install_location'), a.get('InstallLocation')),
        "machine_id": machine_id,
        "hostname": hostname,
        "source": _first(a.get('source'), 'live_client')
    }

def _normalize_software(payload: Dict[str, Any], machine_id: str = '', hostname: str = '') -> List[Dict[str, Any]]:
    raw = _get(payload, 'software.installed', 'software.apps', 'installed_software', 'apps', 'programs', 'packages', 'software', default=[])
    # If software is dict with installed already handled; if dict of apps, list() handles values.
    apps = []
    for a in _list(raw):
        ca = _clean_app(a, machine_id, hostname)
        if ca:
            apps.append(ca)
    # de-dupe by name/version/publisher
    seen=set(); out=[]
    for a in apps:
        key=(_lower(a.get('software_name')), _lower(a.get('version')), _lower(a.get('publisher')))
        if key in seen:
            continue
        seen.add(key); out.append(a)
    return out

def _normalize_disks(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = _get(payload, 'storage.disks', 'hardware.disks', 'disks', 'drives', 'volumes', 'disk', default=[])
    disks=[]
    for d in _list(raw):
        if isinstance(d, str):
            disks.append({"name": d[:80], "mount": "", "type": "Disk", "used_percent": 0, "status": "name_only"})
            continue
        if not isinstance(d, dict):
            continue
        name = _first(d.get('name'), d.get('model'), d.get('device'), d.get('caption'), d.get('volume_name'), d.get('mount'), d.get('drive_letter'), d.get('letter'))
        mount = _first(d.get('mount'), d.get('mountpoint'), d.get('drive'), d.get('drive_letter'), d.get('letter'))
        dtype = _first(d.get('type'), d.get('media_type'), d.get('bus_type'), d.get('kind'), 'Disk')
        total = _gb(_first(d.get('total_gb'), d.get('size_gb'), d.get('capacity_gb'), d.get('total'), d.get('size'), d.get('capacity')), _first(d.get('unit'), d.get('size_unit')))
        free = _gb(_first(d.get('free_gb'), d.get('available_gb'), d.get('free'), d.get('available')), _first(d.get('unit'), d.get('free_unit')))
        used = _gb(_first(d.get('used_gb'), d.get('used')), _first(d.get('unit'), d.get('used_unit')))
        pct = _float(_first(d.get('used_percent'), d.get('usage_percent'), d.get('percent_used'), d.get('used_pct'), d.get('usage')), None)
        if pct is None and total > 0:
            if used > 0:
                pct = (used / total) * 100.0
            elif free >= 0:
                pct = max(0.0, min(100.0, ((total - free) / total) * 100.0))
        if used <= 0 and total > 0 and free >= 0:
            used = max(0.0, total - free)
        if free <= 0 and total > 0 and used >= 0:
            free = max(0.0, total - used)
        disks.append({
            "name": name or mount or "Disk",
            "mount": mount,
            "type": dtype,
            "file_system": _first(d.get('file_system'), d.get('filesystem'), d.get('fs')),
            "total_gb": round(total,2),
            "used_gb": round(used,2),
            "free_gb": round(free,2),
            "used_percent": round(float(pct or 0),2),
            "serial": _first(d.get('serial'), d.get('serial_number')),
            "model": _first(d.get('model'), d.get('caption')),
            "status": _first(d.get('status'), 'reported')
        })
    # root-level fallback
    root_pct = _float(_first(payload.get('disk_max_percent'), payload.get('disk_percent'), payload.get('storage_percent')), None)
    if not disks and root_pct is not None:
        disks.append({"name":"Disk summary", "mount":"", "type":"Disk", "total_gb":0, "used_gb":0, "free_gb":0, "used_percent":round(root_pct,2), "status":"summary_only"})
    return disks

def _normalize_gpu(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = _get(payload, 'hardware.gpus', 'gpus', 'gpu', 'display.gpus', 'video_controllers', default=[])
    gpus=[]
    for g in _list(raw):
        if isinstance(g, str):
            name=g.strip()
            if name:
                gpus.append({"name":name, "memory_total_mb":0, "usage_percent":None, "temperature_c":None, "source":"name_only"})
            continue
        if not isinstance(g, dict):
            continue
        name = _first(g.get('name'), g.get('gpu_name'), g.get('caption'), g.get('model'), g.get('adapter_name'))
        if not name:
            continue
        mem = _float(_first(g.get('memory_total_mb'), g.get('adapter_ram_mb'), g.get('dedicated_memory_mb'), g.get('vram_mb')), 0) or 0
        # AdapterRAM often arrives bytes.
        if mem > 1000000:
            mem = round(mem / (1024*1024), 2)
        gpus.append({
            "name": name,
            "memory_total_mb": round(mem,2),
            "dedicated_memory_mb": _float(g.get('dedicated_memory_mb'), 0) or 0,
            "shared_memory_mb": _float(g.get('shared_memory_mb'), 0) or 0,
            "usage_percent": _float(_first(g.get('usage_percent'), g.get('utilization_gpu'), g.get('load_percent')), None),
            "temperature_c": _float(_first(g.get('temperature_c'), g.get('temp_c')), None),
            "driver_version": _first(g.get('driver_version'), g.get('driver')),
            "source": _first(g.get('source'), 'live_client')
        })
    return gpus

def _normalize_memory(payload: Dict[str, Any]) -> Dict[str, Any]:
    mem = _get(payload, 'hardware.memory', 'memory', 'ram', default={})
    if not isinstance(mem, dict):
        mem={}
    total = _gb(_first(mem.get('total_gb'), mem.get('total'), mem.get('total_bytes'), payload.get('ram_total_gb'), payload.get('total_ram_gb')), _first(mem.get('unit'), mem.get('total_unit')))
    used = _gb(_first(mem.get('used_gb'), mem.get('used'), mem.get('used_bytes'), payload.get('ram_used_gb')), _first(mem.get('unit'), mem.get('used_unit')))
    free = _gb(_first(mem.get('free_gb'), mem.get('available_gb'), mem.get('free'), mem.get('available'), payload.get('ram_free_gb')), _first(mem.get('unit'), mem.get('free_unit')))
    pct = _float(_first(mem.get('used_percent'), mem.get('usage_percent'), mem.get('percent'), payload.get('ram_percent')), None)
    if pct is None and total > 0:
        if used > 0:
            pct = (used/total)*100.0
        elif free >= 0:
            pct = ((total-free)/total)*100.0
    if used <= 0 and total > 0 and free >= 0:
        used = max(0.0, total-free)
    if free <= 0 and total > 0 and used >= 0:
        free = max(0.0, total-used)
    return {"total_gb":round(total,2), "used_gb":round(used,2), "free_gb":round(free,2), "used_percent":round(float(pct or 0),2)}

def _normalize_cpu(payload: Dict[str, Any]) -> Dict[str, Any]:
    cpu = _get(payload, 'hardware.cpu', 'cpu', default={})
    if not isinstance(cpu, dict):
        cpu={}
    return {
        "name": _first(cpu.get('name'), cpu.get('model'), cpu.get('processor_name'), payload.get('cpu_name')),
        "usage_percent": _float(_first(cpu.get('usage_percent'), cpu.get('percent'), cpu.get('load_percent'), payload.get('cpu_percent')), 0) or 0,
        "temperature_c": _float(_first(cpu.get('temperature_c'), cpu.get('temp_c'), payload.get('cpu_temp_c')), None),
        "cores": _float(_first(cpu.get('cores'), cpu.get('physical_cores')), None),
        "logical_processors": _float(_first(cpu.get('logical_processors'), cpu.get('threads'), cpu.get('logical_cores')), None)
    }

def _normalize_network(payload: Dict[str, Any]) -> Dict[str, Any]:
    net = _get(payload, 'network', default={})
    if not isinstance(net, dict):
        net = {}
    raw_adapters = _get(payload, 'network.adapters', 'adapters', 'interfaces', 'nics', default=[])
    adapters=[]; all_ips=[]; macs=[]
    for a in _list(raw_adapters):
        if not isinstance(a, dict):
            continue
        ips = a.get('ips') or a.get('ip_addresses') or a.get('addresses') or a.get('ip') or []
        if isinstance(ips, str):
            ips=[ips]
        ips=[_s(x) for x in ips if _s(x)]
        for ip in ips:
            if ip not in all_ips:
                all_ips.append(ip)
        mac=_first(a.get('mac'), a.get('mac_address'), a.get('physical_address'))
        if mac and mac not in macs:
            macs.append(mac)
        adapters.append({
            "name": _first(a.get('name'), a.get('description'), a.get('interface'), a.get('adapter')),
            "mac": mac,
            "ips": ips,
            "gateway": _first(a.get('gateway'), a.get('default_gateway')),
            "dns": a.get('dns') or a.get('dns_servers') or [],
            "type": _first(a.get('type'), a.get('if_type')),
            "status": _first(a.get('status'), a.get('oper_status')),
            "speed_mbps": _float(a.get('speed_mbps'), None)
        })
    primary_ip = _first(net.get('primary_ip'), payload.get('primary_ip'), all_ips[0] if all_ips else '')
    traffic = _get(payload, 'network.traffic', 'traffic', default={})
    if not isinstance(traffic, dict):
        traffic={}
    # VPN detect from explicit object or adapter names.
    vpn = _get(payload, 'network.vpn', 'vpn', default={})
    vpn_active = False; vpn_name=''
    if isinstance(vpn, dict):
        vpn_active = bool(vpn.get('active') or vpn.get('is_active') or vpn.get('connected'))
        vpn_name = _first(vpn.get('name'), vpn.get('adapter'), vpn.get('provider'))
    elif isinstance(vpn, bool):
        vpn_active = vpn
    for a in adapters:
        text=f"{a.get('name','')} {a.get('type','')}".lower()
        if re.search(r'vpn|wireguard|openvpn|tap-windows|tailscale|zerotier|anyconnect|fortinet|globalprotect|l2tp|pptp', text):
            vpn_active=True
            if not vpn_name:
                vpn_name=a.get('name','')
    return {
        "adapters": adapters,
        "primary_ip": primary_ip,
        "all_ips": all_ips,
        "macs": macs,
        "vpn": {"active": vpn_active, "name": vpn_name},
        "traffic": {
            "current_download_mbps": _float(_first(traffic.get('current_download_mbps'), net.get('current_download_mbps'), payload.get('download_mbps'), payload.get('wan_download_mbps')), 0) or 0,
            "current_upload_mbps": _float(_first(traffic.get('current_upload_mbps'), net.get('current_upload_mbps'), payload.get('upload_mbps'), payload.get('wan_upload_mbps')), 0) or 0,
            "today_download_gb": _float(_first(traffic.get('today_download_gb'), net.get('today_download_gb'), payload.get('today_download_gb')), 0) or 0,
            "today_upload_gb": _float(_first(traffic.get('today_upload_gb'), net.get('today_upload_gb'), payload.get('today_upload_gb')), 0) or 0,
            "latency_ms": _float(_first(traffic.get('latency_ms'), net.get('latency_ms'), payload.get('latency_ms')), None),
            "jitter_ms": _float(_first(traffic.get('jitter_ms'), net.get('jitter_ms'), payload.get('jitter_ms')), None),
            "packet_loss_percent": _float(_first(traffic.get('packet_loss_percent'), net.get('packet_loss_percent'), payload.get('packet_loss_percent')), None),
        },
        "public_internet": _get(payload, 'network.public_internet', 'public_internet', 'isp', default={}) if isinstance(_get(payload, 'network.public_internet', 'public_internet', 'isp', default={}), dict) else {}
    }

def normalize_payload(payload: Dict[str, Any], old_normalize=None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    p = dict(payload)
    # preserve nested existing values first
    if old_normalize:
        try:
            p = old_normalize(p)
        except Exception:
            pass
    hostname = _first(_get(p,'identity.hostname'), p.get('hostname'), p.get('computer_name'), p.get('ComputerName'))
    identity = p.get('identity') if isinstance(p.get('identity'), dict) else {}
    identity.update({
        "hostname": hostname,
        "serial": _first(identity.get('serial'), identity.get('bios_serial'), identity.get('board_serial'), p.get('serial_number'), p.get('motherboard_serial'), p.get('bios_serial')),
        "uuid": _first(identity.get('uuid'), identity.get('system_uuid'), p.get('uuid'), p.get('system_uuid')),
        "mac": _first(identity.get('mac'), p.get('mac'), p.get('mac_address'))
    })
    p['identity'] = identity
    hw = p.get('hardware') if isinstance(p.get('hardware'), dict) else {}
    hw['cpu'] = _normalize_cpu(p)
    hw['memory'] = _normalize_memory(p)
    hw['gpus'] = _normalize_gpu(p)
    p['hardware'] = hw
    p['storage'] = {"disks": _normalize_disks(p), "count": len(_normalize_disks(p))}
    # keep old USB cleaner if available; old normalize may already created usb.devices
    usb_list = _get(p, 'usb.devices', 'usb', 'peripherals', default=[])
    if old_normalize and isinstance(p.get('usb'), dict) and isinstance(p['usb'].get('devices'), list):
        usb_devices = p['usb']['devices']
    else:
        usb_devices = _list(usb_list)
    p['usb'] = {"devices": usb_devices, "count": len(usb_devices)}
    sw = _normalize_software(p, '', hostname)
    p['software'] = {"installed": sw, "count": len(sw)}
    p['network'] = _normalize_network(p)
    if 'changes' not in p or p.get('changes') is None:
        p['changes'] = []
    return p

def summarize_payload(payload: Dict[str, Any], old_summarize=None, old_normalize=None) -> Dict[str, Any]:
    p = normalize_payload(payload, old_normalize)
    summary = {}
    if old_summarize:
        try:
            summary = old_summarize(p) or {}
        except Exception:
            summary = {}
    if not isinstance(summary, dict):
        summary = {}
    hostname = _first(_get(p,'identity.hostname'), p.get('hostname'), summary.get('hostname'))
    cpu = _get(p,'hardware.cpu', default={}) or {}
    mem = _get(p,'hardware.memory', default={}) or {}
    disks = _get(p,'storage.disks', default=[]) or []
    gpus = _get(p,'hardware.gpus', default=[]) or []
    sw = _get(p,'software.installed', default=[]) or []
    usb = _get(p,'usb.devices', default=[]) or []
    net = _get(p,'network', default={}) or {}
    traffic = net.get('traffic') if isinstance(net.get('traffic'), dict) else {}
    public = net.get('public_internet') if isinstance(net.get('public_internet'), dict) else {}
    disk_max = 0.0
    disk_total = 0.0
    for d in disks:
        if isinstance(d, dict):
            disk_max = max(disk_max, _float(d.get('used_percent'), 0) or 0)
            disk_total += _float(d.get('total_gb'), 0) or 0
    gpu_names=[_s(g.get('name')) for g in gpus if isinstance(g, dict) and _s(g.get('name'))]
    gpu_mem=max([_float(g.get('memory_total_mb'),0) or 0 for g in gpus if isinstance(g,dict)] or [0])
    summary.update({
        "hostname": hostname or summary.get('hostname',''),
        "primary_ip": _first(net.get('primary_ip'), summary.get('primary_ip')),
        "all_ips": net.get('all_ips') or summary.get('all_ips') or [],
        "mac_addresses": net.get('macs') or summary.get('mac_addresses') or [],
        "cpu_name": _first(cpu.get('name'), summary.get('cpu_name'), 'Not reported'),
        "cpu_percent": _float(cpu.get('usage_percent'), _float(summary.get('cpu_percent'),0)) or 0,
        "cpu_temp_c": cpu.get('temperature_c') if cpu.get('temperature_c') is not None else summary.get('cpu_temp_c'),
        "cpu_cores": cpu.get('cores'),
        "cpu_logical_processors": cpu.get('logical_processors'),
        "ram_percent": _float(mem.get('used_percent'), _float(summary.get('ram_percent'),0)) or 0,
        "ram_total_gb": _float(mem.get('total_gb'), _float(summary.get('ram_total_gb'),0)) or 0,
        "ram_used_gb": _float(mem.get('used_gb'), _float(summary.get('ram_used_gb'),0)) or 0,
        "ram_free_gb": _float(mem.get('free_gb'), _float(summary.get('ram_free_gb'),0)) or 0,
        "disk_count": len(disks),
        "disk_total_gb": round(disk_total,2),
        "disk_max_percent": round(disk_max,2),
        "gpu_names": gpu_names,
        "gpu_count": len(gpu_names),
        "gpu_total_memory_mb": round(gpu_mem,2),
        "software_count": len(sw),
        "usb_count": len(usb),
        "adapter_count": len(net.get('adapters') or []),
        "vpn_active": bool((net.get('vpn') or {}).get('active')),
        "vpn_name": (net.get('vpn') or {}).get('name',''),
        "wan_download_mbps": _float(traffic.get('current_download_mbps'), _float(summary.get('wan_download_mbps'),0)) or 0,
        "wan_upload_mbps": _float(traffic.get('current_upload_mbps'), _float(summary.get('wan_upload_mbps'),0)) or 0,
        "today_download_gb": _float(traffic.get('today_download_gb'), _float(summary.get('today_download_gb'),0)) or 0,
        "today_upload_gb": _float(traffic.get('today_upload_gb'), _float(summary.get('today_upload_gb'),0)) or 0,
        "latency_ms": traffic.get('latency_ms'),
        "jitter_ms": traffic.get('jitter_ms'),
        "packet_loss_percent": traffic.get('packet_loss_percent'),
        "isp_name": _first(public.get('isp'), public.get('org'), summary.get('isp_name')),
        "public_ip": _first(public.get('public_ip'), public.get('ip'), public.get('query'), summary.get('public_ip')),
        "payload": p
    })
    return summary

def sample_payload() -> Dict[str, Any]:
    return {
        "hostname":"PHASE2-SELFTEST",
        "cpu":{"name":"Intel Test CPU","usage_percent":32,"cores":4,"logical_processors":8},
        "ram":{"total_gb":16,"free_gb":6,"used_percent":62.5},
        "disks":[{"name":"Samsung NVMe","mount":"C:","total_gb":512,"free_gb":128,"type":"NVMe"}],
        "gpu":[{"name":"NVIDIA Test GPU","adapter_ram_mb":4096,"usage_percent":22,"temperature_c":55}],
        "installed_software":[{"DisplayName":"Google Chrome","DisplayVersion":"1.0","Publisher":"Google"},{"name":"Python","version":"3.13"}],
        "usb":[{"name":"Logitech Mouse","class":"Mouse","device_id":"USB\\VID_046D&PID_TEST"}],
        "adapters":[{"name":"Ethernet","mac":"AA-BB-CC-DD-EE-FF","ip":"192.168.1.10","gateway":"192.168.1.1"},{"name":"WireGuard VPN","ip":"10.8.0.2"}],
        "traffic":{"current_download_mbps":12.5,"current_upload_mbps":3.2,"today_download_gb":1.1,"today_upload_gb":0.4,"latency_ms":18,"jitter_ms":2,"packet_loss_percent":0},
        "public_internet":{"isp":"SelfTest ISP","public_ip":"203.0.113.1"}
    }

def selftest(old_summarize=None, old_normalize=None) -> Dict[str, Any]:
    p = normalize_payload(sample_payload(), old_normalize)
    s = summarize_payload(p, old_summarize, old_normalize)
    checks = {
        "disk_count_ok": s.get('disk_count',0) >= 1 and s.get('disk_max_percent',0) > 0,
        "gpu_ok": s.get('gpu_count',0) >= 1 and s.get('gpu_total_memory_mb',0) >= 4096,
        "software_ok": s.get('software_count',0) >= 2,
        "usb_ok": s.get('usb_count',0) >= 1,
        "network_ok": len(s.get('all_ips') or []) >= 1,
        "vpn_ok": bool(s.get('vpn_active')),
        "ram_ok": s.get('ram_total_gb',0) >= 16 and s.get('ram_free_gb',0) > 0,
    }
    return {"ok": all(checks.values()), "phase": PHASE_NAME, "version": PHASE_VERSION, "checks": checks, "summary": s, "normalized_payload": p}

def reprocess_latest(ns: Dict[str, Any]) -> Dict[str, Any]:
    DB_PATH = ns.get('DB_PATH')
    DB_LOCK = ns.get('DB_LOCK')
    if not DB_PATH:
        return {"ok": False, "error": "DB_PATH not found"}
    old_norm = ns.get('_v10_phase2_old_normalize') or ns.get('normalize_payload_inplace')
    old_sum = ns.get('_v10_phase2_old_summarize') or ns.get('summarize_payload')
    updated=0; errors=[]
    def work(con):
        nonlocal updated, errors
        rows=con.execute('SELECT machine_id,payload_json FROM latest').fetchall()
        for r in rows:
            try:
                p=json.loads(r['payload_json'] or '{}')
                pp=normalize_payload(p, old_norm)
                ss=summarize_payload(pp, old_sum, old_norm)
                con.execute('UPDATE latest SET summary_json=?, payload_json=? WHERE machine_id=?', (json.dumps(ss, ensure_ascii=False), json.dumps(pp, ensure_ascii=False), r['machine_id']))
                updated += 1
            except Exception as e:
                errors.append(str(e)[:200])
        con.commit()
    if DB_LOCK:
        with DB_LOCK, sqlite3.connect(str(DB_PATH), timeout=30) as con:
            con.row_factory=sqlite3.Row
            work(con)
    else:
        with sqlite3.connect(str(DB_PATH), timeout=30) as con:
            con.row_factory=sqlite3.Row
            work(con)
    return {"ok": len(errors)==0, "updated_latest_rows": updated, "errors": errors[:5]}

def install(ns: Dict[str, Any]) -> Dict[str, Any]:
    old_normalize = ns.get('normalize_payload_inplace')
    old_summarize = ns.get('summarize_payload')
    ns['_v10_phase2_old_normalize'] = old_normalize
    ns['_v10_phase2_old_summarize'] = old_summarize
    def patched_normalize(payload):
        return normalize_payload(payload, old_normalize)
    def patched_summarize(payload):
        return summarize_payload(payload, old_summarize, patched_normalize)
    ns['normalize_payload_inplace'] = patched_normalize
    ns['summarize_payload'] = patched_summarize
    # expose API endpoints if Handler exists
    Handler = ns.get('Handler')
    if Handler is not None:
        old_get = Handler.do_GET
        old_post = Handler.do_POST
        def parse_qs(handler):
            raw = handler.path
            path = raw.split('?',1)[0]
            qs = urllib.parse.parse_qs(raw.split('?',1)[1]) if '?' in raw else {}
            return path, qs
        def do_GET(self):
            path, qs = parse_qs(self)
            try:
                if path == '/api/v10phase2/status':
                    return _send_json(self, {"ok": True, "phase": PHASE_NAME, "version": PHASE_VERSION, "rules": {"no_fake_gpu": True, "no_fake_disk": True, "normalizes_existing_latest": True}})
                if path == '/api/v10phase2/selftest':
                    return _send_json(self, selftest(old_summarize, patched_normalize))
                if path == '/api/v10phase2/reprocess':
                    return _send_json(self, reprocess_latest(ns))
            except Exception as e:
                return _send_json(self, {"ok": False, "error": str(e), "trace": traceback.format_exc()[-3000:]}, 500)
            return old_get(self)
        def do_POST(self):
            path, qs = parse_qs(self)
            try:
                if path == '/api/v10phase2/reprocess':
                    return _send_json(self, reprocess_latest(ns))
            except Exception as e:
                return _send_json(self, {"ok": False, "error": str(e), "trace": traceback.format_exc()[-3000:]}, 500)
            return old_post(self)
        Handler.do_GET = do_GET
        Handler.do_POST = do_POST
    rp = {"ok": True, "reprocess": None}
    try:
        rp['reprocess'] = reprocess_latest(ns)
    except Exception as e:
        rp['reprocess'] = {"ok": False, "error": str(e)}
    print(f"{PHASE_NAME}_LOADED {PHASE_VERSION}")
    return rp
