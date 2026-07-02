
param([string]$App="D:\SagarMonitor_V10_CleanBuild",[int]$DefaultKeepDays=5)
$ErrorActionPreference="Stop"
$Db=Join-Path $App "data\monitor_v10_notify.db"
$LogDir=Join-Path $App "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Report=Join-Path $LogDir ("v10_retention_cleanup_"+(Get-Date -Format "yyyyMMdd_HHmmss")+".json")
$Py=@'
import sqlite3,json,datetime,sys
from pathlib import Path
app=Path(sys.argv[1]); db=Path(sys.argv[2]); default_keep=int(sys.argv[3]); report=Path(sys.argv[4])
out={"ok":False,"db":str(db),"default_keep_days":default_keep,"deleted":{},"errors":[]}
if not db.exists():
    out["errors"].append("DB not found"); report.write_text(json.dumps(out,indent=2),encoding="utf-8"); print(json.dumps(out,indent=2)); raise SystemExit(0)
con=sqlite3.connect(db,timeout=60); con.row_factory=sqlite3.Row; cur=con.cursor(); keep=default_keep
try:
    rows=cur.execute("SELECT key,value FROM settings WHERE key IN ('retention_keep_days','history_keep_days','data_retention_days')").fetchall()
    for r in rows:
        try:
            v=int(float(str(r['value']).strip()))
            if 1<=v<=365: keep=v; break
        except Exception: pass
except Exception as e: out["errors"].append("settings read failed: "+str(e))
cutoff=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=keep)).isoformat(); out["keep_days"]=keep; out["cutoff_utc"]=cutoff
for table,col in {"heartbeats":"received_at","notifications":"created_at","change_events":"created_at","client_messages":"created_at","client_message_receipts":"delivered_at"}.items():
    try:
        cols=[x[1] for x in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols: out["deleted"][table]="skip_missing_column"; continue
        out["deleted"][table]=cur.execute(f"DELETE FROM {table} WHERE {col} < ?",(cutoff,)).rowcount
    except Exception as e: out["errors"].append(f"{table}: {e}")
try: con.commit()
except Exception as e: out["errors"].append("commit: "+str(e))
finally: con.close()
out["ok"]=len(out["errors"])==0; out["created_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat(); report.write_text(json.dumps(out,indent=2),encoding="utf-8"); print(json.dumps(out,indent=2))
'@
$Tmp=Join-Path $env:TEMP "v10_retention_cleanup_from_setting.py"
[System.IO.File]::WriteAllText($Tmp,$Py,[System.Text.UTF8Encoding]::new($false))
python $Tmp $App $Db $DefaultKeepDays $Report
Write-Host "Report: $Report"
