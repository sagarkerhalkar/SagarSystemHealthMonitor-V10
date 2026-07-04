@echo off
set ROOT=%~dp0
cd /d "%ROOT%"
powershell -ExecutionPolicy Bypass -File "%ROOT%RUN_TEST_3330_READ_2278.ps1" -SourceUrl http://127.0.0.1:2278 -Port 3330
pause
