# V10 Video Error Root Cause and Next Solution

Date: 2026-07-03

## Source of truth

- V10 must read live data from the working 2278 monitor database in read-only mode.
- 2278 must not be modified.
- Source DB: `D:\SagarSystemHealthMonitor\data\monitor.db`
- Source table/data: `latest.summary_json`
- Working source counts already verified:
  - 64 machines from 2278
  - fresh machines around 28-32 depending on current heartbeat time
  - hardware arrays present: CPU, RAM, disk, GPU, USB, network
  - software rows: 58,353 from 2278 payload
  - notification simulation previously passed, but later UI clean test timed out on notification endpoint

## Video-observed errors

1. Home page is still too long and feels like old patch sections stacked together.
2. Home page does not yet look like a clean international/global command center.
3. 3D/animation effect is weak or missing.
4. Hostname / identity logic is not visually clear enough.
5. Machine Fleet is mostly acceptable, but UI needs refinement.
6. Machine 360 is about 80% acceptable, but software details are missing or weak.
7. Network + VPN page fails because it is not selected-machine focused enough.
8. Hardware Intelligence page fails because it still behaves/looks like fleet again.
9. Software Intelligence page fails because it is not selected-machine focused enough.
10. Old/new UI binding creates the feeling of starting from zero.
11. Notification test endpoint timeout blocks acceptance even when hardware/software source tests pass.

## Root cause

The backend live source is working, but the frontend still has multiple old render paths and stacked legacy sections. The UI is not using a single selected-machine state across Home, Machine 360, Network + VPN, Hardware Intelligence, and Software Intelligence.

The notification test endpoint also performs too much work synchronously during the acceptance test and can time out. Notification simulation should be separate, bounded, cached, or skipped from UI acceptance where it is not the page under test.

## Correct next solution

Build name:

`V10_SELECTED_MACHINE_UI_ACCEPTANCE_AND_NOTIFICATION_TIMEOUT_FIX`

This must be a controlled frontend binding + notification timeout fix, not a new backend rewrite.

### Must fix first

1. Remove old duplicate render sections from Home, Machine 360, Network + VPN, Hardware Intelligence, and Software Intelligence.
2. Use one global selected machine state:
   - selected machine id
   - hostname
   - asset fingerprint
   - official serial separately
3. All machine-wise pages must use the same selected machine:
   - Machine 360
   - Network + VPN
   - Hardware Intelligence
   - Software Intelligence
4. Machine Fleet remains fleet/table view only.
5. Home must become compact:
   - KPI band
   - traffic cards
   - ISP/WAN summary
   - small animated machine health cards
   - not a long repeated page
6. Machine 360 must include selected machine installed software list.
7. Network + VPN must show selected machine adapters, IPs, MAC, public IP, ISP, VPN, gateway/DNS when reported.
8. Hardware Intelligence must show selected machine CPU/RAM/disk/GPU/USB only, not a fleet table.
9. Software Intelligence must show selected machine installed software only, with search and CSV.
10. Notification-test timeout must be fixed by bounded simulation:
    - max machines
    - max rules
    - max seconds
    - cached response
    - no blocking full scan during UI acceptance

## Non-negotiable rules

- Do not change 2278.
- Do not rebuild client.
- Do not change CPU/RAM/GPU/disk/network collection logic.
- Do not fake serial numbers.
- Do not use client laptop ISP data for router ISP truth.
- Do not move to ISO until the selected-machine UI acceptance pages pass.
- GitHub must be pushed after every accepted step.

## Acceptance before ISO

The next build is accepted only if these pass:

1. Home is compact and clean.
2. Machine Fleet count = real 2278 machine count.
3. Selected machine dropdown/search works.
4. Machine 360 shows CPU/RAM/disk/GPU/USB/network/software for selected machine.
5. Network + VPN is selected-machine only.
6. Hardware Intelligence is selected-machine only.
7. Software Intelligence is selected-machine only.
8. Notification endpoint returns quickly or is tested separately.
9. No old duplicate cards remain on these pages.
10. GitHub push verified.
