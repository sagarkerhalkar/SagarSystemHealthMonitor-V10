
from __future__ import annotations
import importlib.util, json, os, datetime as dt
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict

BASE_DIR=Path('.')
SOURCE_2278_DB=Path(r'D:\SagarSystemHealthMonitor\data\monitor.db')

def _load(name, filename):
    p=Path(BASE_DIR)/filename
    if not p.exists(): raise RuntimeError(f"Missing required module: {filename}")
    spec=importlib.util.spec_from_file_location(name, str(p))
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for k,v in [('BASE_DIR',Path(BASE_DIR)),('SOURCE_2278_DB',SOURCE_2278_DB)]:
        try: setattr(mod,k,v)
        except Exception: pass
    return mod

def _sel():
    return _load('v10_selected_machine_contract_api_clean_runtime','v10_selected_machine_contract_api.py')

def _send(h,data,status=200):
    if hasattr(h,'send_json'): return h.send_json(data,status)
    body=json.dumps(data,ensure_ascii=False,default=str).encode('utf-8')
    h.send_response(status); h.send_header('Content-Type','application/json; charset=utf-8'); h.send_header('Content-Length',str(len(body))); h.end_headers(); h.wfile.write(body)

def _mid(qs):
    return ((qs.get('machine_id') or qs.get('id') or qs.get('hostname') or qs.get('query') or [''])[0] or '').strip()

def machines():
    s=_sel(); d=s.selected_list(); rows=d.get('machines') or []
    clients=[m for m in rows if not m.get('is_monitor_server')]
    fresh=[m for m in clients if m.get('fresh')]
    stale=[m for m in clients if not m.get('fresh')]
    default=(fresh[0] if fresh else (clients[0] if clients else (rows[0] if rows else {})))
    return {'ok':True,'app_contract':'V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP','source':'2278_readonly_latest_summary_json','source_db':str(SOURCE_2278_DB),'no_write_to_2278':True,'total_2278_rows':len(rows),'client_machines':len(clients),'fresh_clients':len(fresh),'stale_clients':len(stale),'monitor_server_count':len(rows)-len(clients),'default_machine_id':default.get('machine_id',''),'machines':rows}

def home():
    s=_sel(); md=machines()
    try: hs=s.home_summary()
    except Exception as e: hs={'ok':False,'error':str(e)}
    try: nf=s.notification_fast()
    except Exception as e: nf={'ok':False,'error':str(e),'simulated_alerts':[]}
    rows=md.get('machines') or []
    return {'ok':True,'app_contract':'V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP','source':'2278_readonly_compact_home','source_db':str(SOURCE_2278_DB),'no_write_to_2278':True,'machines':md,'home':hs,'notifications':nf,'fresh_machine_cards':[m for m in rows if m.get('fresh') and not m.get('is_monitor_server')][:12],'monitor_servers':[m for m in rows if m.get('is_monitor_server')],'note':'One clean renderer; monitor server separated from client machines.'}

def machine360(mid):
    s=_sel(); hw=s.selected_hardware(machine_id=mid); m=hw.get('machine') or {}; rid=m.get('machine_id') or hw.get('returned_machine_id') or mid
    sw=s.selected_software(machine_id=rid, limit=10000)
    net=s.selected_network(machine_id=rid)
    return {'ok':bool(hw.get('ok')),'app_contract':'V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP','source':'2278_readonly_machine360_combined','no_write_to_2278':True,'requested_machine_id':mid,'returned_machine_id':rid,'returned_hostname':m.get('hostname') or hw.get('returned_hostname'),'exact_machine_id_match':bool(mid and str(rid)==str(mid)),'machine':m,'hardware':hw,'software':sw.get('software') or [],'software_count':len(sw.get('software') or []),'reported_software_count':sw.get('reported_software_count'),'network':net}

def hardware(mid):
    out=_sel().selected_hardware(machine_id=mid); out['app_contract']='V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP'; return out

def network(mid):
    out=_sel().selected_network(machine_id=mid); out['app_contract']='V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP'; return out

def software(mid,qs):
    q=((qs.get('software_query') or qs.get('sw_query') or qs.get('q') or [''])[0] or '').strip()
    try: limit=int(float((qs.get('limit') or ['10000'])[0]))
    except Exception: limit=10000
    out=_sel().selected_software(machine_id=mid, sw_query=q, limit=max(1,min(limit,10000))); out['app_contract']='V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP'; return out

def notify():
    out=_sel().notification_fast(); out['app_contract']='V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP'; return out

def isp():
    return {'ok':True,'app_contract':'V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP','source':'settings_or_router_feed','links':[],'wan_links':[],'note':'ISP/WAN router feed is not faked. Use Settings ISP/WAN Manager module if installed.'}

def install(Handler:Any, base_dir:Any)->None:
    global BASE_DIR,SOURCE_2278_DB
    BASE_DIR=Path(base_dir)
    SOURCE_2278_DB=Path(os.environ.get('V10_SOURCE_2278_DB', r'D:\SagarSystemHealthMonitor\data\monitor.db'))
    old=Handler.do_GET
    def new_get(self):
        parsed=urlparse(self.path); path=parsed.path; qs=parse_qs(parsed.query or '')
        try:
            if path=='/api/v10/app/health': return _send(self,{'ok':True,'app_contract':'V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP','source_db':str(SOURCE_2278_DB),'no_write_to_2278':True,'time':dt.datetime.now(dt.timezone.utc).isoformat()})
            if path=='/api/v10/app/machines': return _send(self,machines())
            if path=='/api/v10/app/home': return _send(self,home())
            if path=='/api/v10/app/machine360': return _send(self,machine360(_mid(qs)))
            if path=='/api/v10/app/hardware': return _send(self,hardware(_mid(qs)))
            if path=='/api/v10/app/network': return _send(self,network(_mid(qs)))
            if path=='/api/v10/app/software': return _send(self,software(_mid(qs),qs))
            if path=='/api/v10/app/notifications-fast': return _send(self,notify())
            if path=='/api/v10/app/isp-wan': return _send(self,isp())
        except Exception as e:
            return _send(self,{'ok':False,'error':str(e),'app_contract':'V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP','source_db':str(SOURCE_2278_DB),'no_write_to_2278':True},500)
        return old(self)
    Handler.do_GET=new_get
