from pathlib import Path
import re

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_TRUSTED_V8_GPU_BASELINE_2294.py")
code = server.read_text(encoding="utf-8")

if "def load_latest_raw()" not in code:
    code = code.replace("def load_latest() -> List[Dict[str, Any]]:", "def load_latest_raw() -> List[Dict[str, Any]]:", 1)

helper = r'''

# V10 REAL BACKEND MACHINE REGISTRY / DEDUP
# This is backend data logic, not UI painting.
# One physical machine = one record.
# Hostname change merges by serial/MAC/fingerprint.
# UNKNOWN-HOST without serial/MAC is ignored as ghost.

V10_BAD_ID_VALUES = {
    "", "none", "null", "unknown", "unknown-host", "localhost",
    "na", "n/a", "not available", "default string",
    "to be filled by o.e.m", "to be filled by o.e.m.",
    "to be filled by oem", "system serial number",
    "base board serial number", "chassis serial number",
    "0", "00000000", "000000000000",
    "ffffffff", "ffffffffffff",
    "00000000-0000-0000-0000-000000000000",
    "ffffffff-ffff-ffff-ffff-ffffffffffff",
    "03000200-0400-0500-0006-000700080009",
    "12345678-1234-5678-90ab-cddeefaabbcc",
    "bss-0123456789", "bss0123456789",
    "0123456789", "123456789", "1234567890"
}

def v10_clean_id(v):
    s = str(v or "").strip()
    low = s.lower().strip()
    if low in V10_BAD_ID_VALUES:
        return ""
    compact = re.sub(r"[^a-z0-9]", "", low)
    if compact in V10_BAD_ID_VALUES:
        return ""
    if re.fullmatch(r"0+", compact or "") or re.fullmatch(r"f+", compact or ""):
        return ""
    if low.startswith("to be filled") or low.startswith("default"):
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

def v10_collect_serials(payload):
    out = []
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    preferred_keys = [
        "bios_serial", "system_serial", "serial_number", "motherboard_serial",
        "baseboard_serial", "board_serial", "chassis_serial"
    ]
    for k in preferred_keys:
        s = v10_clean_id(identity.get(k) or payload.get(k))
        if s and s.upper() not in [x.upper() for x in out]:
            out.append(s)
    if not out:
        for k, v in v10_walk(payload):
            lk = k.lower()
            if "serial" in lk and not any(x in lk for x in ["disk", "drive", "volume", "usb"]):
                s = v10_clean_id(v)
                if s and s.upper() not in [x.upper() for x in out]:
                    out.append(s)
    return out[:5]

def v10_collect_uuids(payload):
    out = []
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    for k in ["system_uuid", "uuid", "machine_uuid"]:
        s = v10_clean_id(identity.get(k) or payload.get(k))
        if s and s.upper() not in [x.upper() for x in out]:
            out.append(s)
    return out[:3]

def v10_normal_mac(v):
    s = str(v or "").strip().upper()
    m = re.findall(r"[0-9A-F]{2}", s)
    if len(m) < 6:
        return ""
    mac = ":".join(m[:6])
    if mac in {"00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"}:
        return ""
    return mac

def v10_is_virtual_mac(mac, text=""):
    t = (text or "").lower()
    if mac.startswith("00:15:5D") or mac.startswith("0A:00:27") or mac.startswith("00:FF"):
        return True
    return bool(re.search(r"virtual|hyper-v|vmware|virtualbox|docker|wsl|loopback|tunnel|tap|tun|vpn", t))

def v10_collect_macs(payload):
    physical = []
    fallback = []
    net = payload.get("network") if isinstance(payload.get("network"), dict) else {}
    adapters = net.get("adapters") or payload.get("adapters") or []
    if isinstance(adapters, dict):
        adapters = list(adapters.values())
    if not isinstance(adapters, list):
        adapters = []
    for a in adapters:
        if not isinstance(a, dict):
            continue
        mac = v10_normal_mac(a.get("mac") or a.get("mac_address") or a.get("MACAddress"))
        if not mac:
            continue
        text = " ".join(str(a.get(k) or "") for k in ["name", "description", "type", "interface"])
        if v10_is_virtual_mac(mac, text):
            if mac not in fallback:
                fallback.append(mac)
        else:
            if mac not in physical:
                physical.append(mac)
    if not physical:
        for k, v in v10_walk(payload):
            if "mac" in k.lower():
                mac = v10_normal_mac(v)
                if mac and mac not in physical and mac not in fallback:
                    if v10_is_virtual_mac(mac):
                        fallback.append(mac)
                    else:
                        physical.append(mac)
    return (physical or fallback)[:8]

def v10_collect_ips(m, payload):
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

def v10_identity_key_for_machine(m):
    payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
    hostname = v10_clean_id(m.get("hostname") or payload.get("hostname") or payload.get("computer_name"))
    serials = v10_collect_serials(payload)
    macs = v10_collect_macs(payload)
    uuids = v10_collect_uuids(payload)

    if serials:
        return "serial", "SERIAL:" + serials[0].upper(), serials, macs, uuids
    if macs:
        return "mac", "MAC:" + macs[0].upper(), serials, macs, uuids
    if uuids:
        return "uuid", "UUID:" + uuids[0].upper(), serials, macs, uuids
    if hostname:
        return "hostname", "HOST:" + hostname.upper(), serials, macs, uuids
    return "ghost", "", serials, macs, uuids

def v10_merge_unique_list(target, values):
    if not isinstance(values, list):
        values = [values] if values else []
    for v in values:
        s = str(v or "").strip()
        if s and s not in target:
            target.append(s)

def load_latest() -> List[Dict[str, Any]]:
    raw = load_latest_raw()
    groups = {}

    for m in raw:
        source, key, serials, macs, uuids = v10_identity_key_for_machine(m)
        if source == "ghost" or not key:
            continue

        payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        hostname = str(m.get("hostname") or payload.get("hostname") or "").strip()

        if key not in groups:
            g = dict(m)
            g["real_machine_id"] = key
            g["identity_source"] = source
            g["rows_merged"] = 0
            g["hostnames_seen"] = []
            g["machine_ids_seen"] = []
            g["serials_seen"] = []
            g["macs_seen"] = []
            g["uuids_seen"] = []
            g["ips_seen"] = []
            groups[key] = g

        g = groups[key]
        g["rows_merged"] = int(g.get("rows_merged") or 0) + 1

        v10_merge_unique_list(g["hostnames_seen"], hostname)
        v10_merge_unique_list(g["machine_ids_seen"], m.get("machine_id"))
        v10_merge_unique_list(g["serials_seen"], serials)
        v10_merge_unique_list(g["macs_seen"], macs)
        v10_merge_unique_list(g["uuids_seen"], uuids)
        v10_merge_unique_list(g["ips_seen"], v10_collect_ips(m, payload))

        # raw is already sorted latest first, so first row remains live current row.
        # Only enrich it with registry metadata.

    machines = list(groups.values())
    machines.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return machines

'''

if "V10 REAL BACKEND MACHINE REGISTRY / DEDUP" not in code:
    code = code.replace("\ndef overview() -> Dict[str, Any]:", helper + "\n\ndef overview() -> Dict[str, Any]:", 1)

server.write_text(code, encoding="utf-8")
print("Backend dedup patch inserted")
