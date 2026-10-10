@echo off
echo Switching Khadira ERP to Isolated Simulation Demo Database...
copy /Y "%~dp0.env.demo" "%~dp0.env"
echo [OK] Active database is now backend/mill_demo.db (311 simulated rolls, 24 orders, full workflow)
echo Normal database (mill.db) is preserved safely.
pause
