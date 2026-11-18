@echo off
setlocal
title Automotive Spare-Part Investigator
cd /d "%~dp0frontend"
echo Starting the MAIN application. The demo is a separate folder.
echo Open the PROJECT_READY address when it appears.
node server.mjs
pause
endlocal
