# ============================================================
# 24/7 Auto AI Trader - Watchdog Startup Script
# Keeps backend server running continuously even after crashes
# ============================================================

$BackendDir = "c:\Users\RAVIKANTH\OneDrive\Desktop\trading agent\trading-ai-bot\backend"
$FrontendDir = "c:\Users\RAVIKANTH\OneDrive\Desktop\trading agent\trading-ai-bot\frontend"

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  AUTO AI TRADER - 24/7 WATCHDOG STARTED" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Yellow
Write-Host "  AI scans coins every 60 seconds automatically" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Kill any existing processes on ports 3000 and 8000
Write-Host "[CLEANUP] Stopping any existing servers..." -ForegroundColor Gray
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq "" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start Frontend (once, in separate window)
Write-Host "[STARTUP] Starting React Frontend on port 3000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$FrontendDir'; npm start" -WindowStyle Normal

Start-Sleep -Seconds 5

# Backend 24/7 Watchdog Loop
$restart_count = 0
while ($true) {
    $restart_count++
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] Starting Backend (Attempt #$restart_count)..." -ForegroundColor Green
    try {
        Set-Location $BackendDir
        python -m uvicorn server:app --host 0.0.0.0 --port 8000
    } catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
    }
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] Backend stopped — restarting in 5 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}
