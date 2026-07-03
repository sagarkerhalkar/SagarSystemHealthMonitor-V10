# V10 ISP/WAN Settings UI + Home Status

Date: 2026-07-03 17:32:52

## Scope
This phase only connects ISP/WAN Settings UI and Home ISP/WAN Status to the already-passed ISP/WAN DB/API.

## Locked requirement
- Settings page must allow Admin/Super Admin to add 1 to 10 ISP/WAN links.
- ISP details are entered once manually and then monitored automatically by backend probes.
- ISP/WAN data must not come from client laptop payload.
- Home page must show all ISP/WAN links configured in Settings.
- Per-WAN upload/download must show only when router API/SNMP/Omada/routed probe is connected; otherwise show Not reported, not dummy values.

## Fields
ISP Name, WAN Name/Number, Router IP, Gateway IP, WAN Interface/Port, Public IP, Expected Download, Expected Upload, Role, Enabled, Locked, Notes, Status, Last Checked, Latency, Jitter, Packet Loss, Current Download, Current Upload.

## Applied files
- public/v10_isp_wan_settings_ui.css
- public/v10_isp_wan_settings_ui.js
- tests/TEST_V10_ISP_WAN_SETTINGS_UI_HOME_STATUS.ps1

## Rollback
Restore public/index.html from: D:\SagarMonitor_V10_CleanBuild\INCREMENTAL_SOURCE_BACKUPS\BEFORE_ISP_WAN_UI_20260703_173252
