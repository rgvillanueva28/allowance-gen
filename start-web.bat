@echo off
REM Windows startup script for Receipt Processor Web Application

echo ========================================
echo Receipt Processor - Web Application
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created.
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Checking dependencies...
pip install -r requirements.txt --quiet

REM Check API key
echo.
echo Checking Gemini API key...
if "%GEMINI_API_KEY%"=="" (
    echo WARNING: GEMINI_API_KEY environment variable not set!
    echo.
    echo Please set your Gemini API key:
    echo   set GEMINI_API_KEY=your-api-key-here
    echo.
    echo Get your API key from: https://aistudio.google.com/app/apikey
    echo.
    pause
    exit /b 1
) else (
    echo API key found: %GEMINI_API_KEY:~0,10%...
)

REM Start the application
echo.
echo ========================================
echo Starting web server...
echo Navigate to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python app.py

pause
