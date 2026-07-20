@echo off
chcp 932 >nul
cd /d "%~dp0"
echo ================================
echo    変更を保存してサイトへ反映
echo ================================
echo.
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
echo.
echo GitHub へ反映しています...
git push
echo.
echo 完了しました。数分後にサイトへ反映されます。
echo 赤字で ERROR / rejected / CONFLICT などが出ていたら、その文面を伝えてください。
pause
