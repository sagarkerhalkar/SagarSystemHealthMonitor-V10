(function(){
  const API_STATUS='/api/v10/source2278/software/status';
  const API_LIST='/api/v10/source2278/software?limit=300&with_items=1';
  const EXPORT='/api/v10/source2278/software/export.csv';
  const SAMPLE='/api/v10/source2278/software/sample.csv';
  function el(tag, cls, html){ const e=document.createElement(tag); if(cls)e.className=cls; if(html!==undefined)e.innerHTML=html; return e; }
  async function j(url){ const r=await fetch(url,{cache:'no-store'}); if(!r.ok) throw new Error(url+' '+r.status); return await r.json(); }
  function esc(v){ return String(v??'').replace(/[&<>"']/g, s=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s])); }
  function hostContainer(){
    let byId=document.getElementById('software')||document.getElementById('software-intelligence')||document.querySelector('[data-tab="software"]')||document.querySelector('[data-page="software"]');
    if(byId) return byId;
    const candidates=[...document.querySelectorAll('section,main,.content,.page,.tab-panel')];
    for(const c of candidates){ if((c.textContent||'').toLowerCase().includes('software')) return c; }
    return document.querySelector('main')||document.body;
  }
  function ensurePanel(){
    let p=document.getElementById('v10sw2278'); if(p) return p;
    p=el('section','v10sw-wrap'); p.id='v10sw2278';
    p.innerHTML=`
      <div class="v10sw-head">
        <div><h2 class="v10sw-title">Software Intelligence · 2278 Live Read-Only</h2><p class="v10sw-sub">Machine-wise installed software from working 2278 source. No write to 2278. No fake software rows.</p></div>
        <div class="v10sw-actions"><button class="v10sw-btn" id="v10swRefresh">Refresh</button><a class="v10sw-btn" href="${EXPORT}">Export CSV</a><a class="v10sw-btn" href="${SAMPLE}">Sample S/W CSV</a></div>
      </div>
      <div class="v10sw-grid" id="v10swKpis"></div>
      <div class="v10sw-toolbar"><input class="v10sw-input" id="v10swSearch" placeholder="Search software, publisher, machine"/><select class="v10sw-select" id="v10swFresh"><option value="all">All machines</option><option value="fresh">Fresh only</option><option value="stale">Stale only</option></select><button class="v10sw-btn" id="v10swApply">Apply</button></div>
      <div id="v10swBody" class="v10sw-empty">Loading software live data...</div>
      <div class="v10sw-note">If the full list is empty but software count is shown, the client reported count only. Values are not created manually or faked.</div>`;
    hostContainer().appendChild(p);
    p.querySelector('#v10swRefresh').onclick=load;
    p.querySelector('#v10swApply').onclick=load;
    return p;
  }
  function kpis(s){
    const box=document.getElementById('v10swKpis'); if(!box) return;
    const items=[
      ['Machines checked',s.machines_checked||0,'2278 latest rows'],
      ['Fresh machines',s.fresh_machines||0,'live/stale split'],
      ['Reported software',s.reported_software_count_total||0,'client reported count'],
      ['Extracted rows',s.extracted_software_rows_total||0,'full list rows']
    ];
    box.innerHTML=items.map(x=>`<div class="v10sw-kpi"><b>${esc(x[1])}</b><span>${esc(x[0])}</span><span>${esc(x[2])}</span></div>`).join('');
  }
  function render(data){
    const body=document.getElementById('v10swBody'); if(!body) return;
    const sw=data.software||[];
    if(sw.length){
      body.className='v10sw-table-wrap';
      body.innerHTML=`<table class="v10sw-table"><thead><tr><th>Machine</th><th>Software</th><th>Version</th><th>Publisher</th><th>Install Date</th><th>Location</th><th>Status</th></tr></thead><tbody>${sw.slice(0,300).map(r=>`<tr><td><b>${esc(r.hostname)}</b><div class="v10sw-small">${esc(r.machine_id)}</div></td><td>${esc(r.name)}</td><td>${esc(r.version)}</td><td>${esc(r.publisher)}</td><td>${esc(r.install_date)}</td><td>${esc(r.install_location)}</td><td><span class="v10sw-pill good">${esc(r.status||'Reported')}</span></td></tr>`).join('')}</tbody></table>`;
    }else{
      const machines=data.machines||[];
      body.className='v10sw-table-wrap';
      body.innerHTML=`<table class="v10sw-table"><thead><tr><th>Machine</th><th>OS/IP</th><th>Reported Count</th><th>Full List Rows</th><th>Status</th><th>Updated</th></tr></thead><tbody>${machines.slice(0,300).map(r=>`<tr><td><b>${esc(r.hostname)}</b><div class="v10sw-small">${esc(r.machine_id)}</div></td><td>${esc(r.os)}<div class="v10sw-small">${esc(r.primary_ip)}</div></td><td>${esc(r.software_count_reported)}</td><td>${esc(r.software_items_extracted)}</td><td><span class="v10sw-pill ${r.software_items_extracted?'good':'warn'}">${esc(r.software_detail_status)}</span></td><td>${esc(r.updated_at)}</td></tr>`).join('')}</tbody></table>`;
    }
  }
  async function load(){
    const p=ensurePanel();
    try{
      const q=document.getElementById('v10swSearch')?.value||'';
      const f=document.getElementById('v10swFresh')?.value||'all';
      const [s,d]=await Promise.all([j(API_STATUS), j(API_LIST+'&freshness='+encodeURIComponent(f)+'&q='+encodeURIComponent(q))]);
      kpis(s); render(d);
    }catch(e){
      const body=document.getElementById('v10swBody'); if(body){ body.className='v10sw-empty'; body.textContent='Software live data failed: '+e.message; }
    }
  }
  function boot(){ ensurePanel(); load(); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
