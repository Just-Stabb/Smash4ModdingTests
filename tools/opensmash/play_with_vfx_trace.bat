@echo off
rem Starts OpenSmash-Ultimate with the vfx_trace mod (docs/vfx-trace.md). Put this file and the vfx_trace folder
rem (vfx_trace.dll inside) in the OpenSmash folder, next to "Play SSBU.bat", and double-click it.
rem "Play SSBU.bat" runs scripts\run.py, which drops every SSBU_* variable of the environment, so a "set SSBU_MODS="
rem never reaches the game: the mod folder goes through run.py's --env instead.
cd /d "%~dp0"
if not exist "%~dp0vfx_trace\vfx_trace.dll" (
    echo vfx_trace\vfx_trace.dll is not here: put the vfx_trace folder next to this file.
    pause
    exit /b 1
)
set "PY="
if exist deps\python\python.exe set "PY=%~dp0deps\python\python.exe"
if not defined PY if exist build\python_path.txt set /p PY=<build\python_path.txt
if defined PY if not exist "%PY%" set "PY="
if not defined PY set "PY=python"
if not defined VFX_TRACE_SETS set "VFX_TRACE_SETS=PZenigame"
"%PY%" scripts\run.py --play --seconds 0 --env "SSBU_MODS=%~dp0vfx_trace"
if errorlevel 1 pause
