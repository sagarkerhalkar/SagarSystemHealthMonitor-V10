
/* V10 Next Toppers International UI Foundation - safe client enhancement */
(function(){
  const DEFAULT={company_name:'Next Toppers',product_name:'System Health Monitor Tool',website_url:'https://www.nexttoppers.com/',logo:'/assets/brand/nexttoppers_logo.png',login_photo:'/assets/brand/nexttoppers_login_photo.png'};
  let config=DEFAULT; let lastUrl='';
  const $=(s,r=document)=>r.querySelector(s); const $$=(s,r=document)=>Array.from(r.querySelectorAll(s));
  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
  async function loadConfig(){try{const r=await fetch('/nt-brand.config.json',{cache:'no-store'}); if(r.ok) config=Object.assign({},DEFAULT,await r.json());}catch(e){config=DEFAULT}}
  function ensureViewport(){if(!$('meta[name="viewport"]')){let m=document.createElement('meta');m.name='viewport';m.content='width=device-width, initial-scale=1, viewport-fit=cover';document.head.appendChild(m)}}
  function setReady(){document.body.classList.add('nt-brand-ready');document.documentElement.classList.add('nt-brand-ready')}
  function replaceProfileWebsite(){
    $$('a,button').forEach(el=>{const t=(el.textContent||'').trim().toLowerCase(); if(t==='profile website'||t==='website'||t==='company website'){el.textContent='Company Website'; el.classList.add('nt-company-website'); if(el.tagName==='A'){el.href=config.website_url;el.target='_blank';el.rel='noopener noreferrer'}}});
  }
  function sidebar(){
    const side=$('aside')||$('.sidebar')||$('[class*="sidebar"]'); if(!side||$('.nt-brand-panel',side)) return;
    const panel=document.createElement('div'); panel.className='nt-brand-panel';
    panel.innerHTML=`<img src="${esc(config.logo)}" alt="${esc(config.company_name)} logo"><div><div class="nt-brand-title">${esc(config.company_name)}</div><div class="nt-brand-sub">${esc(config.product_name)}</div><a class="nt-brand-link" href="${esc(config.website_url)}" target="_blank" rel="noopener noreferrer">Company website</a></div>`;
    side.prepend(panel);
  }
  function loginBrand(){
    const pass=$('input[type="password"]'); if(!pass) return; const form=pass.closest('form')||pass.closest('div')||document.body; if($('.nt-login-brand')) return;
    const card=document.createElement('div'); card.className='nt-login-brand';
    card.innerHTML=`<div><img class="nt-login-brand-logo" src="${esc(config.logo)}" alt="${esc(config.company_name)}"><h2>Secure Fleet Command Center</h2><p>${esc(config.product_name)} for real-time machines, inventory, network, VPN, USB, software, hardware and alerts.</p></div><img class="nt-login-brand-photo" src="${esc(config.login_photo)}" alt="${esc(config.company_name)} team">`;
    form.prepend(card);
  }
  function commandOverview(){
    const pageText=(document.body.innerText||'').slice(0,1800).toLowerCase(); if(!pageText.includes('command center')) return; if($('.nt-command-overview')) return;
    const target=$('main')||$('.content')||$('.page')||document.body; const first=target.firstElementChild;
    const wrap=document.createElement('section');wrap.className='nt-command-overview';
    wrap.innerHTML=`<div class="nt-overview-card dark"><div class="nt-overview-k">Fleet</div><div class="nt-overview-v" id="ntFleetTotal">—</div><div class="nt-overview-s">Total monitored systems</div></div><div class="nt-overview-card"><div class="nt-overview-k">Inventory</div><div class="nt-overview-v" id="ntInventoryTotal">—</div><div class="nt-overview-s">H/W + S/W overview</div></div><div class="nt-overview-card"><div class="nt-overview-k">ISP / Network</div><div class="nt-overview-v" id="ntNetworkHealth">—</div><div class="nt-overview-s">Latency, jitter, loss, upload/download</div></div><div class="nt-overview-card"><div class="nt-overview-k">Attention</div><div class="nt-overview-v" id="ntAttentionTotal">—</div><div class="nt-overview-s">Backend alerts only</div></div>`;
    if(first) target.insertBefore(wrap, first.nextSibling); else target.prepend(wrap); updateOverview();
  }
  async function updateOverview(){
    try{const r=await fetch('/api/overview',{cache:'no-store'}); if(!r.ok) return; const d=await r.json(); const machines=d.machines||d.latest||[]; const notes=(d.notifications||[]).filter(n=>['critical','warning'].includes(String(n.severity||'').toLowerCase()) && !['cpu_high','ram_high'].includes(String(n.rule_id||'')));
      const total=(d.fleet&&d.fleet.total)||d.total_machines||machines.length||'0'; const apps=d.software_count||d.installed_apps||''; const usb=d.usb_count||''; const lat=(d.internet&&d.internet.latency_ms)||d.latency_ms||'';
      const set=(id,v)=>{let e=document.getElementById(id); if(e) e.textContent=v}; set('ntFleetTotal', total); set('ntInventoryTotal', (apps||usb)?`${apps||0}/${usb||0}`:'Ready'); set('ntNetworkHealth', lat?`${lat} ms`:'Live'); set('ntAttentionTotal', notes.length);
    }catch(e){}
  }
  function settingsPanel(){
    const pageText=(document.body.innerText||'').slice(0,2200).toLowerCase(); if(!pageText.includes('settings')) return; if($('.nt-settings-brand-card')) return;
    const target=$('main')||$('.content')||$('.page')||document.body; const card=document.createElement('section'); card.className='nt-settings-brand-card';
    card.innerHTML=`<h3>Company Branding & Role Control <span class="nt-lock-pill">SOURCE LOCKED</span></h3><div class="nt-settings-grid"><div class="nt-field"><label>Company name</label><input readonly value="${esc(config.company_name)}"></div><div class="nt-field"><label>Company website</label><input readonly value="${esc(config.website_url)}"></div><div class="nt-field"><label>Logo asset</label><input readonly value="${esc(config.logo)}"></div><div class="nt-field"><label>Login photo asset</label><input readonly value="${esc(config.login_photo)}"></div></div><div class="nt-note">Next backend step: Super Admin/Admin editable branding, user creation, password reset and inventory permissions. This panel confirms the source requirement is locked and the assets are installed.</div>`;
    target.prepend(card);
  }
  function lockRows(){
    $$('tr').forEach(tr=>{const txt=(tr.innerText||'').toLowerCase(); if(txt.includes('cpu_high')||txt.includes('ram_high')||txt.includes('locked disabled')){tr.style.opacity='.72';tr.style.background='rgba(255,245,220,.55)'; if(!tr.querySelector('.nt-lock-pill')){const td=document.createElement('td');td.innerHTML='<span class="nt-lock-pill">LOCKED</span>';tr.appendChild(td)}}});
  }
  async function init(){await loadConfig(); ensureViewport(); setReady(); replaceProfileWebsite(); sidebar(); loginBrand(); commandOverview(); settingsPanel(); lockRows();}
  init(); setInterval(()=>{if(location.href!==lastUrl){lastUrl=location.href;setTimeout(init,150)} replaceProfileWebsite(); sidebar(); loginBrand(); commandOverview(); settingsPanel(); lockRows(); updateOverview();},3500);
  new MutationObserver(()=>{replaceProfileWebsite(); sidebar(); lockRows();}).observe(document.documentElement,{childList:true,subtree:true});
})();
