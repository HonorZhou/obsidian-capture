# 去重检查脚本
# 用法：.\check_dup.ps1 -SourceUrl "https://mp.weixin.qq.com/s/xxx"

param(
    [Parameter(Mandatory=$true)]
    [string]$SourceUrl,
    [string]$VaultRoot
)

# 跨设备：优先参数 -VaultRoot，其次环境变量 VAULT_ROOT，最后回退旧默认
if (-not $VaultRoot) { $VaultRoot = $env:VAULT_ROOT }
if (-not $VaultRoot) { $VaultRoot = "D:\WorkBuddy\Claw\Obsidian\Obsidian" }
$vaultDir = $VaultRoot

Write-Host "检查去重: $SourceUrl" -ForegroundColor Cyan

$result = Select-String -Path "$vaultDir\01-文章\**\*.md" -Pattern $SourceUrl -SimpleMatch -List 2>$null

if ($result) {
    Write-Host "  DUP: 已存在" -ForegroundColor Yellow
    Write-Host "    文件: $($result.Path)" -ForegroundColor Yellow
    exit 2
}
else {
    Write-Host "  OK: 未重复" -ForegroundColor Green
    exit 0
}
