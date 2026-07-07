@echo off
rem Daily reminder run - registered in Windows Task Scheduler.
rem Runs from the folder this script lives in, so relative paths in
rem config.yaml (state/, logs/) resolve next to the installation.
cd /d "%~dp0"
py -3 -m qmm_reminder --config config.yaml
exit /b %errorlevel%
