@echo off
rem Sm4shCloneTool: the window
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 gui.py %*) || (start "" pythonw gui.py %*)
