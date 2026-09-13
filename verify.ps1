@echo off
echo === AstrovoxAI Final Verification ===
echo.

echo 1. Git status:
git status
echo.

echo 2. Recent commits:
git log --oneline -10
echo.

echo 3. Running tests...
cd 02-Backend
python -m pytest tests/ -q
echo.

echo 4. Verifying app loads...
python -c "from app.main import app; print('App loads OK')"
echo.

echo 5. File counts:
for /f %%i in ('find 02-Backend/app -name "*.py" ^| find /c /v ""') do set pycount=%%i
for /f %%i in ('find 02-Backend/tests -name "*.py" ^| find /c /v ""') do set testcount=%%i
for /f %%i in ('dir /b *.md ^| find /c /v ""') do set doccount=%%i
echo    Python modules: %pycount%
echo    Test files: %testcount%
echo    Docs: %doccount%
echo.

echo === Verification Complete ===
pause
