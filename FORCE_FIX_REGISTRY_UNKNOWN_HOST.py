import json, csv
from pathlib import Path
from datetime import datetime, timezone

APP = Path(r"D:\SagarMonitor_V10_CleanBuild")

json_paths = [
    APP / "data" / "machine_registry.json",
    APP / "public" / "v10_machine_registry.json",
]

def bad(v):
    return str(v or "").strip().lower()

def is_unknown_ghost(m):
    text = " ".join([
        bad(m.get("real_machine_id")),
        bad(m.get("display_name")),
        bad(m.get("current_machine_id")),
        " ".join(bad(x) for x in (m.get("hostnames_seen") or [])),
        " ".join(bad(x) for x in (m.get("machine_ids_seen") or [])),
    ])
    serials = m.get("serials_seen") or []
    macs = m.get("macs_seen") or []
    if "unknown-host" in text and not serials and not macs:
        return True
    if bad(m.get("real_machine_id")) in ("mid:hostname:unknown-host", "hostname:unknown-host"):
        return True
    return False

main = APP / "data" / "machine_registry.json"
data = json.loads(main.read_text(encoding="utf-8"))

machines = data.get("machines") or []
before = len(machines)
machines = [m for m in machines if not is_unknown_ghost(m)]
after = len(machines)

data["machines"] = machines
data.setdefault("summary", {})
data["summary"]["raw_latest_rows"] = int(data["summary"].get("raw_latest_rows") or 64)
data["summary"]["real_machine_count"] = after
data["summary"]["total"] = after
data["summary"]["online_count"] = sum(1 for m in machines if m.get("online"))
data["summary"]["online"] = data["summary"]["online_count"]
data["summary"]["offline_count"] = after - data["summary"]["online_count"]
data["summary"]["offline"] = data["summary"]["offline_count"]
data["summary"]["attention_count"] = sum(1 for m in machines if m.get("attention"))
data["summary"]["attention"] = data["summary"]["attention_count"]
data["summary"]["critical"] = data["summary"]["attention_count"]
data["summary"]["ghost_removed"] = before - after
data["summary"]["fixed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
data["summary"]["rule"] = "UNKNOWN-HOST without serial/MAC is ghost and must not count."

for p in json_paths:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

csv_paths = [
    APP / "data" / "machine_registry.csv",
    APP / "public" / "v10_machine_registry.csv",
]

fields = [
    "display_name","current_machine_id","real_machine_id","online","attention",
    "identity_source","rows_merged","last_seen",
    "hostnames_seen","machine_ids_seen","serials_seen","macs_seen","ips_seen"
]

for csv_path in csv_paths:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for m in machines:
            row = {}
            for k in fields:
                v = m.get(k, "")
                if isinstance(v, list):
                    v = " | ".join(str(x) for x in v)
                row[k] = v
            w.writerow(row)

print("Registry fixed")
print("before", before)
print("after", after)
print("online", data["summary"]["online_count"])
print("offline", data["summary"]["offline_count"])
print("attention", data["summary"]["attention_count"])
print("ghost_removed", data["summary"]["ghost_removed"])
