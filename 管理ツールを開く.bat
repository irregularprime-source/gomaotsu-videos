@echo off
setlocal
chcp 932 >nul
cd /d "%~dp0"
echo ================================
echo    ゴ魔乙 管理ツール
echo ================================
echo.
echo [1/2] 最新データを取得しています...
git pull --ff-only
if errorlevel 1 goto :pullfail
echo.
echo [2/2] サーバーを起動してブラウザで管理ツールを開きます。
echo       終了するには、このウィンドウを閉じるか Ctrl+C を押してください。
set "PYCMD=py -3.14"
if exist ".venv\Scripts\python.exe" set PYCMD=".venv\Scripts\python.exe"
%PYCMD% -B "scripts/serve_admin.py" --open
if errorlevel 1 goto :serverfail
echo サーバーが停止しました。ウィンドウを閉じて構いません。
pause
exit /b 0

:pullfail
echo [中断] 最新データの取得に失敗したため、サーバーを起動しませんでした。
echo この画面の内容をそのまま伝えて、復旧を依頼してください。
pause
exit /b 1

:serverfail
echo [中断] サーバーの起動または実行に失敗しました。
echo Python 3.14 またはプロジェクトの仮想環境と、上のエラーを確認してください。
pause
exit /b 1
