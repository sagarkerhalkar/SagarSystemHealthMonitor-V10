from pathlib import Path
import re

V10 = Path(r"D:\SagarMonitor_V10_CleanBuild")
server = V10 / "V10_IDENTITY_CORE_2294.py"
live_db = r"D:\SagarSystemHealthMonitor\data\monitor.db"

code = server.read_text(encoding="utf-8")

code = code.replace(
    'DB_PATH = DATA_DIR / "monitor.db"',
    f'DB_PATH = Path(r"{live_db}")'
)

code = code.replace(
    'conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)',
    'conn = sqlite3.connect("file:" + str(DB_PATH).replace("\\\\", "/") + "?mode=ro", uri=True, timeout=30, check_same_thread=False)'
)

code = code.replace(
    'parser.add_argument("--port", type=int, default=2278)',
    'parser.add_argument("--port", type=int, default=2294)'
)

code = re.sub(
    r'(?m)^    init_db\(\)\s*$',
    '    print("V10 identity-core read-only mode: init_db skipped; live DB not modified")',
    code,
    count=1
)

code = code.replace(
    '    check_offline_notifications()\n',
    '    # V10 read-only mode: skip DB-writing offline notification check\n',
    1
)

if "def load_latest_raw()" not in code:
    code = code.replace(
        "def load_latest() -> List[Dict[str, Any]]:",
        "def load_latest_raw() -> List[Dict[str, Any]]:",
        1
    )

identity_core = r'''

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

# ================= END V10 IDENTITY CORE BACKEND FIX =================
'''

if "V10 IDENTITY CORE BACKEND FIX" not in code:
    code = code.replace("\ndef overview() -> Dict[str, Any]:", identity_core + "\n\ndef overview() -> Dict[str, Any]:", 1)

server.write_text(code, encoding="utf-8")
print("V10 identity core backend patch done")
