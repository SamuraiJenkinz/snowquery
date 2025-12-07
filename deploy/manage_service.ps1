# ServiceNow Incident Query Tool - Service Management Script
# Created by Kevin "Overlord of AI Bespoke Apps" Taylor

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "status", "remove")]
    [string]$Action,

    [string]$TaskName = "SnowQueryTool"
)

switch ($Action) {
    "start" {
        Write-Host "Starting $TaskName..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $task = Get-ScheduledTask -TaskName $TaskName
        Write-Host "Status: $($task.State)" -ForegroundColor Green
    }
    "stop" {
        Write-Host "Stopping $TaskName..." -ForegroundColor Cyan
        Stop-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $task = Get-ScheduledTask -TaskName $TaskName
        Write-Host "Status: $($task.State)" -ForegroundColor Green
    }
    "restart" {
        Write-Host "Restarting $TaskName..." -ForegroundColor Cyan
        Stop-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 3
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $task = Get-ScheduledTask -TaskName $TaskName
        Write-Host "Status: $($task.State)" -ForegroundColor Green
    }
    "status" {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($task) {
            Write-Host "Task: $TaskName" -ForegroundColor Cyan
            Write-Host "Status: $($task.State)" -ForegroundColor Green
        } else {
            Write-Host "Task '$TaskName' not found" -ForegroundColor Red
        }
    }
    "remove" {
        Write-Host "Removing $TaskName..." -ForegroundColor Yellow
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Task removed" -ForegroundColor Green
    }
}
