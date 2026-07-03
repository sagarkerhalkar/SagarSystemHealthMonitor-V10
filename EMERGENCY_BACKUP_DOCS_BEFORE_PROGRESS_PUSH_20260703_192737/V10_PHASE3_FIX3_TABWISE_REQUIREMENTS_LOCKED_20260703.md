# V10 Phase 3 Fix3 - Tab-wise Requirements Locked

Date: 2026-07-03
Mode: 2-day delivery mode

## New UI correction from user
The previous Phase 3 UI does not fully satisfy UI requirements. The new lock is:

- Header/sidebar must use logo, not team photo.
- Default organization/display name must be `Sagar`.
- Organization name must be editable from Settings for any future organization request.
- Team/photo must be used only as login/welcome background, with glass/effect content in front.
- Big title font must be reduced by about 50 percent.
- Every page must avoid too much scrolling. Large content must use pagination/search/filter.
- Every page footer must show corporate style small text: `Created by Sagar Kerhalkar · Contact: 8105977226 · Profile: sagarkerhalkar.com`.
- All tests must use live server data/API. No dummy data.

## Tab-wise requirement lock

### Home / Command Center
- Show logo and editable organization name.
- Machine-wise animated 3D live summary.
- Total client count from live server.
- Online client count from live server.
- Issue client count. Clicking issue count must open/filter issue machines.
- Hardware asset count and software asset count.
- Alert summary.
- Live ISP / internet details: upload, download, latency, jitter, packet loss, public IP and ISP where reported.
- ISP/router/cloud/tunnel data should come from live client/server data; Cloudflare/public tunnel values should be shown where available.
- No fake count; unavailable values must show `Not reported`.

### Machine Fleet
- Correct client count.
- Online/offline status.
- Last seen.
- IP address.
- OS.
- CPU/RAM.
- Page-wise table.
- Search option.
- Filters: all, online, offline, issue machines.
- Clicking/opening machine goes to Machine 360.
- CSV download option.
- Professional animation and readable font.

### Machine 360
- Full machine story.
- CPU details: name, cores, usage, temperature where real.
- RAM details: total, used, free, usage.
- SSD/HDD/NVMe details: total, used, free, usage, multiple disks.
- GPU details: name, memory, usage, temp only when real.
- USB and peripherals.
- Network and VPN.
- Installed software.
- Inventory sync details.
- Machine-wise CSV download.

### Network + VPN
- IP, MAC, adapters.
- Gateway.
- DNS.
- VPN status.
- ISP.
- Public IP.
- Latency.
- Jitter.
- Packet loss.
- Upload/download.
- Machine-wise CSV download.

### Software Intelligence
- Live installed software list machine-wise.
- Sync/fallback with Software Asset Register.
- Search.
- Page-wise table.
- CSV download.

### Hardware Asset Register
- H/W inventory.
- Search.
- Add/Edit/Delete.
- Export.
- Sync with live machines.
- CSV import for H/W inventory.
- Download sample H/W CSV.
- Page-wise table.

### Software Asset Register
- Software register/license.
- Live fallback, no fake rows.
- Search.
- Add/Edit/Delete.
- Export.
- Sync with live machines.
- CSV import for S/W inventory.
- Download sample S/W CSV.
- Page-wise table.

## Current implementation note
This Fix3 package updates UI and adds extra API endpoints for sample CSV, CSV import and exports. It still depends on live client payload quality for actual GPU/disk/USB/network fields. Missing client fields must show `Not reported`.
