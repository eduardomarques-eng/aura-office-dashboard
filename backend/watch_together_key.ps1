Write-Host "Aguardando TOGETHER_API_KEY no .env..."
$envFile = "C:\Users\erick\aura-office-dashboard\backend\.env"
$lastKey = ""
while ($true) {
    $content = Get-Content $envFile -Raw
    if ($content -match "TOGETHER_API_KEY=(.+)") {
        $key = $Matches[1].Trim()
        if ($key -ne "" -and $key -ne $lastKey) {
            Write-Host "Chave detectada! Reiniciando backend..."
            Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep 2
            Set-Location "C:\Users\erick\aura-office-dashboard\backend"
            Start-Process python -ArgumentList "-m","uvicorn","main:app","--host","0.0.0.0","--port","8000" -WindowStyle Hidden
            Write-Host "Backend reiniciado com Together AI ativo!"
            break
        }
    }
    Start-Sleep 5
}
