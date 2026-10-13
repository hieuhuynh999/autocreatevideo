@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Dang mo Kids 3D Story Video Creator tai http://127.0.0.1:7860
set PYTHONUTF8=1
python -m pip install -q -r requirements.txt
python app.py
pause
