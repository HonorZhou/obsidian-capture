# 写入后验证脚本
# 用法：.\verify_note.ps1 -Path "D:\WorkBuddy\Claw\Obsidian\Obsidian\01-文章\公众号\xxx.md"

param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

if (-not (Test-Path $Path)) {
    Write-Error "文件不存在: $Path"
    exit 1
}

Write-Host "验证: $Path" -ForegroundColor Cyan

# 读取前 15 行
$head = Get-Content $Path -Head 15 -Raw

# 检查 AIGC 注入字段
$blacklist = @(
    'ContentProducer',
    'ProduceID',
    'Label',
    'douyin_author',
    'douyin_description',
    'douyin_create_time',
    'douyin_modify_time',
    'AIGC',
    'ai_generated'
)

$issues = @()
foreach ($field in $blacklist) {
    if ($head -match $field) {
        $issues += "发现注入字段: $field"
    }
}

# 检查是否有 --- 开始和结束
$dashCount = ([regex]::Matches($head, '^---$', [System.Text.RegularExpressions.RegexOptions]::Multiline)).Count
if ($dashCount -lt 2) {
    $issues += "frontmatter 分隔符不完整 (需要前后各一个 ---)"
}

# 输出结果
if ($issues.Count -eq 0) {
    Write-Host "  PASS: frontmatter 正常，无 AIGC 注入" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "  FAIL:" -ForegroundColor Red
    foreach ($issue in $issues) {
        Write-Host "    - $issue" -ForegroundColor Red
    }
    exit 1
}
