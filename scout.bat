@echo off
REM AGORA scout launcher - runs from anywhere; cds to its own folder first.
cd /d "%~dp0"
python scripts\run_scout.py %*
