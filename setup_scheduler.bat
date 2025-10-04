@echo off
echo ========================================
echo  Task Statistics Scheduler Setup
echo ========================================
echo.

echo [1/3] Installing APScheduler...
pip install apscheduler
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install APScheduler
    pause
    exit /b 1
)
echo     Done!
echo.

echo [2/3] Testing TaskStatistics...
python service\statistics\TaskStatistics.py
if %ERRORLEVEL% NEQ 0 (
    echo Error: TaskStatistics test failed
    pause
    exit /b 1
)
echo     Done!
echo.

echo [3/3] Testing Scheduler (Ctrl+C to stop)...
echo Press Ctrl+C to stop the test after a few seconds...
timeout /t 3 /nobreak >nul
python service\statistics\scheduler.py
if %ERRORLEVEL% NEQ 0 (
    echo Error: Scheduler test failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Scheduler has been configured with:
echo   - Update at midnight (00:00)
echo   - Update every 6 hours
echo   - Update at end of day (23:55)
echo.
echo To start the server with scheduler:
echo   python main.py
echo.
echo To check scheduler status:
echo   curl http://localhost:5555/api/statistics/status
echo.
echo To trigger manual update:
echo   curl -X POST http://localhost:5555/api/statistics/update
echo.
pause
