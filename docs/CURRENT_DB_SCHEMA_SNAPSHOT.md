# Current DB Schema Snapshot

Source DB: D:\SagarMonitor_V10_CleanBuild\data\history_cache_lite.db

## index idx_machine_day_day
`sql
CREATE INDEX idx_machine_day_day ON machine_day(day)
`

## index idx_machine_day_machine
`sql
CREATE INDEX idx_machine_day_machine ON machine_day(machine_id)
`

## index sqlite_autoindex_machine_day_1
`sql
-- no sql
`

## index sqlite_autoindex_meta_1
`sql
-- no sql
`

## table machine_day
`sql
CREATE TABLE machine_day(
            day TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            hostname TEXT,
            heartbeats INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT,
            last_seen TEXT,
            day_download_gb REAL NOT NULL DEFAULT 0,
            day_upload_gb REAL NOT NULL DEFAULT 0,
            max_down_mbps REAL NOT NULL DEFAULT 0,
            max_up_mbps REAL NOT NULL DEFAULT 0,
            cpu_sum REAL NOT NULL DEFAULT 0,
            cpu_count INTEGER NOT NULL DEFAULT 0,
            ram_sum REAL NOT NULL DEFAULT 0,
            ram_count INTEGER NOT NULL DEFAULT 0,
            ram_total_gb REAL NOT NULL DEFAULT 0,
            usb_max INTEGER NOT NULL DEFAULT 0,
            apps_max INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(day,machine_id)
        )
`

## table meta
`sql
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT)
`

