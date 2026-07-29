@echo off
setlocal EnableExtensions
title BMW AI Platform — Stop

cd /d "%~dp0"
set "ROOT=%CD%"

echo Stopping Docker stack...
pushd "%ROOT%\infra"
docker compose down
popd

echo.
echo Closing local API / UI windows if still open...
taskkill /FI "WINDOWTITLE eq BMW-API*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq BMW-UI*" /T /F >nul 2>&1

echo.
echo Done. Docker containers stopped; local windows closed when possible.
pause
exit /b 0
