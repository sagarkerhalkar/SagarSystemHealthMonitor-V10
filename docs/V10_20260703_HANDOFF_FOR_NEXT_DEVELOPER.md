# V10 Handoff for Next Developer / Next Chat

## Read This First
The user is frustrated because repeated patches made the project feel like it was starting from zero. Do not suggest another broad patch. Do not modify 2278.

## Working Source
Use 2278 as read-only source:
`D:\SagarSystemHealthMonitor\data\monitor.db`

Read from:
- `latest.summary_json`
- `notification_rules`
- `notifications` for history only

## Known Working Values
- 64 machines in 2278 latest.
- Fresh/stale count changes live.
- 58,353 software rows extracted.
- Hardware arrays are present when output is converted to JSON depth 30.
- Official serial is not reported by client, but asset fingerprint is present in `id_value`.

## UI Problem
Old V10 cards and new 2278 live sections were mixed. Replace old sections. Do not append under old UI.

## Next Development Task
`V10_CORE_PAGE_BINDING_ACCEPTANCE_BUILD`

Scope:
1. Fast notification-test endpoint.
2. Compact Home.
3. Machine-wise Machine 360.
4. Machine-wise Network + VPN.
5. Machine-wise Hardware Intelligence.
6. Machine-wise Software Intelligence.
7. Tests and GitHub push.

## Things Not To Do
- Do not touch 2278.
- Do not change client collection logic.
- Do not start ISO before core UI accepted.
- Do not say complete until tests and screenshots are accepted.