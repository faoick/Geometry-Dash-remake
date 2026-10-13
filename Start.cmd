@echo off
setlocal
cd /d "%~dp0"
if not exist "user_data" mkdir "user_data" 2>nul
set "DASH_BOOT_LOG=%~dp0user_data\bootstrap.log"
echo Dash Rebuild bootstrap > "%DASH_BOOT_LOG%" 2>nul
if errorlevel 1 set "DASH_BOOT_LOG=%TEMP%\DashRebuild-bootstrap.log"
echo Dash Rebuild bootstrap > "%DASH_BOOT_LOG%"
if exist "DashRebuild.exe" goto portable
if not exist "launcher.py" goto incomplete
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys,pygame; assert sys.version_info >= (3,11)" >> "%DASH_BOOT_LOG%" 2>&1
  if not errorlevel 1 goto existing
)
if exist ".runtime\Scripts\python.exe" (
  ".runtime\Scripts\python.exe" -c "import sys,pygame; assert sys.version_info >= (3,11)" >> "%DASH_BOOT_LOG%" 2>&1
  if not errorlevel 1 goto runtime
)
py -3 -c "import sys; assert sys.version_info >= (3,11)" >> "%DASH_BOOT_LOG%" 2>&1
if not errorlevel 1 (
  set "DASH_SYSTEM_PY=py -3"
  goto setup
)
python -c "import sys; assert sys.version_info >= (3,11)" >> "%DASH_BOOT_LOG%" 2>&1
if not errorlevel 1 (
  set "DASH_SYSTEM_PY=python"
  goto setup
)
echo Python 3.11+ was not found. Use the portable ZIP with DashRebuild.exe.
goto fail
:setup
echo Preparing a local Python environment. Please wait...
%DASH_SYSTEM_PY% -m venv .runtime >> "%DASH_BOOT_LOG%" 2>&1
if errorlevel 1 goto fail
".runtime\Scripts\python.exe" -m pip install -r requirements.txt >> "%DASH_BOOT_LOG%" 2>&1
if errorlevel 1 goto fail
:runtime
".runtime\Scripts\python.exe" launcher.py %* >> "%DASH_BOOT_LOG%" 2>&1
goto result
:existing
".venv\Scripts\python.exe" launcher.py %* >> "%DASH_BOOT_LOG%" 2>&1
goto result
:portable
start "" /wait "%~dp0DashRebuild.exe" %*
:result
if errorlevel 1 goto fail
exit /b 0
:incomplete
echo Incomplete archive. Extract the ENTIRE folder before running Start.cmd.
:fail
echo Launch failed. Send user_data\launch.log and the bootstrap log:
echo "%DASH_BOOT_LOG%"
type "%DASH_BOOT_LOG%"
if "%DASH_NO_PAUSE%"=="1" exit /b 1
pause
exit /b 1
