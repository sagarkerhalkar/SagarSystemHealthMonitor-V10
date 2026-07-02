from pathlib import Path

server = Path(r"D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py")
code = server.read_text(encoding="utf-8")

helper = r'''

# ================= V10 GPU BACKEND NORMALIZER =================
# Backend fix only. No HTML/CSS. No Ubuntu client change.
# Ubuntu/lspci rows are kept unchanged.
# NVIDIA nvidia-smi total memory is dedicated VRAM, so blank dedicated_memory_mb can be filled from memory_total_mb.
# Intel/AMD integrated usage/temp remains N/A if exact value is not present.

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

def v10_normalize_gpus_in_machine(m):
    try:
        p = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        hw = p.get("hardware") if isinstance(p.get("hardware"), dict) else {}
        gpus = v10_gpu_list(hw.get("gpus"))

        out = []
        names = []
        usage_vals = []
        temp_vals = []
        memory_vals = []

        for g in gpus:
            if not isinstance(g, dict):
                continue

            ng = dict(g)
            name = str(ng.get("name") or ng.get("gpu_name") or "").strip()
            source = str(ng.get("source") or "").strip()
            low = name.lower()
            src_low = source.lower()

            # Do not change Ubuntu/lspci GPU rows now.
            if src_low == "lspci":
                out.append(ng)
                if name:
                    names.append(name)
                continue

            is_nvidia = ("nvidia" in low) or (src_low == "nvidia-smi")
            is_intel = ("intel" in low) or ("uhd graphics" in low) or ("iris" in low)
            is_amd = ("amd" in low) or ("radeon" in low)

            if v10_gpu_blank(ng.get("gpu_type")):
                if is_nvidia:
                    ng["gpu_type"] = "Dedicated NVIDIA"
                elif is_intel:
                    ng["gpu_type"] = "Integrated Intel"
                elif is_amd and "graphics" in low and not any(x in low for x in ["rx ", "radeon pro", "firepro"]):
                    ng["gpu_type"] = "Integrated AMD"
                elif is_amd:
                    ng["gpu_type"] = "AMD GPU"
                else:
                    ng["gpu_type"] = "GPU"

            total = v10_gpu_num(ng.get("memory_total_mb"))
            dedicated = v10_gpu_num(ng.get("dedicated_memory_mb"))
            shared = v10_gpu_num(ng.get("shared_memory_mb"))

            # For NVIDIA from nvidia-smi, memory_total_mb is exact dedicated VRAM.
            if is_nvidia and total is not None and v10_gpu_blank(ng.get("dedicated_memory_mb")):
                ng["dedicated_memory_mb"] = int(total) if float(total).is_integer() else round(total, 2)
                dedicated = total

            # For discrete NVIDIA, if total is missing but dedicated exists, total equals VRAM.
            if is_nvidia and dedicated is not None and v10_gpu_blank(ng.get("memory_total_mb")):
                ng["memory_total_mb"] = int(dedicated) if float(dedicated).is_integer() else round(dedicated, 2)
                total = dedicated

            if name:
                names.append(name)

            use = v10_gpu_num(ng.get("usage_percent") or ng.get("utilization_gpu"))
            temp = v10_gpu_num(ng.get("temperature_c") or ng.get("temp_c"))
            used_mem = v10_gpu_num(ng.get("memory_used_mb"))

            if use is not None:
                usage_vals.append(use)
            if temp is not None:
                temp_vals.append(temp)

            for x in [total, dedicated, shared, used_mem]:
                if x is not None:
                    memory_vals.append(x)

            out.append(ng)

        hw["gpus"] = out
        p["hardware"] = hw
        m["payload"] = p

        m["gpu_count"] = len(out)
        m["gpu_names"] = names
        m["gpu_max_usage"] = round(max(usage_vals), 2) if usage_vals else None
        m["gpu_max_temp_c"] = round(max(temp_vals), 2) if temp_vals else None
        m["gpu_total_memory_mb"] = round(max(memory_vals), 2) if memory_vals else 0

        return m
    except Exception:
        return m

# ================= END V10 GPU BACKEND NORMALIZER =================
'''

if "V10 GPU BACKEND NORMALIZER" not in code:
    marker = "# ================= END V10 IDENTITY CORE BACKEND FIX ================="
    if marker not in code:
        raise SystemExit("Identity core marker not found")
    code = code.replace(marker, helper + "\n" + marker, 1)

# Insert normalizer call inside load_latest loop.
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
print("V10 GPU backend normalizer inserted")