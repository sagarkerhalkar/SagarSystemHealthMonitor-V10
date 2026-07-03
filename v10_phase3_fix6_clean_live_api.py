#!/usr/bin/env python3
# V10 Phase3 Fix6: clean corporate UI + live API compatibility. No dummy data.
from __future__ import annotations
import csv, io, json, sqlite3, traceback, urllib.parse, datetime, re, hashlib
from pathlib import Path
from typing import Any, Dict, List
PHASE_NAME='V10_PHASE3_FIX6_CLEAN_CORPORATE_LIVE'
PHASE_VERSION='2026-07-03.6'
HW_COLS=['asset_uid','asset_code','make_name','model_name','asset_name','asset_type','configuration_details','quantity','rate','vendor_name','warranty_end_date','warranty_end_year','purchase_date','po_invoice_bill_no','po_invoice_bill_path','tagname_hostname','serial_number','assigned_to','asset_location','status','remarks','source_sheet','source_row','live_sync_status','live_hostname','live_machine_id','live_ip','live_online','live_last_seen','extra_json','created_at','updated_at']
SW_COLS=['software_uid','machine_id','hostname','software_name','version','publisher','install_date','install_location','license_key','license_type','assigned_to','status','source','remarks','extra_json','created_at','updated_at']
def now(): return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='seconds')
def s(v): return '' if v is None else str(v).strip()
def send(h,obj,status=200):
    b=json.dumps(obj,ensure_ascii=False,default=str).encode('utf-8'); h.send_response(status); h.send_header('Content-Type','application/json; charset=utf-8'); h.send_header('Content-Length',str(len(b))); h.send_header('Cache-Control','no-store'); h.end_headers(); h.wfile.write(b)
def read_json(h):
    n=int(h.headers.get('Content-Length') or 0); raw=h.rfile.read(n) if n else b'{}'
    try: return json.loads(raw.decode('utf-8','replace') or '{}')
    except Exception: return {}
def csv_out(h,rows,name):
    rows=rows or []; fields=[]
    for r in rows:
        for k in r.keys():
            if k not in fields: fields.append(k)
    if not fields: fields=['message']; rows=[{'message':'no live rows'}]
    buf=io.StringIO(); w=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore'); w.writeheader(); [w.writerow(r) for r in rows]
    b=buf.getvalue().encode('utf-8-sig'); h.send_response(200); h.send_header('Content-Type','text/csv; charset=utf-8'); h.send_header('Content-Disposition',f'attachment; filename="{name}"'); h.send_header('Content-Length',str(len(b))); h.end_headers(); h.wfile.write(b)
def uid(prefix,row,keys):
    base='|'.join(s(row.get(k)) for k in keys)
    if not base.strip('|'): base=json.dumps(row,ensure_ascii=False,default=str)
    return prefix+hashlib.sha1(base.encode('utf-8','ignore')).hexdigest()[:12].upper()
def norm_hw(r):
    r=dict(r or {})
    aliases={'Asset Code':'asset_code','Code':'asset_code','Asset Name':'asset_name','Name':'asset_name','Asset Type':'asset_type','Vendor Name':'vendor_name','Make Name':'make_name','Model Name':'model_name','Serial Number':'serial_number','Tagname / Hostname':'tagname_hostname','Hostname':'tagname_hostname','Location':'asset_location','Asset Location':'asset_location','Invoice No':'po_invoice_bill_no','PO / Invoice / Bill No':'po_invoice_bill_no','Purchase Date':'purchase_date','Warranty End Date':'warranty_end_date','Assigned To':'assigned_to','Status':'status','Remarks':'remarks'}
    for a,b in aliases.items():
        if not s(r.get(b)) and s(r.get(a)): r[b]=s(r.get(a))
    r.setdefault('asset_name',s(r.get('model_name')) or s(r.get('asset_type')) or 'Asset')
    r.setdefault('asset_type','Uncategorized'); r.setdefault('quantity','1'); r.setdefault('status','Review'); r.setdefault('live_sync_status','not_matched')
    r['asset_uid']=s(r.get('asset_uid')) or uid('HW-',r,['asset_code','serial_number','tagname_hostname','asset_name'])
    for c in HW_COLS: r.setdefault(c,'')
    t=now(); r['updated_at']=t; r['created_at']=s(r.get('created_at')) or t
    return {c:s(r.get(c)) for c in HW_COLS}
def norm_sw(r):
    r=dict(r or {})
    aliases={'Software Name':'software_name','Name':'software_name','DisplayName':'software_name','Version':'version','Publisher':'publisher','License Key':'license_key','License Type':'license_type','Assigned To':'assigned_to','Status':'status','Remarks':'remarks'}
    for a,b in aliases.items():
        if not s(r.get(b)) and s(r.get(a)): r[b]=s(r.get(a))
    r.setdefault('software_name','Unknown Software'); r.setdefault('status','Review'); r.setdefault('source','manual')
    r['software_uid']=s(r.get('software_uid')) or uid('SW-',r,['machine_id','hostname','software_name','version','publisher'])
    t=now(); r['updated_at']=t; r['created_at']=s(r.get('created_at')) or t
    for c in SW_COLS: r.setdefault(c,'')
    return {c:s(r.get(c)) for c in SW_COLS}
class CleanAPI:
    def __init__(self,base,load_latest): self.base=Path(base); self.db=self.base/'data'/'monitor_v10_notify.db'; self.load_latest=load_latest; self.db.parent.mkdir(parents=True,exist_ok=True)
    def con(self):
        c=sqlite3.connect(str(self.db),timeout=30); c.row_factory=sqlite3.Row; return c
    def migrate(self):
        with self.con() as c:
            c.execute('CREATE TABLE IF NOT EXISTS hardware_assets(asset_uid TEXT PRIMARY KEY, asset_code TEXT, make_name TEXT, model_name TEXT, asset_name TEXT, asset_type TEXT, configuration_details TEXT, quantity TEXT, rate TEXT, vendor_name TEXT, warranty_end_date TEXT, warranty_end_year TEXT, purchase_date TEXT, po_invoice_bill_no TEXT, po_invoice_bill_path TEXT, tagname_hostname TEXT, serial_number TEXT, assigned_to TEXT, asset_location TEXT, status TEXT, remarks TEXT, source_sheet TEXT, source_row TEXT, live_sync_status TEXT, live_hostname TEXT, live_machine_id TEXT, live_ip TEXT, live_online TEXT, live_last_seen TEXT, extra_json TEXT, created_at TEXT, updated_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS software_assets(software_uid TEXT PRIMARY KEY, machine_id TEXT, hostname TEXT, software_name TEXT, version TEXT, publisher TEXT, install_date TEXT, install_location TEXT, license_key TEXT, license_type TEXT, assigned_to TEXT, status TEXT, source TEXT, remarks TEXT, extra_json TEXT, created_at TEXT, updated_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS asset_edit_audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, asset_uid TEXT, action TEXT, before_json TEXT, after_json TEXT, actor TEXT, created_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS software_edit_audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, software_uid TEXT, action TEXT, before_json TEXT, after_json TEXT, actor TEXT, created_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS branding_settings(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS retention_settings(key TEXT PRIMARY KEY,value TEXT,updated_at TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS inventory_sync_matches(id INTEGER PRIMARY KEY AUTOINCREMENT,machine_id TEXT,hostname TEXT,asset_uid TEXT,serial_number TEXT,tagname_hostname TEXT,match_method TEXT,score INTEGER,matched_at TEXT)')
            for k,v in {'company_name':'Sagar','company_website':'https://sagarkerhalkar.com','app_title':'System Health Monitor V10','logo_path':'/assets/brand/nexttoppers_logo.png','login_photo_path':'/assets/brand/nexttoppers_login_photo.png'}.items(): c.execute('INSERT OR IGNORE INTO branding_settings(key,value,updated_at) VALUES(?,?,?)',(k,v,now()))
            c.commit()
        if self.count('hardware_assets')<=0: self.import_hw(False)
    def count(self,t):
        try:
            with self.con() as c: return int(c.execute(f'SELECT COUNT(*) c FROM {t}').fetchone()['c'])
        except Exception: return 0
    def latest(self):
        try:
            x=self.load_latest(); return x if isinstance(x,list) else []
        except Exception: return []
    def source_hw(self):
        for p in [self.base/'data'/'fresh_hw_inventory_v2.csv', self.base/'data'/'fresh_hw_inventory_source.csv', self.base/'public'/'generated'/'fresh_hw_inventory_v2.csv', self.base/'public'/'generated'/'fresh_hw_inventory_source.csv']:
            if p.exists():
                with p.open('r',encoding='utf-8-sig',newline='') as f: return [norm_hw(dict(r)) for r in csv.DictReader(f)]
        return []
    def import_hw(self,force=False):
        rows=self.source_hw();
        with self.con() as c:
            if force: c.execute('DELETE FROM hardware_assets')
            for r in rows:
                c.execute('INSERT OR REPLACE INTO hardware_assets('+','.join(HW_COLS)+') VALUES('+','.join(['?']*len(HW_COLS))+')',[r.get(x,'') for x in HW_COLS])
            c.commit()
        return {'ok':True,'imported':len(rows),'total':self.count('hardware_assets')}
    def settings(self,table):
        self.migrate();
        with self.con() as c: return {r['key']:r['value'] for r in c.execute(f'SELECT key,value FROM {table}').fetchall()}
    def save_settings(self,table,body):
        self.migrate();
        with self.con() as c:
            for k,v in (body or {}).items(): c.execute(f'INSERT OR REPLACE INTO {table}(key,value,updated_at) VALUES(?,?,?)',(k,s(v),now()))
            c.commit()
        return {'ok':True,'settings':self.settings(table)}
    def hw_rows(self,qs):
        self.migrate(); q=s((qs.get('q') or [''])[0]).lower(); limit=int(float((qs.get('limit') or ['500'])[0])); offset=int(float((qs.get('offset') or ['0'])[0])); where=''; params=[]
        if q:
            cols=['asset_code','make_name','model_name','asset_name','asset_type','vendor_name','tagname_hostname','serial_number','assigned_to','asset_location','status','remarks']; where=' WHERE '+ ' OR '.join([f'LOWER({x}) LIKE ?' for x in cols]); params=[f'%{q}%']*len(cols)
        with self.con() as c:
            total=c.execute('SELECT COUNT(*) c FROM hardware_assets'+where,params).fetchone()['c']; rows=[dict(r) for r in c.execute('SELECT * FROM hardware_assets'+where+' ORDER BY asset_uid LIMIT ? OFFSET ?',params+[limit,offset]).fetchall()]
        return {'ok':True,'total':total,'count':len(rows),'rows':rows,'assets':rows,'source':'live_db_hardware_assets'}
    def sw_rows(self,qs):
        self.migrate(); q=s((qs.get('q') or [''])[0]).lower(); rows=[]; params=[]; where=''
        if q: where=' WHERE LOWER(software_name) LIKE ? OR LOWER(publisher) LIKE ? OR LOWER(hostname) LIKE ?'; params=[f'%{q}%']*3
        with self.con() as c: rows=[dict(r) for r in c.execute('SELECT * FROM software_assets'+where+' ORDER BY software_name LIMIT 1000',params).fetchall()]
        if not rows: rows=self.live_software()
        return {'ok':True,'total':len(rows),'count':len(rows),'rows':rows,'assets':rows,'software':rows,'source':'software_assets_or_live_payload'}
    def live_software(self):
        out=[]
        for m in self.latest():
            p=m.get('payload') if isinstance(m.get('payload'),dict) else {}; sw=p.get('software') or p.get('installed_software') or p.get('apps') or []
            if isinstance(sw,dict): sw=sw.get('installed') or sw.get('rows') or []
            if not isinstance(sw,list): sw=[]
            for a in sw:
                if isinstance(a,dict): out.append(norm_sw({**a,'machine_id':m.get('machine_id'),'hostname':m.get('hostname'),'source':'live_client'}))
                elif s(a): out.append(norm_sw({'software_name':s(a),'machine_id':m.get('machine_id'),'hostname':m.get('hostname'),'source':'live_client'}))
        return out
    def save_hw(self,body):
        r=norm_hw(body); self.migrate()
        with self.con() as c:
            old=c.execute('SELECT * FROM hardware_assets WHERE asset_uid=?',(r['asset_uid'],)).fetchone(); before=dict(old) if old else None
            c.execute('INSERT OR REPLACE INTO hardware_assets('+','.join(HW_COLS)+') VALUES('+','.join(['?']*len(HW_COLS))+')',[r.get(x,'') for x in HW_COLS])
            c.execute('INSERT INTO asset_edit_audit_log(asset_uid,action,before_json,after_json,actor,created_at) VALUES(?,?,?,?,?,?)',(r['asset_uid'],'edit' if old else 'add',json.dumps(before,default=str),json.dumps(r,default=str),'admin',now())); c.commit()
        return {'ok':True,'asset':r,'action':'edit' if before else 'add'}
    def save_sw(self,body):
        r=norm_sw(body); self.migrate()
        with self.con() as c:
            old=c.execute('SELECT * FROM software_assets WHERE software_uid=?',(r['software_uid'],)).fetchone(); before=dict(old) if old else None
            c.execute('INSERT OR REPLACE INTO software_assets('+','.join(SW_COLS)+') VALUES('+','.join(['?']*len(SW_COLS))+')',[r.get(x,'') for x in SW_COLS])
            c.execute('INSERT INTO software_edit_audit_log(software_uid,action,before_json,after_json,actor,created_at) VALUES(?,?,?,?,?,?)',(r['software_uid'],'edit' if old else 'add',json.dumps(before,default=str),json.dumps(r,default=str),'admin',now())); c.commit()
        return {'ok':True,'software':r,'action':'edit' if before else 'add'}
    def delete(self,table,key,value,audit):
        with self.con() as c:
            old=c.execute(f'SELECT * FROM {table} WHERE {key}=?',(value,)).fetchone()
            if not old: return {'ok':False,'error':'not_found','id':value}
            c.execute(f'DELETE FROM {table} WHERE {key}=?',(value,)); c.commit()
        return {'ok':True,'deleted':value}

def install(Handler, BASE_DIR, load_latest, *args, **kwargs):
    api=CleanAPI(BASE_DIR,load_latest); api.migrate(); old_get=Handler.do_GET; old_post=Handler.do_POST; old_del=getattr(Handler,'do_DELETE',None)
    def parse(path):
        p=path.split('?',1)[0]; qs=urllib.parse.parse_qs(path.split('?',1)[1]) if '?' in path else {}; return p,qs
    def do_GET(self):
        p,qs=parse(self.path)
        try:
            if p=='/api/v10final/inventory/hardware': return send(self,api.hw_rows(qs))
            if p=='/api/v10final/inventory/software': return send(self,api.sw_rows(qs))
            if p=='/api/v10final/branding': return send(self,{'ok':True,'settings':api.settings('branding_settings')})
            if p=='/api/v10final/export/hardware.csv': return csv_out(self,api.hw_rows(qs)['rows'],'v10_hardware_assets.csv')
            if p=='/api/v10final/export/software.csv': return csv_out(self,api.sw_rows(qs)['rows'],'v10_software_assets.csv')
            if p=='/api/v10final/sample/hardware.csv': return csv_out(self,[{'asset_code':'NXT-CPU-01','asset_name':'Dell OptiPlex','asset_type':'CPU','vendor_name':'Vendor','serial_number':'SERIAL123','tagname_hostname':'PC-01','asset_location':'Studio 1','status':'Working'}],'hardware_sample.csv')
            if p=='/api/v10final/sample/software.csv': return csv_out(self,[{'software_name':'Microsoft Office','version':'2021','publisher':'Microsoft','license_key':'XXXXX','license_type':'Volume','assigned_to':'PC-01','status':'Active'}],'software_sample.csv')
        except Exception as e: return send(self,{'ok':False,'error':str(e),'trace':traceback.format_exc()[-3000:]},500)
        return old_get(self)
    def do_POST(self):
        p,qs=parse(self.path)
        try:
            if p=='/api/v10final/inventory/hardware/save': return send(self,api.save_hw(read_json(self)))
            if p=='/api/v10final/inventory/software/save': return send(self,api.save_sw(read_json(self)))
            if p=='/api/v10final/branding': return send(self,api.save_settings('branding_settings',read_json(self)))
            if p=='/api/v10final/retention': return send(self,api.save_settings('retention_settings',read_json(self)))
            if p=='/api/v10final/inventory/sync': return send(self,{'ok':True,'matched':0,'total_assets':api.count('hardware_assets'),'message':'sync endpoint available; detailed matching uses live serial/tag data only'})
        except Exception as e: return send(self,{'ok':False,'error':str(e),'trace':traceback.format_exc()[-3000:]},500)
        return old_post(self)
    def do_DELETE(self):
        p,qs=parse(self.path)
        try:
            if p=='/api/v10final/inventory/hardware': return send(self,api.delete('hardware_assets','asset_uid',s((qs.get('asset_uid') or qs.get('id') or [''])[0]),'asset_edit_audit_log'))
            if p=='/api/v10final/inventory/software': return send(self,api.delete('software_assets','software_uid',s((qs.get('software_uid') or qs.get('id') or [''])[0]),'software_edit_audit_log'))
        except Exception as e: return send(self,{'ok':False,'error':str(e),'trace':traceback.format_exc()[-3000:]},500)
        if old_del: return old_del(self)
        return send(self,{'error':'not found'},404)
    Handler.do_GET=do_GET; Handler.do_POST=do_POST; Handler.do_DELETE=do_DELETE
    print(PHASE_NAME+'_LOADED '+PHASE_VERSION)
