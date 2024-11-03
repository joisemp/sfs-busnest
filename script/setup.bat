@echo off
REM Set the execution policy for the session
PowerShell -Command "Set-ExecutionPolicy Unrestricted -Scope Process -Force"

REM Activate the virtual environment
call env\Scripts\activate

REM Change to the src directory
cd src

REM Install requirements
pip install -r requirements.txt

REM Run migrations
python manage.py migrate

REM Run tests
call ..\script\run_test.bat

:PortPrompt
REM Prompt the user for a port to run the server on
set /p PORT=Enter the port you want to run the Django server on (default is 8000):

REM Use default port 8000 if the user does not provide input
if "%PORT%"=="" set PORT=8000

REM Check if the port is available
PowerShell -Command "if (!(Test-NetConnection -ComputerName localhost -Port %PORT% -WarningAction SilentlyContinue).TcpTestSucceeded) { exit 0 } else { exit 1 }"
if %errorlevel%==0 (
    echo Port %PORT% is available.
) else (
    echo Port %PORT% is already in use. Please choose another port.
    goto PortPrompt
)

REM Start the Django server on the specified port
echo Starting Django server on port %PORT%...
python manage.py runserver %PORT%
