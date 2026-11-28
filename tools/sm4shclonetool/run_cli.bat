@echo off
rem Sm4shCloneTool: the command line (python cli.py --help)
cd /d "%~dp0"
py -3 cli.py %* || python cli.py %*
