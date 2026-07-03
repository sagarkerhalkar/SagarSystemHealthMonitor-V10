# V10 Home Traffic KPI Requirement Implemented

Date: 2026-07-03

## Locked requirement
Home / Command Center must show:

- Today Download
- Today Upload
- Current Download
- Current Upload

The labels/subtitles must be:

- Today Download — All clients
- Today Upload — All clients
- Current Download — Live client traffic
- Current Upload — Live client traffic

## Data rule
Values must come from live V10 client traffic stored in the `latest` table. No dummy data is allowed.

If client payloads do not report traffic counters, the UI must show 0 / Not reported and must not invent data.

## API added

- `GET /api/v10/home/traffic-kpi`
- `GET /api/v10final/home/traffic-kpi`
- `GET /api/v10/home/traffic-kpi/export.csv`

## UI added

- `public/v10_home_traffic_kpi.css`
- `public/v10_home_traffic_kpi.js`

The UI injects a Home panel named **Live Organization Traffic KPIs** without replacing the whole app.
