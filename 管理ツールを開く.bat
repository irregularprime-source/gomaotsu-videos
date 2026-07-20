@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================
echo    ゴ魔乙 管理ツール
echo ================================
echo.
echo [1/2] 最新データを取得しています (git pull)...
git pull --ff-only
echo.
echo [2/2] サーバーを起動してブラウザで管理ツールを開きます。
echo       終了するには、このウィンドウを閉じるか Ctrl+C を押してください。
echo.
set "PYCMD=python"
where python >nul 2>nul || set "PYCMD=py"
%PYCMD% scripts/serve_admin.py --open
echo.
echo サーバーが停止しました。ウィンドウを閉じて構いません。
pause
