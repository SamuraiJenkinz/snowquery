# ServiceNow Incident Query Tool - Scheduled Task Setup Script
# Run as Administrator on Windows Server
# Created by Kevin "Overlord of AI Bespoke Apps" Taylor

param(
    [string]$AppPath = "C:\snow_query",
    [string]$Port = "8501",
    [string]$TaskName = "SnowQueryTool"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ServiceNow Query Tool - Deployment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run this script as Administrator" -ForegroundColor Red
    exit 1
}

# Verify app path exists
if (-not (Test-Path "$AppPath\app.py")) {
    Write-Host "ERROR: app.py not found at $AppPath" -ForegroundColor Red
    Write-Host "Copy the snow_query project to $AppPath first" -ForegroundColor Yellow
    exit 1
}

# Verify venv exists
if (-not (Test-Path "$AppPath\venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found at $AppPath\venv" -ForegroundColor Red
    Write-Host "Create venv first: python -m venv venv && venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Verify .env exists
if (-not (Test-Path "$AppPath\.env")) {
    Write-Host "ERROR: .env file not found at $AppPath" -ForegroundColor Red
    Write-Host "Copy .env.example to .env and configure Azure OpenAI settings" -ForegroundColor Yellow
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  App Path: $AppPath"
Write-Host "  Port: $Port"
Write-Host "  Task Name: $TaskName"
Write-Host ""

# Create startup batch script
$batchScript = @"
@echo off
cd /d $AppPath
call venv\Scripts\activate.bat
streamlit run app.py --server.address 0.0.0.0 --server.port $Port --server.headless true
"@

$batchPath = "$AppPath\start_server.bat"
Set-Content -Path $batchPath -Value $batchScript
Write-Host "Created startup script: $batchPath" -ForegroundColor Green

# Remove existing task if present
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing scheduled task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create scheduled task
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batchPath`"" -WorkingDirectory $AppPath

$trigger = New-ScheduledTaskTrigger -AtStartup

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 3 `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "ServiceNow Incident Query Tool - Streamlit Web App" | Out-Null

Write-Host "Scheduled task created: $TaskName" -ForegroundColor Green

# Open firewall port
$firewallRule = Get-NetFirewallRule -DisplayName "Streamlit - Snow Query" -ErrorAction SilentlyContinue
if (-not $firewallRule) {
    New-NetFirewallRule `
        -DisplayName "Streamlit - Snow Query" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $Port `
        -Action Allow | Out-Null
    Write-Host "Firewall rule created for port $Port" -ForegroundColor Green
} else {
    Write-Host "Firewall rule already exists for port $Port" -ForegroundColor Yellow
}

# Start the task now
Write-Host ""
Write-Host "Starting the service..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5

# Check if running
$task = Get-ScheduledTask -TaskName $TaskName
if ($task.State -eq "Running") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Service is running" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    $hostname = [System.Net.Dns]::GetHostName()
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" } | Select-Object -First 1).IPAddress
    Write-Host "Access the app at:" -ForegroundColor Cyan
    Write-Host "  http://${hostname}:$Port" -ForegroundColor White
    Write-Host "  http://${ip}:$Port" -ForegroundColor White
} else {
    Write-Host "WARNING: Task may not have started. Check Task Scheduler." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Management commands:" -ForegroundColor Cyan
Write-Host "  Stop:    Stop-ScheduledTask -TaskName $TaskName"
Write-Host "  Start:   Start-ScheduledTask -TaskName $TaskName"
Write-Host "  Status:  Get-ScheduledTask -TaskName $TaskName | Select State"
Write-Host "  Remove:  Unregister-ScheduledTask -TaskName $TaskName"
