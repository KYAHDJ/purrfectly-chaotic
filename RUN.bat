@echo off
cd /d "%~dp0"
echo Close any Chrome window opened by login before running.
.venv\Scripts\python run.py
