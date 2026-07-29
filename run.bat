@echo off
setlocal EnableExtensions EnableDelayedExpansion
title BMW AI Platform — Start

REM ============================================================
REM  Double-click or run from repo root:
REM    run.bat
REM  Options:
REM    run.bat docker     — full stack in Docker only
REM    run.bat infra      — Docker infra + local API/UI (default)
REM    run.bat noseed     — skip demo seed
REM ============================================================

cd /d "%~dp0"
set "ROOT=%CD%"
set "MODE=infra"
set "DO_SEED=1"
set "API_PORT=8001"
set "FRONT_PORT=3000"

if /I "%~1"=="docker" set "MODE=docker"
if /I "%~1"=="infra" set "MODE=infra"
if /I "%~1"=="noseed" set "DO_SEED=0"
if /I "%~2"=="noseed" set "DO_SEED=0"
if /I "%~1"=="help" goto :usage
if /I "%~1"=="/?" goto :usage

echo.
echo  ========================================
echo   BMW AI Automotive Intelligence Platform
echo   Mode: %MODE%
echo  ========================================
echo.

REM --- .env ---
if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env.example" (
    copy /Y "%ROOT%\.env.example" "%ROOT%\.env" >nul
    echo [ok] Created .env from .env.example
  ) else (
    echo [warn] No .env or .env.example found
  )
)

REM Point frontend at local API
findstr /C:"NEXT_PUBLIC_API_URL" "%ROOT%\.env" >nul 2>&1
if errorlevel 1 (
  echo NEXT_PUBLIC_API_URL=http://127.0.0.1:%API_PORT%>>"%ROOT%\.env"
)

REM --- Docker ---
where docker >nul 2>&1
if errorlevel 1 (
  echo [error] Docker not found in PATH. Install Docker Desktop and retry.
  pause
  exit /b 1
)

echo [1/4] Starting Docker services...
pushd "%ROOT%\infra"
if /I "%MODE%"=="docker" (
  docker compose up -d --build
  if errorlevel 1 (
    echo [error] docker compose failed. Is Docker Desktop running?
    popd
    pause
    exit /b 1
  )
) else (
  REM Core deps first (required for API)
  docker compose up -d postgres redis
  if errorlevel 1 (
    echo [error] Could not start Postgres/Redis. Is Docker Desktop running?
    popd
    pause
    exit /b 1
  )
  REM Optional infra — continue if one service fails
  docker compose up -d chromadb minio kuksa-databroker ollama prometheus mlflow 2>nul
  docker compose up -d grafana 2>nul
  if errorlevel 1 (
    echo [warn] Grafana failed to start — API/UI will still run. Fix: docker compose -f infra\docker-compose.yml up -d grafana
  )
)
popd
echo [ok] Docker core is up
echo.

if /I "%MODE%"=="docker" (
  echo [done] Full Docker stack starting.
  echo   Frontend:  http://localhost:3000
  echo   API docs:  http://localhost:8001/docs
  echo   Grafana:   http://localhost:3001  ^(admin / admin123^)
  echo.
  echo Tip: first build can take several minutes.
  start "" "http://localhost:3000"
  pause
  exit /b 0
)

REM --- Wait for Postgres ---
echo [2/4] Waiting for Postgres...
set /a _tries=0
:wait_pg
set /a _tries+=1
docker exec bmw-postgres pg_isready -U bmwai >nul 2>&1
if not errorlevel 1 goto :pg_ready
if !_tries! geq 30 (
  echo [warn] Postgres not ready yet — continuing anyway
  goto :pg_ready
)
timeout /t 2 /nobreak >nul
goto :wait_pg
:pg_ready
echo [ok] Postgres ready
echo.

REM --- Python ---
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo [error] Python not found. Install Python 3.11+ and retry.
  pause
  exit /b 1
)

set "PYTHONPATH=%ROOT%;%ROOT%\apps\backend"
set "PUBLIC_API_URL=http://127.0.0.1:%API_PORT%"

echo [3/4] DB migrate + seed...
pushd "%ROOT%\apps\backend"
%PY% -m alembic upgrade head 2>nul
if errorlevel 1 echo [warn] alembic upgrade skipped/failed — create_all on boot may still work
popd

if "%DO_SEED%"=="1" (
  echo Seeding demo users/vehicles...
  %PY% "%ROOT%\scripts\seed_safety_demo.py" 2>nul
  if errorlevel 1 echo [warn] seed_safety_demo.py failed — you can re-run it later
) else (
  echo [skip] seed
)
echo.

REM --- Backend window ---
echo [4/4] Launching API + Frontend windows...
start "BMW-API" cmd /k "cd /d "%ROOT%\apps\backend" && set PYTHONPATH=%ROOT%;%ROOT%\apps\backend && set PUBLIC_API_URL=http://127.0.0.1:%API_PORT% && echo Starting uvicorn on :%API_PORT% ... && %PY% -m uvicorn app.main:app --reload --host 127.0.0.1 --port %API_PORT%"

REM Prefer pnpm, fall back to npm
set "FE_CMD="
where pnpm >nul 2>&1 && set "FE_CMD=pnpm"
if not defined FE_CMD where npm >nul 2>&1 && set "FE_CMD=npm"
if not defined FE_CMD (
  echo [error] Neither pnpm nor npm found. Install Node.js 20+ / pnpm.
  pause
  exit /b 1
)

if /I "%FE_CMD%"=="pnpm" (
  start "BMW-UI" cmd /k "cd /d "%ROOT%\apps\frontend" && set NEXT_PUBLIC_API_URL=http://127.0.0.1:%API_PORT% && if not exist node_modules pnpm install && pnpm dev -p %FRONT_PORT%"
) else (
  start "BMW-UI" cmd /k "cd /d "%ROOT%\apps\frontend" && set NEXT_PUBLIC_API_URL=http://127.0.0.1:%API_PORT% && if not exist node_modules npm install && npm run dev -- -p %FRONT_PORT%"
)

timeout /t 5 /nobreak >nul
start "" "http://localhost:%FRONT_PORT%"
start "" "http://127.0.0.1:%API_PORT%/docs"

echo.
echo  ========================================
echo   Running
echo  ========================================
echo   UI:       http://localhost:%FRONT_PORT%
echo   API docs: http://127.0.0.1:%API_PORT%/docs
echo   Grafana:  http://localhost:3001  ^(admin / admin123^)
echo.
echo   Logins:
echo     demo@bmwai.dev  / demo1234   ^(fleet^)
echo     driver@bmwai.dev / driver1234
echo     admin@bmwai.dev  / admin1234
echo.
echo   Close the BMW-API / BMW-UI windows to stop apps.
echo   Stop Docker infra:  stop.bat
echo  ========================================
echo.
pause
exit /b 0

:usage
echo Usage: run.bat [infra^|docker] [noseed]
echo   infra  ^(default^)  Docker deps + local uvicorn + Next.js
echo   docker            Everything via docker compose
echo   noseed            Skip scripts\seed_safety_demo.py
pause
exit /b 0
