# V10 UI Binding Failure From Video — 2026-07-03

## Summary
The latest video shows the V10 UI still feels like progress is not visible because verified 2278 data is not cleanly replacing old UI sections.

## Root cause
Previous packages added new live/read-only sections under old V10 sections. This was safe for testing but wrong for final UX.

## Required fix
Use one selected-machine state across these tabs:

- Machine 360
- Network + VPN
- Hardware Intelligence
- Software Intelligence
- USB + Peripherals
- Human Change Log

Machine Fleet stays as fleet table only. The selected machine opens or populates the other tabs.

## Page behavior required

### Home
Compact command center only:
- 3D animated machine health summary.
- Today Download / Today Upload / Current Download / Current Upload.
- Total / fresh / stale / issue clients from 2278.
- Hardware/SW asset count.
- ISP/WAN summary.
- Alert summary.
No long mixed page.

### Machine Fleet
Fleet table only:
- Search.
- Fresh/stale/issue filters.
- Click machine to Machine 360.
- CSV export.

### Machine 360
Selected machine only:
- Hostname.
- Machine ID.
- Asset fingerprint.
- Official serial separately.
- CPU/RAM/disk/GPU/USB/network/software cards.
- Full tables for disks, GPUs, USB, adapters, software.

### Network + VPN
Selected machine only:
- Adapters.
- IP/MAC/gateway/DNS/status/speed.
- Public IP.
- ISP route.
- VPN status.
- CSV export.

### Hardware Intelligence
Selected machine only:
- CPU detail.
- RAM detail.
- Storage detail.
- GPU detail.
- USB/peripherals detail.
- Completeness/evidence score.

### Software Intelligence
Selected machine only:
- Installed software list for selected machine.
- Search within selected machine.
- Publisher/version/install date/license fields where available.
- CSV export.

## Design rule
No duplicate old/new blocks. No fleet table inside selected-machine pages except where explicitly needed as a selector.
