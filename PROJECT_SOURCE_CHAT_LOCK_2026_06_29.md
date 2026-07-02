# PROJECT SOURCE CHAT LOCK — 2026-06-29

Project: **Sagar Kerhalkar System Health Monitor Tool**  
Current working context: **V10 test build on port 2294**  
Live production must remain untouched: **D:\SagarSystemHealthMonitor / port 2278 / monitor.sagarkerhalkar.com**

This file records the full working decision state from the latest ChatGPT project session so the next chat/developer does not repeat the same mistakes.

---

## 1. Locked safety rules

1. Do **not** touch live production `2278` unless Sagar explicitly says so.
2. V10 test folder is `D:\SagarMonitor_V10_CleanBuild`.
3. V10 test port is `2294`.
4. V10 reads the live DB read-only; never copy the huge live DB.
5. Do **not** change Ubuntu client now.
6. Do **not** change Windows clients until backend/UI is stable.
7. Do **not** fake hardware values. If exact value is not available, show `N/A`.
8. Keep 12-second offline window. User accepted this and rejected changing it to 2 minutes.
9. Inventory must be merged into the **main dashboard left menu**, not a floating modal and not an ugly separate page.
10. All UI changes must be integrated with the existing dashboard style and navigation.

---

## 2. Backend identity status — solved

The V10 identity backend was created as:

```text
D:\SagarMonitor_V10_CleanBuild\V10_IDENTITY_CORE_2294.py
D:\SagarMonitor_V10_CleanBuild\RUN_V10_IDENTITY_CORE_2294.ps1
```

Validated target result:

```text
/api/overview total = 57
/api/machines count = 57
machine_current.csv rows = 57
Dashboard card = 57
UNKNOWN-HOST removed
DESKTOP-1VTKP12 merged as one
Hostname changes merge by serial/MAC/UUID history
New machine should still appear properly
```

The backend groups machines using serial/MAC/UUID tokens and uses hostname only as fallback.

---

## 3. CPU/RAM audit result

Current backend CPU/RAM data from audit:

```text
CPU/RAM machines = 57
CPU name = 57/57
CPU cores = 57/57
CPU threads = 57/57
CPU usage = 57/57
CPU current MHz = 56/57
CPU max MHz = 25/57
CPU temperature = 47/57
RAM total = 57/57
RAM used = 57/57
RAM free = 57/57
RAM usage = 57/57
RAM module/slot detail = 0/57
```

Meaning:

- CPU/RAM capacity and usage are mostly correct.
- Missing RAM slot/module details require future Windows client collector work.
- CPU temp/source is partial.
- Do not fake missing values.

---

## 4. GPU audit result and truth rule

Current GPU CSV showed about 66 GPU rows across 57 machines.

Correct interpretation:

### NVIDIA dedicated GPUs

Use `nvidia-smi` as truth:

```text
GPU name = exact
Dedicated VRAM = exact
Used VRAM = exact
Usage % = exact
Temperature = exact
Source = nvidia-smi
```

### Intel/AMD integrated GPUs

Only show exact OS-reported values:

```text
Name = OK
Driver = OK
Shared system memory = separate field
Usage/temp = N/A unless exact counter exists
Do not count shared RAM as GPU capacity
Do not treat WMI AdapterRAM as exact dedicated VRAM for integrated GPU
```

### Ubuntu/lspci

Ubuntu GPU rows from `lspci` should remain unchanged now:

```text
Name only
Capacity/usage/temp = N/A unless proper collector is added later
```

---

## 5. Inventory requirement — current locked requirement

User wants H/W inventory from Google Sheet source integrated into the current dashboard.

Google Sheet source URL provided by user:

```text
https://docs.google.com/spreadsheets/d/1xZsdL8zrLt195roBu73bN70qy_Em631V/edit?gid=1702271119#gid=1702271119
```

Fetched file name:

```text
Nexttoppers Assets Detail.xlsx
```

Base sheet columns found:

```text
Code
Name
AssetType
Details
Quantity
Rate
WarrantyDate
PurchaseDate
SerialNumber
VendorName
```

User-required editable columns:

```text
Make Name
Model Name
Asset Name
Asset Type / Category
Configuration / Details
Vendor Name
Warranty End Date
Warranty End Year
Purchase Date
PO / Invoice / Bill No
PO / Invoice / Bill Path
Tagname / Hostname
Serial Number
Assigned To / Person
Room / Location
Status
Remarks
Live Sync Status
```

Required filters:

```text
Category wise
Room wise
Person wise
Vendor wise
Status wise
Serial / Tag / Hostname wise
Free search
```

Required actions:

```text
Add asset
Edit asset
Delete asset
Remove duplicates
Sync with live machine data
Download CSV
```

---

## 6. Inventory data files currently present in V10

From verification:

```text
D:\SagarMonitor_V10_CleanBuild\data\fresh_hw_inventory_v2.json exists = True
fresh_hw_inventory_v2 rows = 370
D:\SagarMonitor_V10_CleanBuild\data\inventory_assets.json exists = True
inventory_assets rows = 477
```

Meaning:

- Data is present.
- The failure is not missing data.
- The failure is UI/backend route integration.

---

## 7. What failed and must not be repeated

Several previous patches were wrong. Do **not** repeat these patterns:

1. Do not add a separate ugly `/inventory-manager` page.
2. Do not add a bottom-right floating `Inventory / ISO` modal.
3. Do not call old broken APIs like:

```text
/api/v10/current-machines
/api/v10/hardware-inventory
```

They caused:

```text
401 Unauthorized
Unexpected token '<', '<!doctype ... is not valid JSON
```

4. Do not inject route code blindly before proving it is inside the active server file.
5. Do not print success when Python patch failed. The patch must check `$LASTEXITCODE`.
6. Last patch caused root page to show a blank white page. This means the active frontend/server was broken by injection and needs rollback/debug before more features.

---

## 8. Current visible problem

After latest UI integration attempt, opening:

```text
http://127.0.0.1:2294/
```

showed a blank white page.

Likely cause:

- frontend JS injection or server hook broke the current index/app load, or
- V10 server is returning an incomplete/failed response, or
- JS runtime error prevents dashboard rendering.

Before adding more inventory work, recover the dashboard.

---

## 9. Immediate recovery checklist

Run on Sagar's Windows machine if V10 page is blank:

```powershell
$V10 = "D:\SagarMonitor_V10_CleanBuild"

# Stop V10 only
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match "2294|V10_IDENTITY_CORE|SagarMonitor_V10_CleanBuild" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Find latest backup made before main UI H/W inventory patch
Get-ChildItem $V10 -Directory -Filter "_BACKUP_BEFORE_MAIN_UI_HW_INVENTORY_*" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 FullName,LastWriteTime
```

If a backup folder exists, restore:

```powershell
$V10 = "D:\SagarMonitor_V10_CleanBuild"
$Backup = Get-ChildItem $V10 -Directory -Filter "_BACKUP_BEFORE_MAIN_UI_HW_INVENTORY_*" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if (!$Backup) { throw "No backup folder found" }

Copy-Item "$($Backup.FullName)\V10_IDENTITY_CORE_2294.py" "$V10\V10_IDENTITY_CORE_2294.py" -Force
Copy-Item "$($Backup.FullName)\index.html" "$V10\public\index.html" -Force
Copy-Item "$($Backup.FullName)\app.js" "$V10\public\app.js" -Force -ErrorAction SilentlyContinue
Copy-Item "$($Backup.FullName)\styles.css" "$V10\public\styles.css" -Force -ErrorAction SilentlyContinue

cd $V10
python -m py_compile .\V10_IDENTITY_CORE_2294.py
powershell -ExecutionPolicy Bypass -File "$V10\RUN_V10_IDENTITY_CORE_2294.ps1"
```

Then test:

```powershell
Invoke-WebRequest "http://127.0.0.1:2294/" -UseBasicParsing | Select-Object StatusCode
```

Expected: dashboard loads again.

---

## 10. Correct next implementation plan

Do not create a new page first. Do not create a floating modal.

Correct integration plan:

### Step A — inspect current dashboard UI system

Find exact active files:

```powershell
$V10 = "D:\SagarMonitor_V10_CleanBuild"
Get-ChildItem $V10\public -File | Select-Object Name,Length,LastWriteTime
Select-String -Path "$V10\public\app.js" -Pattern "Command Center|Machine 360|Hardware|Software|Deploy|Settings" -Context 2,2
```

### Step B — add a real section to existing app.js

Add left menu item exactly where existing menu is rendered:

```text
H/W Inventory
```

It must behave like existing sections, not separate route.

### Step C — backend API endpoints

Use clean backend endpoints only:

```text
/api/hw-inventory-main/summary
/api/hw-inventory-main/assets
/api/hw-inventory-main/save
/api/hw-inventory-main/delete
/api/hw-inventory-main/sync-save
/api/hw-inventory-main/dedupe-save
/api/hw-inventory-main/export.csv
```

### Step D — UI panel inside dashboard

Panel must show:

```text
cards: total assets, missing vendor, missing make, missing model, missing serial, missing tag/host, missing person, missing room, missing bill/PO
filters: category, room, person, vendor, status, free search
table: all required columns
actions: edit, delete, add, sync, CSV download
```

### Step E — QA must pass before user opens browser

Required PowerShell QA:

```powershell
$r = Invoke-WebRequest "http://127.0.0.1:2294/" -UseBasicParsing
"ROOT_STATUS=$($r.StatusCode)"
"ROOT_HAS_APP=$($r.Content.Length -gt 1000)"

$j = Invoke-RestMethod "http://127.0.0.1:2294/api/hw-inventory-main/summary"
$j | ConvertTo-Json -Depth 5
```

Expected:

```text
ROOT_STATUS=200
imported_assets = 370
```

---

## 11. Important lesson for next developer/chat

The inventory feature is possible. The failure was implementation approach, not requirement impossibility.

Do it as a proper app feature:

```text
existing dashboard navigation -> existing section renderer -> inventory panel -> backend JSON APIs
```

Do not keep patching with floating plugin scripts.

---

## 12. User mood / communication note

User is very frustrated because repeated patches broke or failed. Keep responses short, honest, and action-based.

Avoid:

```text
This should work
Maybe
Try this huge blind patch
```

Use:

```text
This failed because...
First recover dashboard.
Then patch only app.js section after verifying exact menu renderer.
```

