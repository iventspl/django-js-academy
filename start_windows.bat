@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 start.py %*
) else (
  python start.py %*
)
if errorlevel 1 (
  echo.
  echo Django Quest could not start. Read the message above.
  pause
)
endlocal
