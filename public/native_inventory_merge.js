(function(){
  const A = "/api/native-inventory";
  const pages = [
    {id:"hw-inventory", label:"H/W Inventory", render:renderHw},
    {id:"sw-inventory", label:"S/W Inventory", render:renderSw},
    {id:"iso-audit", label:"ISO Audit", render:renderIso}
  ];
  let hwRows=[], swLicRows=[], swLiveRows=[], current=null, swCurrent=null;

  const hwCols=[
    ["Asset Code","asset_code"],["Make","make_name"],["Model","model_name"],["Asset Name","asset_name"],
    ["Category","asset_type"],["Details","configuration_details"],["Qty","quantity"],["Vendor","vendor_name"],
    ["Warranty End","warranty_end_date"],["Warranty Year","warranty_end_year"],["Purchase Date","purchase_date"],
    ["Bill/PO No","po_invoice_bill_no"],["Bill Path","po_invoice_bill_path"],["Tag/Hostname","tagname_hostname"],
    ["Serial","serial_number"],["Person","assigned_to"],["Room","asset_location"],["Status","status"],
    ["Remarks","remarks"],["Live Sync","live_sync_status"],["Live Host","live_hostname"],["Live IP","live_ip"]
  ];
  const hwEdit=["asset_uid","asset_code","make_name","model_name","asset_name","asset_type","configuration_details","quantity","rate","vendor_name","warranty_end_date","warranty_end_year","purchase_date","po_invoice_bill_no","po_invoice_bill_path","tagname_hostname","serial_number","assigned_to","asset_location","status","remarks"];

  const swEdit=["license_uid","software_name","vendor_name","publisher","version","license_type","license_count","assigned_to","assigned_machine","login_username","password_vault_ref","license_key_ref","purchase_date","renewal_date","expiry_date","po_invoice_bill_no","po_invoice_bill_path","status","remarks"];

  function esc(x){return String(x??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]))}
  async function api(u,o){let r=await fetch(u,o); if(!r.ok)throw new Error(await r.text()); return r.json()}
  function card(k,v){return `<div class="native-inv-card"><div class="native-inv-k">${esc(k)}</div><div class="native-inv-v">${esc(v)}</div></div>`}
  function optHtml(label, arr){return `<option value="">${esc(label)}</option>`+(arr||[]).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}
  function qs(ids){const p=new URLSearchParams(); ids.forEach(id=>{let e=document.getElementById(id); if(e&&e.value)p.set(id.replace(/^hw|^sw/,"").toLowerCase(),e.value)}); return p.toString()}

  function pageParent(){return document.querySelector(".page")?.parentElement || document.querySelector("main") || document.body}
  function addPages(){
    const parent=pageParent();
    pages.forEach(p=>{
      if(!document.getElementById("page-"+p.id)){
        const sec=document.createElement("section");
        sec.className="page";
        sec.id="page-"+p.id;
        sec.innerHTML=`<div class="native-inv-wrap" id="${p.id}-mount"></div>`;
        parent.appendChild(sec);
      }
    });
  }
  function addNav(){
    const old=document.querySelectorAll('link[href*="v10_inventory_plugin"],script[src*="v10_inventory_plugin"]');
    old.forEach(x=>x.remove());
    pages.forEach(p=>{
      if(document.querySelector(`.nav[data-page="${p.id}"]`))return;
      const ref=[...document.querySelectorAll(".nav,[data-page],a,button,div")].find(x=>(x.textContent||"").trim()==="Software");
      const el=document.createElement(ref?.tagName==="BUTTON"?"button":"div");
      el.className="nav";
      el.dataset.page=p.id;
      el.textContent=p.label;
      el.onclick=()=>nativeSwitch(p.id);
      if(ref&&ref.parentNode)ref.parentNode.insertBefore(el,ref.nextSibling);
    });
  }
  function hideOldFloating(){
    [...document.querySelectorAll("*")].forEach(el=>{
      const t=(el.textContent||"").trim();
      if(t==="Inventory / ISO"||t.includes("V10 Inventory / ISO Merge")){
        let p=el;
        for(let i=0;i<8&&p;i++){
          const st=getComputedStyle(p);
          if(st.position==="fixed"||st.position==="absolute"){p.style.display="none";break}
          p=p.parentElement;
        }
        el.style.display="none";
      }
    });
  }
  function nativeSwitch(id){
    document.querySelectorAll(".page").forEach(x=>x.classList.remove("active"));
    document.getElementById("page-"+id)?.classList.add("active");
    document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("active",x.dataset.page===id));
    const found=pages.find(x=>x.id===id);
    if(found) found.render();
  }

  async function renderHw(){
    const m=document.getElementById("hw-inventory-mount");
    m.innerHTML=`<div class="native-inv-hero"><h2>H/W Inventory</h2><div class="native-inv-sub">Same dashboard UI: category, room, person, vendor, status filters with add/edit/delete and live sync.</div></div><div id="hwCards" class="native-inv-cards"></div><div class="native-inv-panel"><div class="native-inv-toolbar"><input id="hwq" class="native-inv-search" placeholder="Search serial, tag, make, model, vendor, room..."><select id="hwcategory"></select><select id="hwroom"></select><select id="hwperson"></select><select id="hwvendor"></select><select id="hwstatus"></select><button class="native-inv-btn" onclick="NativeInv.loadHw()">Search</button><button class="native-inv-btn green" onclick="NativeInv.hwForm({})">Add Asset</button><a class="native-inv-btn dark" id="hwCsv" href="${A}/hw/export.csv">Download CSV</a><a class="native-inv-btn dark" href="${A}/hw/gaps.csv">Missing Data CSV</a><a class="native-inv-btn dark" href="${A}/hw/duplicates.csv">Duplicate CSV</a><a class="native-inv-btn dark" href="${A}/hw/warranty.csv">Warranty CSV</a></div><div class="native-inv-form" id="hwForm"><h3 id="hwFormTitle"></h3><div class="native-inv-grid" id="hwFormGrid"></div><div class="native-inv-toolbar"><button class="native-inv-btn green" onclick="NativeInv.hwSave()">Save</button><button class="native-inv-btn dark" onclick="NativeInv.closeForms()">Cancel</button></div></div><div class="native-inv-tablewrap"><table class="native-inv-table"><thead><tr id="hwHead"></tr></thead><tbody id="hwBody"></tbody></table></div></div>`;
    const s=await api(A+"/hw/summary");
    hwCards.innerHTML=card("Assets",s.assets)+card("Missing Vendor",s.missing_vendor)+card("Missing Make",s.missing_make)+card("Missing Serial",s.missing_serial)+card("Missing Tag/Host",s.missing_tag)+card("Missing Person",s.missing_person)+card("Missing Room",s.missing_room)+card("Missing Bill/PO",s.missing_bill);
    hwcategory.innerHTML=optHtml("Category",s.categories); hwroom.innerHTML=optHtml("Room",s.rooms); hwperson.innerHTML=optHtml("Person",s.persons); hwvendor.innerHTML=optHtml("Vendor",s.vendors); hwstatus.innerHTML=optHtml("Status",s.statuses);
    await loadHw();
  }
  async function loadHw(){
    const p=new URLSearchParams();
    [["q","hwq"],["category","hwcategory"],["room","hwroom"],["person","hwperson"],["vendor","hwvendor"],["status","hwstatus"]].forEach(([k,id])=>{let v=document.getElementById(id)?.value;if(v)p.set(k,v)});
    hwCsv.href=A+"/hw/export.csv"+(p.toString()?"?"+p.toString():"");
    const j=await api(A+"/hw/assets"+(p.toString()?"?"+p.toString():""));
    hwRows=j.rows||[];
    hwHead.innerHTML='<th class="act">Action</th>'+hwCols.map(c=>`<th>${esc(c[0])}</th>`).join("");
    hwBody.innerHTML=hwRows.map((r,i)=>`<tr><td class="act"><button class="native-inv-btn" onclick="NativeInv.hwForm(NativeInv.hwRows[${i}])">Edit</button><br><button class="native-inv-btn red" onclick="NativeInv.hwDel(${i})">Delete</button></td>${hwCols.map(c=>`<td>${esc(r[c[1]]||"")}</td>`).join("")}</tr>`).join("")||'<tr><td>No rows</td></tr>';
  }
  function hwForm(r){current=r||{}; hwFormTitle.textContent=current.asset_uid?"Edit Asset":"Add Asset"; hwForm.style.display="block"; hwFormGrid.innerHTML=hwEdit.map(k=>`<label>${esc(k.replaceAll("_"," ").toUpperCase())}<input id="hwf_${k}" value="${esc(current[k]||"")}"></label>`).join(""); hwForm.scrollIntoView({behavior:"smooth"})}
  async function hwSave(){let r={}; hwEdit.forEach(k=>r[k]=document.getElementById("hwf_"+k).value); await api(A+"/hw/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(r)}); await renderHw();}
  async function hwDel(i){if(!confirm("Delete asset?"))return; await api(A+"/hw/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({asset_uid:hwRows[i].asset_uid})}); await renderHw();}

  async function renderSw(){
    const m=document.getElementById("sw-inventory-mount");
    m.innerHTML=`<div class="native-inv-hero"><h2>S/W Inventory</h2><div class="native-inv-sub">Live installed software + manual license/bill/PO register.</div></div><div id="swCards" class="native-inv-cards"></div><div class="native-inv-panel"><div class="native-inv-toolbar"><input id="swq" class="native-inv-search" placeholder="Search software, publisher, machine..."><select id="swvendor"></select><select id="swstatus"></select><button class="native-inv-btn" onclick="NativeInv.loadSwLic()">License Search</button><button class="native-inv-btn green" onclick="NativeInv.swForm({})">Add License</button><a class="native-inv-btn dark" href="${A}/sw/licenses.csv">License CSV</a><a class="native-inv-btn dark" href="${A}/sw/live.csv">Live Software CSV</a></div><div class="native-inv-form" id="swForm"><h3 id="swFormTitle"></h3><div class="native-inv-grid" id="swFormGrid"></div><div class="native-inv-toolbar"><button class="native-inv-btn green" onclick="NativeInv.swSave()">Save</button><button class="native-inv-btn dark" onclick="NativeInv.closeForms()">Cancel</button></div></div><h3>Software License Register</h3><div class="native-inv-tablewrap"><table class="native-inv-table"><thead><tr id="swLicHead"></tr></thead><tbody id="swLicBody"></tbody></table></div><h3>Live Installed Software</h3><div class="native-inv-tablewrap"><table class="native-inv-table"><thead><tr id="swLiveHead"></tr></thead><tbody id="swLiveBody"></tbody></table></div></div>`;
    const s=await api(A+"/sw/summary");
    swCards.innerHTML=card("License Rows",s.license_rows)+card("Live Software Rows",s.live_software_rows)+card("Missing Bill",s.missing_license_bill)+card("Missing Machine",s.missing_assigned_machine);
    swvendor.innerHTML=optHtml("Vendor",s.vendors); swstatus.innerHTML=optHtml("Status",s.statuses);
    await loadSwLic(); await loadSwLive();
  }
  async function loadSwLic(){
    const p=new URLSearchParams(); if(swq.value)p.set("q",swq.value); if(swvendor.value)p.set("vendor",swvendor.value); if(swstatus.value)p.set("status",swstatus.value);
    const j=await api(A+"/sw/licenses"+(p.toString()?"?"+p.toString():"")); swLicRows=j.rows||[];
    const cols=["software_name","vendor_name","version","license_type","license_count","assigned_to","assigned_machine","login_username","po_invoice_bill_no","renewal_date","expiry_date","status"];
    swLicHead.innerHTML='<th class="act">Action</th>'+cols.map(c=>`<th>${esc(c)}</th>`).join("");
    swLicBody.innerHTML=swLicRows.map((r,i)=>`<tr><td class="act"><button class="native-inv-btn" onclick="NativeInv.swForm(NativeInv.swLicRows[${i}])">Edit</button><br><button class="native-inv-btn red" onclick="NativeInv.swDel(${i})">Delete</button></td>${cols.map(c=>`<td>${esc(r[c]||"")}</td>`).join("")}</tr>`).join("")||'<tr><td>No license rows</td></tr>';
  }
  async function loadSwLive(){
    const j=await api(A+"/sw/live"); swLiveRows=j.rows||[];
    const cols=["hostname","ip","software_name","publisher","version","install_date","source"];
    swLiveHead.innerHTML=cols.map(c=>`<th>${esc(c)}</th>`).join("");
    swLiveBody.innerHTML=swLiveRows.slice(0,1000).map(r=>`<tr>${cols.map(c=>`<td>${esc(r[c]||"")}</td>`).join("")}</tr>`).join("")||'<tr><td>No live software rows</td></tr>';
  }
  function swForm(r){swCurrent=r||{}; swFormTitle.textContent=swCurrent.license_uid?"Edit License":"Add License"; swForm.style.display="block"; swFormGrid.innerHTML=swEdit.map(k=>`<label>${esc(k.replaceAll("_"," ").toUpperCase())}<input id="swf_${k}" value="${esc(swCurrent[k]||"")}"></label>`).join(""); swForm.scrollIntoView({behavior:"smooth"})}
  async function swSave(){let r={}; swEdit.forEach(k=>r[k]=document.getElementById("swf_"+k).value); await api(A+"/sw/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(r)}); await renderSw();}
  async function swDel(i){if(!confirm("Delete software license row?"))return; await api(A+"/sw/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({license_uid:swLicRows[i].license_uid})}); await renderSw();}

  async function renderIso(){
    const m=document.getElementById("iso-audit-mount");
    const s=await api(A+"/iso/summary");
    m.innerHTML=`<div class="native-inv-hero"><h2>ISO / ITAM Audit</h2><div class="native-inv-sub">Download audit evidence pack for hardware, software, missing fields, duplicates and warranty.</div></div><div class="native-inv-cards">${card("H/W Assets",s.hardware_assets)+card("S/W License Rows",s.software_license_rows)+card("Live Software Rows",s.live_software_rows)+card("H/W Gaps",s.hardware_gap_rows)+card("Duplicate Rows",s.duplicate_rows)+card("Warranty Issues",s.warranty_issue_rows)}</div><div class="native-inv-panel"><div class="native-inv-toolbar"><a class="native-inv-btn green" href="${A}/iso/audit-pack.zip">Download Full ISO Audit ZIP</a><a class="native-inv-btn dark" href="${A}/hw/export.csv">H/W Register CSV</a><a class="native-inv-btn dark" href="${A}/sw/licenses.csv">S/W License CSV</a><a class="native-inv-btn dark" href="${A}/sw/live.csv">Live Software CSV</a><a class="native-inv-btn dark" href="${A}/hw/gaps.csv">Missing Data CSV</a><a class="native-inv-btn dark" href="${A}/hw/duplicates.csv">Duplicate CSV</a><a class="native-inv-btn dark" href="${A}/hw/warranty.csv">Warranty CSV</a></div><p><b>Note:</b> This is audit evidence support, not ISO certification by itself.</p></div>`;
  }
  function closeForms(){document.querySelectorAll(".native-inv-form").forEach(x=>x.style.display="none")}
  window.NativeInv={loadHw,hwRows,hwForm,hwSave,hwDel,loadSwLic,swLicRows,swForm,swSave,swDel,closeForms};

  function boot(){addPages();addNav();hideOldFloating(); if(location.hash==="#hw-inventory")nativeSwitch("hw-inventory"); if(location.hash==="#sw-inventory")nativeSwitch("sw-inventory"); if(location.hash==="#iso-audit")nativeSwitch("iso-audit");}
  window.addEventListener("hashchange",()=>{if(location.hash==="#hw-inventory")nativeSwitch("hw-inventory"); if(location.hash==="#sw-inventory")nativeSwitch("sw-inventory"); if(location.hash==="#iso-audit")nativeSwitch("iso-audit");});
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);else boot();
  setInterval(()=>{addNav();hideOldFloating();},1500);
})();