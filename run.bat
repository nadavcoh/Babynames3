@echo off
rem שם טוב — Name Explorer
rem
rem Usage:
rem   run.bat                         Plain HTTP (no PWA offline support)
rem   run.bat --cert HOST.crt --key HOST.key    HTTPS (enables PWA offline)
rem
rem To enable HTTPS with Tailscale (recommended for PWA offline support):
rem   1. In PowerShell:  tailscale cert <your-machine-name>
rem   2. Run:  run.bat --cert <your-machine-name>.crt --key <your-machine-name>.key
rem   3. Access via:  https://<your-machine-name>:5003
rem
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
title babynames3
python app.py %*
