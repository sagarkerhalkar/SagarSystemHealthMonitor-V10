#!/usr/bin/env python3
# V10 Phase3 Fix4 extra API: sample CSV, CSV import, extra exports/status helpers.
from __future__ import annotations
import csv, io, json, traceback, urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Tuple

PHASE_NAME="V10_PHASE3_FIX4_EXTRA_API"
PHASE_VERSION="2026-07-03.4"

def _send_json(handler: Any, obj: Any, status: int = 200) -> None:
    body=json.dumps(obj,ensure_ascii=False,default=str).encode('utf-8')
    handler.send_response(status); handler.send_header('Content-Type','application/json; charset=utf-8')
    handler.send_header('Content-Length',str(len(body))); handler.send_header('Cache-Control','no-store'); handler.end_headers(); handler.wfile.write(body)

def _read_json(handler: Any) -> Dict[str, Any]:
    n=int(handler.headers.get('Content-Length') or 0); raw=handler.rfile.read(n) if n else b'{}'
    try:
        data=json.loads(raw.decode('utf-8',errors='replace') or '{}')
        return data if isinstance(data,dict) else {}
    except Exception:
        return {}

def _csv_response(handler: Any, rows: List[Dict[str,Any]], filename: str) -> None:
    fields=[]
    for r in rows or []:
        if isinstance(r,dict):
            for k in r.keys():
                if k not in fields: fields.append(k)
    if not fields:
        fields=['message']; rows=[{'message':'no rows'}]
    buf=io.StringIO(); w=csv.DictWriter(buf, fieldnames=fields, extrasaction='ignore'); w.writeheader()
    for r in rows: w.writerow(r if isinstance(r,dict) else {'message':str(r)})
    body=buf.getvalue().encode('utf-8-sig')
    handler.send_response(200); handler.send_header('Content-Type','text/csv; charset=utf-8')
    handler.send_header('Content-Disposition',f'attachment; filename="{filename}"')
    handler.send_header('Content-Length',str(len(body))); handler.send_header('Cache-Control','no-store'); handler.end_headers(); handler.wfile.write(body)

def _s(v: Any) -> str:
    return '' if v is None else str(v).strip()

def install(Handler: Any, BASE_DIR: Any, load_latest: Any, *args: Any, **kwargs: Any) -> None:
    # Reuse the Phase1 bridge where possible.
    try:
        import importlib.util
        bridge_file=Path(BASE_DIR)/'v10_final_bridge.py'
        spec=importlib.util.spec_from_file_location('v10_final_bridge_fix3', str(bridge_file))
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)  # type: ignore
        bridge=mod.V10Bridge(Handler, BASE_DIR, load_latest)
        bridge.migrate(); bridge.import_hw_if_needed(False)
    except Exception as e:
        bridge=None
        print('V10_PHASE3_FIX3_EXTRA_API_BRIDGE_INIT_FAILED', e)
    old_get=Handler.do_GET
    old_post=Handler.do_POST

    def parse_qs(handler: Any) -> Tuple[str, Dict[str,List[str]]]:
        raw=handler.path; path=raw.split('?',1)[0]; qs=urllib.parse.parse_qs(raw.split('?',1)[1]) if '?' in raw else {}; return path, qs

    def do_GET(self: Any) -> None:
        path,qs=parse_qs(self)
        try:
            if path=='/api/v10final/sample/hardware.csv':
                return _csv_response(self,[{
                    'asset_code':'NXT-LAP-001','make_name':'Dell','model_name':'Latitude 5420','asset_name':'Teacher Laptop','asset_type':'Laptop','vendor_name':'Vendor Name','warranty_end_date':'2027-03-31','purchase_date':'2024-04-01','po_invoice_bill_no':'INV-001','tagname_hostname':'TEACHER-PC-01','serial_number':'ABC123456','assigned_to':'Teacher Name','asset_location':'Studio 1','status':'Working','remarks':'sample row'
                }],'hardware_asset_register_sample.csv')
            if path=='/api/v10final/sample/software.csv':
                return _csv_response(self,[{
                    'hostname':'TEACHER-PC-01','software_name':'Microsoft Office','version':'2021','publisher':'Microsoft','license_key':'XXXXX-XXXXX','license_type':'Volume','assigned_to':'Teacher Name','status':'Active','remarks':'sample row'
                }],'software_asset_register_sample.csv')
            if path=='/api/v10final/export/machines.csv' and bridge:
                return _csv_response(self, bridge.latest(), 'machine_fleet_live.csv')
            if path=='/api/v10final/export/machine360.csv' and bridge:
                data=bridge.machine360(qs); rows=[]
                for sec in ['summary','hardware','network','inventory_sync']:
                    obj=data.get(sec) if isinstance(data,dict) else {}
                    if isinstance(obj,dict):
                        for k,v in obj.items(): rows.append({'section':sec,'field':k,'value':json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v})
                for i,x in enumerate(data.get('usb') or []): rows.append({'section':'usb','field':str(i),'value':json.dumps(x,ensure_ascii=False)})
                for i,x in enumerate(data.get('software') or []): rows.append({'section':'software','field':str(i),'value':json.dumps(x,ensure_ascii=False)})
                return _csv_response(self, rows, 'machine360_live.csv')
            if path=='/api/v10final/export/network.csv' and bridge:
                data=bridge.machine360(qs); net=data.get('network') or {}; rows=[]
                for k,v in net.items(): rows.append({'field':k,'value':json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v})
                return _csv_response(self, rows, 'machine_network_vpn_live.csv')
            if path=='/api/v10final/network/isp' and bridge:
                rows=[]
                for m in bridge.latest():
                    payload=m.get('payload') if isinstance(m.get('payload'),dict) else {}
                    net=payload.get('network') if isinstance(payload.get('network'),dict) else {}
                    pub=net.get('public_internet') if isinstance(net.get('public_internet'),dict) else {}
                    rows.append({'machine_id':m.get('machine_id'),'hostname':m.get('hostname'),'isp':pub.get('isp') or net.get('isp') or '', 'public_ip':pub.get('public_ip') or net.get('public_ip') or '', 'download_mbps':net.get('current_download_mbps') or net.get('download_mbps') or '', 'upload_mbps':net.get('current_upload_mbps') or net.get('upload_mbps') or '', 'latency_ms':net.get('latency_ms') or '', 'jitter_ms':net.get('jitter_ms') or '', 'packet_loss_percent':net.get('packet_loss_percent') or ''})
                return _send_json(self, {'ok':True,'count':len(rows),'rows':rows,'source':'live client payload/router/cloudflare when reported'})
        except Exception as e:
            return _send_json(self, {'ok':False,'error':str(e),'trace':traceback.format_exc()[-3000:]},500)

            if path=='/api/v10final/export/iso.csv' and bridge:
                try:
                    audit = bridge.iso_audit()
                except Exception:
                    audit = {}
                rows=[]
                if isinstance(audit, dict):
                    for sec,val in audit.items():
                        if isinstance(val, dict):
                            for k,v in val.items(): rows.append({'section':sec,'field':k,'value':v})
                        elif isinstance(val, list):
                            for i,x in enumerate(val): rows.append({'section':sec,'field':i,'value':json.dumps(x,ensure_ascii=False)})
                        else:
                            rows.append({'section':'summary','field':sec,'value':val})
                return _csv_response(self, rows, 'iso_audit_summary.csv')
            if path=='/api/v10final/export/usb.csv' and bridge:
                data=bridge.machine360(qs); return _csv_response(self, data.get('usb') or [], 'machine_usb_peripherals.csv')
            if path=='/api/v10final/export/software-live.csv' and bridge:
                data=bridge.machine360(qs); return _csv_response(self, data.get('software') or [], 'machine_installed_software.csv')
            if path=='/api/v10final/export/changes.csv' and bridge:
                with bridge.connect() as con:
                    try:
                        rows=[dict(r) for r in con.execute("SELECT * FROM change_events ORDER BY created_at DESC LIMIT 500")]
                    except Exception:
                        rows=[]
                return _csv_response(self, rows, 'human_change_log.csv')
            if path=='/api/v10final/export/messages.csv' and bridge:
                with bridge.connect() as con:
                    try:
                        rows=[dict(r) for r in con.execute("SELECT * FROM client_messages ORDER BY created_at DESC LIMIT 500")]
                    except Exception:
                        rows=[]
                return _csv_response(self, rows, 'client_messages_history.csv')
            if path=='/api/v10final/export/day-history.csv' and bridge:
                with bridge.connect() as con:
                    try:
                        rows=[dict(r) for r in con.execute("SELECT * FROM history_summary_cache ORDER BY day DESC, machine_id LIMIT 1000")]
                    except Exception:
                        rows=[]
                return _csv_response(self, rows, 'day_history_summary.csv')
            if path=='/api/v10final/settings/users' and bridge:
                with bridge.connect() as con:
                    try:
                        rows=[dict(r) for r in con.execute("SELECT id, username, role, created_at FROM users ORDER BY id DESC LIMIT 200")]
                    except Exception:
                        rows=[]
                return _send_json(self, {'ok':True,'users':rows,'roles':['viewer','asset_entry','organization_admin','super_admin']})
        return old_get(self)

    def do_POST(self: Any) -> None:
        path,qs=parse_qs(self)
        try:
            data=_read_json(self); rows=data.get('rows') if isinstance(data.get('rows'),list) else []
            if path=='/api/v10final/inventory/hardware/import-csv' and bridge:
                imported=0
                with bridge.connect() as con:
                    for row in rows:
                        if not isinstance(row,dict): continue
                        rr=mod._norm_hw(row)  # type: ignore
                        now=mod._now()  # type: ignore
                        vals=[rr.get(c,'') for c in mod.HW_COLUMNS] + [json.dumps(row,ensure_ascii=False), now, now]  # type: ignore
                        con.execute("""INSERT OR REPLACE INTO hardware_assets(asset_uid,asset_code,make_name,model_name,asset_name,asset_type,configuration_details,quantity,rate,vendor_name,warranty_end_date,warranty_end_year,purchase_date,po_invoice_bill_no,po_invoice_bill_path,tagname_hostname,serial_number,assigned_to,asset_location,status,remarks,source_sheet,source_row,live_sync_status,live_hostname,live_machine_id,live_ip,live_online,live_last_seen,extra_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
                        con.execute("INSERT INTO asset_edit_audit_log(asset_uid,action,before_json,after_json,actor,created_at) VALUES(?,?,?,?,?,?)", (rr.get('asset_uid'),'csv_import','',json.dumps(rr,ensure_ascii=False),'admin',now))
                        imported+=1
                    con.commit()
                return _send_json(self, {'ok':True,'imported':imported,'message':'hardware csv imported'})
            if path=='/api/v10final/inventory/software/import-csv' and bridge:
                imported=0
                with bridge.connect() as con:
                    for row in rows:
                        if not isinstance(row,dict): continue
                        rr=mod._norm_sw(row)  # type: ignore
                        vals=[rr.get(c,'') for c in mod.SW_COLUMNS]  # type: ignore
                        con.execute("""INSERT OR REPLACE INTO software_assets(software_uid,machine_id,hostname,software_name,version,publisher,install_date,install_location,license_key,license_type,assigned_to,status,source,remarks,extra_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
                        con.execute("INSERT INTO software_edit_audit_log(software_uid,action,before_json,after_json,actor,created_at) VALUES(?,?,?,?,?,?)", (rr.get('software_uid'),'csv_import','',json.dumps(rr,ensure_ascii=False),'admin',rr.get('updated_at')))
                        imported+=1
                    con.commit()
                return _send_json(self, {'ok':True,'imported':imported,'message':'software csv imported'})
        except Exception as e:
            return _send_json(self, {'ok':False,'error':str(e),'trace':traceback.format_exc()[-3000:]},500)

            if path=='/api/v10final/deploy/profiles/save' and bridge:
                with bridge.connect() as con:
                    con.execute("CREATE TABLE IF NOT EXISTS deploy_profiles(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, os_type TEXT, command TEXT, test_command TEXT, troubleshooting TEXT, message TEXT, notes TEXT, enabled INTEGER DEFAULT 1, updated_at TEXT)")
                    now=__import__('datetime').datetime.now().isoformat(timespec='seconds')
                    vals=(data.get('name',''),data.get('os_type',''),data.get('command',''),data.get('test_command',''),data.get('troubleshooting',''),data.get('message',''),data.get('notes',''),int(data.get('enabled',1)),now)
                    con.execute("INSERT INTO deploy_profiles(name,os_type,command,test_command,troubleshooting,message,notes,enabled,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", vals)
                    con.commit()
                return _send_json(self, {'ok':True,'message':'deploy profile saved'})
            if path=='/api/v10final/notifications/rules/save' and bridge:
                rid=_s(data.get('id') or data.get('rule_id'))
                if rid in ('cpu_high','ram_high') and not data.get('super_admin'):
                    return _send_json(self, {'ok':False,'error':'cpu_high and ram_high are locked off; only super admin can change locked rules'},403)
                with bridge.connect() as con:
                    cols=[]; vals=[]
                    for k in ['enabled','threshold','severity','cooldown_minutes']:
                        if k in data:
                            cols.append(f"{k}=?"); vals.append(data[k])
                    if cols and rid:
                        vals.append(rid); con.execute(f"UPDATE notification_rules SET {', '.join(cols)} WHERE id=?", vals); con.commit()
                return _send_json(self, {'ok':True,'message':'notification rule updated'})
            if path=='/api/v10final/settings/users/save' and bridge:
                username=_s(data.get('username')); role=_s(data.get('role') or 'viewer'); password=_s(data.get('password') or 'ChangeMe@123')
                if role not in ('viewer','asset_entry','organization_admin','super_admin'):
                    return _send_json(self, {'ok':False,'error':'invalid role'},400)
                import hashlib, datetime
                pw_hash=hashlib.sha256(password.encode('utf-8')).hexdigest(); now=datetime.datetime.now().isoformat(timespec='seconds')
                with bridge.connect() as con:
                    try:
                        con.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, role TEXT, created_at TEXT)")
                        con.execute("INSERT OR REPLACE INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)", (username,pw_hash,role,now)); con.commit()
                    except Exception as e:
                        return _send_json(self, {'ok':False,'error':str(e)},500)
                return _send_json(self, {'ok':True,'message':'user saved','username':username,'role':role})
        return old_post(self)

    Handler.do_GET=do_GET
    Handler.do_POST=do_POST
    print(f'{PHASE_NAME}_LOADED {PHASE_VERSION}')
