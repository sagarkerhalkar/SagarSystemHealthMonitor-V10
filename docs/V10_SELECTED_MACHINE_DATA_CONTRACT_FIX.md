# V10 Selected-Machine Data Contract Fix

Date: 2026-07-03

## Problem from video/user report
- Home page flickering.
- Server machine was being treated as a normal client/default machine.
- Hardware, Network + VPN, Software Intelligence, and Machine 360 did not keep the same selected machine.
- Old UI renderer and new 2278 UI were fighting.
- API call with `query=HOSTNAME` was ignored because the older endpoint only accepted `q=`.

## Locked solution
This package reapplies the already working 2278 read-only logic but adds a strict selected-machine contract.

2278 is not modified. Client logic is not changed. CPU/GPU/RAM/SSD/network/software collection is not changed.

## New contract APIs
- `/api/v10/selected-machine/list`
- `/api/v10/selected-machine/hardware?machine_id=...`
- `/api/v10/selected-machine/software?machine_id=...`
- `/api/v10/selected-machine/network?machine_id=...`
- `/api/v10/selected-machine/home`
- `/api/v10/selected-machine/notification-fast`

## Acceptance rule
If `machine_id=A` is requested, hardware, network, and software must all return machine `A`. No current/default machine overwrite is allowed.

## UI rule
Home, Machine Fleet, Machine 360, Network + VPN, Hardware Intelligence, and Software Intelligence use the selected-machine contract only.

## Server separation rule
The monitor server is separated from client machine counts where possible, using the server host name and known existing server host fallback.
