# V10 Stable Selected-Machine No-Flicker Fix

Date: 2026-07-03

## Problem from latest video
- Home page flickering.
- Old V10 JS auto refresh was still running every 30 seconds.
- Old V10 renderer and new 2278 selected-machine UI were fighting each other.
- Server/monitor host was being selected like a normal client by default.
- Hardware page machine selection did not stay fixed because old renderer could overwrite it.

## Root cause
The previous package added selected-machine UI on top of the old `v10_phase3_fix9_global.js` flow, but the old script still ran:

```js
setInterval(refreshAll,30000)
renderCommand(); renderFleet(); renderMachine360(); renderNetwork(); renderHardware(); renderSoftware();
```

This caused flicker and old/fake-looking cards to return.

## Solution
- Disable old auto refresh loop.
- Stop old renderer from writing Home / Machine Fleet / Machine 360 / Network / Hardware / Software.
- Keep old renderer for remaining tabs only: inventory, ISO, USB, history, messages, notifications, deploy, settings.
- Hide old global hero on Home.
- Replace selected-machine UI script with stable mode:
  - no MutationObserver loop
  - no auto re-render interval
  - no notification-test on Home load
  - selected machine saved in localStorage
  - monitor server separated from client machines
  - selected machine shared across Machine 360, Network + VPN, Hardware Intelligence, Software Intelligence

## Protected rules
- Do not touch 2278 server.
- Do not touch 2278 clients.
- Do not change CPU/RAM/GPU/SSD/network data calculation.
- Use only 2278 read-only source.
