@echo off
cd /d "%~dp0"

:menu
cls
echo ==========================================
echo      ONLYSNAP DASHBOARD
echo ==========================================
echo 1) Run OnlySnap
echo 2) Install Requirements
echo 3) Install DRM Tools (FFmpeg, MP4Decrypt, RE)
echo 4) Add to PATH (use "onlyfans" / "patreon" from anywhere)
echo.
set /p choice=Select option (1, 2, 3 or 4): 

if "%choice%"=="1" goto op1
if "%choice%"=="2" goto op2
if "%choice%"=="3" goto op3
if "%choice%"=="4" goto op4
goto menu

:op1
python OnlySnap.py
pause
goto menu

:op2
cls
echo Installing Python requirements...
echo ----------------------------------------
pip install -r Site\requirements.txt
echo.
echo Done!
pause
goto menu

:op3
cls
echo Starting DRM Tools Install...
echo ==========================================

REM Check if VC++ Redistributable is already installed
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64" /v Version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Visual C++ Redistributable already installed. Skipping.
) else (
    echo [0/4] Downloading Visual C++ Redistributable...
    curl -L -o "vc_redist.x64.exe" "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    if exist "vc_redist.x64.exe" (
        echo      Installing silently...
        start /wait vc_redist.x64.exe /quiet /norestart
        echo      Done! Cleaning up...
        del /f "vc_redist.x64.exe"
        echo [OK] Visual C++ Redistributable installed.
    ) else (
        echo [!] Download failed. Skipping VC++ install.
    )
)

echo.

if not exist "dmr" mkdir "dmr"

echo [1/3] Downloading FFmpeg (Heavy file, give it a sec)...
curl -L -o "dmr\ffmpeg.exe" "https://www.dropbox.com/scl/fi/5a7kqu8519irz1qqo8yze/ffmpeg.exe?rlkey=40t2hcjvxwx0x6h70lruppacy&st=t7i6ez8v&dl=1"

echo.
echo [2/3] Downloading mp4decrypt...
curl -L -o "dmr\mp4decrypt.exe" "https://www.dropbox.com/scl/fi/2bcw6bketkk9kecwcetxb/mp4decrypt.exe?rlkey=6krq977y6x75bzegx1o9okxk2&st=82t1yhnb&dl=1"

echo.
echo [3/3] Downloading N_m3u8DL-RE...
curl -L -o "dmr\N_m3u8DL-RE.exe" "https://www.dropbox.com/scl/fi/441bo1nnfcgswt43n6x36/N_m3u8DL-RE.exe?rlkey=eu8ev25m8j5ewqki4qbgrx55l&st=azr7xln5&dl=1"

echo.
echo ==========================================
if exist "dmr\ffmpeg.exe" (
    echo SUCCESS! All tools are ready in 'dmr' folder.
) else (
    echo ERROR: Download failed. Check your internet.
)
echo ==========================================
pause
goto menu

:op4
cls
echo ==========================================
echo   ADD ONLYSNAP COMMANDS TO PATH
echo ==========================================
echo.
echo This will create "onlyfans" and "patreon" commands
echo that work from ANY folder, ANY drive.
echo.
echo If you move OnlySnap, just run this option again!
echo ==========================================
echo.

set "BIN_DIR=%USERPROFILE%\.onlysnap\bin"
set "SITE_DIR=%~dp0Site"

if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

echo Creating "onlyfans" command...
(
echo @echo off
echo cd /d "%SITE_DIR%"
echo python "%SITE_DIR%\OnlyFans.py" %%*
echo pause
) > "%BIN_DIR%\onlyfans.bat"

echo Creating "patreon" command...
(
echo @echo off
echo cd /d "%SITE_DIR%"
echo python "%SITE_DIR%\Patreon.py" %%*
echo pause
) > "%BIN_DIR%\patreon.bat"

echo Creating "onlysnap" command...
(
echo @echo off
echo cd /d "%~dp0"
echo python "%~dp0OnlySnap.py" %%*
echo pause
) > "%BIN_DIR%\onlysnap.bat"

REM Check if already in PATH
echo %PATH% | findstr /I /C:"%BIN_DIR%" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Adding to PATH...
    setx PATH "%PATH%;%BIN_DIR%" >nul 2>&1
    echo PATH updated successfully!
) else (
    echo PATH already contains OnlySnap bin folder.
)

echo.
echo ==========================================
echo   DONE! Commands registered:
echo.
echo   onlyfans   - Launch OnlyFans scraper
echo   patreon    - Launch Patreon scraper
echo   onlysnap   - Launch OnlySnap Hub
echo.
echo   Open a NEW terminal to use them.
echo   If you move the folder, run option 4 again.
echo ==========================================
pause
goto menu