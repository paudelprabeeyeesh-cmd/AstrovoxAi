@echo off
title AstrovoxAI - Local Development
echo ========================================
echo   AstrovoxAI - Starting Locally
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and fill in your values.
    pause
    exit /b 1
)

REM Check if venv exists
if not exist venv\Scripts\activate (
    echo ERROR: Python virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

echo Starting Backend...
cd 02-Backend
call ..\venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
