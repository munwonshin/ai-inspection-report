@echo off
setlocal
chcp 65001 >nul
set "APPDIR=%~dp0"
if exist "%APPDIR%AIInspectionReport.exe" goto check_runtime
if not exist "%APPDIR%dist\AIInspectionReport\AIInspectionReport.exe" goto source_only
set "APPDIR=%~dp0dist\AIInspectionReport\"

:check_runtime
if not exist "%APPDIR%_internal\" goto missing_runtime
set "AIR_INSTALL_SOURCE=%APPDIR%"
powershell.exe -NoLogo -NoProfile -Command ^
 "$ErrorActionPreference='Stop'; $stage=$null; $stageOwned=$false; try {" ^
 "$source=[IO.Path]::GetFullPath($env:AIR_INSTALL_SOURCE).TrimEnd([IO.Path]::DirectorySeparatorChar); $version='0.4.25';" ^
 "$base=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Programs\AIInspectionReport';" ^
 "$shell=New-Object -ComObject WScript.Shell; $desktop=$shell.SpecialFolders('Desktop');" ^
 "if (-not (Test-Path -LiteralPath $desktop -PathType Container)) { throw '바탕화면 폴더에 접근할 수 없습니다.' };" ^
 "if ($source.StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase)) { $installed=$source } else {" ^
 "New-Item -ItemType Directory -Path $base -Force | Out-Null;" ^
 "$stage=Join-Path $base ('.install-'+[Guid]::NewGuid().ToString('N')); New-Item -ItemType Directory -Path $stage | Out-Null; $stageOwned=$true;" ^
 "Copy-Item -LiteralPath (Join-Path $source 'AIInspectionReport.exe') -Destination $stage;" ^
 "foreach ($dir in @('_internal','licenses')) { $item=Join-Path $source $dir; if (Test-Path -LiteralPath $item -PathType Container) { Copy-Item -LiteralPath $item -Destination $stage -Recurse -Force } };" ^
 "foreach ($name in @('바탕화면 아이콘 만들기.cmd','THIRD_PARTY_NOTICES.md','처음_사용하기.txt')) { $item=Join-Path $source $name; if (Test-Path -LiteralPath $item -PathType Leaf) { Copy-Item -LiteralPath $item -Destination $stage } };" ^
 "$hash=[Security.Cryptography.SHA256]::Create(); try { $original=[Convert]::ToBase64String($hash.ComputeHash([IO.File]::ReadAllBytes((Join-Path $source 'AIInspectionReport.exe')))); $copied=[Convert]::ToBase64String($hash.ComputeHash([IO.File]::ReadAllBytes((Join-Path $stage 'AIInspectionReport.exe')))); if ($original -ne $copied) { throw '실행 파일의 복사 검증에 실패했습니다.' } } finally { $hash.Dispose() };" ^
 "$installed=Join-Path $base $version; $i=2; while (Test-Path -LiteralPath $installed) { $installed=Join-Path $base ($version+' ('+$i+')'); $i++ };" ^
 "[IO.Directory]::Move($stage,$installed); $stage=$null; $stageOwned=$false;" ^
 "};" ^
 "$target=Join-Path $installed 'AIInspectionReport.exe'; $name='AI 현장점검 결과서'; $link=Join-Path $desktop ($name+'.lnk');" ^
 "if (Test-Path -LiteralPath $link) { $ours=$false; try { $old=[IO.Path]::GetFullPath($shell.CreateShortcut($link).TargetPath); $ours=$old.StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase) } catch {}; if (-not $ours) { $link=Join-Path $desktop ($name+' '+$version+'.lnk'); $i=2; while (Test-Path -LiteralPath $link) { $link=Join-Path $desktop ($name+' '+$version+' ('+$i+').lnk'); $i++ } } };" ^
 "$shortcut=$shell.CreateShortcut($link); $shortcut.TargetPath=$target; $shortcut.Arguments=''; $shortcut.WorkingDirectory=$installed; $shortcut.IconLocation=$target+',0'; $shortcut.Description=$name; $shortcut.WindowStyle=1; $shortcut.Save();" ^
 "$check=$shell.CreateShortcut($link); if ($check.TargetPath -ne $target -or $check.Arguments) { throw '바로가기 대상 검증에 실패했습니다.' };" ^
 "Write-Host '바탕화면 아이콘을 만들었습니다. 이 아이콘으로 프로그램을 실행하세요.'; exit 0;" ^
 "} catch { Write-Host ('설치 실패: '+$_.Exception.Message); exit 1 } finally {" ^
 "if ($stageOwned -and $stage -and [IO.Path]::GetFullPath($stage).StartsWith($base+'\',[StringComparison]::OrdinalIgnoreCase) -and [IO.Path]::GetFileName($stage).StartsWith('.install-')) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue };" ^
 "}"
if errorlevel 1 goto install_failed
pause
exit /b 0

:source_only
echo [실행 파일 없음 / SOURCE_ZIP]
echo GitHub의 Code - Download ZIP은 프로그램 소스 코드입니다.
echo README의 Windows 실행용 ZIP을 받아 전체 압축을 풀어 주세요.
pause
exit /b 2

:missing_runtime
echo [필수 폴더 없음 / MISSING_RUNTIME]
echo EXE와 _internal 폴더를 함께 유지해 주세요. ZIP 전체를 다시 풀어 주세요.
pause
exit /b 3

:install_failed
echo [설치 실패 / INSTALL_FAILED]
echo 위 오류를 확인해 주세요. API 설정과 업무 문서는 변경하지 않았습니다.
pause
exit /b 4
