@echo off
chcp 65001 >nul
echo ========================================
echo   人力资源效能分析大屏 - 启动服务
echo ========================================
echo.
echo 正在启动服务器...
echo.
python "%~dp0server.py"
pause