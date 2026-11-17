@echo off
setlocal
title Can This Part Replace That - Teacher Demo
cd /d "%~dp0frontend"
set "PORT=3101"
echo Open http://127.0.0.1:3101 after "Demo ready" appears.
echo Keep this window open. Press Ctrl+C to stop the demo.
node server.mjs
pause
endlocal
