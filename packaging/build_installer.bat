@echo off
setlocal

cd /d "%~dp0.."

if not exist "dist\TranscriptSanitizer\TranscriptSanitizer.exe" (
    call "packaging\build_exe.bat"
)

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo Inno Setup 6 compiler was not found.
    echo Install Inno Setup from https://jrsoftware.org/isinfo.php and run this script again.
    exit /b 1
)

"%ISCC%" "packaging\TranscriptSanitizer.iss"
