# ─────────────────────────────────────────────────────────────────────────────
# Aura Decore — Ativar todos os workflows no n8n Cloud via API
#
# COMO USAR:
#   1. Abra app.n8n.cloud e faça login
#   2. Vá em Settings → API → copie a "API Key"
#   3. Verifique a URL do seu workspace (ex: https://seuworkspace.app.n8n.cloud)
#   4. Execute: .\ativar-workflows-n8n.ps1
# ─────────────────────────────────────────────────────────────────────────────

param(
    [string]$N8nUrl   = $env:N8N_INSTANCE_URL,   # ex: https://aura-decore.app.n8n.cloud
    [string]$ApiKey   = $env:N8N_API_KEY,
    [string]$WorkflowsDir = "$PSScriptRoot\ready-to-import"
)

if (-not $N8nUrl) {
    $N8nUrl = Read-Host "URL do workspace n8n (ex: https://aura-decore.app.n8n.cloud)"
}
if (-not $ApiKey) {
    $ApiKey = Read-Host "API Key do n8n Cloud"
}

$Headers = @{
    "X-N8N-API-KEY" = $ApiKey
    "Content-Type"  = "application/json"
}

Write-Host "`n=== Aura Decore — Ativador de Workflows n8n ===" -ForegroundColor Cyan
Write-Host "URL: $N8nUrl" -ForegroundColor Gray

# 1. Lista workflows existentes
$existing = @{}
try {
    $resp = Invoke-RestMethod "$N8nUrl/api/v1/workflows?limit=50" -Headers $Headers
    foreach ($wf in $resp.data) {
        $existing[$wf.name] = $wf.id
        Write-Host "  [existente] $($wf.name) (id=$($wf.id), ativo=$($wf.active))" -ForegroundColor Gray
    }
} catch {
    Write-Host "Erro ao listar workflows: $_" -ForegroundColor Red
    Write-Host "Verifique a URL e a API Key." -ForegroundColor Yellow
    exit 1
}

# 2. Importa workflows que ainda não existem
$jsonFiles = Get-ChildItem $WorkflowsDir -Filter "*.json" | Sort-Object Name
$imported  = @()

foreach ($file in $jsonFiles) {
    $content = Get-Content $file.FullName -Raw | ConvertFrom-Json
    $wfName  = $content.name

    if ($existing.ContainsKey($wfName)) {
        Write-Host "  [skip] $wfName — já existe (id=$($existing[$wfName]))" -ForegroundColor Gray
        $imported += $existing[$wfName]
        continue
    }

    Write-Host "  [importar] $wfName ..." -ForegroundColor Yellow
    try {
        $body = Get-Content $file.FullName -Raw
        $created = Invoke-RestMethod "$N8nUrl/api/v1/workflows" -Method POST -Headers $Headers -Body $body
        $imported += $created.id
        Write-Host "    ✓ Importado id=$($created.id)" -ForegroundColor Green
    } catch {
        Write-Host "    ✗ Erro ao importar $($file.Name): $_" -ForegroundColor Red
    }
}

# 3. Ativa todos os workflows importados
Write-Host "`n=== Ativando workflows ===" -ForegroundColor Cyan
foreach ($id in $imported) {
    try {
        Invoke-RestMethod "$N8nUrl/api/v1/workflows/$id/activate" -Method POST -Headers $Headers | Out-Null
        Write-Host "  ✓ Ativado: id=$id" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Erro ao ativar id=$id: $_" -ForegroundColor Red
    }
}

# 4. Resumo final
Write-Host "`n=== Status Final ===" -ForegroundColor Cyan
$final = Invoke-RestMethod "$N8nUrl/api/v1/workflows?limit=50" -Headers $Headers
foreach ($wf in $final.data) {
    $status = if ($wf.active) { "✅ ATIVO" } else { "⏸ inativo" }
    Write-Host "  $status — $($wf.name)" -ForegroundColor $(if ($wf.active) { "Green" } else { "Yellow" })
}
Write-Host "`nConcluído. Workflows prontos para rodar." -ForegroundColor Cyan
