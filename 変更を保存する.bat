@echo off
chcp 932 >nul
cd /d "%~dp0"
echo ================================
echo    変更を保存してサイトへ反映
echo ================================
echo.

rem --- 前回の同期が途中で止まっていないか先に確認する ---
rem rebase 途中や main 以外の状態でコミットすると、保存がブランチの外に積まれて
rem GitHub へ push できず、サイトへ永久に反映されない。その場合は何もせず終了する。
set BRANCH=
if exist ".git\rebase-merge" goto :stuck
if exist ".git\rebase-apply" goto :stuck
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if not "%BRANCH%"=="main" goto :stuck

echo 対象ファイル: docs/videos.json, docs/tags.json, data/channels.json
echo それ以外のファイルは保存されません。
echo.
git add docs/videos.json docs/tags.json data/channels.json
git diff --cached --quiet && echo 変更はありませんでした。保存の必要はありません。 && pause && goto :eof
echo 変更をコミットしています...
git commit -m "手動更新 %date% %time%"
echo.
echo 最新の状態と統合しています...
git pull --rebase
if errorlevel 1 goto :pullfail
echo.
echo GitHub へ反映しています...
git push
if errorlevel 1 goto :pushfail
echo.
echo 完了しました。数分後にサイトへ反映されます。
pause
goto :eof

:stuck
echo [中断] 前回の同期が途中で止まっているか、main 以外の状態です。
echo 今コミットすると、変更がサイトへ反映されない場所に積まれてしまうため、何もしませんでした。
echo 編集内容はファイルに残っているので失われていません。
echo.
echo 現在の状態:
git status --short --branch
echo.
echo この画面の内容をそのまま伝えて、復旧を依頼してください。
pause
goto :eof

:pullfail
echo.
echo [中断] 最新の状態との統合に失敗しました（自動収集との競合の可能性）。
echo コミットは済んでいるので編集内容は失われていません。GitHub への反映だけ行っていません。
echo この状態でもう一度実行しても直りません。この画面の内容をそのまま伝えて、復旧を依頼してください。
pause
goto :eof

:pushfail
echo.
echo [中断] GitHub への反映に失敗しました。
echo コミットは済んでいるので編集内容は失われていません。
echo この画面の内容をそのまま伝えて、復旧を依頼してください。
pause
goto :eof
