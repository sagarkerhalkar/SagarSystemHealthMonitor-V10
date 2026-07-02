import argparse, csv, json, re, sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

BAD_LITERAL = {
    "", "none", "null", "unknown", "n/a", "na", "not available", "not specified",
    "to be filled by o.e.m", "to be filled by o.e.m.", "to be filled by oem",
    "default string", "system serial number", "chassis serial number", "base board serial number",
    "serial number", "0", "00000000", "0000000000", "ffffffff", "ffffffff-ffff-ffff-ffff-ffffffffffff",
    "03000200-0400-0500-0006-000700080009", "12345678-1234-5678-90ab-cddeefaabbcc",
    "bss-0123456789",
}
BAD_UUIDS = {
    "03000200-0400-0500-0006-000700080009",
    "12345678-1234-5678-90ab-cddeefaabbcc",
    "58006b9c-32d2-0000-0000-000000000000",
    "58006b9c-add2-0000-0000-000000000000",
    "58006b9c-b0d2-0000-0000-000000000000",
    "58006b9c-59d1-0000-0000-000000000000",
}
BAD_MAC_PREFIXES = ("00:FF:", "00:15:5D:", "0A:00:27:", "02:")
BAD_HOSTS = {"", "unknown", "unknown-host", "localhost", "desktop", "windows"}

MAC_RE = re.compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def clean(v):
    if v is None:
        return ""
    s = str(v).strip().strip("\x00")
    if not s:
        return ""
    return s


def norm(s):
    return clean(s).lower()


def is_bad_value(s):
    n = norm(s).strip(" .")
    return n in BAD_LITERAL


def is_bad_serial(s):
    n = norm(s).strip(" .")
    if n in BAD_LITERAL:
        return True
    if len(n) < 5:
        return True
    return False


def is_bad_uuid(s):
    n = norm(s)
    if n in BAD_UUIDS or n in BAD_LITERAL:
        return True
    if len(n) < 8:
        return True
    return False


def norm_mac(s):
    m = clean(s).upper().replace("-", ":")
    return m


def is_good_mac(s):
    m = norm_mac(s)
    if not MAC_RE.fullmatch(m):
        return False
    if m in {"00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"}:
        return False
    if any(m.startswith(p) for p in BAD_MAC_PREFIXES):
        return False
    return True


def is_good_host(s):
    h = norm(s)
    return h not in BAD_HOSTS and len(h) >= 3


def parse_json(s):
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            yield p, v
            yield from walk(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


def collect_path_values(payload, words, limit=20):
    vals = []
    for p, v in walk(payload):
        lp = p.lower()
        if any(w in lp for w in words) and isinstance(v, (str, int, float)):
            c = clean(v)
            if c and c not in vals:
                vals.append(c)
    return vals[:limit]


def collect_macs(payload):
    vals = []
    for p, v in walk(payload):
        if isinstance(v, str):
            lp = p.lower()
            if "mac" in lp or "adapter" in lp or "network" in lp:
                for m in MAC_RE.findall(v):
                    mm = norm_mac(m)
                    if is_good_mac(mm) and mm not in vals:
                        vals.append(mm)
            elif "mac" in lp:
                mm = norm_mac(v)
                if is_good_mac(mm) and mm not in vals:
                    vals.append(mm)
    return vals[:20]


def collect_ips(payload):
    vals = []
    for p, v in walk(payload):
        if isinstance(v, str) and any(w in p.lower() for w in ["ip", "address", "network", "adapter", "wan", "lan"]):
            for m in IP_RE.findall(v):
                parts = m.split('.')
                if any(int(x) > 255 for x in parts):
                    continue
                if m.startswith("127.") or m.startswith("0."):
                    continue
                if m not in vals:
                    vals.append(m)
    return vals[:20]


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def get_field(summary, payload, *names):
    # first shallow summary keys, then deep payload keys by exact/suffix match
    for n in names:
        if isinstance(summary, dict) and summary.get(n) not in (None, ""):
            return summary.get(n)
    lower_names = [n.lower() for n in names]
    for p, v in walk(payload):
        lp = p.lower().split('.')[-1]
        if lp in lower_names and isinstance(v, (str, int, float, bool)):
            return v
    return None


def number(v, default=None):
    try:
        if v is None or v == "": return default
        return float(v)
    except Exception:
        return default


class DSU:
    def __init__(self):
        self.parent = {}
    def find(self, x):
        self.parent.setdefault(x, x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def build_registry(db_path, app_path, online_minutes=2):
    con = sqlite3.connect("file:" + str(db_path).replace("\\", "/") + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT machine_id, hostname, updated_at, summary_json, payload_json
        FROM latest
        ORDER BY updated_at DESC
    """).fetchall()

    parsed = []
    serial_freq = Counter()
    uuid_freq = Counter()

    for r in rows:
        payload = parse_json(r["payload_json"])
        summary = parse_json(r["summary_json"])
        hostname = clean(r["hostname"]) or clean(summary.get("hostname")) or clean(payload.get("hostname"))
        machine_id = clean(r["machine_id"])
        updated_at = clean(r["updated_at"])
        serials_raw = collect_path_values(payload, ["serial"], 30)
        uuids_raw = collect_path_values(payload, ["uuid", "guid"], 30)
        serials = []
        for s in serials_raw:
            for part in re.split(r"[|,;]", str(s)):
                c = clean(part).upper()
                if c and not is_bad_serial(c) and c not in serials:
                    serials.append(c)
                    serial_freq[c] += 1
        uuids = []
        for u in uuids_raw:
            for part in re.split(r"[|,;]", str(u)):
                c = clean(part).lower()
                if c and not is_bad_uuid(c) and c not in uuids:
                    uuids.append(c)
                    uuid_freq[c] += 1
        parsed.append({
            "row": r, "payload": payload, "summary": summary,
            "machine_id": machine_id, "hostname": hostname, "updated_at": updated_at,
            "serials_pre": serials, "uuids_pre": uuids,
            "macs": collect_macs(payload),
            "ips": collect_ips(payload),
        })

    dsu = DSU()
    row_tokens = []
    for i, it in enumerate(parsed):
        tokens = []
        real_serials = [s for s in it["serials_pre"] if serial_freq[s] == 1]
        real_uuids = [u for u in it["uuids_pre"] if uuid_freq[u] == 1]
        it["serials"] = real_serials
        it["uuids"] = real_uuids
        for s in real_serials:
            tokens.append("SERIAL:" + s)
        for u in real_uuids:
            tokens.append("UUID:" + u)
        for m in it["macs"]:
            tokens.append("MAC:" + m)
        if is_good_host(it["hostname"]):
            tokens.append("HOST:" + norm(it["hostname"]))
        if not tokens:
            tokens.append("MID:" + norm(it["machine_id"]))
        root = "ROW:" + str(i)
        dsu.find(root)
        for t in tokens:
            dsu.union(root, t)
        row_tokens.append((root, tokens))

    groups = defaultdict(list)
    for i, (root, tokens) in enumerate(row_tokens):
        comp = dsu.find(root)
        groups[comp].append((i, tokens))

    datetimes = [parse_dt(it["updated_at"]) for it in parsed if parse_dt(it["updated_at"])]
    ref_time = max(datetimes) if datetimes else datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)
    online_delta = timedelta(minutes=online_minutes)

    registry = []
    duplicate_groups = []
    for comp, members in groups.items():
        members_sorted = sorted(members, key=lambda mt: parse_dt(parsed[mt[0]]["updated_at"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        latest_idx, latest_tokens = members_sorted[0]
        latest = parsed[latest_idx]
        last_dt = parse_dt(latest["updated_at"])
        if last_dt and last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        online = bool(last_dt and (ref_time - last_dt) <= online_delta)

        all_machine_ids, all_hosts, all_serials, all_uuids, all_macs, all_ips = [], [], [], [], [], []
        for idx, toks in members_sorted:
            it = parsed[idx]
            for arr, vals in [
                (all_machine_ids, [it["machine_id"]]), (all_hosts, [it["hostname"]]),
                (all_serials, it.get("serials", [])), (all_uuids, it.get("uuids", [])),
                (all_macs, it.get("macs", [])), (all_ips, it.get("ips", [])),
            ]:
                for v in vals:
                    c = clean(v)
                    if c and c not in arr:
                        arr.append(c)

        if all_serials:
            real_id = "SERIAL:" + all_serials[0]
            source = "serial"
        elif all_uuids:
            real_id = "UUID:" + all_uuids[0]
            source = "uuid"
        elif all_macs:
            real_id = "MAC:" + all_macs[0]
            source = "mac"
        elif all_hosts:
            real_id = "HOST:" + norm(all_hosts[0])
            source = "hostname"
        else:
            real_id = "MID:" + norm(all_machine_ids[0] if all_machine_ids else comp)
            source = "machine_id"

        summary = latest["summary"]
        payload = latest["payload"]
        cpu = number(get_field(summary, payload, "cpu_percent", "cpu_usage", "cpu"), 0)
        ram = number(get_field(summary, payload, "ram_percent", "memory_percent", "memory_usage"), 0)
        disk = number(get_field(summary, payload, "disk_max_percent", "disk_percent", "storage_percent"), 0)
        attention_reasons = []
        if cpu is not None and cpu >= 90: attention_reasons.append("cpu_high")
        if ram is not None and ram >= 90: attention_reasons.append("ram_high")
        if disk is not None and disk >= 90: attention_reasons.append("disk_high")

        item = {
            "real_machine_id": real_id,
            "identity_source": source,
            "display_name": latest["hostname"] or (all_hosts[0] if all_hosts else real_id),
            "current_machine_id": latest["machine_id"],
            "last_seen": latest["updated_at"],
            "online": online,
            "attention": bool(attention_reasons),
            "attention_reasons": attention_reasons,
            "rows_merged": len(members),
            "hostnames_seen": all_hosts,
            "machine_ids_seen": all_machine_ids,
            "serials_seen": all_serials,
            "uuids_seen": all_uuids,
            "macs_seen": all_macs,
            "ips_seen": all_ips[:20],
            "os": get_field(summary, payload, "os", "platform"),
            "cpu_percent": cpu,
            "ram_percent": ram,
            "disk_max_percent": disk,
            "software_count": get_field(summary, payload, "software_count", "installed_count"),
            "gpu_count": get_field(summary, payload, "gpu_count"),
            "usb_count": get_field(summary, payload, "usb_count"),
        }
        registry.append(item)
        if len(members) > 1:
            duplicate_groups.append(item)

    registry.sort(key=lambda x: (not x["online"], str(x["display_name"]).lower()))
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reference_time": ref_time.isoformat(timespec="seconds"),
        "online_timeout_minutes": online_minutes,
        "raw_latest_rows": len(rows),
        "real_machine_count": len(registry),
        "online_count": sum(1 for r in registry if r["online"]),
        "offline_count": sum(1 for r in registry if not r["online"]),
        "attention_count": sum(1 for r in registry if r["attention"]),
        "duplicate_groups": len(duplicate_groups),
        "ignored_identity_values": sorted(BAD_LITERAL | BAD_UUIDS),
        "rule": "Ignore fake UUID/serial values; merge by unique serial/uuid, physical MAC, then hostname fallback; keep all known real clients; online/offline from latest heartbeat.",
    }
    out = {"summary": summary, "machines": registry, "duplicate_groups": duplicate_groups}

    app = Path(app_path)
    data_dir = app / "data"
    public_dir = app / "public"
    data_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "machine_registry.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (public_dir / "v10_machine_registry.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    csv_fields = ["real_machine_id", "identity_source", "display_name", "current_machine_id", "last_seen", "online", "attention", "rows_merged", "hostnames_seen", "machine_ids_seen", "serials_seen", "uuids_seen", "macs_seen", "ips_seen", "cpu_percent", "ram_percent", "disk_max_percent", "software_count", "gpu_count", "usb_count"]
    for path in [data_dir / "machine_registry.csv", public_dir / "v10_machine_registry.csv"]:
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=csv_fields)
            w.writeheader()
            for r in registry:
                row = {k: r.get(k, "") for k in csv_fields}
                for k in ["hostnames_seen", "machine_ids_seen", "serials_seen", "uuids_seen", "macs_seen", "ips_seen"]:
                    row[k] = " | ".join(row[k] or [])
                w.writerow(row)

    print("V10 MACHINE REGISTRY BUILT")
    print("raw_latest_rows=", summary["raw_latest_rows"])
    print("real_machine_count=", summary["real_machine_count"])
    print("online_count=", summary["online_count"])
    print("offline_count=", summary["offline_count"])
    print("attention_count=", summary["attention_count"])
    print("duplicate_groups=", summary["duplicate_groups"])
    print("json=", data_dir / "machine_registry.json")
    print("csv=", data_dir / "machine_registry.csv")
    print("viewer=", public_dir / "v10-machine-registry.html")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--app", required=True)
    ap.add_argument("--online-minutes", type=int, default=2)
    args = ap.parse_args()
    build_registry(args.db, args.app, args.online_minutes)
