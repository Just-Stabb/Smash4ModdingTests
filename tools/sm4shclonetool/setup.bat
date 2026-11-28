@echo off
rem Sm4shCloneTool: installs what the tool needs (numpy for the texture decoder, Pillow for pictures).
rem Needs Python 3.9 or later from python.org (tick "Add python.exe to PATH"; tcl/tk is included).
cd /d "%~dp0"
py -3 -m pip install --upgrade -r requirements.txt || python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (echo. & echo Setup failed: is Python 3 installed and on PATH? & pause & exit /b 1)
echo.
echo Sm4shCloneTool is ready: double-click run.bat
pause
