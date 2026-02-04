
@echo off
python -m venv .venv
call .venv\Scriptsctivate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo ✅ Environment ready. Activate with: .venv\Scripts\Activate.ps1
