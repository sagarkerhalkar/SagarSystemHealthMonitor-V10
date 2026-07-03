(function(){
  'use strict';
  const MARK = 'V10_STABLE_SELECTED_MACHINE_NO_FLICKER_MARKER';
  const ROOT_IDS = ['command','fleet','machine360','network','hardware','software'];
  const API = {
    hstat:'/api/v10/source2278/hardware/status',
    hw:'/api/v10/source2278/hardware?limit=1000&freshness=all',
    swstat:'/api/v10/source2278/software/status',
    sw:'/api/v10/source2278/software?limit=5000&with_items=1&freshness=all',
    traffic:'/api/v10/source2278/home-traffic-kpi',
    isp:'/api/v10/isp-wan/status',
    notify:'/api/v10/source2278/notification-test'
  };
  const LS_SEL='v10.selectedMachineId.2278';
  const LS_MONITOR='v10.monitorServerHostnames';
  const DEFAULT_MONITOR_HOSTS=['desktop-1vtkp12'];
  const S = {
    loading:false, loaded:false, err:'', last:0,
    hwStatus:{}, machines:[], swStatus:{}, software:[], traffic:{}, isp:{}, notify:{ok:false, skipped:true, note:'Notification test is manual/cached so it cannot freeze the UI.'},
    selectedId: localStorage.getItem(LS_SEL)||'',
    q:'', fleetFilter:'fresh', softwareQ:'', active:'command'
  };
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));
  const esc = v => String(v ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const isNR = v => v===undefined || v===null || v==='' || v==='Not reported' || v==='Not reported by client';
  const clean = v => isNR(v) ? 'Not reported by client' : v;
  const num = (v,d=0) => { const n=Number(v); return Number.isFinite(n)?n:d; };
  const fmt = (v,u='') => isNR(v) ? 'Not reported' : `${v}${u}`;
  const pct = v => Math.max(0, Math.min(100, num(v,0)));
  function monitorHosts(){
    try{
      const raw=localStorage.getItem(LS_MONITOR);
      if(raw){ const arr=JSON.parse(raw); if(Array.isArray(arr)) return arr.map(x=>String(x).toLowerCase().trim()).filter(Boolean); }
    }catch(e){}
    return DEFAULT_MONITOR_HOSTS;
  }
  function isMonitorServer(m){
    const h=String(m?.hostname||'').toLowerCase().trim();
    return monitorHosts().includes(h);
  }
  function clientMachines(){ return S.machines.filter(m=>!isMonitorServer(m)); }
  function withTimeout(ms){ const c=new AbortController(); const t=setTimeout(()=>c.abort(),ms); return {signal:c.signal, done:()=>clearTimeout(t)}; }
  async function j(url, ms=12000){
    const to=withTimeout(ms);
    try{
      const r=await fetch(url,{cache:'no-store', signal:to.signal});
      const t=await r.text();
      let d={};
      try{ d=t?JSON.parse(t):{}; } catch(e){ throw new Error(url+' non-json '+t.slice(0,120)); }
      if(!r.ok) throw new Error(d.error || r.statusText || ('HTTP '+r.status));
      return d;
    } finally { to.done(); }
  }
  function sortMachines(rows){
    return (rows||[]).slice().sort((a,b)=>{
      const sa=isMonitorServer(a)?1:0, sb=isMonitorServer(b)?1:0;
      return sa-sb || (b.fresh?1:0)-(a.fresh?1:0) || String(a.hostname||'').localeCompare(String(b.hostname||''));
    });
  }
  function pickDefaultMachine(){
    if(S.selectedId && S.machines.some(m=>m.machine_id===S.selectedId)) return;
    const saved=localStorage.getItem(LS_SEL);
    if(saved && S.machines.some(m=>m.machine_id===saved)){ S.selectedId=saved; return; }
    const row = S.machines.find(m=>m.fresh && !isMonitorServer(m)) || S.machines.find(m=>!isMonitorServer(m)) || S.machines[0];
    S.selectedId = row ? row.machine_id : '';
    if(S.selectedId) localStorage.setItem(LS_SEL,S.selectedId);
  }
  async function load(){
    if(S.loading) return;
    S.loading=true; S.err=''; markStatus(false,'Loading 2278 read-only source...');
    try{
      const res=await Promise.allSettled([j(API.hstat),j(API.hw,18000),j(API.swstat),j(API.sw,22000),j(API.traffic,8000),j(API.isp,8000)]);
      const get=i=>res[i].status==='fulfilled'?res[i].value:{ok:false,error:res[i].reason?.message||'not available'};
      S.hwStatus=get(0);
      S.machines=sortMachines(get(1).machines||[]);
      S.swStatus=get(2);
      S.software=get(3).software||[];
      S.traffic=get(4);
      S.isp=get(5);
      pickDefaultMachine();
      S.loaded=true; S.last=Date.now();
      markStatus(true,`2278 read-only source connected · ${S.machines.length} machines`);
    }catch(e){
      S.err=e.message; console.warn('V10 stable selected-machine load failed',e); markStatus(false,'2278 source error: '+e.message);
    }finally{ S.loading=false; }
  }
  function selected(){ return S.machines.find(m=>m.machine_id===S.selectedId) || S.machines.find(m=>!isMonitorServer(m)) || S.machines[0] || {}; }
  function identity(m){
    const id=String(m?.id_value || m?.machine_id || '').trim();
    const parts=id.split('/').map(x=>x.trim()).filter(Boolean);
    return {display:id, fingerprint:parts[1]||id||'Not reported by client', host:m?.hostname||parts[0]||m?.machine_id||'Select machine'};
  }
  function machineSoft(m=selected()){
    let rows=(S.software||[]).filter(x=>x.machine_id===m.machine_id || x.hostname===m.hostname);
    if(S.softwareQ){ const q=S.softwareQ.toLowerCase(); rows=rows.filter(x=>JSON.stringify(x).toLowerCase().includes(q)); }
    return rows;
  }
  function kpi(label,value,sub,cls=''){
    return `<div class="v10m-card v10m-kpi ${cls}"><div class="label">${esc(label)}</div><div class="num">${esc(value)}</div><div class="sub">${esc(sub)}</div></div>`;
  }
  function table(rows, cols, maxRows){
    rows=rows||[]; if(maxRows) rows=rows.slice(0,maxRows);
    if(!rows.length) return `<div class="v10m-empty">No rows from verified 2278 read-only source for this selection.</div>`;
    return `<div class="v10m-tablewrap"><table class="v10m-table"><thead><tr>${cols.map(c=>`<th>${esc(c.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${c.render?c.render(r):esc(clean(r[c.key]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  function machineOptions(){
    return S.machines.map(m=>{
      const id=identity(m);
      const tag=isMonitorServer(m)?' [monitor server]':(m.fresh?' ●':'');
      return `<option value="${esc(m.machine_id)}" ${m.machine_id===S.selectedId?'selected':''}>${esc(id.host+tag)}</option>`;
    }).join('');
  }
  function toolbar(extra=''){
    return `<div class="v10m-toolbar"><label class="v10m-field-label">Selected machine</label><select class="v10m-select" onchange="v10mSelect(this.value)">${machineOptions()}</select><button class="v10m-btn primary" onclick="v10mReload()">Refresh 2278 Data</button>${extra}</div>`;
  }
  function page(el,title,sub,body,cls=''){
    if(!el) return;
    el.innerHTML=`<span id="${MARK}"></span><div class="v10m ${cls}"><div class="v10m-shell"><div class="v10m-hero"><span class="v10m-badge"><span class="v10m-live-dot"></span> 2278 read-only selected-machine mode</span><h2 class="v10m-title">${esc(title)}</h2><p class="v10m-sub">${esc(sub)}</p></div>${body}</div></div>`;
  }
  function showOnlyCurrent(){
    const active=document.querySelector('.tab.show')?.id || S.active || 'command';
    S.active=active;
    hideOldHero();
    renderTab(active);
  }
  function renderTab(id){
    if(id==='command') renderHome();
    else if(id==='fleet') renderFleet();
    else if(id==='machine360') renderMachine360();
    else if(id==='network') renderNetwork();
    else if(id==='hardware') renderHardware();
    else if(id==='software') renderSoftware();
  }
  function renderCoreTabs(){ ROOT_IDS.forEach(renderTab); hideOldHero(); }
  function visibleRows(){
    const q=(S.q||'').toLowerCase();
    return S.machines.filter(m=>{
      const ok=S.fleetFilter==='all' || (S.fleetFilter==='fresh'&&m.fresh&&!isMonitorServer(m)) || (S.fleetFilter==='stale'&&!m.fresh) || (S.fleetFilter==='server'&&isMonitorServer(m));
      return ok && (!q || JSON.stringify(m).toLowerCase().includes(q));
    });
  }
  function renderHome(){
    const el=$('#command'); if(!el) return;
    const clients=clientMachines(); const fresh=clients.filter(m=>m.fresh).length; const stale=clients.length-fresh; const servers=S.machines.length-clients.length;
    const tr=S.traffic||{}; const ispRows=S.isp.links||S.isp.wan_links||[];
    const cards=`<div class="v10m-grid v10m-home-kpis">${kpi('Client Machines',clients.length,'excluding monitor server','v10m-info')}${kpi('Online / Fresh',fresh,'heartbeat < 10 min','v10m-good')}${kpi('Stale / Offline',stale,'needs client check','v10m-warn')}${kpi('Monitor Server',servers,'separate from clients','v10m-neutral')}${kpi('Today Download',fmt(tr.today_download_gb,' GB'),'all live clients')}${kpi('Today Upload',fmt(tr.today_upload_gb,' GB'),'all live clients')}${kpi('Current Download',fmt(tr.current_download_mbps,' Mbps'),'live client traffic')}${kpi('Current Upload',fmt(tr.current_upload_mbps,' Mbps'),'live client traffic')}</div>`;
    const machineCards=clients.filter(m=>m.fresh).slice(0,8).map(m=>{const id=identity(m);return `<button class="v10m-card v10m-machine" onclick="v10mSelect('${esc(m.machine_id)}');v10mOpenTab('machine360')"><span class="v10m-pill fresh">fresh</span><b>${esc(id.host)}</b><div class="v10m-small">${esc(m.primary_ip)} · ${esc(m.os)}</div><div class="v10m-small">CPU ${esc(m.cpu_percent)}% · RAM ${esc(m.ram_percent)}% · Disk ${esc(m.disk_max_percent)}%</div><div class="meter"><span style="width:${pct(m.ram_percent)}%"></span></div></button>`}).join('');
    const body=`${cards}<div class="v10m-grid v10m-home-sections"><div class="v10m-card v10m-half"><h3 class="v10m-section-title">3D Live Client Summary</h3><p class="v10m-sub">Compact. No duplicate old home blocks. Click any machine to open 360.</p><div class="v10m-machines compact">${machineCards||'<div class="v10m-empty">No fresh client machine loaded.</div>'}</div></div><div class="v10m-card v10m-half"><h3 class="v10m-section-title">ISP / WAN + Alert Status</h3><div class="v10m-detail-list"><div class="v10m-mini"><div class="k">ISP/WAN links</div><div class="v">${esc(ispRows.length)}</div></div><div class="v10m-mini"><div class="k">Alert test</div><div class="v">Manual / non-blocking</div></div></div><div class="v10m-toolbar"><button class="v10m-btn" onclick="v10mRunNotifyTest()">Run notification test</button><a class="v10m-btn" href="/api/v10/isp-wan/export.csv">ISP CSV</a></div><div id="v10mNotifyBox" class="v10m-empty">Notification test will not auto-run on Home, so the page will not freeze or flicker.</div>${table(ispRows,[{label:'WAN',key:'wan_name'},{label:'ISP',key:'isp_name'},{label:'Status',key:'status'},{label:'Latency',key:'latency_ms'},{label:'Jitter',key:'jitter_ms'},{label:'Loss',key:'packet_loss_percent'}],10)}</div></div>`;
    page(el,'Home / Command Center','Compact no-flicker dashboard. Server is separated from client machines.',body,'v10m-home-compact');
  }
  function renderFleet(){
    const el=$('#fleet'); if(!el) return; const rows=visibleRows();
    const body=`<div class="v10m-card v10m-wide"><div class="v10m-toolbar"><input class="v10m-input" placeholder="Search hostname, IP, OS" value="${esc(S.q)}" oninput="v10mSearch(this.value)"><select class="v10m-select" onchange="v10mFilter(this.value)"><option value="fresh" ${S.fleetFilter==='fresh'?'selected':''}>Fresh / online clients</option><option value="stale" ${S.fleetFilter==='stale'?'selected':''}>Stale / offline</option><option value="all" ${S.fleetFilter==='all'?'selected':''}>All machines</option><option value="server" ${S.fleetFilter==='server'?'selected':''}>Monitor server</option></select><button class="v10m-btn primary" onclick="v10mReload()">Refresh</button><a class="v10m-btn" href="/api/v10/source2278/hardware/export.csv">CSV</a></div>${table(rows,[{label:'Status',render:r=>`<span class="v10m-pill ${r.fresh?'fresh':'stale'}">${isMonitorServer(r)?'server':(r.fresh?'fresh':'stale')}</span><div class="v10m-small">${esc(r.age_minutes)} min</div>`},{label:'Hostname / Identity',render:r=>{const id=identity(r);return `<b>${esc(id.host)}</b><div class="v10m-small">Fingerprint: ${esc(id.fingerprint)}</div><div class="v10m-small">${esc(r.machine_id)}</div>`}},{label:'IP / OS',render:r=>`${esc(r.primary_ip)}<div class="v10m-small">${esc(r.os)}</div>`},{label:'CPU / RAM',render:r=>`${esc(clean(r.cpu_name))}<div class="v10m-small">CPU ${esc(r.cpu_percent)}% · RAM ${esc(r.ram_percent)}%</div>`},{label:'Disk / GPU / USB / SW',render:r=>`Disk ${esc(r.disk_max_percent)}%<div class="v10m-small">GPU ${esc(r.gpu_count)} · USB ${esc(r.usb_count)} · SW ${esc(r.software_count)}</div>`},{label:'Action',render:r=>`<button class="v10m-btn primary" onclick="v10mSelect('${esc(r.machine_id)}');v10mOpenTab('machine360')">Open 360</button>`}],500)}</div>`;
    page(el,'Machine Fleet','Fleet list only. Selecting a row opens that exact machine.',body);
  }
  function detailCards(m){
    const id=identity(m), sw=machineSoft(m);
    return `<div class="v10m-grid">${kpi('Hostname',id.host,'selected machine','v10m-info')}${kpi('Asset Fingerprint',id.fingerprint,'old working identity logic')}${kpi('Official Serial',clean(m.serial_number),'audit field')}${kpi('Freshness',isMonitorServer(m)?'Monitor Server':(m.fresh?'Fresh':'Stale'),`${esc(m.age_minutes||'')} minutes`,m.fresh?'v10m-good':'v10m-warn')}${kpi('CPU',`${esc(m.cpu_percent||0)}%`,clean(m.cpu_name))}${kpi('RAM',`${esc(m.ram_percent||0)}%`,`${esc(m.ram_used_gb||0)} / ${esc(m.ram_total_gb||0)} GB`)}${kpi('Disk Max',`${esc(m.disk_max_percent||0)}%`,`${esc((m.disks||[]).length)} disk(s)`)}${kpi('GPU',m.gpu_count||0,(m.gpu_names||[]).join(', ')||'Not reported')}${kpi('USB / Peripheral',m.usb_count||0,'keyboard, mouse, headset, storage')}${kpi('Software',m.software_count||sw.length||0,'installed software')}${kpi('Public IP',m.public_ip||'Not reported','network source')}${kpi('ISP',m.isp_name||'Not reported','client route')}</div>`;
  }
  function renderMachine360(){
    const el=$('#machine360'); if(!el) return; const m=selected(); const sw=machineSoft(m);
    const body=`<div class="v10m-card v10m-wide">${toolbar(`<a class="v10m-btn" href="/api/v10/source2278/hardware/export.csv">Hardware CSV</a><a class="v10m-btn" href="/api/v10/source2278/software/export.csv">Software CSV</a>`)}<div class="v10m-page-note">Selected machine is locked across Machine 360, Network + VPN, Hardware Intelligence and Software Intelligence.</div></div>${detailCards(m)}<div class="v10m-grid"><div class="v10m-card v10m-half"><h3 class="v10m-section-title">Disks / SSD / HDD / NVMe</h3>${table(m.disks||[],[{label:'Name',key:'name'},{label:'Mount',key:'mount'},{label:'Size GB',key:'size_gb'},{label:'Used GB',key:'used_gb'},{label:'Free GB',key:'free_gb'},{label:'Percent',key:'percent'}],50)}</div><div class="v10m-card v10m-half"><h3 class="v10m-section-title">GPU</h3>${table(m.gpus||[],[{label:'Name',key:'name'},{label:'Memory MB',key:'memory_mb'},{label:'Usage %',key:'usage_percent'},{label:'Temp C',key:'temperature_c'},{label:'Driver',key:'driver'}],20)}</div><div class="v10m-card v10m-half"><h3 class="v10m-section-title">USB + Peripherals</h3>${table(m.usb_devices||[],[{label:'Category',key:'category'},{label:'Name',key:'name'},{label:'Vendor',key:'vendor'},{label:'Status',key:'status'}],80)}</div><div class="v10m-card v10m-half"><h3 class="v10m-section-title">Network Adapters</h3>${table(m.network_adapters||[],[{label:'Name',key:'name'},{label:'MAC',key:'mac'},{label:'IPs',render:r=>esc((r.ips||[]).join(', '))},{label:'Status',key:'status'},{label:'Speed',key:'speed'}],20)}</div><div class="v10m-card v10m-wide"><h3 class="v10m-section-title">Installed Software for selected machine</h3><div class="v10m-toolbar"><input class="v10m-input" placeholder="Search selected machine software" value="${esc(S.softwareQ)}" oninput="v10mSoftwareSearch(this.value)"></div>${table(sw,[{label:'Name',key:'name'},{label:'Version',key:'version'},{label:'Publisher',key:'publisher'},{label:'Install Date',key:'install_date'},{label:'Status',key:'status'}],500)}</div></div>`;
    page(el,'Machine 360','Full machine-wise story from 2278 read-only payload.',body);
  }
  function renderNetwork(){
    const el=$('#network'); if(!el) return; const m=selected();
    const body=`<div class="v10m-card v10m-wide">${toolbar(`<a class="v10m-btn" href="/api/v10/source2278/hardware/export.csv">Network CSV</a>`)}<div class="v10m-page-note">Network + VPN is selected-machine only. Router ISP links are in Settings/Home.</div></div><div class="v10m-grid">${kpi('Hostname',identity(m).host,'selected machine')}${kpi('Primary IP',m.primary_ip||'Not reported','client adapter')}${kpi('Public IP',m.public_ip||'Not reported','reported route')}${kpi('VPN Active',String(m.vpn_active),'client reported')}${kpi('ISP Route',m.isp_name||'Not reported','client route')}${kpi('Adapters',(m.network_adapters||[]).length,'network cards')}</div><div class="v10m-card v10m-wide"><h3 class="v10m-section-title">Machine Network Adapters</h3>${table(m.network_adapters||[],[{label:'Adapter',key:'name'},{label:'MAC',key:'mac'},{label:'IPs',render:r=>esc((r.ips||[]).join(', '))},{label:'Gateway',key:'gateway'},{label:'DNS',render:r=>esc(Array.isArray(r.dns)?r.dns.join(', '):(r.dns||'Not reported'))},{label:'Status',key:'status'},{label:'Speed',key:'speed'}],100)}</div>`;
    page(el,'Network + VPN','Machine-wise IP, MAC, adapters, VPN, public IP and ISP route.',body);
  }
  function renderHardware(){
    const el=$('#hardware'); if(!el) return; const m=selected();
    const body=`<div class="v10m-card v10m-wide">${toolbar(`<a class="v10m-btn" href="/api/v10/source2278/hardware/export.csv">Hardware CSV</a>`)}<div class="v10m-page-note">Hardware Intelligence is selected-machine only. It is not Machine Fleet again.</div></div>${detailCards(m)}<div class="v10m-grid"><div class="v10m-card v10m-half"><h3 class="v10m-section-title">CPU / RAM</h3><div class="v10m-detail-list"><div class="v10m-mini"><div class="k">CPU name</div><div class="v">${esc(clean(m.cpu_name))}</div></div><div class="v10m-mini"><div class="k">CPU usage/temp</div><div class="v">${esc(m.cpu_percent)}% · ${esc(m.cpu_temp_c||'Temp not reported')}</div></div><div class="v10m-mini"><div class="k">Cores / logical</div><div class="v">${esc(m.cpu_cores)} / ${esc(m.cpu_logical_processors)}</div></div><div class="v10m-mini"><div class="k">RAM</div><div class="v">${esc(m.ram_used_gb)} / ${esc(m.ram_total_gb)} GB · ${esc(m.ram_percent)}%</div></div></div></div><div class="v10m-card v10m-half"><h3 class="v10m-section-title">Identity / Audit</h3><div class="v10m-detail-list"><div class="v10m-mini"><div class="k">Hostname</div><div class="v">${esc(identity(m).host)}</div></div><div class="v10m-mini"><div class="k">Asset fingerprint</div><div class="v">${esc(identity(m).fingerprint)}</div></div><div class="v10m-mini"><div class="k">Official serial</div><div class="v">${esc(clean(m.serial_number))}</div></div><div class="v10m-mini"><div class="k">Completeness</div><div class="v">${esc(m.hardware_completeness_percent||0)}%</div></div></div></div><div class="v10m-card v10m-half"><h3 class="v10m-section-title">Storage</h3>${table(m.disks||[],[{label:'Name',key:'name'},{label:'Mount',key:'mount'},{label:'Size',key:'size_gb'},{label:'Used',key:'used_gb'},{label:'Free',key:'free_gb'},{label:'%',key:'percent'}],80)}</div><div class="v10m-card v10m-half"><h3 class="v10m-section-title">GPU</h3>${table(m.gpus||[],[{label:'Name',key:'name'},{label:'Memory',key:'memory_mb'},{label:'Usage',key:'usage_percent'},{label:'Temp',key:'temperature_c'},{label:'Driver',key:'driver'}],50)}</div><div class="v10m-card v10m-wide"><h3 class="v10m-section-title">USB / Peripheral</h3>${table(m.usb_devices||[],[{label:'Category',key:'category'},{label:'Name',key:'name'},{label:'Vendor',key:'vendor'},{label:'Status',key:'status'},{label:'Device ID',key:'device_id'}],150)}</div></div>`;
    page(el,'Hardware Intelligence','Selected-machine hardware. No old fleet-style data.',body);
  }
  function renderSoftware(){
    const el=$('#software'); if(!el) return; const m=selected(); const sw=machineSoft(m);
    const body=`<div class="v10m-card v10m-wide">${toolbar(`<input class="v10m-input" placeholder="Search selected machine software" value="${esc(S.softwareQ)}" oninput="v10mSoftwareSearch(this.value)"><a class="v10m-btn" href="/api/v10/source2278/software/export.csv">Software CSV</a>`)}<div class="v10m-page-note">Software Intelligence is selected-machine only. Selected: ${esc(identity(m).host)}. Global extracted rows: ${esc(S.swStatus.extracted_software_rows_total||S.software.length)}.</div></div><div class="v10m-grid">${kpi('Selected Machine',identity(m).host,'software source')}${kpi('Reported Count',m.software_count||sw.length,'from 2278 payload')}${kpi('Loaded Rows',sw.length,'matched by machine')}${kpi('OS',m.os||'Not reported','machine OS')}</div><div class="v10m-card v10m-wide"><h3 class="v10m-section-title">Installed Software on selected machine</h3>${table(sw,[{label:'Software',key:'name'},{label:'Version',key:'version'},{label:'Publisher',key:'publisher'},{label:'Install Date',key:'install_date'},{label:'Install Location',key:'install_location'},{label:'Status',key:'status'}],1000)}</div>`;
    page(el,'Software Intelligence','Machine-wise installed software from 2278 read-only payload.',body);
  }
  function hideOldHero(){ const gh=$('#globalHero'); if(gh) gh.style.display='none'; }
  function markStatus(ok,msg){
    const t=$('#apiStatusText') || $('.live-status') || $('#apiStatus'); if(t) t.textContent=msg;
    const d=$('#apiDot'); if(d) d.className=ok?'good':'bad';
  }
  window.v10mSelect=function(id){
    S.selectedId=id; localStorage.setItem(LS_SEL,id); S.softwareQ='';
    renderMachine360(); renderNetwork(); renderHardware(); renderSoftware();
    markStatus(true,'Selected machine: '+identity(selected()).host);
  };
  window.v10mSearch=function(q){ S.q=q; renderFleet(); };
  window.v10mFilter=function(f){ S.fleetFilter=f; renderFleet(); };
  window.v10mSoftwareSearch=function(q){ S.softwareQ=q; renderMachine360(); renderSoftware(); };
  window.v10mOpenTab=function(id){ const btn=document.querySelector(`[data-tab="${id}"]`); if(btn) btn.click(); setTimeout(()=>renderTab(id),120); };
  window.v10mReload=async function(){ await load(); renderCoreTabs(); };
  window.v10mRunNotifyTest=async function(){
    const box=$('#v10mNotifyBox'); if(box) box.innerHTML='Running notification test with timeout...';
    try{
      const d=await j(API.notify,5000); S.notify=d;
      if(box) box.innerHTML=`Notification test OK: ${esc(d.machines_checked||0)} machines, ${esc(d.rules_count||0)} rules, ${esc(d.simulated_alerts_count||0)} simulated alerts.`;
    }catch(e){ if(box) box.innerHTML='Notification test did not finish in 5 seconds. UI remains working. Error: '+esc(e.message); }
  };
  // Override the top Refresh button after old global script loads. It must not run old full refresh loop for these pages.
  window.refreshAll = window.v10mReload;
  async function boot(){
    hideOldHero();
    await load();
    renderCoreTabs();
    $$('.nav').forEach(b=>b.addEventListener('click',()=>{S.active=b.dataset.tab; setTimeout(()=>{hideOldHero(); renderTab(b.dataset.tab);},160);}));
    window.refreshAll = window.v10mReload;
    markStatus(true,'2278 read-only source connected · no auto flicker');
  }
  window.v10MachinewiseState=S;
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
