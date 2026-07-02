from pathlib import Path
import re

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

helper = r'''

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
'''

if "V10 STORAGE BACKEND NORMALIZER" not in code:
    insert_before = "# ================= END V10 IDENTITY CORE BACKEND FIX ================="
    if insert_before not in code:
        raise SystemExit("Identity core marker not found")
    code = code.replace(insert_before, helper + "\n" + insert_before, 1)

old = '''    for idx, m in enumerate(raw):
        tokens, serials, macs, uuids, hostname = v10_machine_tokens(m)
'''

new = '''    for idx, m in enumerate(raw):
        m = v10_normalize_storage_in_machine(m)
        raw[idx] = m
        tokens, serials, macs, uuids, hostname = v10_machine_tokens(m)
'''

if "m = v10_normalize_storage_in_machine(m)" not in code:
    if old not in code:
        raise SystemExit("load_latest loop marker not found")
    code = code.replace(old, new, 1)

server.write_text(code, encoding="utf-8")
print("V10 disk backend filter patch inserted")