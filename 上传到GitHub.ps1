# GitHub 上传脚本
# 使用方法：在 PowerShell 中执行此脚本

Write-Host "开始上传到 GitHub..." -ForegroundColor Green

# 切换到项目目录
$projectPath = "e:\课题组\声纹识别项目\remote代码备份\vioce 1.20"
Set-Location $projectPath

# 检查并清理锁定文件
Write-Host "检查 Git 状态..." -ForegroundColor Yellow
if (Test-Path .git\config.lock) {
    Write-Host "发现锁定文件，尝试删除..." -ForegroundColor Yellow
    Remove-Item .git\config.lock -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# 初始化 Git 仓库（如果不存在）
if (-not (Test-Path .git)) {
    Write-Host "初始化 Git 仓库..." -ForegroundColor Yellow
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Git 初始化失败，请关闭所有可能占用 Git 的进程后重试" -ForegroundColor Red
        exit 1
    }
}

# 添加远程仓库
Write-Host "配置远程仓库..." -ForegroundColor Yellow
$remoteUrl = "https://github.com/megumi020313/voice.git"
$existingRemote = git remote get-url origin 2>&1
if ($LASTEXITCODE -ne 0) {
    git remote add origin $remoteUrl
    Write-Host "已添加远程仓库" -ForegroundColor Green
} else {
    if ($existingRemote -ne $remoteUrl) {
        git remote set-url origin $remoteUrl
        Write-Host "已更新远程仓库地址" -ForegroundColor Green
    } else {
        Write-Host "远程仓库已配置" -ForegroundColor Green
    }
}

# 添加所有文件
Write-Host "添加文件到暂存区..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "添加文件失败" -ForegroundColor Red
    exit 1
}

# 检查是否有更改
$status = git status --short
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "没有需要提交的更改" -ForegroundColor Yellow
} else {
    # 提交更改
    Write-Host "提交更改..." -ForegroundColor Yellow
    git commit -m "Initial commit: 声纹识别项目代码"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "提交失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "提交成功" -ForegroundColor Green
}

# 设置主分支
Write-Host "设置主分支..." -ForegroundColor Yellow
git branch -M main

# 推送到远程仓库
Write-Host "推送到 GitHub..." -ForegroundColor Yellow
Write-Host "注意：如果这是第一次推送，可能需要输入 GitHub 用户名和密码（或 Personal Access Token）" -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n上传成功！" -ForegroundColor Green
    Write-Host "仓库地址: https://github.com/megumi020313/voice" -ForegroundColor Cyan
} else {
    Write-Host "`n推送失败，可能的原因：" -ForegroundColor Red
    Write-Host "1. 需要 GitHub 身份验证（用户名/密码或 Personal Access Token）" -ForegroundColor Yellow
    Write-Host "2. 网络连接问题" -ForegroundColor Yellow
    Write-Host "3. 权限问题" -ForegroundColor Yellow
    Write-Host "`n建议：使用 GitHub CLI (gh) 或配置 SSH 密钥进行身份验证" -ForegroundColor Cyan
}
