# V10 Current Acceptance Status — 2026-07-03

## Passed
- 2278 is working and must not be touched.
- V10 2278 read-only source works.
- 2278 DB counts confirmed: latest 64, heartbeats 665418, notification_rules 13, notifications 532, client_messages 5, users 2.
- Hardware source from 2278 works.
- Software source from 2278 works: 58,353 rows.
- ISP/WAN Settings DB/API passed.
- Notification simulation passed once using read-only logic.

## Partial
- Machine Fleet: mostly okay; UI needs optimization.
- Machine 360: around 80%; software section missing/weak.
- Home: data foundation exists, but page is too long and 3D/animation weak.

## Failed / Not Accepted
- Network + VPN: not proper machine-wise selected-machine page.
- Hardware Intelligence: not proper machine-wise selected-machine page.
- Software Intelligence: not proper machine-wise selected-machine page.
- Latest machine-wise UI clean test timed out on notification-test endpoint.
- Duplicate/old UI sections caused user frustration.

## Do Not Proceed To ISO Until
- Home accepted.
- Machine Fleet accepted.
- Machine 360 accepted.
- Network + VPN accepted.
- Hardware Intelligence accepted.
- Software Intelligence accepted.
- Notification fast test passes.