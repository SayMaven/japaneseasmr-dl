@echo off
setlocal

set "REFERER=https://japaneseasmr.com"
set "USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
set "DEFAULT_ID=RJ01673437"

:loop
echo.
echo ===================================================
echo   JapaneseASMR Downloader + Cover Art Embedder
echo ===================================================
echo.

set "RJ_ID="
set /p "RJ_ID=Masukkan Kode/Angka RJ (Tekan Enter untuk %DEFAULT_ID%): "
if "%RJ_ID%"=="" set "RJ_ID=%DEFAULT_ID%"

:: Susun URL dan Nama Output Otomatis
set "M3U8_URL=https://v.weeab0o.xyz/%RJ_ID%.m3u8"
set "COVER_URL=https://pic.weeabo0.xyz/%RJ_ID%_img_main.jpg"
set "OUT_NAME=%RJ_ID%.mp3"

echo.
echo ---------------------------------------------------
echo  ID/Kode     : %RJ_ID%
echo  URL M3U8    : %M3U8_URL%
echo  URL Cover   : %COVER_URL%
echo  File Output : %OUT_NAME%
echo ---------------------------------------------------
echo.

echo [1/3] Mendownload cover image...
curl -s -H "Referer: %REFERER%" "%COVER_URL%" -o "temp_cover.jpg"

echo [2/3] Mendownload stream audio (16 parallel connections)...
yt-dlp -N 16 --downloader aria2c --fixup never --add-header "Referer: %REFERER%" --add-header "Origin: %REFERER%" --user-agent "%USER_AGENT%" "https://v.weeab0o.xyz/%RJ_ID%.m3u8" -x --audio-format mp3 -o "temp_audio.%%(ext)s"

if not exist "temp_audio.mp3" (
    echo [INFO] M3U8 tidak ditemukan, mencoba link direct MP3...
    yt-dlp -N 16 --downloader aria2c --fixup never --add-header "Referer: %REFERER%" --add-header "Origin: %REFERER%" --user-agent "%USER_AGENT%" "https://v.weeab0o.xyz/%RJ_ID%.mp3" -x --audio-format mp3 -o "temp_audio.%%(ext)s"
)

if not exist "temp_audio.mp3" (
    echo.
    echo [ERROR] Gagal mendownload audio dari sumber .m3u8 maupun .mp3!
    goto cleanup
)

echo [3/3] Menyematkan thumbnail ke metadata MP3...
ffmpeg -hide_banner -loglevel error -y -i "temp_audio.mp3" -i "temp_cover.jpg" -map 0:a -map 1:v -c copy -id3v2_version 3 -metadata:s:v title="Album cover" -metadata:s:v comment="Cover (front)" "%OUT_NAME%"

if exist "%OUT_NAME%" (
    echo.
    echo ===================================================
    echo   SELESAI! File tersimpan sebagai: %OUT_NAME%
    echo ===================================================
) else (
    echo.
    echo [ERROR] Gagal menyematkan thumbnail!
)

:cleanup
:: Bersihkan file sementara
if exist "temp_cover.jpg" del /f /q "temp_cover.jpg"
if exist "temp_audio.mp3" del /f /q "temp_audio.mp3"
if exist "temp_audio.mp4" del /f /q "temp_audio.mp4"
if exist "temp_audio.temp.mp4" del /f /q "temp_audio.temp.mp4"
if exist "temp_audio.(ext)s.mp3" del /f /q "temp_audio.(ext)s.mp3"

echo.
goto loop