@echo off
chcp 65001 >nul
title 修复超时误判的任务

echo.
echo ========================================
echo   一键修复超时误判的任务
echo ========================================
echo.
echo 正在检查并修复...
echo.

python backend/fix_all_timeout_errors.py

echo.
echo 按任意键退出...
pause >nul
