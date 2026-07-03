# V10 Software Intelligence from 2278 Read-Only Live Source

Date: 2026-07-03

## Scope
This module adds Software Intelligence using the working 2278 monitor database as a read-only live source.

Source DB:

```text
D:\SagarSystemHealthMonitor\data\monitor.db
```

## Safety
- Does not write to 2278.
- Does not restart 2278.
- Does not modify 2278 tables.
- Reads SQLite using `mode=ro`.

## APIs
- `GET /api/v10/source2278/software/status`
- `GET /api/v10/source2278/software?limit=300&with_items=1`
- `GET /api/v10/source2278/software/export.csv`
- `GET /api/v10/source2278/software/sample.csv`

## Data Rule
No fake rows. If 2278 client reports only `software_count`, V10 shows count only and marks details as count-only. Full list appears only when client payload contains installed software list.

## Next Step
After this passes, connect Software Asset Register import/add/edit/delete/sync to this live software source.
