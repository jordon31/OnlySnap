@echo off
cd /d "%~dp0"

:menu
cls
echo ==========================================
echo      ONLYSNAP DASHBOARD
echo ==========================================
echo 1) Run OnlySnap
echo 2) Auto paste cookie (OnlyFans)
echo 3) Install DRM Tools (FFmpeg, MP4Decrypt, RE)
echo.
set /p choice=Select option (1, 2 or 3): 

if "%choice%"=="1" goto op1
if "%choice%"=="2" goto op2
if "%choice%"=="3" goto op3
goto menu

:op1
python OnlySnap.py
pause
goto menu

:op2
python cookie-onlyfans.py
pause
goto menu

:op3
cls
echo Starting Direct Download from Dropbox...
echo ----------------------------------------

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