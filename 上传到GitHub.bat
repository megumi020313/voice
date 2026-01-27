@echo off
chcp 65001 >nul
echo 正在上传到 GitHub...
echo.

cd /d "%~dp0"

REM 检查 Git 是否安装
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到 Git，请先安装 Git
    pause
    exit /b 1
)

REM 检查并清理锁定文件
if exist .git\config.lock (
    echo 发现锁定文件，尝试删除...
    del /f /q .git\config.lock >nul 2>&1
    timeout /t 2 >nul
)

REM 初始化 Git 仓库
if not exist .git (
    echo 初始化 Git 仓库...
    git init
    if %errorlevel% neq 0 (
        echo Git 初始化失败，请关闭所有可能占用 Git 的进程后重试
        pause
        exit /b 1
    )
)

REM 配置远程仓库
echo 配置远程仓库...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/megumi020313/voice.git

REM 添加文件
echo 添加文件到暂存区...
git add .

REM 提交更改
echo 提交更改...
git commit -m "Initial commit: 声纹识别项目代码"
if %errorlevel% neq 0 (
    echo 提交失败或没有更改需要提交
)

REM 设置主分支
git branch -M main

REM 推送到远程
echo.
echo 推送到 GitHub...
echo 注意：如果这是第一次推送，可能需要输入 GitHub 用户名和密码（或 Personal Access Token）
echo.
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo 上传成功！
    echo 仓库地址: https://github.com/megumi020313/voice
) else (
    echo.
    echo 推送失败，可能的原因：
    echo 1. 需要 GitHub 身份验证（用户名/密码或 Personal Access Token）
    echo 2. 网络连接问题
    echo 3. 权限问题
    echo.
    echo 建议：使用 GitHub CLI (gh) 或配置 SSH 密钥进行身份验证
)

echo.
pause
