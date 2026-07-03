# V10 ISP / WAN Settings DB API Implementation

## Locked requirement
Settings must allow Admin/Super Admin to manually add ISP/WAN details for one organization.
The organization can have 1 to 10 ISP links. If it has 1 ISP, add one row. If it has 3, add three rows. Maximum is 10.

## Rules
- ISP/WAN details do not come from client machine payload.
- Admin can add/edit ISP links.
- Super Admin can add/edit/delete/lock ISP links.
- Viewer can only view status.
- Asset Entry user cannot edit ISP settings.
- After saving ISP details, backend monitoring runs automatically.

## DB tables
- router_wan_links
- router_probe_history

## API endpoints
- GET /api/v10/settings/isp-links
- POST /api/v10/settings/isp-link
- POST /api/v10/settings/isp-links
- POST /api/v10/settings/isp-link/delete
- GET /api/v10/isp-wan/status
- POST /api/v10/isp-wan/probe-now
- GET /api/v10/isp-wan/sample.csv
- GET /api/v10/isp-wan/export.csv

## Monitoring behavior
The first version monitors saved ISP links using gateway ping and Cloudflare active route.
It shows latency, jitter and packet loss per configured gateway.
It does not fake per-WAN speed. Per-WAN upload/download requires router API, SNMP, Omada controller data, or routed WAN probes.
