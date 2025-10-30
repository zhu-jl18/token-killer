# PowerShell startup script for Windows

Write-Host "🚀 Starting Triple-Thread Thinking API..." -ForegroundColor Green
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".\venv")) {
    Write-Host "⚠️  Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "📦 Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Install dependencies if needed
Write-Host "📦 Checking dependencies..." -ForegroundColor Cyan
pip show fastapi > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Check if .env file exists
if (-not (Test-Path ".\.env")) {
    Write-Host "⚠️  .env file not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "⚠️  Please edit .env file with your API keys!" -ForegroundColor Red
    Start-Sleep -Seconds 3
}

# Start the server
Write-Host ""
Write-Host "🎯 Starting FastAPI server..." -ForegroundColor Green
Write-Host "📍 API URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📚 Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info