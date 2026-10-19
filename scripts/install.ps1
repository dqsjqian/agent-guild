# Agent Guild Windows 安装器，要求 PowerShell 5.1+ 和 Python 3.9+。
# 下载并检查同一固定提交的 install.ps1 和 ag.py 后执行：.\install.ps1
# 不使用 Invoke-Expression，不下载或执行可变 main 分支代码。
# 两个平台复用 ag.py 的 release SHA-256 门禁和受限解包逻辑。

$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (-not $PSScriptRoot -or -not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'ag.py') -PathType Leaf)) {
    throw '缺少同目录 ag.py；请先下载并检查同一固定提交的安装脚本与 ag.py。'
}
$Python = if ($env:AGENT_GUILD_PYTHON) { $env:AGENT_GUILD_PYTHON } else { 'python' }
if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw '需要 Python 3.9+；可通过 AGENT_GUILD_PYTHON 指定可执行文件。'
}
$Version = if ($env:AGENT_GUILD_VERSION) { $env:AGENT_GUILD_VERSION } else { '4.0.0' }
$env:PYTHONDONTWRITEBYTECODE = '1'
# 内层只用单引号，避免 PowerShell 5.1 的原生命令参数处理吞掉双引号。
$Code = "import sys; sys.version_info >= (3, 9) or sys.exit('需要 Python 3.9+'); sys.path.insert(0, sys.argv[1]); import ag; sys.exit(ag._install_release(sys.argv[2]))"
& $Python -c $Code $PSScriptRoot $Version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "release 校验或安装失败（退出码 $LASTEXITCODE），未报告安装成功。"
}

Write-Host ''
Write-Host '  请复制以下内容发给你的 AI 助手：'
Write-Host ''
Write-Host '  Read ~/.agent-guild/ONBOARDING.md'
Write-Host ''
