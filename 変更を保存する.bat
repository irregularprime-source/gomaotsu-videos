@echo off
setlocal
chcp 932 >nul
cd /d "%~dp0"
echo ================================
echo    変更を保存してサイトへ反映
echo ================================
echo.

rem 前回の同期が途中で止まっている状態や main 以外では保存しない。
set "BRANCH="
if exist ".git\rebase-merge" goto :stuck
if exist ".git\rebase-apply" goto :stuck
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set "BRANCH=%%b"
if not "%BRANCH%"=="main" goto :stuck

set "PYCMD=py -3.14"
if exist ".venv\Scripts\python.exe" set PYCMD=".venv\Scripts\python.exe"
%PYCMD% -B "scripts/check_staged.py"
if errorlevel 1 goto :stagefail

echo 対象ファイル: docs/videos.json, docs/tags.json, data/channels.json
echo 　　（あわせて docs/index.html と docs/sitemap.xml を自動で作り直します）
echo.
echo 検索・AI向けの索引を作り直しています...
%PYCMD% -B "scripts/build_static.py"
if errorlevel 1 goto :buildfail

git add -- "docs/videos.json" "docs/tags.json" "data/channels.json" "docs/index.html" "docs/sitemap.xml"
if errorlevel 1 goto :gitfail
%PYCMD% -B "scripts/check_staged.py"
if errorlevel 1 goto :stagefail
git diff --cached --quiet
if errorlevel 2 goto :gitfail
if not errorlevel 1 goto :unchanged

echo 変更をコミットしています...
git commit -m "手動更新 %date% %time%"
if errorlevel 1 goto :gitfail
echo 最新の状態と統合しています...
git pull --rebase
if errorlevel 1 goto :pullfail
echo GitHub へ反映しています...
git push
if errorlevel 1 goto :pushfail
echo 完了しました。数分後にサイトへ反映されます。
pause
exit /b 0

:unchanged
echo 変更はありませんでした。保存の必要はありません。
pause
exit /b 0

:stagefail
echo [中断] 保存前の確認で止めました（対象外のファイルの変更、または確認の失敗）。上の表示を確認してください。
echo Python が使えない場合は、Python 3.14 またはプロジェクトの仮想環境を確認してください。
pause
exit /b 1

:buildfail
echo [中断] 検索・AI向けの索引の作り直しに失敗しました。
echo 編集内容はファイルに残っています。まだコミットしていません。
echo この画面の内容をそのまま伝えて、復旧を依頼してください。
pause
exit /b 1

:gitfail
echo [中断] Git のステージ処理またはコミットに失敗しました。
echo 編集内容はファイルに残っています。GitHub への反映は行っていません。
pause
exit /b 1

:stuck
echo [中断] 前回の同期が途中で止まっているか、main 以外の状態です。
echo 編集内容はファイルに残っています。
git status --short --branch
echo この画面の内容をそのまま伝えて、復旧を依頼してください。
pause
exit /b 1

:pullfail
echo [中断] 最新の状態との統合に失敗しました（自動収集との競合の可能性）。
echo コミットは済んでいますが、GitHub への反映は行っていません。
echo この画面の内容をそのまま伝えて、復旧を依頼してください。
pause
exit /b 1

:pushfail
echo [中断] GitHub への反映に失敗しました。コミットは済んでいます。
echo この画面の内容をそのまま伝えて、復旧を依頼してください。
pause
exit /b 1
