$ErrorActionPreference = "Stop"
$env:V10_ACTIVE_WINDOW_HOURS = "24"
$env:V10_ONLINE_TIMEOUT_MINUTES = "2"
cd "D:\SagarMonitor_V10_CleanBuild"
python .\V10_FRESH_ACTIVE_COUNT_SERVER_2294.py --host 0.0.0.0 --port 2294
