@echo off
setlocal
chcp 65001 >nul
set "APPDIR=%~dp0"
if exist "%APPDIR%AIInspectionReport.exe" goto check_runtime
if not exist "%APPDIR%dist\AIInspectionReport\AIInspectionReport.exe" goto source_only
set "APPDIR=%~dp0dist\AIInspectionReport\"

:check_runtime
if not exist "%APPDIR%_internal\" goto missing_runtime
start "" /D "%APPDIR%" "%APPDIR%AIInspectionReport.exe" --desktop-shortcut
if errorlevel 1 goto launch_failed
exit /b 0

:source_only
echo [실행 파일 없음 / SOURCE_ZIP]
echo GitHub의 Code - Download ZIP은 프로그램 소스 코드입니다.
echo 실행용 배포 ZIP 전체를 풀고 그 안의 이 CMD를 실행해 주세요.
echo 소스에서 직접 빌드하려면 README.md의 소스 실행·빌드를 참고하세요.
pause
exit /b 2

:missing_runtime
echo [필수 폴더 없음 / MISSING_RUNTIME]
echo EXE만 옮기지 말고 실행용 ZIP 전체를 다시 풀어 주세요.
echo AIInspectionReport.exe와 _internal 폴더가 함께 있어야 합니다.
pause
exit /b 3

:launch_failed
echo [실행 실패 / LAUNCH_FAILED]
echo 프로그램을 실행하지 못했습니다. 위 Windows 오류를 확인해 주세요.
pause
exit /b 4
