param([int]$OnlineTimeoutMinutes = 2)
$ErrorActionPreference = "Stop"
python "D:\SagarMonitor_V10_CleanBuild\V10_BUILD_MACHINE_REGISTRY.py" --db "D:\SagarSystemHealthMonitor\data\monitor.db" --app "D:\SagarMonitor_V10_CleanBuild" --online-minutes $OnlineTimeoutMinutes
