from pathlib import Path

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

start_marker = "# ================= V10 GPU BACKEND NORMALIZER ================="
end_marker = "# ================= END V10 GPU BACKEND NORMALIZER ================="

helper = r'''
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
'''

start = code.find(start_marker)
if start >= 0:
    end = code.find(end_marker, start)
    if end < 0:
        raise SystemExit("GPU end marker not found")
    end = end + len(end_marker)
    code = code[:start] + helper + code[end:]
else:
    marker = "# ================= END V10 IDENTITY CORE BACKEND FIX ================="
    if marker not in code:
        raise SystemExit("Identity core marker not found")
    code = code.replace(marker, helper + "\n" + marker, 1)

if "m = v10_normalize_gpus_in_machine(m)" not in code:
    if "m = v10_normalize_storage_in_machine(m)\n        raw[idx] = m" in code:
        code = code.replace(
            "m = v10_normalize_storage_in_machine(m)\n        raw[idx] = m",
            "m = v10_normalize_storage_in_machine(m)\n        m = v10_normalize_gpus_in_machine(m)\n        raw[idx] = m",
            1
        )
    else:
        code = code.replace(
            "tokens, serials, macs, uuids, hostname = v10_machine_tokens(m)",
            "m = v10_normalize_gpus_in_machine(m)\n        raw[idx] = m\n        tokens, serials, macs, uuids, hostname = v10_machine_tokens(m)",
            1
        )

server.write_text(code, encoding="utf-8")
print("GPU truth mapping patched")