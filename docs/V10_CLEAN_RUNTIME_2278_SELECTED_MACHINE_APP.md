# V10 Clean Runtime 2278 Selected Machine App

Purpose: stop old patch-chain UI from running and use one clean renderer with 2278 read-only selected-machine data.

Changes:
- Replaces public/index.html runtime with one JS and one CSS.
- Adds v10_clean_app_2278_api.py.
- Adds /api/v10/app/* endpoints.
- Parks ISO/extra pages until core pages pass.

Does not change:
- 2278 server.
- Client machines.
- CPU/RAM/GPU/disk/network/software collection logic.
- Notification rules logic.

Acceptance:
- Home no flicker for 2 minutes.
- Machine Fleet table works.
- Machine 360 / Hardware / Network / Software use the same selected machine.
- DESKTOP-1VTKP12 is not selected by default as a client if marked monitor server.
