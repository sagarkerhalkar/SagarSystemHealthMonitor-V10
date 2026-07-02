
# V10 inventory 30min/native bridge restored for old working frontend.
import csv, io, json, time, zipfile, uuid, re
from pathlib import Path
from urllib.parse import parse_qs

def install(Handler, BASE_DIR, load_latest):
    base = Path(BASE_DIR); data_dir = base / "data"; data_dir.mkdir(parents=True, exist_ok=True)
    hw_store = data_dir / "hw_inventory_editable.json"; sw_store = data_dir / "software_license_editable.json"
    def _read_json(path, default):
        try:
            if path.exists():
                txt = path.read_text(encoding="utf-8-sig", errors="replace").strip()
                if txt: return json.loads(txt)
        except Exception as e: print("INV30 read_json failed", path, e, flush=True)
        return default
    def _write_json(path, data):
        tmp = path.with_suffix(path.suffix + ".tmp"); tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"); tmp.replace(path)
    def _norm_key(k): return str(k or "").strip().lstrip("\ufeff").lower().replace(" ", "_").replace("/", "_").replace("-", "_")
    def _canon_hw(row):
        r = {_norm_key(k): ("" if v is None else str(v)) for k, v in dict(row or {}).items()}
        mapping = {"vendor":"vendor_name","make":"make_name","model":"model_name","warranty_date":"warranty_end_date","bill_no":"po_invoice_bill_no","bill_photo_url":"po_invoice_bill_path","hostname_or_tag":"tagname_hostname","location_room":"asset_location","assigned_user":"assigned_to","remark":"remarks","model_or_config":"configuration_details"}
        for a,b in mapping.items():
            if not r.get(b) and r.get(a): r[b]=r.get(a,"")
        if not r.get("asset_uid"):
            seed=(r.get("asset_code") or r.get("serial_number") or r.get("tagname_hostname") or str(uuid.uuid4()))
            r["asset_uid"]="HW-"+re.sub(r"[^A-Za-z0-9]","",seed.upper())[:16]
        if not r.get("asset_name"): r["asset_name"]=" ".join(x for x in [r.get("make_name"),r.get("model_name"),r.get("asset_type") or r.get("category")] if x).strip()
        if not r.get("category") and r.get("asset_type"): r["category"]=r["asset_type"]
        if not r.get("asset_type") and r.get("category"): r["asset_type"]=r["category"]
        return r
    def _canon_sw(row):
        r={_norm_key(k):("" if v is None else str(v)) for k,v in dict(row or {}).items()}
        if not r.get("license_uid"):
            seed=(r.get("software_name") or r.get("name") or str(uuid.uuid4()))
            r["license_uid"]="SW-"+re.sub(r"[^A-Za-z0-9]","",seed.upper())[:16]+"-"+str(int(time.time()*1000))[-6:]
        if not r.get("software_name") and r.get("name"): r["software_name"]=r.get("name","")
        if not r.get("vendor_name") and r.get("vendor"): r["vendor_name"]=r.get("vendor","")
        if not r.get("publisher") and r.get("vendor_name"): r["publisher"]=r.get("vendor_name","")
        return r
    def load_hw():
        if hw_store.exists(): return [_canon_hw(r) for r in _read_json(hw_store, []) if isinstance(r,dict)]
        for name in ["fresh_hw_inventory_v2.json","fresh_hw_inventory.json","inventory_assets.json"]:
            rows=_read_json(data_dir/name, [])
            if isinstance(rows,list) and rows:
                rows=[_canon_hw(r) for r in rows if isinstance(r,dict)]; _write_json(hw_store, rows); return rows
        return []
    def save_hw(rows): _write_json(hw_store, [_canon_hw(r) for r in rows])
    def load_sw_licenses():
        if sw_store.exists(): return [_canon_sw(r) for r in _read_json(sw_store, []) if isinstance(r,dict)]
        for name in ["software_asset_register_2294.json","fresh_sw_inventory.json"]:
            rows=_read_json(data_dir/name, [])
            if isinstance(rows,list) and rows:
                rows=[_canon_sw(r) for r in rows if isinstance(r,dict)]; _write_json(sw_store, rows); return rows
        _write_json(sw_store, []); return []
    def save_sw(rows): _write_json(sw_store, [_canon_sw(r) for r in rows])
    def latest_machines():
        try: return load_latest() or []
        except Exception as e: print("INV30 load_latest failed", e, flush=True); return []
    def val(row,*keys):
        for k in keys:
            v=row.get(k)
            if v not in (None,"","NA","N/A","na","n/a"): return str(v)
        return ""
    def match_live(row,machines):
        keys=[val(row,"serial_number"),val(row,"tagname_hostname"),val(row,"asset_code"),val(row,"asset_name")]
        keys=[k.lower().strip() for k in keys if k and k.lower().strip() not in ("na","n/a","none")]
        for m in machines:
            blob=json.dumps(m, ensure_ascii=False, default=str).lower(); host=str(m.get("hostname") or "").lower(); mid=str(m.get("machine_id") or "").lower()
            if any(k and (k==host or k in host or k in mid or k in blob) for k in keys): return m
        return None
    def enrich_hw(rows):
        machines=latest_machines(); out=[]
        for r0 in rows:
            r=dict(r0); m=match_live(r,machines)
            if m:
                r.update({"live_sync_status":"MATCHED","live_hostname":m.get("hostname",""),"live_machine_id":m.get("machine_id",""),"live_ip":m.get("primary_ip",""),"live_online":"Online" if m.get("online") else "Offline","live_last_seen":m.get("updated_at","")})
            else: r.setdefault("live_sync_status","Not matched")
            out.append(r)
        return out
    def filt(rows,qs):
        q=(qs.get("q") or [""])[0].lower().strip(); category=(qs.get("category") or [""])[0].lower(); room=(qs.get("room") or [""])[0].lower(); person=(qs.get("person") or [""])[0].lower(); vendor=(qs.get("vendor") or [""])[0].lower(); status=(qs.get("status") or [""])[0].lower(); out=[]
        for r in rows:
            blob=json.dumps(r,ensure_ascii=False,default=str).lower()
            if q and q not in blob: continue
            if category and category != val(r,"category","asset_type").lower(): continue
            if room and room != val(r,"asset_location","location_room").lower(): continue
            if person and person != val(r,"assigned_to","assigned_user").lower(): continue
            if vendor and vendor != val(r,"vendor_name","vendor").lower(): continue
            if status and status != val(r,"status").lower(): continue
            out.append(r)
        return out
    def uniq(rows,*keys):
        s=[]; seen=set()
        for r in rows:
            v=val(r,*keys).strip()
            if v and v.lower() not in seen: seen.add(v.lower()); s.append(v)
        return sorted(s,key=lambda x:x.lower())[:1000]
    def missing(rows,*keys): return sum(1 for r in rows if not val(r,*keys))
    def hw_summary():
        rows=enrich_hw(load_hw()); serials={}
        for r in rows:
            s=val(r,"serial_number").lower()
            if s and s not in ("na","n/a","none"): serials[s]=serials.get(s,0)+1
        dups=sum(c-1 for c in serials.values() if c>1)
        return {"ok":True,"assets":len(rows),"missing_vendor":missing(rows,"vendor_name"),"missing_make":missing(rows,"make_name"),"missing_serial":missing(rows,"serial_number"),"missing_tag":missing(rows,"tagname_hostname"),"missing_person":missing(rows,"assigned_to"),"missing_room":missing(rows,"asset_location"),"missing_bill":missing(rows,"po_invoice_bill_no","po_invoice_bill_path"),"duplicates":dups,"categories":uniq(rows,"category","asset_type"),"rooms":uniq(rows,"asset_location"),"persons":uniq(rows,"assigned_to"),"vendors":uniq(rows,"vendor_name"),"statuses":uniq(rows,"status")}
    def sw_live_rows():
        rows=[]
        for m in latest_machines():
            host=m.get("hostname") or m.get("machine_id") or ""; ip=m.get("primary_ip") or ""; p=m.get("payload") if isinstance(m.get("payload"),dict) else {}
            if isinstance(p.get("payload"),dict): p=p.get("payload")
            apps=[]
            if isinstance(p.get("software"),dict): apps=p.get("software",{}).get("apps") or []
            if not apps and isinstance(m.get("software"),list): apps=m.get("software")
            for a in apps:
                if isinstance(a,dict): rows.append({"hostname":host,"ip":ip,"software_name":a.get("name") or a.get("software_name") or "","publisher":a.get("publisher") or "","version":a.get("version") or "","install_date":a.get("install_date") or a.get("installDate") or "","source":"live_client"})
        return rows
    def sw_summary():
        lic=load_sw_licenses(); live=sw_live_rows(); return {"ok":True,"license_rows":len(lic),"live_software_rows":len(live),"missing_license_bill":missing(lic,"po_invoice_bill_no","po_invoice_bill_path"),"missing_assigned_machine":missing(lic,"assigned_machine"),"vendors":uniq(lic,"vendor_name","publisher"),"statuses":uniq(lic,"status")}
    def csv_bytes(rows,filename):
        allkeys=[]; seen=set()
        for r in rows:
            for k in r.keys():
                if k not in seen: seen.add(k); allkeys.append(k)
        if not allkeys: allkeys=["message"]
        out=io.StringIO(newline=""); w=csv.DictWriter(out,fieldnames=allkeys,extrasaction="ignore"); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in allkeys})
        return out.getvalue().encode("utf-8-sig"), {"Content-Disposition":f'attachment; filename="{filename}"'}
    def send_csv(self, rows, filename):
        body,headers=csv_bytes(rows,filename); return self._send(200, body, "text/csv; charset=utf-8", headers)
    def hw_gaps(): return [r for r in enrich_hw(load_hw()) if not val(r,"vendor_name") or not val(r,"serial_number") or not val(r,"tagname_hostname") or not val(r,"assigned_to") or not val(r,"po_invoice_bill_no","po_invoice_bill_path")]
    def hw_dups():
        rows=enrich_hw(load_hw()); counts={}
        for r in rows:
            s=val(r,"serial_number").lower()
            if s and s not in ("na","n/a","none"): counts[s]=counts.get(s,0)+1
        return [r for r in rows if counts.get(val(r,"serial_number").lower(),0)>1]
    def hw_warranty(): return [r for r in enrich_hw(load_hw()) if not val(r,"warranty_end_date","warranty_end_year")]
    def send_zip(self):
        mem=io.BytesIO()
        with zipfile.ZipFile(mem,"w",zipfile.ZIP_DEFLATED) as z:
            for name,rows in [("hardware_register.csv",enrich_hw(load_hw())),("software_license_register.csv",load_sw_licenses()),("live_software.csv",sw_live_rows()),("hardware_missing_data.csv",hw_gaps()),("hardware_duplicates.csv",hw_dups()),("hardware_warranty.csv",hw_warranty())]:
                body,_=csv_bytes(rows,name); z.writestr(name,body)
            z.writestr("README_AUDIT_NOTE.txt","ISO/ITAM evidence export generated by V10. Evidence support, not certification.\n")
        return self._send(200, mem.getvalue(), "application/zip", {"Content-Disposition":"attachment; filename=iso_itam_audit_pack.zip"})
    orig_get=Handler.do_GET; orig_post=Handler.do_POST
    def do_GET(self):
        path=self.path.split("?",1)[0]; qs=parse_qs(self.path.split("?",1)[1]) if "?" in self.path else {}
        try:
            if not path.startswith("/api/inv30/"): return orig_get(self)
            if hasattr(self,"is_authenticated") and not self.is_authenticated(): return self.send_json({"error":"login_required"},401)
            if path=="/api/inv30/hw/summary": return self.send_json(hw_summary())
            if path=="/api/inv30/hw/assets": return self.send_json({"ok":True,"rows":filt(enrich_hw(load_hw()),qs)[:5000]})
            if path=="/api/inv30/hw/export.csv": return send_csv(self,filt(enrich_hw(load_hw()),qs),"hardware_asset_register.csv")
            if path=="/api/inv30/hw/gaps.csv": return send_csv(self,hw_gaps(),"hardware_missing_data.csv")
            if path=="/api/inv30/hw/duplicates.csv": return send_csv(self,hw_dups(),"hardware_duplicates.csv")
            if path=="/api/inv30/hw/warranty.csv": return send_csv(self,hw_warranty(),"hardware_warranty_review.csv")
            if path=="/api/inv30/sw/summary": return self.send_json(sw_summary())
            if path=="/api/inv30/sw/licenses":
                q=(qs.get("q") or [""])[0].lower().strip(); rows=load_sw_licenses()
                if q: rows=[r for r in rows if q in json.dumps(r,ensure_ascii=False,default=str).lower()]
                return self.send_json({"ok":True,"rows":rows[:5000]})
            if path=="/api/inv30/sw/live": return self.send_json({"ok":True,"rows":sw_live_rows()[:5000]})
            if path=="/api/inv30/sw/licenses.csv": return send_csv(self,load_sw_licenses(),"software_license_register.csv")
            if path=="/api/inv30/sw/live.csv": return send_csv(self,sw_live_rows(),"live_installed_software.csv")
            if path=="/api/inv30/iso/summary": return self.send_json({"ok":True,"hardware_assets":len(load_hw()),"software_license_rows":len(load_sw_licenses()),"live_software_rows":len(sw_live_rows()),"hardware_gap_rows":len(hw_gaps()),"duplicate_rows":len(hw_dups()),"warranty_issue_rows":len(hw_warranty())})
            if path=="/api/inv30/iso/audit-pack.zip": return send_zip(self)
            return self.send_json({"error":"inv30 not found"},404)
        except Exception as e:
            import traceback; traceback.print_exc(); return self.send_json({"error":str(e)},500)
    def do_POST(self):
        path=self.path.split("?",1)[0]
        try:
            if not path.startswith("/api/inv30/"): return orig_post(self)
            if hasattr(self,"require_admin") and not self.require_admin(): return
            body=self.read_json() if hasattr(self,"read_json") else {}
            if path=="/api/inv30/hw/save":
                row=_canon_hw(body); rows=load_hw(); uid=row.get("asset_uid"); done=False
                for i,r in enumerate(rows):
                    if r.get("asset_uid")==uid: rows[i]=row; done=True; break
                if not done: rows.insert(0,row)
                save_hw(rows); return self.send_json({"ok":True,"row":row,"summary":hw_summary()})
            if path=="/api/inv30/hw/delete":
                uid=str(body.get("asset_uid") or ""); rows=[r for r in load_hw() if r.get("asset_uid")!=uid]; save_hw(rows); return self.send_json({"ok":True,"deleted":uid,"summary":hw_summary()})
            if path=="/api/inv30/sw/save":
                row=_canon_sw(body); rows=load_sw_licenses(); uid=row.get("license_uid"); done=False
                for i,r in enumerate(rows):
                    if r.get("license_uid")==uid: rows[i]=row; done=True; break
                if not done: rows.insert(0,row)
                save_sw(rows); return self.send_json({"ok":True,"row":row,"summary":sw_summary()})
            if path=="/api/inv30/sw/delete":
                uid=str(body.get("license_uid") or ""); rows=[r for r in load_sw_licenses() if r.get("license_uid")!=uid]; save_sw(rows); return self.send_json({"ok":True,"deleted":uid,"summary":sw_summary()})
            return self.send_json({"error":"inv30 post not found"},404)
        except Exception as e:
            import traceback; traceback.print_exc(); return self.send_json({"error":str(e)},500)
    Handler.do_GET=do_GET; Handler.do_POST=do_POST
    print("INVENTORY_30MIN_NATIVE_API_RESTORED", flush=True)
