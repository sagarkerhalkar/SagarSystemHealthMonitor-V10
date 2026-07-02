(function(){
  const API = "/api/hw-inventory-main";
  const STATE = { rows: [], options: {}, current: null, installed: false };

  const COLS = [
    ["Asset Code","asset_code"],["Make Name","make_name"],["Model Name","model_name"],
    ["Asset Name","asset_name"],["Category","asset_type"],["Config / Details","configuration_details"],
    ["Qty","quantity"],["Vendor","vendor_name"],["Warranty End","warranty_end_date"],
    ["Warranty Year","warranty_end_year"],["Purchase Date","purchase_date"],
    ["PO / Invoice / Bill No","po_invoice_bill_no"],["PO / Bill Path","po_invoice_bill_path"],
    ["Tagname / Hostname","tagname_hostname"],["Serial Number","serial_number"],
    ["Assigned Person","assigned_to"],["Room / Location","asset_location"],["Status","status"],
    ["Remarks","remarks"],["Live Sync","live_sync_status"],["Live Host","live_hostname"],["Live IP","live_ip"]
  ];

  const EDIT = [
    "asset_uid","asset_code","make_name","model_name","asset_name","asset_type","configuration_details",
    "quantity","rate","vendor_name","warranty_end_date","warranty_end_year","purchase_date",
    "po_invoice_bill_no","po_invoice_bill_path","tagname_hostname","serial_number","assigned_to",
    "asset_location","status","remarks"
  ];

  function esc(x){
    return String(x ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }

  async function api(url, opt){
    const r = await fetch(url, opt);
    if(!r.ok) throw new Error(await r.text());
    return r.json();
  }

  function hideOldIsoModal(){
    document.querySelectorAll("*").forEach(el => {
      const t = (el.textContent || "").trim();
      if(t === "Inventory / ISO" || t.includes("V10 Inventory / ISO Merge")){
        let p = el;
        for(let i=0; i<8 && p; i++){
          const st = getComputedStyle(p);
          if(st.position === "fixed" || st.position === "absolute"){
            p.style.display = "none";
            break;
          }
          p = p.parentElement;
        }
        el.style.display = "none";
      }
    });
  }

  function findSidebar(){
    const texts = ["Command Center","Machine Fleet","Machine 360","Hardware","Software","Deploy","Settings"];
    for(const txt of texts){
      const el = [...document.querySelectorAll("a,button,div,span")].find(x => (x.textContent || "").trim() === txt);
      if(el){
        return el.closest("aside") || el.closest("nav") || el.parentElement;
      }
    }
    return null;
  }

  function findMain(){
    const sidebar = findSidebar();
    if(sidebar && sidebar.parentElement){
      const sibs = [...sidebar.parentElement.children].filter(x => x !== sidebar);
      if(sibs.length){
        return sibs.sort((a,b)=>b.getBoundingClientRect().width-a.getBoundingClientRect().width)[0];
      }
    }
    return document.querySelector("main") || document.querySelector("#app") || document.body;
  }

  function addMenu(){
    if(document.getElementById("hwi-main-menu")) return;

    const software = [...document.querySelectorAll("a,button,div,span")]
      .find(x => (x.textContent || "").trim() === "Software");

    const item = document.createElement(software && software.tagName === "A" ? "a" : "div");
    item.id = "hwi-main-menu";
    item.textContent = "H/W Inventory";
    item.href = "#hw-inventory";
    item.onclick = function(e){
      e.preventDefault();
      location.hash = "hw-inventory";
      renderInventory();
    };

    item.style.cssText = [
      "display:block",
      "cursor:pointer",
      "margin:8px 0",
      "padding:12px 14px",
      "border-radius:12px",
      "font-weight:900",
      "color:#dce8ff",
      "text-decoration:none",
      "background:linear-gradient(135deg,#0f766e,#1d4ed8)",
      "border-left:4px solid #2dd4bf"
    ].join(";");

    if(software && software.parentNode){
      software.parentNode.insertBefore(item, software.nextSibling);
    }
  }

  function style(){
    if(document.getElementById("hwi-main-style")) return;
    const s = document.createElement("style");
    s.id = "hwi-main-style";
    s.textContent = `
      #hwi-main-panel{padding:20px 24px}
      .hwi-hero{background:linear-gradient(135deg,#ffffff,#eef8ff);border-radius:24px;padding:22px;box-shadow:0 18px 50px rgba(30,58,138,.14);margin-bottom:18px}
      .hwi-title{font-size:30px;font-weight:950;color:#0f254a;margin:0}
      .hwi-sub{color:#64748b;margin-top:6px}
      .hwi-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0}
      .hwi-card{background:white;border:1px solid #d9e7f7;border-radius:18px;padding:14px;box-shadow:0 14px 36px rgba(30,58,138,.10)}
      .hwi-k{font-size:11px;color:#64748b;font-weight:900;text-transform:uppercase}
      .hwi-v{font-size:24px;font-weight:950;color:#0f172a;margin-top:4px}
      .hwi-panel{background:white;border-radius:22px;padding:16px;box-shadow:0 18px 50px rgba(30,58,138,.14)}
      .hwi-toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0}
      .hwi-toolbar input,.hwi-toolbar select,.hwi-form input{border:1px solid #cbd5e1;border-radius:12px;padding:10px;background:white;min-height:38px}
      .hwi-search{width:340px;max-width:90%}
      .hwi-btn{border:0;border-radius:12px;padding:10px 13px;background:#2563eb;color:white;font-weight:900;cursor:pointer;text-decoration:none}
      .hwi-btn.dark{background:#0f172a}.hwi-btn.red{background:#dc2626}.hwi-btn.green{background:#0f766e}
      .hwi-tablewrap{overflow:auto;max-height:62vh;border:1px solid #d9e7f7;border-radius:16px}
      .hwi-table{border-collapse:collapse;width:100%;min-width:2050px}
      .hwi-table th,.hwi-table td{padding:9px;border-bottom:1px solid #e2e8f0;font-size:13px;vertical-align:top}
      .hwi-table th{position:sticky;top:0;background:#eaf2ff;color:#1e3a8a;text-align:left;z-index:1}
      .hwi-form{display:none;background:#f8fbff;border:1px solid #cfe0f5;border-radius:18px;padding:14px;margin:12px 0}
      .hwi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
      .hwi-grid label{font-size:12px;font-weight:900;color:#334155}
      .hwi-grid input{width:100%;box-sizing:border-box;margin-top:4px}
    `;
    document.head.appendChild(s);
  }

  function card(k,v){ return `<div class="hwi-card"><div class="hwi-k">${esc(k)}</div><div class="hwi-v">${esc(v)}</div></div>`; }

  function selectHtml(id, label, values){
    return `<select id="${id}"><option value="">${label}</option>${(values||[]).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}</select>`;
  }

  function panelHtml(){
    return `
      <div id="hwi-main-panel">
        <div class="hwi-hero">
          <h1 class="hwi-title">H/W Inventory</h1>
          <div class="hwi-sub">Merged inside main dashboard. Filter category-wise, room-wise, person-wise, vendor-wise, status-wise. Add, edit, delete, sync with live monitor.</div>
        </div>
        <div class="hwi-cards" id="hwiCards"></div>
        <div class="hwi-panel">
          <div class="hwi-toolbar" id="hwiFilters">
            <input id="hwiQ" class="hwi-search" placeholder="Search serial, tag/hostname, model, make, vendor, person, room...">
            <span id="hwiSelects"></span>
            <button class="hwi-btn" id="hwiSearchBtn">Search</button>
            <button class="hwi-btn green" id="hwiAddBtn">Add Asset</button>
            <button class="hwi-btn dark" id="hwiSyncBtn">Sync Live</button>
            <button class="hwi-btn dark" id="hwiDedupeBtn">Remove Duplicates</button>
            <a class="hwi-btn dark" id="hwiCsvBtn" href="/api/hw-inventory-main/export.csv">Download CSV</a>
          </div>
          <div class="hwi-form" id="hwiForm">
            <h3 id="hwiFormTitle">Edit Asset</h3>
            <div class="hwi-grid" id="hwiFormGrid"></div>
            <div class="hwi-toolbar">
              <button class="hwi-btn green" id="hwiSaveBtn">Save</button>
              <button class="hwi-btn dark" id="hwiCancelBtn">Cancel</button>
            </div>
          </div>
          <div class="hwi-tablewrap">
            <table class="hwi-table">
              <thead><tr id="hwiHead"></tr></thead>
              <tbody id="hwiBody"></tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  function hideMainChildren(main){
    [...main.children].forEach(c => {
      if(c.id !== "hwi-main-panel"){
        c.setAttribute("data-hwi-hidden", "1");
        c.style.display = "none";
      }
    });
  }

  function showMainChildren(){
    document.querySelectorAll("[data-hwi-hidden='1']").forEach(c => {
      c.style.display = "";
      c.removeAttribute("data-hwi-hidden");
    });
    const p = document.getElementById("hwi-main-panel");
    if(p) p.remove();
  }

  async function renderInventory(){
    style();
    hideOldIsoModal();

    const main = findMain();
    hideMainChildren(main);

    let panel = document.getElementById("hwi-main-panel");
    if(!panel){
      const wrap = document.createElement("div");
      wrap.innerHTML = panelHtml();
      panel = wrap.firstElementChild;
      main.appendChild(panel);
      bind();
    }

    await loadSummary();
    await loadRows();
  }

  async function loadSummary(){
    const s = await api(API + "/summary");
    STATE.options = s.options || {};
    document.getElementById("hwiCards").innerHTML =
      card("Assets", s.imported_assets) +
      card("Missing Vendor", s.missing_vendor_name) +
      card("Missing Make", s.missing_make_name) +
      card("Missing Model", s.missing_model_name) +
      card("Missing Serial", s.missing_serial_number) +
      card("Missing Tag/Host", s.missing_tagname_hostname) +
      card("Missing Person", s.missing_assigned_to) +
      card("Missing Room", s.missing_location) +
      card("Missing Bill/PO", s.missing_po_invoice_bill_no);

    document.getElementById("hwiSelects").innerHTML =
      selectHtml("hwiCategory","Category",STATE.options.categories) +
      selectHtml("hwiRoom","Room",STATE.options.rooms) +
      selectHtml("hwiPerson","Person",STATE.options.persons) +
      selectHtml("hwiVendor","Vendor",STATE.options.vendors) +
      selectHtml("hwiStatus","Status",STATE.options.statuses);
  }

  function queryString(){
    const p = new URLSearchParams();
    const q = document.getElementById("hwiQ")?.value || "";
    const category = document.getElementById("hwiCategory")?.value || "";
    const room = document.getElementById("hwiRoom")?.value || "";
    const person = document.getElementById("hwiPerson")?.value || "";
    const vendor = document.getElementById("hwiVendor")?.value || "";
    const status = document.getElementById("hwiStatus")?.value || "";
    if(q) p.set("q", q);
    if(category) p.set("category", category);
    if(room) p.set("room", room);
    if(person) p.set("person", person);
    if(vendor) p.set("vendor", vendor);
    if(status) p.set("status", status);
    return p.toString();
  }

  async function loadRows(){
    const qs = queryString();
    const j = await api(API + "/assets" + (qs ? "?" + qs : ""));
    STATE.rows = j.rows || [];

    document.getElementById("hwiCsvBtn").href = API + "/export.csv" + (qs ? "?" + qs : "");

    document.getElementById("hwiHead").innerHTML =
      "<th>Action</th>" + COLS.map(c => `<th>${esc(c[0])}</th>`).join("");

    document.getElementById("hwiBody").innerHTML = STATE.rows.map((r,i) =>
      `<tr>
        <td>
          <button class="hwi-btn" onclick="window.HWI.edit(${i})">Edit</button>
          <button class="hwi-btn red" onclick="window.HWI.del(${i})">Delete</button>
        </td>
        ${COLS.map(c => `<td>${esc(r[c[1]] || "")}</td>`).join("")}
      </tr>`
    ).join("") || `<tr><td colspan="${COLS.length+1}">No rows</td></tr>`;
  }

  function openForm(r){
    STATE.current = r || {};
    document.getElementById("hwiForm").style.display = "block";
    document.getElementById("hwiFormTitle").textContent = STATE.current.asset_uid ? "Edit Asset" : "Add Asset";
    document.getElementById("hwiFormGrid").innerHTML = EDIT.map(k =>
      `<label>${esc(k.replaceAll("_"," ").toUpperCase())}<input id="hwi_f_${k}" value="${esc(STATE.current[k] || "")}"></label>`
    ).join("");
    document.getElementById("hwiForm").scrollIntoView({behavior:"smooth",block:"start"});
  }

  function closeForm(){
    STATE.current = null;
    document.getElementById("hwiForm").style.display = "none";
  }

  async function saveForm(){
    const r = {};
    EDIT.forEach(k => r[k] = document.getElementById("hwi_f_" + k)?.value || "");
    await api(API + "/save", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(r)});
    closeForm();
    await loadSummary();
    await loadRows();
  }

  async function deleteRow(i){
    const r = STATE.rows[i];
    if(!r) return;
    if(!confirm("Delete this asset?")) return;
    await api(API + "/delete", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({asset_uid:r.asset_uid})});
    await loadSummary();
    await loadRows();
  }

  async function syncLive(){
    const j = await api(API + "/sync-save", {method:"POST"});
    alert("Live sync done. matched=" + j.matched + " / rows=" + j.rows);
    await loadSummary();
    await loadRows();
  }

  async function dedupe(){
    const j = await api(API + "/dedupe-save", {method:"POST"});
    alert("Duplicate cleanup saved. rows=" + j.rows);
    await loadSummary();
    await loadRows();
  }

  function bind(){
    document.getElementById("hwiSearchBtn").onclick = loadRows;
    document.getElementById("hwiAddBtn").onclick = () => openForm({});
    document.getElementById("hwiSyncBtn").onclick = syncLive;
    document.getElementById("hwiDedupeBtn").onclick = dedupe;
    document.getElementById("hwiSaveBtn").onclick = saveForm;
    document.getElementById("hwiCancelBtn").onclick = closeForm;
    window.HWI = { edit: i => openForm(STATE.rows[i]), del: deleteRow };
  }

  function boot(){
    hideOldIsoModal();
    addMenu();

    if(location.hash === "#hw-inventory"){
      renderInventory().catch(e => alert("H/W Inventory load failed: " + e.message));
    }

    window.addEventListener("hashchange", () => {
      if(location.hash === "#hw-inventory"){
        renderInventory().catch(e => alert("H/W Inventory load failed: " + e.message));
      } else {
        showMainChildren();
      }
    });
  }

  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  setInterval(() => { hideOldIsoModal(); addMenu(); }, 1500);
})();