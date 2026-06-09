@echo off
cd /d C:\Users\HEBE\Desktop\journal

:: Get today's date
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TODAY=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2%

set FILE=entries\%TODAY%.md

:: Create entry if not exists
if not exist "%FILE%" (
    echo # %TODAY%> "%FILE%"
    echo.>> "%FILE%"
    echo 今天的感悟...>> "%FILE%"
    echo ✅ 新建日记: %FILE%
) else (
    echo 📝 编辑已有日记: %FILE%
)

:: Open in default editor
start notepad "%FILE%"

echo.
echo 写完保存，然后按任意键发布...
pause >nul

:: Build
echo 🔨 构建中...
python build.py tongshapai

:: Push
echo 🚀 发布到 GitHub...
git add -A
git commit -m "日记 %TODAY%"
git push

echo.
echo ✅ 已发布！https://hanshaolong881-lang.github.io/journal/
pause
