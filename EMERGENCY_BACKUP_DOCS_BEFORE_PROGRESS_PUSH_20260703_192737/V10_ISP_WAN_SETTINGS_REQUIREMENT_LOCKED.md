# V10 ISP / WAN Settings Requirement Locked

Date: 2026-07-03

## Requirement
Settings page must have ISP / WAN Manager.

Admin or Super Admin can add ISP details manually.

One organization can have minimum 1 ISP and maximum 10 ISP links.

If organization has 1 ISP, add 1.
If organization has 3 ISP, add 3.
If organization has 10 ISP, add 10 maximum.

After saving ISP details, backend must automatically monitor those ISP/WAN links.

ISP details must not come from client machine.

## ISP Fields
- ISP Name
- WAN Name / WAN Number
- Router IP
- Gateway IP
- WAN Interface / Port Name
- Public IP / Auto-detected Public IP
- Expected Download Mbps
- Expected Upload Mbps
- Monitoring Enabled Yes/No
- Primary / Backup / Load-balance
- Notes
- Status
- Last Checked
- Latency
- Jitter
- Packet Loss
- Current Download
- Current Upload

## Roles
Viewer: view only.
Asset Entry User: no ISP edit.
Admin: add/edit ISP details.
Super Admin: add/edit/delete/lock ISP details.

## Home Page
Home must show all ISP links registered in Settings with live health:
- Active ISP
- Backup ISP
- Down ISP
- Latency
- Jitter
- Packet Loss
- Upload
- Download
- Public IP / Cloudflare route
- Router feed not connected if router API/SNMP is not configured.

## Build Order
1. DB table first.
2. API CRUD second.
3. Settings UI third.
4. Home ISP status fourth.
5. Test with live server data.
6. GitHub push after test.
