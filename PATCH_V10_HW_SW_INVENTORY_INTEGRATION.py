from pathlib import Path

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

helper = r'''

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
'''

if "V10 INVENTORY BACKEND INTEGRATION" not in code:
    marker = "def check_offline_notifications() -> None:"
    if marker not in code:
        raise SystemExit("insert marker not found")
    code = code.replace(marker, helper + "\n" + marker, 1)

json_marker = '''            if path == "/api/machines":
                return self.send_json({"machines": load_latest()})
'''

json_routes = '''            if path == "/api/inventory/summary":
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
'''

if "/api/inventory/hardware" not in code:
    if json_marker not in code:
        raise SystemExit("json route marker not found")
    code = code.replace(json_marker, json_routes, 1)

export_marker = '''            if path.startswith("/api/export/") and not self.is_admin():
                return self.send_json({"error":"admin_required", "message":"Downloads are available only to admin users."}, 403)
'''

export_routes = '''            if path == "/api/export/inventory_hardware.csv":
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
'''

if "/api/export/inventory_hardware.csv" not in code:
    if export_marker not in code:
        raise SystemExit("export route marker not found")
    code = code.replace(export_marker, export_routes + export_marker, 1)

server.write_text(code, encoding="utf-8")
print("HW/SW inventory backend integration patched")