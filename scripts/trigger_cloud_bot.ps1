# Script disparador de GitHub Actions para YouTube & TikTok Bot
$repo = "kr0zapps/youtube-ai-bot"
$workflow = "youtube_bot.yml"
$logPath = Join-Path $PSScriptRoot "scheduler.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

try {
    & "C:\Program Files\GitHub CLI\gh.exe" workflow run $workflow --repo $repo
    $msg = "$timestamp [INFO] Workflow '$workflow' disparado con éxito en GitHub Actions."
    Write-Output $msg
    Add-Content -Path $logPath -Value $msg
} catch {
    $err = "$timestamp [ERROR] Error al disparar workflow: $_"
    Write-Error $err
    Add-Content -Path $logPath -Value $err
}
