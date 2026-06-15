@echo off
chcp 65001 >nul
echo ========================================
echo   人力资源效能分析大屏 - 一键生成工具
echo ========================================
echo.

:: 检查参数
if "%~1"=="" (
    echo 用法: 双击运行后输入Excel文件路径
    echo.
    set /p EXCEL_PATH=请输入Excel文件路径:
) else (
    set EXCEL_PATH=%~1
)

:: 检查文件是否存在
if not exist "%EXCEL_PATH%" (
    echo 错误: 文件不存在 %EXCEL_PATH%
    pause
    exit /b 1
)

:: 运行生成脚本
echo.
echo 正在生成大屏数据...
python "%~dp0generate_dashboard.py" "%EXCEL_PATH%"

if %errorlevel% neq 0 (
    echo.
    echo 生成失败！
    pause
    exit /b 1
)

echo.
echo ========================================
echo   生成成功！
echo ========================================
echo.
echo 现在可以运行 server.py 启动大屏预览
echo.
pause