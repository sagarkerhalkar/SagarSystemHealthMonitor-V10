(function(){
  async function loadRegistryCounts(){
    try{
      const r = await fetch("/v10_machine_registry.json?v=" + Date.now(), {cache:"no-store"});
      if(!r.ok) return;
      const data = await r.json();
      const s = data.summary || data.stats || data || {};

      const counts = {
        "Total": Number(s.real_machines ?? s.real_machine_count ?? s.current_machines ?? s.total ?? 0),
        "Online": Number(s.online ?? s.online_machines ?? 0),
        "Offline": Number(s.offline ?? s.offline_machines ?? 0),
        "Attention": Number(s.attention ?? s.attention_machines ?? 0)
      };

      for (const [label, value] of Object.entries(counts)) {
        updateCard(label, value);
      }

      let badge = document.getElementById("v10RegistryCountBadge");
      if(!badge){
        badge = document.createElement("div");
        badge.id = "v10RegistryCountBadge";
        badge.style.cssText = "position:fixed;right:14px;bottom:14px;z-index:99999;background:#111827;color:#fff;padding:8px 12px;border-radius:999px;font:12px Segoe UI,Arial;box-shadow:0 8px 25px rgba(0,0,0,.25)";
        document.body.appendChild(badge);
      }
      badge.textContent = "V10 Registry Count: " + counts.Total + " real machines";
    }catch(e){}
  }

  function updateCard(label, value){
    const all = Array.from(document.querySelectorAll("body *"));
    const labelNodes = all.filter(el => {
      const t = (el.textContent || "").trim().toLowerCase();
      return t === label.toLowerCase();
    });

    for(const labelEl of labelNodes){
      let card = labelEl.closest(".card,.stat-card,.metric-card,.kpi-card,.summary-card,.glass-card,.tile,section,div") || labelEl.parentElement;
      if(!card) continue;

      const children = Array.from(card.querySelectorAll("*"));
      let numberNode = children.find(el => {
        const t = (el.textContent || "").trim();
        return /^\d+$/.test(t) && el !== labelEl;
      });

      if(!numberNode){
        const parentChildren = Array.from((labelEl.parentElement || card).querySelectorAll("*"));
        numberNode = parentChildren.find(el => /^\d+$/.test((el.textContent || "").trim()));
      }

      if(numberNode){
        numberNode.textContent = String(value);
        numberNode.title = "V10 Machine Registry Count";
        numberNode.setAttribute("data-v10-registry-count","true");
        return;
      }
    }
  }

  window.V10_LOAD_REGISTRY_COUNTS = loadRegistryCounts;
  loadRegistryCounts();
  setInterval(loadRegistryCounts, 5000);
})();
