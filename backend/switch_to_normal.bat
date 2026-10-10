@echo off
echo Switching Khadira ERP to Normal Database...
copy /Y "%~dp0.env.normal" "%~dp0.env"
echo [OK] Active database is now backend/mill.db (clean normal database)
pause
