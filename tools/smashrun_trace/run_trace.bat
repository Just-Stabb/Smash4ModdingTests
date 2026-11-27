@echo off
rem Smash Run trace: double-click to record (Ctrl+C in this window to stop).
rem Arguments are passed on, e.g.  run_trace.bat --kinds kuribo --out goomba_1.jsonl
rem or  run_trace.bat probe   /   run_trace.bat dump all
cd /d "%~dp0"
set CMD=run
if not "%~1"=="" (
  if /i "%~1"=="probe" set CMD=
  if /i "%~1"=="dump" set CMD=
  if /i "%~1"=="run" set CMD=
  if /i "%~1"=="calibrate-clock" set CMD=
)
where python >nul 2>nul
if %errorlevel%==0 (
  python trace.py %CMD% %*
) else (
  py -3 trace.py %CMD% %*
)
echo.
echo Finished. The log is the newest smashrun_trace_*.jsonl file in this folder.
pause
