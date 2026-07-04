# V10 Clean Runtime Auth Gate Fix

## Problem

Clean runtime test passed the first gate: index uses only clean runtime. Then /api/v10/app/health returned login_required.

## Root cause

The clean runtime app endpoints were added under /api/v10/app/*, but V10's original uth_required_path() protects all /api/* paths unless explicitly whitelisted. The static dashboard and test could not read the clean runtime APIs.

## Fix

Allow read-only clean runtime GET endpoints:

/api/v10/app/*

These endpoints only read the verified 2278 read-only selected-machine contract and do not write to 2278.

## Not changed

- 2278 server not touched.
- Client not touched.
- CPU/RAM/GPU/disk/network/software collection not changed.
- UI patch chain remains disabled by clean runtime package.
