let machines = [];
let selectedMachine = "";

async function api(url, opts = {}) {
  const r = await fetch(url, {credentials: "include", ...opts});
  if (r.status === 401) throw new Error("login_required");
  if (!r.ok) throw new Error(await r.text());
  return await r.json();
}

async function login() {
  const msg = document.getElementById("loginMsg");
  msg.textContent = "Logging in...";
  try {
    const r = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "include",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        username: document.getElementById("username").value,
        password: document.getElementById("password").value
      })
    });
    if (!r.ok) throw new Error("Login failed");
    msg.textContent = "";
    await boot();
  } catch(e) {
    msg.textContent = e.message;
  }
}

function showLogin() {
  document.getElementById("login").classList.remove("hidden");
  document.getElementById("app").classList.add("hidden");
}

function showApp() {
  document.getElementById("login").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
}

function showTab(id) {
  document.querySelectorAll(".tab").forEach(x => x.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
  document.querySelectorAll("nav button").forEach(b => b.classList.remove("active"));
  [...document.querySelectorAll("nav button")].find(b => b.textContent.toLowerCase().includes(id === "machine" ? "machine 360" : id))?.classList.add("active");
  if (id === "fleet") renderFleet();
  if (id === "machine") renderMachine();
  if (id === "software") renderSoftware();
}

async function boot() {
  try {
    const st = await api("/api/auth/status");
    if (!st.authenticated && !st.ok) return showLogin();
    showApp();
    await refresh();
    setInterval(refresh, 5000);
  } catch(e) {
    showLogin();
  }
}

async function refresh() {
  try {
    const health = await api("/api/health");
    document.getElementById("health").textContent = "V10 online · 2294";
    document.getElementById("health").className = "status-pill ok";

    const data = await api("/api/machines");
    machines = data.machines || [];

    renderHome();
    renderFleet();
    fillMachineSelect();
    renderMachine();
    renderSoftware();

    try {
      const net = await api("/api/internet-health");
      document.getElementById("internetState").textContent = net.ok ? "Healthy" : "Problem";
    } catch {
      document.getElementById("internetState").textContent = "N/A";
    }
  } catch(e) {
    if (String(e.message).includes("login")) return showLogin();
    document.getElementById("health").textContent = "error";
    document.getElementById("health").className = "status-pill bad";
  }
}

function online(m) {
  return m.online === true || m.online === 1 || m.online === "true";
}

function renderHome() {
  const total = machines.length;
  const on = machines.filter(online).length;
  const critical = machines.filter(m => Number(m.disk_max_percent||0) >= 90 || Number(m.cpu_percent||0) >= 90 || Number(m.ram_percent||0) >= 90).length;

  totalMachines.textContent = total;
  onlineMachines.textContent = on;
  criticalMachines.textContent = critical;

  const rows = machines.slice(0, 12).map(m => `
    <tr onclick="selectMachine('${escapeHtml(m.machine_id || "")}');showTab('machine')">
      <td><b>${escapeHtml(m.hostname || "-")}</b><small>${escapeHtml(m.machine_id || "")}</small></td>
      <td>${online(m) ? "Online" : "Offline"}</td>
      <td>${fmt(m.cpu_percent)}%</td>
      <td>${fmt(m.ram_percent)}%</td>
      <td>${fmt(m.disk_max_percent)}%</td>
      <td>${fmt(m.wan_download_mbps)} / ${fmt(m.wan_upload_mbps)} Mbps</td>
    </tr>`).join("");

  summaryTable.innerHTML = table(["Machine","Status","CPU","RAM","Disk","Down / Up"], rows);
}

function renderFleet() {
  if (!document.getElementById("fleetTable")) return;
  const q = (search?.value || "").toLowerCase();
  const f = filter?.value || "all";
  let list = machines.filter(m => {
    const hay = JSON.stringify([m.hostname,m.machine_id,m.primary_ip,m.public_ip,m.isp_name,m.os]).toLowerCase();
    if (q && !hay.includes(q)) return false;
    if (f === "online" && !online(m)) return false;
    if (f === "offline" && online(m)) return false;
    return true;
  });

  const rows = list.map(m => `
    <tr onclick="selectMachine('${escapeHtml(m.machine_id || "")}');showTab('machine')">
      <td><b>${escapeHtml(m.hostname || "-")}</b><small>${escapeHtml(m.os || "")}</small></td>
      <td>${online(m) ? "🟢 Online" : "🔴 Offline"}</td>
      <td>${escapeHtml(m.primary_ip || "-")}</td>
      <td>${escapeHtml(m.isp_name || "-")}</td>
      <td>${fmt(m.cpu_percent)}%</td>
      <td>${fmt(m.ram_percent)}%</td>
      <td>${fmt(m.wan_download_mbps)} Mbps</td>
      <td>${fmt(m.updated_at)}</td>
    </tr>`).join("");

  fleetTable.innerHTML = table(["Machine","Status","IP","ISP","CPU","RAM","Down","Last seen"], rows);
}

function fillMachineSelect() {
  const sel = document.getElementById("machineSelect");
  const old = selectedMachine || sel.value;
  sel.innerHTML = machines.map(m => `<option value="${escapeHtml(m.machine_id || "")}">${escapeHtml(m.hostname || m.machine_id || "-")}</option>`).join("");
  if (old && machines.find(m => m.machine_id === old)) sel.value = old;
  selectedMachine = sel.value || machines[0]?.machine_id || "";
}

function selectMachine(id) {
  selectedMachine = id;
  const sel = document.getElementById("machineSelect");
  if (sel) sel.value = id;
  renderMachine();
}

function renderMachine() {
  const m = machines.find(x => x.machine_id === selectedMachine) || machines[0];
  if (!m) {
    machine360.innerHTML = `<div class="panel">No machine data found.</div>`;
    return;
  }

  machine360.innerHTML = `
    <div class="big-card">
      <h3>${escapeHtml(m.hostname || "-")}</h3>
      <p>${escapeHtml(m.machine_id || "")}</p>
      <div class="metric-row"><span>Status</span><b>${online(m) ? "Online" : "Offline"}</b></div>
      <div class="metric-row"><span>IP</span><b>${escapeHtml(m.primary_ip || "-")}</b></div>
      <div class="metric-row"><span>ISP</span><b>${escapeHtml(m.isp_name || "-")}</b></div>
    </div>
    ${metricCard("CPU", fmt(m.cpu_percent)+"%", "Temp: "+fmt(m.cpu_temp_c)+"°C")}
    ${metricCard("RAM", fmt(m.ram_percent)+"%", "Total: "+fmt(m.ram_total_gb)+" GB · Used: "+fmt(m.ram_used_gb)+" GB")}
    ${metricCard("Disk", fmt(m.disk_max_percent)+"%", "Highest disk usage")}
    ${metricCard("Internet", fmt(m.wan_download_mbps)+" ↓ / "+fmt(m.wan_upload_mbps)+" ↑", "Mbps current")}
    ${metricCard("GPU", fmt(m.gpu_count), Array.isArray(m.gpu_names) ? m.gpu_names.join(", ") : (m.gpu_names || "N/A"))}
    ${metricCard("USB", fmt(m.usb_count), "peripherals")}
    ${metricCard("Software", fmt(m.software_count), "installed apps")}
    ${metricCard("VPN", m.vpn_active ? "Active" : "Not active", "client reported")}
  `;
}

function renderSoftware() {
  const rows = machines.map(m => `
    <tr>
      <td><b>${escapeHtml(m.hostname || "-")}</b><small>${escapeHtml(m.machine_id || "")}</small></td>
      <td>${escapeHtml(m.os || "-")}</td>
      <td>${fmt(m.software_count)}</td>
      <td>${fmt(m.usb_count)}</td>
      <td>${escapeHtml(m.updated_at || "-")}</td>
    </tr>`).join("");
  softwareTable.innerHTML = table(["Machine","OS","Software Count","USB Count","Last Seen"], rows);
}

function metricCard(title, value, sub) {
  return `<div class="card metric"><span>${title}</span><b>${escapeHtml(value)}</b><small>${escapeHtml(sub || "")}</small></div>`;
}

function table(headers, rows) {
  return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${rows || `<tr><td colspan="${headers.length}">No data</td></tr>`}</tbody></table></div>`;
}

function fmt(v) {
  if (v === null || v === undefined || v === "") return "N/A";
  if (typeof v === "number") return Math.round(v * 100) / 100;
  return String(v);
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

boot();
