(function(){
  if (window.__v10InventoryPluginLoaded) return; window.__v10InventoryPluginLoaded = true;
  const state = { tab:'machines', rows:[], filtered:[], loading:false };
  const tabs = {
    machines:{label:'Current Machines', api:'/api/v10/current-machines', csv:'/api/export/machine_current.csv'},
    hardware:{label:'Hardware Inventory', api:'/api/v10/hardware-inventory', csv:'/api/export/hardware.csv'},
    software:{label:'Software Inventory', api:'/api/v10/software-inventory', csv:'/api/export/software.csv'},
    gpu:{label:'GPU Inventory', api:'/api/v10/gpu-inventory', csv:'/api/export/gpu.csv'},
    usb:{label:'USB Inventory', api:'/api/v10/usb-inventory', csv:'/api/export/usb.csv'},
  };
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
  function pick(o, keys){for(const k of keys){if(o && o[k]!=null && o[k]!=='' && !(Array.isArray(o[k])&&!o[k].length)) return o[k];}return '';}
  function flattenRows(json){
    if (Array.isArray(json)) return json;
    if (Array.isArray(json.rows)) return json.rows;
    if (Array.isArray(json.machines)) return json.machines;
    if (json.machine) return [json.machine];
    return [];
  }
  function preferredColumns(tab, rows){
    const pref = {
      machines:['hostname','machine_id','online','primary_ip','public_ip','isp_name','cpu_percent','ram_percent','disk_max_percent','wan_download_mbps','wan_upload_mbps','gpu_count','software_count','usb_count','updated_at'],
      hardware:['component','machine','machine_id','name','model','serial','type','total_gb','used_gb','free_gb','used_percent','usage_percent','temperature_c','health','sensor_note'],
      software:['machine','machine_id','primary_ip','os','name','version','publisher','install_date','install_location','source','license_review'],
      gpu:['machine','machine_id','primary_ip','gpu_index','name','memory_mb','shared_memory_mb','usage_percent','temperature_c','driver_version','source','sensor_note'],
      usb:['machine','machine_id','primary_ip','device','type','class','manufacturer','vid','pid','status','source','device_id']
    }[tab] || [];
    const seen = new Set(); const cols = [];
    for (const c of pref) { if (rows.some(r => r && Object.prototype.hasOwnProperty.call(r,c))) { seen.add(c); cols.push(c); } }
    for (const r of rows.slice(0,100)) for (const k of Object.keys(r||{})) if(!seen.has(k) && typeof r[k] !== 'object') {seen.add(k); cols.push(k);}
    return cols.slice(0,28);
  }
  function cell(tab, col, val){
    if (col==='online') return val ? '<span class="v10inv-pill v10inv-ok">Online</span>' : '<span class="v10inv-pill v10inv-danger">Offline</span>';
    if (val == null || val === '') return '<span class="v10inv-muted">N/A</span>';
    if (Array.isArray(val)) return esc(val.join(', '));
    if (typeof val === 'object') return esc(JSON.stringify(val));
    return esc(val);
  }
  function render(){
    const q = (document.getElementById('v10InvSearch')?.value || '').toLowerCase();
    const rows = state.rows.filter(r => !q || JSON.stringify(r).toLowerCase().includes(q));
    state.filtered = rows;
    const cols = preferredColumns(state.tab, rows);
    document.getElementById('v10InvStatus').textContent = state.loading ? 'Loading...' : `${rows.length} rows`;
    const wrap = document.getElementById('v10InvTableWrap');
    if (!rows.length) { wrap.innerHTML = '<div style="padding:18px" class="v10inv-muted">No rows found. Check client payload/source or login session.</div>'; return; }
    wrap.innerHTML = `<table class="v10inv-table"><thead><tr>${cols.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.slice(0,2000).map(r=>`<tr>${cols.map(c=>`<td>${cell(state.tab,c,r[c])}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  }
  async function load(tab){
    state.tab = tab; state.loading = true; renderTabs(); render();
    try{
      const res = await fetch(tabs[tab].api, {credentials:'include'});
      if(!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const json = await res.json();
      state.rows = flattenRows(json);
    }catch(e){
      state.rows = [{error:'Failed to load V10 inventory API', detail:String(e), api:tabs[tab].api, note:'Login to old UI first, then open this panel again.'}];
    }
    state.loading = false; renderTabs(); render();
  }
  function renderTabs(){
    const el = document.getElementById('v10InvTabs'); if(!el) return;
    el.innerHTML = Object.entries(tabs).map(([id,t])=>`<button data-tab="${id}" class="${id===state.tab?'active':''}">${esc(t.label)}</button>`).join('');
    el.querySelectorAll('button').forEach(b=>b.onclick=()=>load(b.dataset.tab));
    document.getElementById('v10InvCsv').href = tabs[state.tab].csv;
  }
  function make(){
    if(document.getElementById('v10InvDock')) return;
    const dock = document.createElement('div'); dock.id = 'v10InvDock';
    dock.innerHTML = `<button id="v10InvOpen">Inventory / ISO <small>V10</small></button>`;
    const panel = document.createElement('div'); panel.id = 'v10InvPanel';
    panel.innerHTML = `<div class="v10inv-head"><div><h3>V10 Inventory / ISO Merge</h3><p>Old UI kept. Correct current-machine dedup + S/W, H/W, GPU, USB inventory. V10 only; live 2278 untouched.</p></div><button class="v10inv-close" id="v10InvClose">Close</button></div><div id="v10InvTabs" class="v10inv-tabs"></div><div class="v10inv-body"><div class="v10inv-tools"><input id="v10InvSearch" placeholder="Search machine, software, GPU, serial, IP, publisher..."/><div class="v10inv-actions"><a id="v10InvCsv" href="#" target="_blank">Download CSV</a><a href="/api/v10/status" target="_blank">API Status</a></div><div id="v10InvStatus" class="v10inv-status">Ready</div></div><div id="v10InvTableWrap"></div></div>`;
    document.body.appendChild(dock); document.body.appendChild(panel);
    document.getElementById('v10InvOpen').onclick = ()=>{ panel.classList.toggle('v10show'); if(panel.classList.contains('v10show')) load(state.tab); };
    document.getElementById('v10InvClose').onclick = ()=>panel.classList.remove('v10show');
    document.getElementById('v10InvSearch').oninput = render;
    renderTabs();
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', make); else make();
})();
