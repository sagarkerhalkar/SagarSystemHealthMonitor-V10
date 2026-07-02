
// === V10_UI_FIX4_DEPLOY_MESSAGES_ASSETS_START ===
(function(){
  const FIX4_VERSION='fix4-deploy-messages-assets-readability';
  const staticCache={};
  function safeEsc(v){try{return esc(v)}catch{return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}}
  function safeTitle(s){try{return title(s)}catch{return String(s||'').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}}
  function asList(v){try{return listify(v)}catch{return Array.isArray(v)?v:(v&&typeof v==='object'?Object.values(v):[])}}
  function val(row, names){
    if(!row||typeof row!=='object')return '';
    const keys=Object.keys(row);
    for(const n of names){
      const target=String(n).toLowerCase().replace(/[^a-z0-9]/g,'');
      const k=keys.find(x=>String(x).toLowerCase().replace(/[^a-z0-9]/g,'')===target);
      if(k && row[k]!==undefined && row[k]!==null && String(row[k]).trim()!=='')return row[k];
    }
    return '';
  }
  function flattenRows(raw){
    if(Array.isArray(raw))return raw;
    if(raw&&typeof raw==='object'){
      for(const k of ['rows','assets','data','items','hardware','software','machines','register']){
        if(Array.isArray(raw[k]))return raw[k];
      }
      const vals=Object.values(raw).filter(x=>x&&typeof x==='object');
      if(vals.length && vals.every(x=>!Array.isArray(x)))return vals;
    }
    return [];
  }
  async function fetchJson(url){
    if(staticCache[url])return staticCache[url];
    try{const r=await fetch(url,{credentials:'include',cache:'no-store'}); if(!r.ok)throw new Error(String(r.status)); const j=await r.json(); staticCache[url]=j; return j;}catch(e){staticCache[url]=null; return null;}
  }
  async function loadHardwareRegister(){
    const files=['/generated/fresh_hw_inventory_v2.json','/generated/fresh_hw_inventory.json','/generated/inventory_assets.json','/generated/machine_registry.json'];
    for(const f of files){const j=await fetchJson(f); const rows=flattenRows(j); if(rows.length)return {source:f,rows};}
    return {source:'live-client-only',rows:[]};
  }
  async function loadSoftwareRegister(){
    const files=['/generated/fresh_sw_inventory.json','/generated/software_asset_register_2294.json'];
    for(const f of files){const j=await fetchJson(f); const rows=flattenRows(j); if(rows.length)return {source:f,rows};}
    return {source:'live-client-only',rows:[]};
  }
  function matchMachine(row,m){
    if(!row||!m)return false;
    const hay=JSON.stringify(row).toLowerCase();
    const probes=[m.hostname,m.machine_id,m.primary_ip,m.id_value,m.serial_number].filter(Boolean).map(x=>String(x).toLowerCase());
    return probes.some(p=>p && hay.includes(p));
  }
  function copyCode(txt){navigator.clipboard?.writeText(txt).then(()=>{try{toast('Command copied.')}catch{}}).catch(()=>{});} window.v10CopyCode=copyCode;
  window.getApps=function(m){
    const p=m?.payload||{}, s=p.software;
    if(Array.isArray(s))return s;
    if(s&&Array.isArray(s.apps))return s.apps;
    if(s&&Array.isArray(s.installed))return s.installed;
    if(s&&Array.isArray(s.programs))return s.programs;
    if(Array.isArray(p.apps))return p.apps;
    return [];
  };
  window.renderMessages=async function(){
    const box=document.querySelector('#messagesContent'); if(!box)return;
    try{
      const d=await api('/api/messages'); latestMessages=d.messages||[];
      box.innerHTML=latestMessages.slice(0,100).map(m=>`<div class="message-card"><div><b>${safeEsc(m.title||'Client message')}</b> <span class="rule-badge ${String(m.priority||'normal').toLowerCase()==='critical'?'rule-critical':String(m.priority||'normal').toLowerCase()==='high'?'rule-warning':'rule-info'}">${safeEsc(m.priority||'normal')}</span></div><div class="message-meta"><span class="source-note">${safeEsc(m.target_hostname||m.target_machine_id||'All machines')}</span><span class="rule-badge rule-off">${safeEsc(m.status||'pending')}</span><span class="muted small">${safeEsc((m.created_at||'').replace('T',' ').slice(0,19))}</span></div><p>${safeEsc(m.message||'')}</p></div>`).join('')||empty('No sent client messages yet.');
    }catch(e){box.innerHTML=empty('Message history unavailable: '+e.message)}
  };
  window.renderNotifications=async function(){
    const nbox=document.querySelector('#notificationsContent'), rbox=document.querySelector('#rulesContent');
    try{
      const nr=await api('/api/notifications'); latestNotifications=nr.notifications||[];
      if(nbox)nbox.innerHTML=latestNotifications.filter(n=>!['cpu_high','ram_high'].includes(String(n.rule_id||''))).slice(0,200).map(n=>`<div class="list-item"><b>${safeEsc(n.title||'Notification')}</b> <span class="rule-badge ${String(n.severity||'').toLowerCase()==='critical'?'rule-critical':String(n.severity||'').toLowerCase()==='warning'?'rule-warning':'rule-info'}">${safeEsc(n.severity||'')}</span><br><small>${safeEsc(n.hostname||n.machine_id||'')} · ${safeEsc(n.rule_id||'')} · ${safeEsc((n.created_at||'').replace('T',' ').slice(0,19))}</small><p>${safeEsc(n.message||'')}</p></div>`).join('')||empty('No backend alert rows.');
      const rr=await api('/api/notifications/rules'); latestRules=rr.rules||[];
      if(rbox)rbox.innerHTML=`<div class="metric-strip"><article><span>Active Rules</span><b>${latestRules.filter(r=>r.enabled).length}</b><small>Currently enabled</small></article><article><span>Disabled</span><b>${latestRules.filter(r=>!r.enabled).length}</b><small>Off/optional</small></article><article><span>Locked</span><b>${latestRules.filter(r=>['cpu_high','ram_high'].includes(r.id)).length}</b><small>CPU/RAM singles blocked</small></article></div><div class="table-wrap"><table><thead><tr><th>Status</th><th>Rule</th><th>Metric</th><th>Condition</th><th>Severity</th><th>Cooldown</th></tr></thead><tbody>${latestRules.map(r=>{const locked=['cpu_high','ram_high'].includes(r.id);const cls=locked?'rule-lock':r.enabled?'rule-on':'rule-off';const label=locked?'LOCKED OFF':r.enabled?'ACTIVE':'OFF';return `<tr class="${locked?'locked-row':''}"><td><span class="rule-badge ${cls}">${label}</span></td><td><b>${safeEsc(r.name)}</b><br><small>${safeEsc(r.id)}</small></td><td>${safeEsc(r.metric)}</td><td>${safeEsc(r.op)} ${safeEsc(r.threshold)}</td><td><span class="rule-badge ${String(r.severity).toLowerCase()==='critical'?'rule-critical':String(r.severity).toLowerCase()==='warning'?'rule-warning':'rule-info'}">${safeEsc(r.severity)}</span></td><td>${safeEsc(r.cooldown_minutes)} min</td></tr>`}).join('')}</tbody></table></div>`;
    }catch(e){if(nbox)nbox.innerHTML=empty('Notification load failed: '+e.message)}
  };
  window.renderDeploy=function(){
    const box=document.querySelector('#deployContent'); if(!box)return;
    const origin=location.origin; const clientCmd=`mkdir C:\\Temp -Force\n# Use one client first for V10 test\npowershell -ExecutionPolicy Bypass -File C:\\Temp\\V10_REAL_CLIENT_TEST_FIXED.ps1 -ServerUrl "${origin}"`;
    const firewallCmd=`New-NetFirewallRule -DisplayName "Sagar Monitor V10 2294" -Direction Inbound -Protocol TCP -LocalPort 2294 -Action Allow`;
    const startCmd=`cd D:\\SagarMonitor_V10_CleanBuild\npowershell -ExecutionPolicy Bypass -File .\\RUN_SERVER_2294.ps1`;
    box.innerHTML=`<div class="deploy-hero"><p class="eyebrow">V10 Deploy Command Center</p><h2>Safe rollout for Windows + Ubuntu clients</h2><p>V10 runs on port 2294. Main 2278 is untouched. Use this page for test rollout, installer evidence and client commands.</p></div><div class="deploy-grid"><div class="deploy-card"><h4>1. Server port</h4><p class="muted">Open V10 inbound port on the server.</p><div class="deploy-command"><code>${safeEsc(firewallCmd)}</code></div><button class="copy-btn" onclick="v10CopyCode(${JSON.stringify(firewallCmd)})">Copy firewall command</button></div><div class="deploy-card"><h4>2. Start V10</h4><p class="muted">Keep the V10 PowerShell window open during testing.</p><div class="deploy-command"><code>${safeEsc(startCmd)}</code></div><button class="copy-btn" onclick="v10CopyCode(${JSON.stringify(startCmd)})">Copy start command</button></div><div class="deploy-card"><h4>3. One-client test</h4><p class="muted">Point only one machine to V10 until UI/data is approved.</p><div class="deploy-command"><code>${safeEsc(clientCmd)}</code></div><button class="copy-btn" onclick="v10CopyCode(${JSON.stringify(clientCmd)})">Copy client command</button></div></div><div class="panel glass-card" style="margin-top:18px"><div class="panel-head"><div><h3>Installer / ISO / Download Evidence</h3><p class="muted">Files detected by backend download API.</p></div><button onclick="downloadCsv('/api/export/downloads.csv')">Download Deploy CSV</button></div><div id="deployDownloads" class="list-stack">${empty('Loading deploy files...')}</div></div>`;
    api('/api/downloads').then(d=>{const el=document.querySelector('#deployDownloads'); if(!el)return; el.innerHTML=(d.downloads||[]).map(x=>`<div class="list-item"><b>${safeEsc(x.file_name)}</b><br><small>${safeEsc(x.type||'file')} · ${safeEsc(x.size_mb)} MB · ${safeEsc(x.modified_at||'')}</small><br><a href="${safeEsc(x.download_url)}" target="_blank" rel="noopener">Download</a></div>`).join('')||empty('No deploy/installer files found yet.');}).catch(e=>{const el=document.querySelector('#deployDownloads'); if(el)el.innerHTML=empty('Deploy file list unavailable: '+e.message)});
  };
  window.renderHwInventory=async function(){
    const box=document.querySelector('#hwInventoryContent'), m=selectedMachine(); if(!box)return;
    box.innerHTML=empty('Loading uploaded hardware asset register...');
    const reg=await loadHardwareRegister(); const q=(document.querySelector('#globalSearch')?.value||'').toLowerCase();
    let rows=reg.rows||[]; const total=rows.length;
    if(q)rows=rows.filter(r=>JSON.stringify(r).toLowerCase().includes(q));
    const matches=m?rows.filter(r=>matchMachine(r,m)):[]; const show=(matches.length?matches:rows).slice(0,300);
    const fields=[['Vendor',['vendor_name','vendor','make','manufacturer']],['Make',['make_name','make','brand']],['Model',['model_name','model','asset_model']],['Serial Number',['serial_number','serial','sr_no','service_tag']],['Hostname / Tag',['tagname','hostname','tag','asset_tag','computer_name']],['Warranty End',['warranty_end_date','warranty_end_year','warranty','amc_end']],['Invoice / PO',['invoice_no','po_no','bill_no','invoice','po','bill']],['Assigned To',['assigned_to','user','owner']],['Location',['location','site','branch']],['Status',['status','asset_status']],['Remarks',['remarks','remark','notes']]];
    box.innerHTML=`<div class="asset-toolbar"><span class="source-note">Uploaded H/W register: ${total}</span><span class="source-note">Source: ${safeEsc(reg.source)}</span><button onclick="downloadCsv('/generated/fresh_hw_inventory_v2.csv')">Download Uploaded H/W CSV</button><button onclick="printCurrentPage()">PDF</button></div>${m?`<div class="asset-row"><div class="mini-card"><span>Selected Machine</span><b>${safeEsc(m.hostname||m.machine_id)}</b></div><div class="mini-card"><span>Matched Uploaded Assets</span><b>${matches.length}</b></div><div class="mini-card"><span>Live Sync</span><b>${matches.length?'Matched by hostname/IP/serial':'Not matched yet'}</b></div></div>`:''}<div class="table-wrap"><table class="asset-table"><thead><tr>${fields.map(f=>`<th>${f[0]}</th>`).join('')}</tr></thead><tbody>${show.map(r=>`<tr class="${m&&matchMachine(r,m)?'match-row':''}">${fields.map(f=>`<td>${safeEsc(val(r,f[1])||'')}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${fields.length}">No uploaded hardware register rows found. Re-run patch after placing fresh_hw_inventory_v2.json/csv in data folder.</td></tr>`}</tbody></table></div>`;
  };
  window.renderSwInventory=async function(){
    const box=document.querySelector('#swInventoryContent'), m=selectedMachine(); if(!box)return;
    const reg=await loadSoftwareRegister(); let rows=reg.rows||[]; const live=m?getApps(m):[]; const q=(document.querySelector('#globalSearch')?.value||'').toLowerCase();
    if(q)rows=rows.filter(r=>JSON.stringify(r).toLowerCase().includes(q));
    const fields=[['Software',['software_name','name','display_name','DisplayName','application']],['Version',['version','display_version','DisplayVersion']],['Publisher',['publisher','vendor','manufacturer']],['License',['license','license_type','license_key']],['Install Date',['install_date','InstallDate','date']],['Machine/User',['hostname','computer_name','user','assigned_to']],['Status',['status','compliance','sync_status']]];
    box.innerHTML=`<div class="asset-toolbar"><span class="source-note">Uploaded S/W register: ${reg.rows.length}</span><span class="source-note">Live client apps: ${live.length}</span><span class="source-note">Source: ${safeEsc(reg.source)}</span><button onclick="downloadCsv('/generated/fresh_sw_inventory.json')">Download Uploaded S/W JSON</button><button onclick="printCurrentPage()">PDF</button></div><h3>Live software from selected machine</h3><div class="table-wrap"><table><thead><tr><th>Software</th><th>Version</th><th>Publisher</th><th>Install Date</th></tr></thead><tbody>${live.slice(0,300).map(a=>`<tr><td><b>${safeEsc(a.name||a.display_name||a.DisplayName||'Application')}</b></td><td>${safeEsc(a.version||a.DisplayVersion||'')}</td><td>${safeEsc(a.publisher||a.Publisher||'')}</td><td>${safeEsc(a.install_date||a.InstallDate||'')}</td></tr>`).join('')||'<tr><td colspan="4">No live software apps reported.</td></tr>'}</tbody></table></div><h3>Uploaded software register</h3><div class="table-wrap"><table class="asset-table"><thead><tr>${fields.map(f=>`<th>${f[0]}</th>`).join('')}</tr></thead><tbody>${rows.slice(0,300).map(r=>`<tr>${fields.map(f=>`<td>${safeEsc(val(r,f[1])||'')}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${fields.length}">No uploaded software register rows found.</td></tr>`}</tbody></table></div>`;
  };
  window.renderInventories=function(){renderHwInventory();renderSwInventory();};
  function updateAfterLoad(){
    try{document.body.classList.add('v10-fix4-active'); if(window.refresh)refresh(false); renderMessages?.(); renderNotifications?.();}catch(e){console.warn('fix4 refresh skipped',e)}
  }
  setTimeout(updateAfterLoad,400);
})();
// === V10_UI_FIX4_DEPLOY_MESSAGES_ASSETS_END ===
