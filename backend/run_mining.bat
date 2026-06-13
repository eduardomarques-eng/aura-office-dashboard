@echo off
cd /d "%~dp0"
set PYTHON=C:\Users\erick\AppData\Local\Programs\Python\Python312\python.exe
if not exist "%PYTHON%" set PYTHON=python
"%PYTHON%" run_mining.py >> mining_log.txt 2>&1
