
(function(){
  const API='/api/v10/source2278/hardware';
  const STATUS='/api/v10/source2278/hardware/status';
  const EXPORT='/api/v10/source2278/hardware/export.csv';
  const NOTIFY='/api/v10/source2278/notification-test';
  const state={rows:[],summary:{},q:'',freshness:'all',notify:null,lastRender:0};
  function $(s,r=document){return r.querySelector(s)}
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  function val(v){return (v===null||v===undefined||v===''||v===0&&false)?'Not reported':v}
  function arr(v){return Array.isArray(v)?v:[]}
  async function jget(url){const r=await fetch(url,{credentials:'same-origin'});const t=await r.text();let d={};try{d=JSON.parse(t)}catch(e){throw new Error(url+' returned non JSON: '+t.slice(0,160))}if(!r.ok||d.ok===false)throw new Error(d.message||d.error||url+' failed');return d}
  function toast(msg){let el=document.createElement('div');el.className='v10hw-toast';el.textContent=msg;document.body.appendChild(el);setTimeout(()=>el.remove(),3600)}
  function target(){
    const nodes=[...document.querySelectorAll('section,main,div,article')].filter(n=>/Hardware Asset Register|Hardware Intelligence|Hardware/i.test((n.innerText||'').slice(0,900)));
    const best=nodes.find(n=>n.offsetParent!==null && n.clientHeight>80) || document.querySelector('main') || document.querySelector('#app') || document.body;
    return best;
  }
  async function load(){
    try{const url=API+'?limit=500&q='+encodeURIComponent(state.q||'')+'&freshness='+encodeURIComponent(state.freshness||'all');let d=await jget(url);state.rows=d.machines||[];state.summary=d.summary||{};}catch(e){console.warn(e);toast(e.message)}
    try{state.notify=await jget(NOTIFY)}catch(e){console.warn('notification check unavailable',e)}
  }
  function kpis(){let s=state.summary||{};return `<div class="v10hw-kpis">
    ${kpi(s.machines_checked,'Machines','2278 read-only')}${kpi(s.fresh_machines,'Fresh','<=10 min')}${kpi(s.stale_machines,'Stale/Offline','last report old')}${kpi(s.missing_serial_count,'Missing Serial','client/inventory gap')}${kpi(s.gpu_reported_count,'GPU Reported','real only')}${kpi(s.usb_reported_count,'USB Reported','real only')}
  </div>`}
  function kpi(v,l,s){return `<div class="v10hw-kpi"><b>${esc(v??0)}</b><span>${esc(l)}</span><div class="v10hw-muted" style="font-size:11px;margin-top:4px">${esc(s)}</div></div>`}
  function details(r){
    let disks=arr(r.disks).slice(0,3).map(d=>`${esc(d.name||'Disk')} ${esc(d.size_gb||'')}GB ${esc(d.percent||'')}%`).join('<br>') || `Max ${esc(r.disk_max_percent||0)}%`;
    let gpus=(arr(r.gpu_names).length?arr(r.gpu_names):arr(r.gpus).map(g=>g.name)).filter(Boolean).slice(0,3).map(esc).join('<br>') || 'Not reported by client';
    let usb=arr(r.usb_devices).slice(0,4).map(u=>`${esc(u.category||'USB')}: ${esc(u.name||'Device')}`).join('<br>') || (r.usb_count?`${esc(r.usb_count)} USB/peripherals`:'Not reported by client');
    let net=arr(r.all_ips).join(', ') || r.primary_ip || 'Not reported';
    return `<div class="v10hw-details"><b>Disk:</b><br>${disks}<br><b>GPU:</b><br>${gpus}<br><b>USB:</b><br>${usb}<br><b>Network:</b> ${esc(net)}</div>`;
  }
  function rows(){if(!state.rows.length)return `<div class="v10hw-empty">No hardware rows found from 2278 read-only source. Check /api/v10/source2278/hardware/status.</div>`;return `<div class="v10hw-tablewrap"><table class="v10hw-table"><thead><tr><th>Status</th><th>Machine</th><th>Serial / Identity</th><th>CPU</th><th>RAM</th><th>Storage / GPU / USB / Network</th><th>Completeness</th></tr></thead><tbody>${state.rows.map(r=>`<tr><td><span class="v10hw-badge ${r.fresh?'fresh':'stale'}">${r.fresh?'fresh':'stale'}</span><div class="v10hw-muted">${esc(r.age_minutes??'')} min</div></td><td><b>${esc(r.hostname||r.machine_id)}</b><div class="v10hw-muted">${esc(r.os||'')}</div><div class="v10hw-muted">${esc(r.primary_ip||'')}</div></td><td>${esc(r.serial_number||'Not reported')}<div class="v10hw-muted">MB: ${esc(r.motherboard_serial||'Not reported')}</div><div class="v10hw-muted">BIOS: ${esc(r.bios_serial||'Not reported')}</div></td><td>${esc(r.cpu_name||'Not reported')}<div class="v10hw-muted">Usage: ${esc(r.cpu_percent||0)}%</div><div class="v10hw-muted">Temp: ${esc(r.cpu_temp_c||'Not reported')}</div></td><td>${esc(r.ram_total_gb||0)} GB total<div class="v10hw-muted">Used ${esc(r.ram_used_gb||0)} GB / ${esc(r.ram_percent||0)}%</div><div class="v10hw-muted">Slots: ${esc(r.ram_slots||'Not reported')}</div></td><td>${details(r)}</td><td><b>${esc(r.hardware_completeness_percent||0)}%</b><div class="v10hw-muted">Missing: ${esc(arr(r.missing_live_hardware_fields).join(', ')||'None')}</div></td></tr>`).join('')}</tbody></table></div>`}
  function panel(){let n=state.notify;let note=n?`Notification read-only test: ${n.machines_checked||0} machines, ${n.rules_count||0} rules, simulated alerts ${n.simulated_alerts_count||0}.`: 'Notification test not loaded yet.';return `<section class="v10hw-panel" id="v10Hardware2278Panel"><h3>Live Hardware from 2278 — Read Only</h3><p class="v10hw-sub">This tab reads the working 2278 monitor database only in SQLite read-only mode. It does not write/change 2278. Missing fields show “Not reported by client”; no fake hardware values.</p>${kpis()}<div class="v10hw-toolbar"><input class="v10hw-input" id="v10hwSearch" placeholder="Search machine, serial, IP, CPU" value="${esc(state.q)}"><select class="v10hw-select" id="v10hwFresh"><option value="all" ${state.freshness==='all'?'selected':''}>All machines</option><option value="fresh" ${state.freshness==='fresh'?'selected':''}>Fresh only</option><option value="stale" ${state.freshness==='stale'?'selected':''}>Stale/offline only</option></select><button class="v10hw-btn primary" id="v10hwReload">Refresh Hardware</button><a class="v10hw-btn" href="${EXPORT}?q=${encodeURIComponent(state.q)}&freshness=${encodeURIComponent(state.freshness)}">Download CSV</a></div><div class="v10hw-muted" style="margin:8px 0 12px">${esc(note)}</div>${rows()}</section>`}
  function render(){let old=$('#v10Hardware2278Panel'); if(old) old.remove(); let t=target(); t.insertAdjacentHTML('beforeend',panel()); $('#v10hwReload')?.addEventListener('click',async()=>{state.q=$('#v10hwSearch')?.value||'';state.freshness=$('#v10hwFresh')?.value||'all';await load();render();toast('Hardware refreshed from 2278 read-only source')}); $('#v10hwFresh')?.addEventListener('change',async()=>{state.freshness=$('#v10hwFresh')?.value||'all';await load();render()}); $('#v10hwSearch')?.addEventListener('keydown',async(e)=>{if(e.key==='Enter'){state.q=e.target.value||'';await load();render()}})}
  async function init(){await load(); render(); const mo=new MutationObserver(()=>{let now=Date.now(); if(!$('#v10Hardware2278Panel') && now-state.lastRender>1000){state.lastRender=now; setTimeout(render,80)}}); mo.observe(document.body,{childList:true,subtree:true});}
  window.V10Hardware2278={reload:async()=>{await load();render()}};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
