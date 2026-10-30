@echo off
setlocal
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"

net session >nul 2>&1
if not "%errorlevel%"=="0" (
  echo Requesting administrator permission...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%PORT%' -Verb RunAs"
  exit /b
)

echo Allowing inbound TCP port %PORT% from the local subnet only...
netsh advfirewall firewall delete rule name="Django Quest LAN %PORT%" >nul 2>&1
netsh advfirewall firewall add rule name="Django Quest LAN %PORT%" dir=in action=allow protocol=TCP localport=%PORT% remoteip=LocalSubnet profile=any
if errorlevel 1 (
  echo.
  echo Could not add the firewall rule.
  pause
  exit /b 1
)

echo.
echo Firewall rule created: Django Quest LAN %PORT%
echo Scope: local subnet only. This does not expose the app to the internet.
netsh advfirewall firewall show rule name="Django Quest LAN %PORT%"
echo.
pause
